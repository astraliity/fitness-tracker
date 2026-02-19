# Fitness Tracker API

REST API для отслеживания тренировок, прогресса и планирования занятий.

## Стек технологий

- Python 3.12
- Django 6.0 + Django REST Framework
- PostgreSQL (Docker) / SQLite (локально)
- JWT-аутентификация (SimpleJWT)
- Docker + Docker Compose

## Возможности

- Регистрация и аутентификация пользователей (JWT)
- CRUD для упражнений (общие + пользовательские)
- Ведение тренировок с подходами (вес, повторения, RIR)
- Планирование тренировок с расписанием
- Календарь (выполненные + запланированные)
- Уведомления о предстоящих тренировках
- Аналитика: тоннаж, максимальный вес, личные рекорды

## Быстрый старт

### Docker (рекомендуется)

```bash
git clone https://github.com/astraliity/fitness-tracker.git
cd fitness-tracker
docker compose up --build
```

API доступен на `http://localhost:8000/api/`

### Локально

```bash
git clone https://github.com/astraliity/fitness-tracker.git
cd fitness-tracker

python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API-эндпоинты

### Аутентификация

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/auth/register/` | Регистрация нового пользователя |
| POST | `/api/auth/token/` | Получение JWT-токена (login) |
| POST | `/api/auth/token/refresh/` | Обновление access-токена |

### Упражнения

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/exercises/` | Список упражнений (общие + свои) |
| POST | `/api/exercises/` | Создать пользовательское упражнение |
| GET | `/api/exercises/{id}/` | Детали упражнения |
| PUT | `/api/exercises/{id}/` | Обновить упражнение |
| DELETE | `/api/exercises/{id}/` | Удалить упражнение |

### Тренировки

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/workouts/` | Список тренировок (краткий формат) |
| POST | `/api/workouts/` | Начать новую тренировку |
| GET | `/api/workouts/{id}/` | Детали тренировки (подходы сгруппированы по упражнениям) |
| POST | `/api/workouts/{id}/finish/` | Завершить тренировку |
| DELETE | `/api/workouts/{id}/` | Удалить тренировку |

### Подходы

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/sets/` | Список подходов |
| POST | `/api/sets/` | Добавить подход в тренировку |
| PUT | `/api/sets/{id}/` | Обновить подход |
| DELETE | `/api/sets/{id}/` | Удалить подход |

### Расписание

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/schedule/` | Список запланированных тренировок |
| POST | `/api/schedule/` | Запланировать тренировку |
| POST | `/api/schedule/{id}/start/` | Начать тренировку из расписания |
| POST | `/api/schedule/{id}/complete/` | Отметить как выполненную |

### Календарь и уведомления

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/calendar/?start=2026-02-01&end=2026-02-28` | Календарь за период |
| GET | `/api/notifications/upcoming/` | Тренировки на ближайшие 24 часа |

### Аналитика

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/analytics/volume/?days=30` | Тоннаж по дням |
| GET | `/api/analytics/max/?exercise_id=3&days=90` | Прогресс максимального веса |
| GET | `/api/analytics/records/` | Личные рекорды по упражнениям |

## Примеры запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "athlete", "password": "securepass123"}'
```

### Получение токена

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "athlete", "password": "securepass123"}'
```

### Создание тренировки

```bash
curl -X POST http://localhost:8000/api/workouts/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"note": "Грудь + трицепс"}'
```

### Добавление подхода

```bash
curl -X POST http://localhost:8000/api/sets/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"workout": 1, "exercise": 1, "weight": 80, "reps": 10, "rir": 2}'
```

## Структура проекта

```
fitness-tracker/
├── config/                # Настройки Django-проекта
│   ├── settings.py        # Конфигурация (БД, JWT, DRF)
│   └── urls.py            # Корневые URL-маршруты
├── workouts/              # Основное приложение
│   ├── models.py          # Exercise, Workout, WorkoutSet, ScheduledWorkout
│   ├── views.py           # ViewSets + APIViews (аналитика, календарь)
│   ├── serializers.py     # Сериализаторы (list/detail для тренировок)
│   ├── urls.py            # Router + кастомные URL
│   └── migrations/        # 4 миграции (модели + данные)
├── users/                 # Аутентификация
│   ├── views.py           # RegisterView (CreateAPIView)
│   └── serializers.py     # RegisterSerializer, UserSerializer
├── Dockerfile             # Python 3.12-slim
├── docker-compose.yml     # PostgreSQL 16 + Django
├── requirements.txt       # Зависимости
└── .gitignore
```

## Модели данных

```
Exercise (справочник упражнений)
├── name, muscle_group (13 групп), description
├── is_custom (общее / пользовательское)
└── user (FK → User, null для общих)

Workout (тренировочная сессия)
├── user (FK → User)
├── start_time, end_time
├── status (STARTED / FINISHED)
└── note

WorkoutSet (подход)
├── workout (FK → Workout)
├── exercise (FK → Exercise)
├── weight, reps, rir
└── created_at

ScheduledWorkout (план)
├── user (FK → User)
├── date, time, title
├── exercises (M2M → Exercise)
├── is_completed
├── workout (OneToOne → Workout)
└── notify_before (минут)
```
