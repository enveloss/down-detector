# 🤖 Down Detector Bot

Telegram бот для мониторинга доступности сайтов с поддержкой прокси-серверов и автоматическими уведомлениями.

## 📋 Возможности

### 🌐 Мониторинг сайтов
- **Добавление/удаление сайтов** для мониторинга
- **Автоматическая проверка** доступности сайтов
- **Измерение времени отклика** с визуальными индикаторами скорости
- **Отслеживание HTTP статус-кодов**
- **История проверок** с временными метками

### 🌍 Поддержка прокси
- **Мультипрокси** - использование нескольких прокси-серверов
- **Географическое распределение** - прокси по странам
- **Автоматическая ротация** - случайный выбор прокси для каждой проверки
- **Тестирование прокси** - проверка работоспособности
- **Статистика использования** - успешные/неуспешные запросы

### 📊 Уведомления и отчеты
- **Telegram уведомления** о недоступности сайтов
- **Детальные отчеты** с информацией о времени отклика
- **Визуальные индикаторы** статуса (эмодзи)
- **Команды для получения статуса** в реальном времени

## 🚀 Установка и запуск

### Требования
- Python 3.12+
- Docker (опционально)

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd down-detector
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
Создайте файл `.env` в корневой директории:

```env
# Telegram Bot Token (получите у @BotFather)
BOT_TOKEN=your_bot_token_here

# ID чата для отправки отчетов (опционально)
REPORT_CHAT_ID=your_chat_id_here

# Список ID администраторов (через запятую)
ADMINS=123456789,987654321

# Режим работы (development/production)
MODE=production
```

### 4. Запуск

#### Обычный запуск
```bash
python run.py
```

#### Запуск через Docker
```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```