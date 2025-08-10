import datetime
import logging
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Определяем, является ли день четным
def is_even_day(date):
    return date.day % 2 == 0


# Получаем расписание для конкретной даты
def get_schedule_for_date(date):
    weekday = date.weekday()

    # Пятница - особое расписание
    if weekday == 4:  # Пятница
        return "12.00-15.30"

    # Для остальных рабочих дней
    if weekday < 5:  # Понедельник-четверг
        if is_even_day(date):
            return "8.00-11.30"
        else:
            return "16.00-19.30"

    # Выходные (суббота и воскресенье)
    return "выходной"


# Проверяем, идет ли сейчас прием
def is_work_time_now():
    now = datetime.datetime.now()
    schedule = get_schedule_for_date(now)

    # Если выходной - приема нет
    if schedule == "выходной":
        return False

    # Парсим время начала и окончания
    start_str, end_str = schedule.split('-')

    # Преобразуем строки во время
    def parse_time(time_str):
        parts = time_str.replace('.', ':').split(':')
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return datetime.time(hours, minutes)

    start_time = parse_time(start_str)
    end_time = parse_time(end_str)
    current_time = now.time()

    return start_time <= current_time < end_time


# Форматируем расписание для дня с указанием даты
def get_formatted_schedule(day_offset=0):
    target_date = datetime.datetime.now() + datetime.timedelta(days=day_offset)

    # Русские названия дней недели
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[target_date.weekday()]

    # Форматируем дату: день.месяц
    date_str = target_date.strftime("%d.%m")

    # Получаем расписание
    schedule = get_schedule_for_date(target_date)

    return f"{day_name} ({date_str}): {schedule}"


# Генерируем расписание на неделю
def get_weekly_schedule(start_offset=0, days_count=7):
    schedule_lines = []
    for i in range(start_offset, start_offset + days_count):
        schedule_lines.append(get_formatted_schedule(i))
    return "\n".join(schedule_lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Обработка /start от пользователя: {update.effective_user.id}")

        # Приветственное сообщение с эмодзи
        welcome_message = (
            "👋 Привет! Я семейный бот.\n\n"
            "Сейчас могу помочь с расписанием работы Шириной Натальи Владимировны.\n\n"
            "📅 Просто выбери нужную опцию ниже:\n\n"
            "Если у тебя есть интересные предложения или вопросы - пиши @aoshirin 😊"
        )

        # Клавиатура с кнопками
        keyboard = [
            [KeyboardButton("Приветствие")],
            [KeyboardButton("Расписание на сегодня")],
            [KeyboardButton("Расписание на завтра")],
            [KeyboardButton("Расписание на неделю")],
            [KeyboardButton("Расписание на следующую неделю")]  # Новая кнопка
        ]

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )

        # Отправляем приветственное сообщение с клавиатурой
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup
        )

        logger.info("Приветственное сообщение с клавиатурой отправлено")
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Получено сообщение: {update.message.text}")
        text = update.message.text

        # Обработка кнопки "Приветствие"
        if text == "Приветствие":
            logger.info("Обработка кнопки 'Приветствие'")
            await start(update, context)
            return

        if text == "Расписание на сегодня":
            logger.info("Обработка 'Расписание на сегодня'")

            # Проверяем, идет ли сейчас прием
            if is_work_time_now():
                status_msg = "❌ Идет прием"
            else:
                status_msg = "✅ Приема нет, можно позвонить"

            # Получаем расписание на сегодня с датой
            schedule_msg = get_formatted_schedule(0)

            # Формируем полное сообщение
            full_msg = f"{status_msg}\n\nРасписание на сегодня:\n{schedule_msg}"
            await update.message.reply_text(full_msg)

        elif text == "Расписание на завтра":
            logger.info("Обработка 'Расписание на завтра'")
            schedule_msg = get_formatted_schedule(1)
            await update.message.reply_text(schedule_msg)

        elif text == "Расписание на неделю":
            logger.info("Обработка 'Расписание на неделю'")
            # Расписание на 7 дней начиная с сегодня
            weekly_schedule = get_weekly_schedule(0, 7)
            await update.message.reply_text(weekly_schedule)

        elif text == "Расписание на следующую неделю":
            logger.info("Обработка 'Расписание на следующую неделю'")
            # Расписание на 7 дней начиная со следующего понедельника
            next_week_schedule = get_weekly_schedule(7, 7)
            await update.message.reply_text(next_week_schedule)

        # Обработка команды /start через текстовое сообщение
        elif text == "/start":
            await start(update, context)

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")


def main():
    try:
        logger.info("Запуск бота...")
        application = Application.builder().token(config.TOKEN).build()

        logger.info("Добавление обработчиков...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Запуск polling...")
        application.run_polling()
        logger.info("Бот запущен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")


if __name__ == '__main__':
    main()