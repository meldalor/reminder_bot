# Шпаргалка разработчика

## Быстрый старт

```bash
# 1. Установка
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Настройка
# Отредактируйте .env и укажите BOT_TOKEN

# 3. Запуск
python main.py
```

## Структура проекта - где что находится

```
bot/
├── config.py              → Все настройки и константы
├── states.py              → FSM состояния для диалогов
├── database/
│   └── db.py             → Работа с SQLite (создание, запросы)
├── handlers/
│   ├── start.py          → /start команда
│   ├── timezone.py       → Выбор часового пояса
│   └── reminders.py      → Создание/удаление напоминаний
├── keyboards/
│   └── main_keyboard.py  → Все клавиатуры и кнопки
├── services/
│   └── scheduler.py      → Планировщик отправки напоминаний
└── utils/
    └── datetime_utils.py → Утилиты для работы с датой/временем
```

## Как добавить новую функцию

### 1. Новый обработчик команды

```python
# bot/handlers/my_feature.py
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command(commands=['mycommand']))
async def my_handler(message: types.Message):
    await message.answer("Hello from my feature!")
```

```python
# main.py
from bot.handlers import my_feature_router
dp.include_router(my_feature_router)
```

### 2. Добавить настройку в config

```python
# bot/config.py
MY_NEW_SETTING = os.getenv("MY_SETTING", "default_value")
```

```env
# .env
MY_SETTING=my_value
```

### 3. Добавить функцию в БД

```python
# bot/database/db.py
async def my_database_function(param):
    async with aiosqlite.connect(DB_PATH) as db:
        # ваш SQL код
        pass
```

### 4. Создать новую клавиатуру

```python
# bot/keyboards/main_keyboard.py
from bot.keyboards import create_inline_keyboard

my_keyboard = create_inline_keyboard([
    [("Кнопка 1", "callback_1"), ("Кнопка 2", "callback_2")],
    [("Кнопка 3", "callback_3")]
])
```

## Полезные команды

```bash
# Запуск бота
python main.py

# Установка новой зависимости
pip install package_name
pip freeze > requirements.txt

# Проверка кода (если установлен flake8)
flake8 bot/

# Форматирование кода (если установлен black)
black bot/

# Просмотр логов
tail -f logs/bot.log  # Linux/Mac
type logs\bot.log     # Windows
```

## Отладка

### Включить подробное логирование

```python
# main.py
logging.basicConfig(
    level=logging.DEBUG,  # было INFO
    ...
)
```

### Проверить подключение к БД

```bash
sqlite3 data/reminders.db
.tables
.schema reminders
SELECT * FROM reminders;
.quit
```

### Типичные ошибки

**"BOT_TOKEN is not set"**
- Проверьте файл `.env`
- Убедитесь, что `python-dotenv` установлен

**"No module named 'bot'"**
- Запускайте из корня проекта: `python main.py`
- Не из папки bot: `cd ..`

**"Database is locked"**
- Закройте другие соединения к БД
- Перезапустите бота

## Git команды

```bash
# Первый коммит
git init
git add .
git commit -m "Initial commit: structured bot"

# Создать репозиторий на GitHub и подключить
git remote add origin https://github.com/username/reminder_bot.git
git branch -M main
git push -u origin main

# Работа с ветками
git checkout -b feature/new-feature
git add .
git commit -m "feat: добавлена новая функция"
git push origin feature/new-feature
```

## Полезные сниппеты

### Отправить сообщение с инлайн кнопками

```python
from bot.keyboards import create_inline_keyboard

keyboard = create_inline_keyboard([
    [("Кнопка 1", "data_1")],
    [("Кнопка 2", "data_2")]
])

await message.answer("Выберите:", reply_markup=keyboard)
```

### Обработать callback

```python
@router.callback_query(lambda c: c.data == "data_1")
async def process_callback(callback: types.CallbackQuery):
    await callback.answer("Вы нажали кнопку 1")
    await callback.message.edit_text("Новый текст")
```

### Работа с FSM

```python
# Установить состояние
await state.set_state(MyStates.waiting_for_input)

# Сохранить данные
await state.update_data(key="value")

# Получить данные
data = await state.get_data()
value = data.get("key")

# Очистить состояние
await state.clear()
```

### Запросы к БД

```python
import aiosqlite
from bot.config import DB_PATH

async with aiosqlite.connect(DB_PATH) as db:
    # SELECT
    async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
        result = await cursor.fetchone()

    # INSERT
    await db.execute("INSERT INTO table (col) VALUES (?)", (value,))
    await db.commit()

    # UPDATE
    await db.execute("UPDATE table SET col = ? WHERE id = ?", (new_value, id))
    await db.commit()

    # DELETE
    await db.execute("DELETE FROM table WHERE id = ?", (id,))
    await db.commit()
```

## Переменные окружения (.env)

```env
# Обязательные
BOT_TOKEN=your_telegram_bot_token

# Опциональные (есть значения по умолчанию)
CHECK_INTERVAL_SECONDS=60           # Как часто проверять напоминания
REMINDER_OFFSET_MINUTES=15          # Интервал повторных напоминаний
TEMP_REMINDER_EXPIRATION_HOURS=1    # Время жизни временных напоминаний
```

## Тестирование

```bash
# Ручное тестирование
1. Запустите бота: python main.py
2. Найдите бота в Telegram
3. /start
4. Создайте напоминание
5. Проверьте список: "Мои уведомления"
6. Удалите: /delete<ID>
```

## FAQ

**Q: Как изменить часовые пояса?**
A: Редактируйте `CITY_TIMEZONES` в `bot/config.py`

**Q: Как изменить формат даты?**
A: Измените `DATE_FORMAT`, `FULL_DATE_FORMAT` в `bot/config.py`

**Q: Где хранятся данные?**
A: SQLite база в `data/reminders.db`

**Q: Как добавить логи в файл?**
A: Добавьте FileHandler в `main.py`:
```python
import logging
file_handler = logging.FileHandler('logs/bot.log')
logging.getLogger().addHandler(file_handler)
```

## Полезные ссылки

- [aiogram документация](https://docs.aiogram.dev/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [SQLite](https://www.sqlite.org/docs.html)
- [APScheduler](https://apscheduler.readthedocs.io/)

---

**Всегда смотрите README.md для полной документации!**
