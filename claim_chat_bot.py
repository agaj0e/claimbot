import logging
import os
import datetime
import httpx  # Для асинхронных HTTP-запросов
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)


# Настройка логирования: выводим только сообщения WARNING и выше
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Отключение лишних логов requests/urllib3
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Получение токена бота и секретного ключа из переменных окружения
TELEGRAM_BOT_TOKEN = os.environ["BOT_TOKEN"]
SECRET_KEY = os.environ['MINDBOX_SECRET_KEY']

# Константы API
API_URL = 'https://api.mindbox.ru/v3/operations/sync?endpointId=tui-epk&operation=OrderStatusChange.Mindbox'
HEADERS = {
    'Authorization': f'Mindbox secretKey="{SECRET_KEY}"'
}

# Состояния диалога
ASK_CLAIM, ASK_STATUS = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.message.from_user
    logging.info(f"Команда /start от пользователя: {user.id} ({user.username})")
    await update.message.reply_text(
        "Привет! Я помогу вам изменить статус заказа.\n"
        "Пожалуйста, введите номер claim заказа:"
    )
    return ASK_CLAIM


async def handle_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода номера claim"""
    user = update.message.from_user
    claim = update.message.text.strip()
    context.user_data['claim'] = claim

    logging.info(f"Получен claim от пользователя: {user.id} ({user.username}), claim: {claim}")

    # Предлагаем выбрать статус заказа через inline-клавиатуру
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
    """Обработка выбора статуса заказа"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    status = query.data  # выбранный статус

    logging.info(f"Статус выбран пользователем: {user.id} ({user.username}), статус: {status}")

    claim = context.user_data.get('claim')

    if not claim:
        await query.edit_message_text("Ошибка: номер claim не найден. Пожалуйста, начните заново командой /start.")
        return

    current_time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

    # Вывод тела запроса для отладки (можно убрать или оставить)
    print(f"\n[{current_time_str}] Отправка запроса от пользователя: {user.username} (ID: {user.id})")
    print("Тело запроса:")
    print(payload)

    # Отправка асинхронного POST-запроса с помощью httpx
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=HEADERS, json=payload)
            response_text = response.text

            # Логирование ответа API
            print(f"\n[{current_time_str}] Получен ответ для пользователя: {user.username} (ID: {user.id})")
            print(f"Статус код: {response.status_code}")
            print(response_text)

            if response.status_code == 200:
                await query.edit_message_text("Статус заказа успешно обновлён!\nОтвет API:\n" + response_text)
            else:
                await query.edit_message_text(
                    f"Ошибка при отправке запроса. Статус: {response.status_code}\nОтвет:\n{response_text}"
                )
        except Exception as e:
            await query.edit_message_text(f"Произошла ошибка при отправке запроса: {e}")
            logging.error(f"Ошибка при отправке запроса для пользователя {user.id} ({user.username}): {e}")


def main():
    """Основная функция запуска бота"""

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler('start', start))

    # Обработка текста вне команд — предполагается ввод номера claim
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_claim))

    # Обработка выбора статуса через inline-клавиатуру
    application.add_handler(CallbackQueryHandler(handle_status_selection))

    # Запуск бота в режиме polling
    application.run_polling()


if __name__ == '__main__':
    main()