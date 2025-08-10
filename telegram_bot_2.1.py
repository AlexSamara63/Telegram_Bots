import datetime
import logging
from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
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


# Проверяем, идет ли сейчас прием и возвращаем оставшееся время
def get_work_status():
    now = datetime.datetime.now()
    schedule = get_schedule_for_date(now)

    # Если выходной - приема нет
    if schedule == "выходной":
        return {"status": False, "remaining": None}

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

    if start_time <= current_time < end_time:
        # Рассчитываем оставшееся время
        end_datetime = datetime.datetime.combine(now.date(), end_time)
        remaining = end_datetime - now
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes = remainder // 60
        return {
            "status": True,
            "remaining": f"{hours:02d}:{minutes:02d}"
        }
    return {"status": False, "remaining": None}


# Форматируем расписание для дня с указанием даты
def format_schedule_for_date(target_date):
    # Русские названия дней недели
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[target_date.weekday()]

    # Форматируем дату: день.месяц
    date_str = target_date.strftime("%d.%m")

    # Получаем расписание
    schedule = get_schedule_for_date(target_date)

    return f"{day_name} ({date_str}): {schedule}"


# Генерируем расписание на текущую неделю, начиная с текущего дня
def get_current_week_schedule():
    today = datetime.date.today()
    schedule_lines = []

    # Добавляем дни от сегодня до конца недели (воскресенья)
    for i in range(7 - today.weekday()):
        current_date = today + datetime.timedelta(days=i)
        schedule_lines.append(format_schedule_for_date(current_date))

    return "\n".join(schedule_lines)


# Генерируем расписание на следующую неделю
def get_next_week_schedule():
    today = datetime.date.today()
    # Находим следующий понедельник
    next_monday = today + datetime.timedelta(days=(7 - today.weekday()))

    schedule_lines = []
    for i in range(7):
        current_date = next_monday + datetime.timedelta(days=i)
        schedule_lines.append(format_schedule_for_date(current_date))
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
            [KeyboardButton("Расписание на следующую неделю")]
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


# Обработчик кнопки "Позвонить"
async def call_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Исправленная ссылка для звонка через Telegram
    phone_number = "+79277985185"
    call_link = f"tg://call?phone={phone_number}"  # Изменено с tel: на tg://call?phone=

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🕺 Нажмите для звонка", url=call_link)
    ]])

    await query.edit_message_text(
        text="Телефонный звонок инициирован:\n+7 (927) 798-51-85",
        reply_markup=keyboard
    )


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

            # Получаем расписание на сегодня
            today = datetime.datetime.now()
            schedule_msg = format_schedule_for_date(today)

            # Проверяем статус работы
            work_status = get_work_status()

            # Формируем сообщение в зависимости от статуса
            if work_status["status"]:
                # Идет прием - добавляем информацию об оставшемся времени
                message = (
                    f"❌ Сейчас идет прием\n"
                    f"До конца приема: {work_status['remaining']}\n\n"
                    f"{schedule_msg}"
                )
                await update.message.reply_text(message)
            else:
                # Приема нет - добавляем кнопку звонка (включая выходные)
                # Определяем тип сообщения для выходных/рабочих дней
                schedule = get_schedule_for_date(today)
                status_msg = "✅ Сейчас можно позвонить"

                if schedule == "выходной":
                    status_msg = "ℹ️ Сегодня:"

                message = (
                    f"{status_msg}\n\n"
                    f"{schedule_msg}"
                )
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📞 Позвонить", callback_data="call")
                ]])
                await update.message.reply_text(
                    message,
                    reply_markup=keyboard
                )

        elif text == "Расписание на завтра":
            logger.info("Обработка 'Расписание на завтра'")
            tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
            schedule_msg = format_schedule_for_date(tomorrow)
            await update.message.reply_text(schedule_msg)

        elif text == "Расписание на неделю":
            logger.info("Обработка 'Расписание на неделю'")
            weekly_schedule = get_current_week_schedule()
            await update.message.reply_text(weekly_schedule)

        elif text == "Расписание на следующую неделю":
            logger.info("Обработка 'Расписание на следующую неделю'")
            next_week_schedule = get_next_week_schedule()
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
        application.add_handler(CallbackQueryHandler(call_button, pattern="^call$"))

        logger.info("Запуск polling...")
        application.run_polling()
        logger.info("Бот запущен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")


if __name__ == '__main__':
    main()