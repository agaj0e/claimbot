import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ЛОГИ В КОНСОЛЬ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ПЕРЕМЕННАя ТОКЕНА
TELEGRAM_BOT_TOKEN = getenv("BOT_TOKEN")
MB_SECRET_KEY = getenv("SECRET_KEY")

# ЭНДПОИНТ И ТОКЕН АПИШКИ
API_URL = 'https://api.mindbox.ru/v3/napishisvoyeendpoint'
HEADERS = {
    'Authorization': 'Mindbox secretKey="{SECRET_KEY}"'
}

ASK_CLAIM, ASK_STATUS = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу вам изменить статус заказа.\n"
        "Пожалуйста, введите номер claim заказа:"
    )
 
    return ASK_CLAIM


async def handle_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    claim = update.message.text.strip()
    context.user_data['claim'] = claim

    # ВЫЮОР СТАТУСА
    ЗАКАЗА
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
    status = query.data  # выбранный статус

    claim = context.user_data.get('claim')

    # ТЕЛО ЗАПРОСА
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

    # КИДАЕМ ПОСТ К АПИШКЕ
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            await query.edit_message_text("Статус заказа успешно обновлён!\nОтвет API:\n" + response.text)
        else:
            await query.edit_message_text(
                f"Ошибка при отправке запроса. Статус: {response.status_code}\nОтвет:\n{response.text}")
    except Exception as e:
        await query.edit_message_text(f"Произошла ошибка: {e}")


def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # КОМАНДЫ ЗАПУСКА БОТА
    application.add_handler(CommandHandler('start', start))

    #(номер заказа)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_claim))

    # ОБРАБОТКА КНОПКИ
    application.add_handler(CallbackQueryHandler(handle_status_selection))

    
    application.run_polling()


if __name__ == '__main__':
    main()
