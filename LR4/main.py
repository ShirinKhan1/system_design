from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from pymongo import MongoClient
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import json

app = FastAPI()

# Конфигурация для JWT и базы данных
SECRET_KEY = "secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:secret@db:5432/postgres"
MONGO_DATABASE_URL = "mongodb://mongodb:27017/"

# Подключение к MongoDB
client = MongoClient(MONGO_DATABASE_URL)

# Настройки по MongoDB
db_mongo = client['arch']

# Выбор коллекции
collection = db_mongo['orders']

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
class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    hashed_password: str
    age: Optional[int] = None

    class Config:
        orm_mode = True  # Включаем поддержку преобразования ORM объектов в Pydantic модели

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
    to_encode.update({"exp": expire.total_seconds()})  # Преобразуем в секунды
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db, username: str):
    return db.query(UserDB).filter(UserDB.username == username).first()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: SessionLocal = Depends(get_db)):
    user = get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# User registration
@app.post("/register", response_model=Token)
async def register_user(user: User, db: SessionLocal = Depends(get_db)):
    hashed_password = get_password_hash(user.hashed_password)
    db_user = UserDB(username=user.username, email=user.email, hashed_password=hashed_password, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

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

@app.get("/packages")
async def read_packages(db: SessionLocal = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return db.query(PackageDB).all()

@app.get("/users/{username}", response_model=User)
async def get_user_by_username(username: str, db: SessionLocal = Depends(get_db), token: str = Depends(oauth2_scheme)):
    db_user = db.query(UserDB).filter(UserDB.username == username).first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Отладочное сообщение
    print(db_user)  # Посмотрите, что приходит из базы данных
    
    return db_user

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
