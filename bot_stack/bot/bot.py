# 1344678447 // не удалять это мой тг id
import os
import logging
from pathlib import Path
from typing import Dict, Any

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
    """Отправка уведомления на веб-сервер"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{WEB_SERVER_URL}{endpoint}", json=data) as response:
                if response.status != 200:
                    logger.error(f"Ошибка при отправке на веб-сервер: {await response.text()}")
                    return False
                return True
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка подключения к веб-серверу: {e}")
        return False

@app.post("/message")
async def send_text_to_user(data: dict):
    """Отправка текстового сообщения пользователю"""
    chat_id = data.get("chat_id")
    text = data.get("text")
    
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
    chat_id = data.get("chat_id")
    msg_title = data.get("title")
    buttons = data.get("buttons")
    
    if not chat_id or not msg_title or not buttons:
        raise HTTPException(status_code=400, detail="chat_id, title и buttons обязательны")
    
    if len(buttons) < 2:
        raise HTTPException(status_code=400, detail="buttons должно содержать хотя бы 2 кнопки")
    
    keyboard = [
        [InlineKeyboardButton(button, callback_data=button)] for button in buttons
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
    """Отправка изображения пользователю"""
    chat_id = data.get("chat_id")
    image_url = data.get("image_url")
    
    if not chat_id or not image_url:
        raise HTTPException(status_code=400, detail="chat_id и image_url обязательны")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    await telegram_app.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_data
                    )
                    logger.info(f"Изображение отправлено пользователю {chat_id}")
                    return {"status": "success", "message": "Изображение отправлено"}
                else:
                    raise HTTPException(status_code=500, detail="Не удалось загрузить изображение")
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
    """Обработка нажатий на кнопки клавиатуры"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    sender_nick = query.from_user.username or query.from_user.full_name
    button = query.data
    
    # Уведомляем веб-сервер
    await notify_web_server('/keyboard/input', {
        'chat_id': str(chat_id),
        'sender_nick': sender_nick,
        'button': button
    })
    
    # Обновляем сообщение
    try:
        await telegram_app.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
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
    await notify_web_server('/user_message', {
        'chat_id': str(update.message.chat_id),
        'sender_nick': update.message.from_user.username or "Новый пользователь",
        'text': "Пользователь начал диалог"
    })

async def handle_message_from_user(update: Update, context):
    """Обработка текстовых сообщений от пользователя"""
    message_text = update.message.text
    sender_nick = update.message.from_user.username or update.message.from_user.full_name
    chat_id = update.message.chat_id
    
    await notify_web_server('/user_message', {
        'chat_id': str(chat_id),
        'sender_nick': sender_nick,
        'text': message_text
    })

async def handle_photo_from_user(update: Update, context):
    """Обработка фотографий от пользователя"""
    if not update.message.photo:
        return
    
    photo = update.message.photo[-1]
    sender_nick = update.message.from_user.username or update.message.from_user.full_name
    chat_id = update.message.chat_id
    
    # Получаем файл
    file = await photo.get_file()
    file_path = IMAGES_DIR / f"{photo.file_id}.jpg"
    
    try:
        # Скачиваем файл
        await file.download_to_drive(file_path)
        
        # Отправляем на веб-сервер
        with open(file_path, 'rb') as f:
            form_data = aiohttp.FormData()
            form_data.add_field('image', f, filename=f"{photo.file_id}.jpg", content_type='image/jpeg')
            form_data.add_field('chat_id', str(chat_id))
            form_data.add_field('sender_nick', sender_nick)
            form_data.add_field('file_id', photo.file_id)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{WEB_SERVER_URL}/image", data=form_data) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка при отправке изображения: {await response.text()}")
        
        logger.info(f"Изображение {photo.file_id} обработано")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
    finally:
        # Удаляем временный файл
        if file_path.exists():
            file_path.unlink()

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