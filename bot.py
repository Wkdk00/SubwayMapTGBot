import logging
from typing import Dict
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, CallbackQueryHandler
import requests

from config import CONFIG

BOT_TOKEN = "7446284006:AAGoq3Lh-aIw__XuQ4hNuaFuLD6Z220I2xo"
API_URL = "http://localhost:8000"

SELECTING_ACTION, SELECTING_LINE, SELECTING_STATION, SELECTING_END_STATION = range(4)

user_cities: Dict[int, str] = {}
user_data_cache: Dict[int, Dict] = {}

CITY_LINES = {
    "nsk": {
        "Красная линия": ["Заельцовская", "Гагаринская", "Красный проспект", "Площадь Ленина","Октябрьская", "Речной вокзал", "Спортивная", "Студентческая", "Площадь Маркса"],
        "Зеленая линия": ["Площадь Гарина-Михайловского", "Сибирская", "Маршала Покрышкина","Берёзовая роща", "Золотая нива"]
    },
    "spb": {
        "Кировско-Выборгская (красная)": ["Девяткино", "Гражданский проспект", "Академическая",
                                        "Политехническая", "Площадь Мужества", "Лесная",
                                        "Выборгская", "Площадь Ленина", "Чернышевская",
                                        "Площадь Восстания", "Владимирская", "Пушкинская",
                                        "Технологический институт 1", "Балтийская", "Нарвская",
                                        "Кировский завод", "Автово", "Ленинский проспект",
                                        "Проспект Ветеранов"],
        "Московско-Петроградская (синяя)": ["Парнас", "Проспект Просвещения", "Озерки",
                                           "Удельная", "Пионерская", "Чёрная речка",
                                           "Петроградская", "Горьковская", "Невский проспект",
                                           "Сенная площадь", "Технологический институт 2",
                                           "Фрунзенская", "Московские ворота", "Электросила",
                                           "Парк Победы", "Московская", "Звёздная", "Купчино"],
        "Невско-Василеостровская (зелёная)": ["Беговая", "Зенит", "Приморская",
                                             "Василеостровская", "Гостиный двор", "Маяковская",
                                             "Площадь Александра Невского 1", "Елизаровская",
                                             "Ломоносовская", "Пролетарская", "Обухово", "Рыбацкое"],
        "Правобережная (оранжевая)": ["Спасская", "Достоевская", "Лиговский проспект",
                                     "Площадь Александра Невского 2", "Новочеркасская",
                                     "Ладожская", "Проспект Большевиков", "Улица Дыбенко"],
        "Фрунзенско-Приморская (фиолетовая)": ["Комендантский проспект", "Старая Деревня",
                                              "Крестовский остров", "Чкаловская", "Спортивная",
                                              "Адмиралтейская", "Садовая", "Звенигородская",
                                              "Обводный канал", "Волковская", "Бухарестская",
                                              "Международная", "Проспект Славы", "Дунайская",
                                              "Шушары"]
    }
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update) -> int:
    user_id = update.effective_user.id
    user_cities[user_id] = "nsk"

    keyboard = [
        ["🚇 Рассчитать время", "⚙️ Настройки"],
        ["ℹ️ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Добро пожаловать в бот метро! 🚇\n\n"
        "Я помогу рассчитать время пути между станциями метро.\n"
        f"Текущий город: {get_city_name(user_cities[user_id])}",
        reply_markup=reply_markup
    )

    return SELECTING_ACTION


async def calculate_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city = user_cities.get(user_id, "nsk")

    lines = list(CITY_LINES[city].keys())
    keyboard = []

    for i in range(0, len(lines), 2):
        row = lines[i:i + 2]
        keyboard.append(row)

    keyboard.append(["↩️ Назад"])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите линию для начальной станции:",
        reply_markup=reply_markup
    )

    context.user_data['step'] = 'select_start_line'
    return SELECTING_LINE


async def handle_line_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city = user_cities.get(user_id, "nsk")
    selected_line = update.message.text

    if selected_line == "↩️ Назад":
        return await show_main_menu(update, context)

    if selected_line not in CITY_LINES[city]:
        await update.message.reply_text("Пожалуйста, выберите линию из предложенных вариантов.")
        return SELECTING_LINE

    if context.user_data['step'] == 'select_start_line':
        context.user_data['start_line'] = selected_line
        next_step = SELECTING_STATION
        message_text = "Выберите начальную станцию:"
    else:
        context.user_data['end_line'] = selected_line
        next_step = SELECTING_END_STATION
        message_text = "Выберите конечную станцию:"

    stations = CITY_LINES[city][selected_line]
    keyboard = []

    for i in range(0, len(stations), 2):
        row = stations[i:i + 2]
        keyboard.append(row)

    keyboard.append(["↩️ К выбору линии"])
    keyboard.append(["🏠 Главное меню"])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(message_text, reply_markup=reply_markup)

    return next_step


async def handle_station_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city = user_cities.get(user_id, "nsk")
    selected_station = update.message.text

    if selected_station == "↩️ К выбору линии":
        return await calculate_time(update, context)

    if selected_station == "🏠 Главное меню":
        return await show_main_menu(update, context)

    current_line = context.user_data.get('start_line')
    if selected_station not in CITY_LINES[city][current_line]:
        await update.message.reply_text("Пожалуйста, выберите станцию из предложенных вариантов.")
        return SELECTING_STATION

    context.user_data['start_station'] = selected_station

    lines = list(CITY_LINES[city].keys())
    keyboard = []

    for i in range(0, len(lines), 2):
        row = lines[i:i + 2]
        keyboard.append(row)

    keyboard.append(["↩️ Назад"])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите линию для конечной станции:",
        reply_markup=reply_markup
    )

    context.user_data['step'] = 'select_end_line'
    return SELECTING_LINE


async def handle_end_station_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city = user_cities.get(user_id, "nsk")
    selected_station = update.message.text

    if selected_station == "↩️ К выбору линии":
        lines = list(CITY_LINES[city].keys())
        keyboard = []

        for i in range(0, len(lines), 2):
            row = lines[i:i + 2]
            keyboard.append(row)

        keyboard.append(["↩️ Назад"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "Выберите линию для конечной станции:",
            reply_markup=reply_markup
        )

        context.user_data['step'] = 'select_end_line'
        return SELECTING_LINE

    if selected_station == "🏠 Главное меню":
        return await show_main_menu(update, context)

    current_line = context.user_data.get('end_line')
    if selected_station not in CITY_LINES[city][current_line]:
        await update.message.reply_text("Пожалуйста, выберите станцию из предложенных вариантов.")
        return SELECTING_END_STATION

    context.user_data['end_station'] = selected_station

    start_station = context.user_data['start_station']
    end_station = context.user_data['end_station']

    try:
        response = requests.get(
            f"{API_URL}/?city={city}&start={start_station}&finish={end_station}",
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            time_minutes = data['time']
            way = " → ".join(data['way'])

            result_text = (
                f"🚇 <b>Маршрут:</b> {start_station} → {end_station}\n"
                f"⏱ <b>Время в пути:</b> {time_minutes} минут\n"
                f"📍 <b>Путь:</b> {way}\n\n"
                f"🏙 <b>Город:</b> {get_city_name(city)}"
            )
        else:
            result_text = "❌ Ошибка: Не удалось рассчитать маршрут. Проверьте правильность станций."

    except requests.exceptions.RequestException:
        result_text = "❌ Ошибка соединения с сервером. Попробуйте позже."

    context.user_data.clear()

    keyboard = [
        ["🚇 Рассчитать время", "⚙️ Настройки"],
        ["ℹ️ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(result_text, reply_markup=reply_markup, parse_mode='HTML')
    return SELECTING_ACTION


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        ["Новосибирск", "Санкт-Петербург"],
        ["↩️ Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    user_id = update.effective_user.id
    current_city = user_cities.get(user_id, "nsk")

    await update.message.reply_text(
        f"Текущий город: {get_city_name(current_city)}\n"
        "Выберите город:",
        reply_markup=reply_markup
    )

    return SELECTING_ACTION


async def change_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city_name = update.message.text

    if city_name == "Новосибирск":
        user_cities[user_id] = "nsk"
    elif city_name == "Санкт-Петербург":
        user_cities[user_id] = "spb"
    elif city_name == "↩️ Назад":
        return await show_main_menu(update, context)
    else:
        await update.message.reply_text("Неизвестный город.")
        return SELECTING_ACTION

    keyboard = [
        ["🚇 Рассчитать время", "⚙️ Настройки"],
        ["ℹ️ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Город изменен на: {get_city_name(user_cities[user_id])}",
        reply_markup=reply_markup
    )

    return SELECTING_ACTION


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    help_text = (
        "🤖 <b>Бот метро - помощь</b>\n\n"
        "🚇 <b>Рассчитать время</b> - расчет времени между станциями\n"
        "⚙️ <b>Настройки</b> - смена города (по умолчанию Новосибирск)\n"
        "ℹ️ <b>Помощь</b> - это сообщение\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Выберите 'Рассчитать время'\n"
        "2. Выберите линию метро\n"
        "3. Выберите станцию из списка\n"
        "4. Повторите для конечной станции\n"
        "5. Получите результат!\n\n"
        "Все действия через удобные кнопки! 🎯"
    )

    await update.message.reply_text(help_text, parse_mode='HTML')
    return SELECTING_ACTION


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        ["🚇 Рассчитать время", "⚙️ Настройки"],
        ["ℹ️ Помощь"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    user_id = update.effective_user.id
    current_city = user_cities.get(user_id, "nsk")

    await update.message.reply_text(
        f"🏠 Главное меню\nТекущий город: {get_city_name(current_city)}",
        reply_markup=reply_markup
    )

    context.user_data.clear()
    return SELECTING_ACTION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await show_main_menu(update, context)


def get_city_name(city_code: str) -> str:
    return {
        "nsk": "Новосибирск",
        "spb": "Санкт-Петербург"
    }.get(city_code, "Неизвестно")


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.Regex('^🚇 Рассчитать время$'), calculate_time),
                MessageHandler(filters.Regex('^⚙️ Настройки$'), settings),
                MessageHandler(filters.Regex('^ℹ️ Помощь$'), help_command),
                MessageHandler(filters.Regex('^(Новосибирск|Санкт-Петербург|↩️ Назад)$'), change_city),
            ],
            SELECTING_LINE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_line_selection),
            ],
            SELECTING_STATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_station_selection),
            ],
            SELECTING_END_STATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_end_station_selection),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()