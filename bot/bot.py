#1344678447
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from fastapi import FastAPI
import uvicorn
import threading
import aiofiles
from pathlib import Path

TELEGRAM_TOKEN = '1873920038:AAGbA5l5Uv0qqLRxYrcs1iShTaZ0MBH7eM4'
WEB_SERVER_URL = 'http://web-server:3000'
telegram_app = None

app = FastAPI()

# Создаем директорию для временного хранения изображений
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)

# обработка текстовых сообщений от web-интерфейса
@app.post("/message")
async def send_text_to_user(data: dict):
    chat_id = data.get("chat_id")
    sending_text = data.get("text")
    if not chat_id or not sending_text:
        return {"error": "chat_id и text обязательны"}
    try:
        await telegram_app.bot.send_message(chat_id=chat_id, text=sending_text)
        return {'message': f"ВЫ: {sending_text}"}
    except Exception as e:
        return {"error": f"Не удалось отправить text: {str(e)}"}

# обработка текстовых клавиатур от web-интерфейса
@app.post("/keyboard/create")
async def send_inline_keyboard_to_user(data: dict):
    chat_id = data.get("chat_id")
    msg_title = data.get("title")
    buttons = data.get("buttons")
    if not chat_id or not msg_title or not buttons:
        return {"error": "chat_id, title и buttons обязательны"}
    elif len(buttons) < 2:
        return {"error": "buttons должно содержать хотя бы 2 кнопки"}
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
        return {'message': f"Встроенная клавиатура отправлена пользователю {chat_id}"}
    except Exception as e:
        return {"error": f"Не удалось отправить встроенную клавиатуру: {str(e)}"}

# обработка действий с клавиатурами
async def button_click(update: Update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    sender_nick = query.from_user.username or query.from_user.full_name
    button = query.data
    payload = {
        'chat_id': str(chat_id),
        'sender_nick': sender_nick,
        'button': button
    }
    try:
        response = requests.post(WEB_SERVER_URL + '/keyboard/input', json=payload)
        if response.status_code != 200:
            print(f"Ошибка при отправке сообщения на веб-сервер: {response.text}")
    except Exception as e:
        print(f"Не удалось отправить реакцию на inline клавиатуру: {e}")
    await query.message.delete()

async def start(update: Update, context):
    await update.message.reply_text("Привет! Отправляй сообщения или изображения, они появятся в веб-интерфейсе. Ответы придут от веб-интерфейса.")

# обработка текстовых сообщений от пользователя
async def handle_message_from_user(update: Update, context):
    if update.message and update.message.text:
        message_text = update.message.text
        sender_nick = update.message.from_user.username or update.message.from_user.full_name
        chat_id = update.message.chat_id
        payload = {
            'chat_id': str(chat_id),
            'sender_nick': sender_nick,
            'text': message_text
        }
        try:
            response = requests.post(WEB_SERVER_URL + '/user_message', json=payload)
            if response.status_code != 200:
                print(f"Ошибка при отправке сообщения на веб-сервер: {response.text}")
        except Exception as e:
            print(f"Не удалось отправить сообщение: {e}")

async def handle_photo_from_user(update: Update, context):
    def download_file(url, local_filename):
        with requests.get(url, stream=False) as r: # stream=True для больших файлов
            r.raise_for_status() # Проверка на ошибки
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    if update.message and update.message.photo:
        photo = update.message.photo[-1]  # Берем фото наилучшего качества
        sender_nick = update.message.from_user.username or update.message.from_user.full_name
        chat_id = update.message.chat_id

        # Проверяем размер файла (не больше 10 МБ)
        if photo.file_size > 10 * 1024 * 1024:
            print(f"Изображение слишком большое: {photo.file_size} байт")
            return

        # Получаем файл из Telegram
        file = await photo.get_file()
        # await telegram_app.bot.send_message(chat_id=chat_id, text=f"размер файла {file.file_size}")
        file_path = IMAGES_DIR / f"{photo.file_id}.jpg"

        # Скачиваем файл
        download_file(file.file_path, file_path) ## надо сделать функцию ассинхронной или она за счет вложенности уже ассинхронная?

        # Отправляем файл на веб-сервер
        payload = {
            'chat_id': str(chat_id),
            'sender_nick': sender_nick,
            'file_id': photo.file_id # файл id больше для откладки нужен 
        }
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    WEB_SERVER_URL + '/image',
                    data=payload,
                    files={'image': (f"{file_path}", f, 'image/jpeg')}
                )
                # await telegram_app.bot.send_message(chat_id=chat_id, text="файл отправлен")
            if response.status_code != 200:
                print(f"Ошибка при отправке изображения на веб-сервер: {response.text}")
            else:
                print(f"Изображение отправлено на веб-сервер: {file_path}")
        except Exception as e:
            print(f"Не удалось отправить изображение: {e}")
        finally:
            1 == 1
            # Удаляем временный файл
            #if file_path.exists():
            #    file_path.unlink()

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

def main():
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_from_user))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo_from_user))
    telegram_app.add_handler(CallbackQueryHandler(button_click))
    threading.Thread(target=run_fastapi, daemon=True).start()
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()