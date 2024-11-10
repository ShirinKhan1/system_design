# Project Management Service

Этот проект представляет собой REST API для управления проектами и задачами с использованием FastAPI и PostgreSQL. API поддерживает управление пользователями, проектами и задачами с использованием аутентификации JWT.

## Требования

Перед началом работы убедитесь, что у вас установлены Docker и Docker Compose.

## Структура проекта

Проект содержит следующие файлы:
- **Dockerfile**: Инструкции для сборки образа приложения.
- **docker-compose.yml**: Настройка для запуска контейнеров приложения и базы данных PostgreSQL.
- **wait-for-postgres.sh**: Скрипт ожидания готовности базы данных перед запуском приложения.
- **main.py**: Основной файл FastAPI приложения.
- **requirements.txt**: Файл с зависимостями Python для FastAPI приложения.

## Установка и запуск

1. Клонируйте репозиторий и перейдите в директорию проекта:
   git clone https://github.com/chaous/systemdesignlab1.git && cd systemdesignlab1/lab3

2. Запустите контейнеры:
   docker-compose down -v && docker-compose up --build

   После запуска приложение будет доступно по адресу [http://localhost:8000](http://localhost:8000).

## Доступные API-эндпоинты

После запуска приложения вы можете использовать следующие эндпоинты для взаимодействия с API:

- **Создание пользователя**: `POST /users/`
- **Поиск пользователя по логину**: `GET /users/{username}`
- **Создание проекта**: `POST /projects/`
- **Поиск проекта по имени**: `GET /projects/?name={name}`
- **Создание задачи в проекте**: `POST /tasks/`
- **Получение всех задач в проекте**: `GET /projects/{project_id}/tasks`

## Пример использования с помощью cURL

- **Создание пользователя**:
   curl -X POST "http://localhost:8000/users/" -H "Content-Type: application/json" -d '{"username": "user1", "password": "password1"}'

- **Получение информации о пользователе**:
   curl -X GET "http://localhost:8000/users/user1"

- **Создание проекта**:
   curl -X POST "http://localhost:8000/projects/" -H "Content-Type: application/json" -d '{"name": "Project A", "description": "Description of Project A"}'

- **Получение информации о проекте по имени**:
   curl -X GET "http://localhost:8000/projects/?name=Project%20A"

- **Создание задачи в проекте**:
   curl -X POST "http://localhost:8000/tasks/" -H "Content-Type: application/json" -d '{"title": "Task 1", "description": "First task", "project_id": 1}'

- **Получение всех задач в проекте**:
   curl -X GET "http://localhost:8000/projects/1/tasks"

## Завершение работы

Для остановки контейнеров и удаления томов используйте команду:
docker-compose down -v

