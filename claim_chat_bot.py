import logging
import requests
import os
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")


# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Ваш токен бота Telegram (убедитесь, что переменная окружения установлена)
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
secret_key = os.getenv('MINDBOX_SECRET_KEY')

# Константы для API Mindbox
API_URL = 'https://api.mindbox.ru/v3/operations/sync?endpointId=tui-epk&operation=OrderStatusChange.Mindbox'
HEADERS = {
    'Authorization': f'Mindbox secretKey="{secret_key}"'
}

# Состояния диалога
ASK_CLAIM, ASK_STATUS = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logging.info(f"Команда /start от пользователя: {user.id} ({user.username})")
    await update.message.reply_text(
        "Привет! Я помогу вам изменить статус заказа.\n"
        "Пожалуйста, введите номер claim заказа:"
    )
    return ASK_CLAIM


async def handle_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    claim = update.message.text.strip()
    context.user_data['claim'] = claim

    # Логируем информацию о пользователе и claim
    logging.info(f"Получен claim от пользователя: {user.id} ({user.username}), claim: {claim}")

    # Предлагаем выбрать статус заказа
    keyboard = [
        [InlineKeyboardButton("Отменено", callback_data='Отменено')],
        [InlineKeyboardButton("Completed", callback_data='Completed')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите статус заказа:",
        reply_markup=reply_markup
    )
    return ASK_STATUS


async def handle_status_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    status = query.data  # выбранный статус

    # Логируем информацию о пользователе и выбранном статусе
    logging.info(f"Статус выбран пользователем: {user.id} ({user.username}), статус: {status}")

    claim = context.user_data.get('claim')
    if not claim:
        await query.edit_message_text("Ошибка: номер claim не найден. Пожалуйста, начните заново командой /start.")
        return

    # Формируем payload для API Mindbox
    payload = {
        "orderLinesStatus": status,
        "order": {
            "ids": {
                "claim": claim
            },
            "customFields": {
                "loyalty": True
            }
        }
    }

    # Отправляем POST-запрос к API Mindbox с обработкой ошибок
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            await query.edit_message_text("Статус заказа успешно обновлён!\nОтвет API:\n" + response.text)
        else:
            await query.edit_message_text(
                f"Ошибка при отправке запроса. Статус: {response.status_code}\nОтвет:\n{response.text}"
            )
        # Логируем ответ API вместе с информацией о пользователе
        logging.info(f"API ответ для пользователя {user.id} ({user.username}): {response.status_code}")
    except Exception as e:
        await query.edit_message_text(f"Произошла ошибка при отправке запроса: {e}")
        logging.error(f"Ошибка при отправке запроса для пользователя {user.id} ({user.username}): {e}")


def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler('start', start))

    # Обработка ввода claim (номер заказа)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_claim))

    # Обработка выбора статуса через inline-кнопки
    application.add_handler(CallbackQueryHandler(handle_status_selection))

    # Запуск бота
    application.run_polling()


if __name__ == '__main__':
    main()
