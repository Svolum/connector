# 1344678447 // не удалять это мой тг id
import os
import logging
from pathlib import Path
from typing import Dict, Any
import asyncio

import base64
from datetime import datetime

import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('API_TOKEN')
WEB_SERVER_URL = os.getenv('WEB_SERVER_URL', 'http://localhost:3000')
BOT_HOST = os.getenv('BOT_HOST', '0.0.0.0')
BOT_PORT = int(os.getenv('BOT_PORT', '8080'))

# Глобальные переменные
telegram_app = None
app = FastAPI(title="Telegram Bot API")

# Создаем директорию для временного хранения изображений
IMAGES_DIR = Path("/app/images")
IMAGES_DIR.mkdir(exist_ok=True)

async def notify_web_server(endpoint: str, data: Dict[str, Any]) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{WEB_SERVER_URL}{endpoint}", json=data) as response:
                response_text = await response.text()
                if response.status != 200:
                    logger.error(
                        f"Ошибка при отправке на веб-сервер. "
                        f"URL={WEB_SERVER_URL}{endpoint}, status={response.status}, body={response_text}"
                    )
                    return False

                logger.info(f"Успешно отправлено на {WEB_SERVER_URL}{endpoint}")
                return True

    except asyncio.TimeoutError:
        logger.error(f"Таймаут при отправке на веб-сервер: {WEB_SERVER_URL}{endpoint}")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка подключения к веб-серверу: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке на веб-сервер: {e}")
        return False

@app.post("/message")
async def send_text_to_user(data: dict):
    """Отправка текстового сообщения пользователю"""
    user_id = data.get("user_id") or None
    place = data.get("place") or {}
    chat_id = place.get("chat_id") or None
    text = data.get("text") or None

    if not chat_id or not text:
        raise HTTPException(status_code=400, detail="chat_id и text обязательны")

    try:
        await telegram_app.bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Текст отправлен пользователю {chat_id}")
        return {"status": "success", "message": "Текст отправлен"}
    except TelegramError as e:
        logger.error(f"Ошибка Telegram при отправке текста: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/keyboard/create")
async def send_inline_keyboard_to_user(data: dict):
    """Отправка inline клавиатуры пользователю"""
    msg_title = data.get("title")
    user_id = data.get("user_id") or None
    place = data.get("place") or {}
    chat_id = place.get("chat_id") or None
    title = data.get("title") or None
    buttons = data.get("buttons") or []

    if not chat_id or not msg_title or not buttons:
        raise HTTPException(status_code=400, detail="chat_id, title и buttons обязательны")

    if len(buttons) < 2:
        raise HTTPException(status_code=400, detail="buttons должно содержать хотя бы 2 кнопки")

    keyboard = [
        [InlineKeyboardButton(btn.get("text"), callback_data=btn.get("text"))]
        for btn in buttons
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await telegram_app.bot.send_message(
            chat_id=chat_id,
            text=msg_title,
            reply_markup=reply_markup
        )
        logger.info(f"Клавиатура отправлена пользователю {chat_id}")
        return {"status": "success", "message": "Клавиатура отправлена"}
    except TelegramError as e:
        logger.error(f"Ошибка Telegram при отправке клавиатуры: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/image")
async def send_image_to_user(data: dict):

    user_id = data.get("user_id")
    place = data.get("place") or {}
    chat_id = place.get("chat_id")
    attachments = data.get("attachments_base64") or []

    if not chat_id or not attachments:
        raise HTTPException(status_code=400, detail="chat_id и attachments обязательны")

    try:
        image_bytes = base64.b64decode(attachments[0])

        await telegram_app.bot.send_photo(
            chat_id=chat_id,
            photo=image_bytes
        )

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Ошибка при отправке изображения: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "web_server_url": WEB_SERVER_URL
    }

async def button_click(update: Update, context):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    button = query.data
    message_id = query.message.message_id

    await notify_web_server('/keyboard/input', {
        "user_id": str(chat_id),
        "button": button if button is not None else None,
        "place": {
            "chat_id": str(chat_id),
            "message_id": str(message_id) if message_id is not None else None
        },
        "date_time": datetime.now().astimezone().isoformat()
    })

    try:
        await telegram_app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"{query.message.text} ✅ {button}"
        )
    except TelegramError as e:
        logger.error(f"Ошибка при обновлении сообщения: {e}")

async def start(update: Update, context):
    """Обработка команды /start"""
    welcome_text = (
        "👋 Привет! Я бот для связи с веб-интерфейсом.\n\n"
        "📝 Отправляй мне сообщения или изображения, "
        "и они появятся в веб-интерфейсе.\n"
        "💬 Ответы из веб-интерфейса будут приходить сюда."
    )
    await update.message.reply_text(welcome_text)

    # Уведомляем веб-сервер о новом пользователе
    chat_id = update.effective_chat.id

    await notify_web_server('/user_message', {
        "user_id": str(chat_id),
        "place": {
            "chat_id": str(chat_id)
        },
        "text": "Пользователь начал диалог"
    })

async def handle_message_from_user(update: Update, context):
    """Обработка текстовых сообщений от пользователя"""

    message_text = update.message.text
    chat_id = update.message.chat_id
    logger.info(f"CHAT_ID: {chat_id}")
    logger.info(f"MESSAGE_TEXT: {message_text}")

    await notify_web_server('/user_message', {
        "user_id": str(chat_id),
        "place": {
            "chat_id": str(chat_id)
        },
        "text": message_text
    })

async def handle_photo_from_user(update: Update, context):
    try:
        photo = update.message.photo[-1]  # самое большое фото
        tg_file = await photo.get_file()
        image_bytes = await tg_file.download_as_bytearray()

        encoded = base64.b64encode(bytes(image_bytes)).decode("utf-8")
        chat_id = update.message.chat_id

        await notify_web_server('/image', {
            "user_id": str(chat_id),
            "place": {
                "chat_id": str(chat_id)
            },
            "attachments_base64": [encoded],
            "date_time": datetime.now().astimezone().isoformat()
        })
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")

async def error_handler(update: Update, context):
    """Обработка ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")

def run_fastapi():
    """Запуск FastAPI сервера"""
    uvicorn.run(app, host=BOT_HOST, port=BOT_PORT)

def main():
    """Основная функция"""
    global telegram_app

    from datetime import datetime

    # Создаем приложение Telegram бота
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_from_user))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo_from_user))
    telegram_app.add_handler(CallbackQueryHandler(button_click))

    # Добавляем обработчик ошибок
    telegram_app.add_error_handler(error_handler)

    # Запускаем FastAPI в отдельном потоке
    import threading
    threading.Thread(target=run_fastapi, daemon=True).start()

    logger.info(f"Бот запущен. Веб-сервер: {WEB_SERVER_URL}")

    # Запускаем бота
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

