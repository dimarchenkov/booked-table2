# Booked Table

Production-ready сервис аренды столов по времени: FastAPI + PostgreSQL + Redis + Celery + SQLAdmin + aiogram. Базовый образ использует Python 3.13 и драйвер PostgreSQL psycopg v3.

## Быстрый старт

```bash
git clone <repo>
cd booked-table2
cp .env.example .env

docker compose build
docker compose up -d
```

Проверка:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status": "ok"}
```

## Сидирование данных

```bash
docker compose exec api python -m app.scripts.seed
```

Создает:
- `schedule_rules`
- `working_hours` (пн-вс 09:00-21:00)
- 3 таблицы

## Админка

- URL: `http://localhost:8000/admin`
- Логин: `ADMIN_EMAIL`
- Пароль: хэш `ADMIN_PASSWORD_HASH` (bcrypt)

Если админка работает за HTTPS через reverse proxy (Angie/Nginx),
обязательно прокидывайте заголовок `X-Forwarded-Proto https`, иначе браузер (например Safari)
может считать форму логина "небезопасной".

### Генерация bcrypt-хэша

```bash
python -m app.scripts.gen_admin_hash
```

Вводите пароль обычным текстом, в ответ получите bcrypt-строку для `ADMIN_PASSWORD_HASH`.

### Group poster

Откройте `http://localhost:8000/admin/group-poster` для текста и ссылки для закрепа.

Если `TELEGRAM_BOT_USERNAME` не задан, страница покажет инструкцию.

## Telegram-бот

Бот запускается отдельным сервисом. Если `TELEGRAM_BOT_TOKEN` не задан, сервис выводит лог `TELEGRAM_BOT_TOKEN missing, bot disabled` и завершает работу без ошибки.

Включение:
1. Укажите `TELEGRAM_BOT_TOKEN`.
2. Опционально укажите `TELEGRAM_BOT_USERNAME`.

Групповая команда для админов:
- `/post_booking` (только группы и `ADMIN_TG_IDS`)

Deep-link:
- `https://t.me/<bot_username>?start=from_group`

## API

- `GET /health`
- `GET /tables`
- `GET /availability?table_id=&date=YYYY-MM-DD`
- `POST /bookings/hold`
- `GET /bookings/{id}`
- `POST /bookings/{id}/cancel`
- `POST /bookings/{id}/confirm` (guarded with `ADMIN_API_KEY` if `DEBUG=false`)
- `POST /webhooks/tbank`

Пример создания HOLD:

```bash
curl -X POST http://localhost:8000/bookings/hold \
  -H "Content-Type: application/json" \
  -d '{"table_id":1,"start_at":"2024-01-01T10:00:00Z","end_at":"2024-01-01T11:00:00Z","tg_user_id":"123"}'
```

## Интеграции

По умолчанию включены заглушки:
- `StubPaymentProvider`
- `StubCalendarProvider`

Включение TBank:
- `TBANK_ENABLED=true`
- `TBANK_TOKEN`, `TBANK_TERMINAL_KEY`

Включение календаря:
- `CALENDAR_ENABLED=true`
- `CALENDAR_BASE_URL`, `CALENDAR_USERNAME`, `CALENDAR_PASSWORD`

## Тесты

```bash
pytest
```
