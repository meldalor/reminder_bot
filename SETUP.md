# Быстрая настройка и запуск

## 1. Установка зависимостей

```bash
# Создайте виртуальное окружение
python -m venv venv

# Активируйте его
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

## 2. Настройка конфигурации

1. Откройте файл `.env`
2. Замените `your_bot_token_here` на ваш токен от [@BotFather](https://t.me/botfather)

```env
BOT_TOKEN=5983969823:AAGEzp9i5iu6T3ZlgvEGXhyxx6bKni9V6bo
```

## 3. Запуск бота

### Windows:
```bash
start.bat
```

### Linux/Mac:
```bash
python main.py
```

## 4. Проверка работы

1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Выберите часовой пояс
4. Попробуйте создать напоминание через кнопку `+`

## Возможные проблемы

### "BOT_TOKEN is not set"
- Проверьте, что файл `.env` существует
- Убедитесь, что токен указан правильно
- Перезапустите бота

### "Module not found"
```bash
pip install -r requirements.txt
```

### База данных не создается
- Проверьте права доступа к папке `data/`
- Убедитесь, что папка существует

## Структура проекта

```
reminder_bot/
├── bot/                      # Основной пакет бота
│   ├── config.py            # Конфигурация
│   ├── states.py            # FSM состояния
│   ├── database/            # Работа с БД
│   ├── handlers/            # Обработчики команд
│   ├── keyboards/           # Клавиатуры
│   ├── services/            # Бизнес-логика
│   └── utils/               # Утилиты
├── data/                    # База данных SQLite
├── logs/                    # Логи (создается автоматически)
├── main.py                  # Точка входа
├── .env                     # Конфигурация (не в git)
├── requirements.txt         # Зависимости
└── README.md               # Документация
```

## Следующие шаги

1. Прочитайте [README.md](README.md) для полной документации
2. Изучите [CONTRIBUTING.md](CONTRIBUTING.md) если хотите развивать проект
3. Настройте бота под свои нужды в `bot/config.py`

---

Если возникли проблемы, создайте Issue на GitHub!
