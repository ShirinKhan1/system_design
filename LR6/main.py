from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.context import CryptContext
from jose import jwt, JWTError
from pymongo import MongoClient
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient
import redis
import datetime
import time
import json

app = FastAPI()

# Конфигурация для JWT и базы данных
SECRET_KEY = "secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:secret@db:5432/postgres"
MONGO_DATABASE_URL = "mongodb://mongo:27017"
REDIS_HOST = "redis"
REDIS_PORT = 6379

# Подключение к Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Подключение к MongoDB
client = MongoClient(MONGO_DATABASE_URL)
db_mongo = client['arch']
collection = db_mongo['orders']

KAFKA_BROKER = "kafka:9092"

conf = {
    'bootstrap.servers': KAFKA_BROKER  # Адрес Kafka брокера
}

producer = Producer(**conf)

# Инициализация SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Конфигурация для хеширования пароля
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# SQLAlchemy модели
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    age = Column(Integer, nullable=True)

    packages = relationship("PackageDB", back_populates="user")

class PackageDB(Base):
    __tablename__ = "packages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    height = Column(Float)
    width = Column(Float)
    long = Column(Float)
    weight = Column(Float)

    user = relationship("UserDB", back_populates="packages")

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Pydantic схемы
class UserCreate(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    hashed_password: str
    age: Optional[int] = None

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    hashed_password: str
    age: Optional[int] = None

    class Config:
        orm_mode = True

class Package(BaseModel):
    id: Optional[int] = None
    user_id: int
    height: float
    width: float
    long: float
    weight: float

    class Config:
        orm_mode = True  # Включаем поддержку преобразования ORM объектов в Pydantic модели

class Orders(BaseModel):
    id: Optional[int] = None
    user_id: int
    package_id: float
    address_from: str
    address_to: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
# Утилиты
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta if expires_delta else timedelta(minutes=15)
    to_encode.update({"exp": expire.timestamp()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_from_db(db, username: str):
    return db.query(UserDB).filter(UserDB.username == username).first()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для работы с кешем Redis
def get_user_from_cache(username: str):
    user_data = redis_client.get(username)
    if user_data:
        return json.loads(user_data)
    return None

def set_user_in_cache(username: str, user: dict, expire: int = 3600):
    redis_client.set(username, json.dumps(user), ex=expire)

@app.post("/register", response_model=UserCreate)
async def register_user(user: UserCreate, db: SessionLocal = Depends(get_db)):
    hashed_password = get_password_hash(user.hashed_password)
    db_user = UserDB(username=user.username, email=user.email, hashed_password=hashed_password, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    user_data = UserCreate.from_orm(db_user)
    set_user_in_cache(user.username, user_data.dict())

    kafka_message = {
        "username": user_data.username,
        "timestamp": str(datetime.datetime.now().isoformat())
    }

    producer.produce(
            "created user",  # Укажите ваш топик
            key=kafka_message["username"].encode("utf-8"),
            value=json.dumps(kafka_message).encode("utf-8")
        )
    producer.flush()
    return user_data


# CRUD для посылок
@app.post("/packages", response_model=Package)
async def create_package(package: Package, db: SessionLocal = Depends(get_db), token: str = Depends(oauth2_scheme)):
    db_package = PackageDB(
        user_id=package.user_id,
        height=package.height,
        width=package.width,
        long=package.long,
        weight=package.weight
    )
    db.add(db_package)
    db.commit()
    db.refresh(db_package)
    return db_package

@app.get("/users")
async def read_packages(db: SessionLocal = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return db.query(UserDB).all()

# CRUD операции
@app.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str, db: SessionLocal = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # Проверяем кеш
    user_data = get_user_from_cache(username)
    if user_data:
        print('Из кэша!!!')
        return user_data

    # Если в кеше нет, то читаем из базы
    db_user = get_user_from_db(db, username)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = UserResponse.from_orm(db_user)

    # Сохраняем в кеш
    set_user_in_cache(username, user.dict())

    return user

@app.get("/packages")
async def read_packages(db: SessionLocal = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return db.query(PackageDB).all()

@app.post("/orders/", response_model=Orders)
def create_user(order: Orders):
    insert_result = collection.insert_one(order.__dict__)
    print(f"Order inserted with id: {insert_result.inserted_id}")
    return order

@app.get("/orders/", response_model=list[Orders])
def get_all_users():
    result = collection.find() 
    # users = db.query(User).all()
    orders = [Orders(**doc) for doc in result]
    return orders