# Client Base MVP — инструкция

## 1. Локальный запуск (проверить, что всё работает)

```bash
cd irina-crm
python -m venv venv
source venv/bin/activate  # на Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Открой http://localhost:8000 — увидишь пустую базу (это нормально, локально
используется sqlite-файл `demo.db`, создаётся сам).

Проверить API: http://localhost:8000/docs — там можно вручную добавить
2-3 тестовых клиентов через `POST /api/clients`, чтобы увидеть список живьём.

## 2. Подключение Supabase (для прод-версии)

1. В Supabase: Settings → Database → Connection string → выбрать режим
   **Transaction pooler** (важно, обычный `direct connection` не выдержит
   несколько запросов от разных клиентов Render).
2. Скопировать строку, заменить `[YOUR-PASSWORD]` на реальный пароль.
3. В Render (или .env локально) задать переменную окружения:
   ```
   DATABASE_URL=postgresql+psycopg://postgres.xxxx:[PASSWORD]@aws-...pooler.supabase.com:6543/postgres
   ```
   Префикс `+psycopg` обязателен — указывает SQLAlchemy использовать драйвер
   psycopg3 (он ставится через `psycopg[binary]` в requirements.txt и не
   требует компилятора, в отличие от старого psycopg2).
   ```
   ```
4. Перезапустить сервис — таблица `client` создастся автоматически при старте.

## 3. Деплой на Render (бесплатно)

1. Залить эту папку в GitHub-репозиторий.
2. render.com → New → Web Service → подключить репозиторий.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Добавить переменную окружения `DATABASE_URL` (из шага 2).
6. Деплой — получишь ссылку вида `https://irina-crm.onrender.com`.

## 4. Настройка Telegram-бота

1. У @BotFather: `/newbot` → получить токен.
2. `/setmenubutton` → выбрать бота → указать URL: ссылку из Render.
   Это добавит кнопку в интерфейсе бота, которая открывает WebApp.
3. (Позже, не для демо) — отдельный процесс на aiogram, который раз в день
   дёргает `/api/cron/check-sleeping` и шлёт мастеру сообщение с кнопкой
   «Открыть базу», если `sleeping_count > 0`.

## 5. Cron-job.org — держим сервис живым и проверяем спящих клиентов

Бесплатный Render засыпает после 15 минут простоя. Настраиваем два cron-задания:

- Каждые 10 минут → GET `https://irina-crm.onrender.com/api/ping` (не даёт уснуть)
- Раз в день в 10:00 → GET `https://irina-crm.onrender.com/api/cron/check-sleeping`
  (на этом шаге позже подвяжем отправку сообщения в Telegram)

## Что демонстрировать в первую очередь

1. Открыть WebApp — сразу видно красный/жёлтый баннер вверху.
2. Список клиентов с цветными точками — дать ей самой найти "забытых".
3. Нажать «+1 Сеанс» на одной карточке — показать, как мгновенно всё обновляется.
4. Нажать «WhatsApp» — показать, что сообщение уже готово, осталось отправить.
5. Добавить нового клиента через «Выбрать контакт» — показать, что не нужно
   вручную вбивать номер.
