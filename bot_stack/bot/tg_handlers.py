import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import httpx

import base64
import io

import load_env

HTTPX_HEADER_NAME = load_env.HTTPX_HEADER_NAME
HTTPX_HEADER_CONNECTOR_NAME = load_env.HTTPX_HEADER_CONNECTOR_NAME
header = {
    HTTPX_HEADER_NAME: HTTPX_HEADER_CONNECTOR_NAME
}

bot: telegram.Bot = None
WEB_URL: str = None


async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Bot seem to start')

async def command_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Pong!')

async def text_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(update.message.text)

async def call_web_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = str()
    async with httpx.AsyncClient(trust_env=False, headers=header) as client:
        response = await client.get("http://127.0.0.1:8000/")
        message += f'Status: {response.status_code}\n'
        if response.status_code == 200:
            message += f'Text: {response.text}\n'
    await update.message.reply_text(message)

async def send_inline_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton('Option 1', callback_data='1'),
            InlineKeyboardButton('Option 2', callback_data='2')
        ],
        [
            InlineKeyboardButton('Option 3', callback_data='3')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Please choose:', reply_markup=reply_markup)

async def parse_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(text=f'selected option: {query.data}')


async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    # отвечаем на callback, чтобы у пользователя убралась анимация загрузки
    await query.answer()

    await query.edit_message_text(text=f'Selected option: {query.data}')

    async with httpx.AsyncClient(trust_env=True, headers=header) as client:
        payload = {
            "user_id": str(query.from_user.id),
            "button": query.data,
            "place": {
                "chat_id": str(query.message.chat.id),
                "message_id": str(query.message.message_id)
            },
            "date_time": query.message.date.isoformat()
        }

        try:
            response = await client.post(url=f"{WEB_URL}/keyboard/update", json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка при отправке в FastAPI: {e}")

async def command_docement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_document(document='public/ruichi.png')


async def command_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_photo(photo='public/ruichi.png')

async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id: int = update.message.chat_id
    message: str = 'try to help me!' + str(chat_id)

    await bot.send_message(chat_id=chat_id, text=message)


async def send_message_text(chat_id: int, text: str) -> bool:
    if bot == None:
        print('bot is None')
        return False
    await bot.send_message(chat_id=chat_id, text=text)
    return True


async def handle_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with httpx.AsyncClient(trust_env=False, headers=header) as client:
        payload = {
                "user_id": update.message.from_user.id,
                "place": {
                    "chat_id": update.message.chat_id
                },
                "text": update.message.text,
                "date_time": update.message.date.isoformat()
        }
        response = await client.post(url=f"{WEB_URL}/user_message", json=payload)


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Берем самое качественное фото(последнее в списке)
    photo = update.message.photo[-1]

    # Получаем файл от Telegram
    new_file = await context.bot.get_file(photo.file_id)

    # Скачиваем в "виртуальный" файл в памяти
    photo_buffer = io.BytesIO()
    await new_file.download_to_memory(photo_buffer)

    # Кодируем байты в base64 строку
    # .getvalue() — получает все байты из буфера
    # base64.b64encode — кодирует байты в base64-байты
    # .decode('utf-8') — превращает байты base64 в обычную строку
    image_base64 = base64.b64encode(photo_buffer.getvalue()).decode('utf-8')

    payload = {
        "user_id": str(update.effective_user.id),
        "place": {
            "chat_id": str(update.effective_chat.id)
        },
        "attachments_base64": [
            image_base64
        ],
        "date_time": update.message.date.isoformat()
    }

    async with httpx.AsyncClient(trust_env=False, headers=header) as client:
        response = await client.post(
            f"{WEB_URL}/image",
            json=payload,
            timeout=10.0  # Фото может быть тяжелым, лучше увеличить таймаут
        )