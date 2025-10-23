#1344678447
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from fastapi import FastAPI
import uvicorn
import threading

TELEGRAM_TOKEN = '1873920038:AAGbA5l5Uv0qqLRxYrcs1iShTaZ0MBH7eM4'
WEB_SERVER_URL = 'http://web-server:3000'
telegram_app = None

app = FastAPI()

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

@app.post("/keyboard/create")
async def send_inline_keyboard_to_user(data: dict):
    chat_id = data.get("chat_id")
    msg_title = data.get("title")
    buttons = data.get("buttons")

    if not chat_id or not msg_title or not buttons:
        return {"error": "chat_id, title и buttons обязательны"}
    elif len(buttons) < 2:
        return {"error": "buttons должно содержать хотя бы 2 кнопки"}

    # Создаем список кнопок для InlineKeyboardMarkup
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

async def button_click(update: Update, context):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    sender_nick = query.from_user.username or query.from_user.full_name
    button = query.data # строка

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
    await update.message.reply_text("Привет! Отправляй сообщения, они появятся в веб-интерфейсе. Ответы придут от веб-интерфейса.")

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

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

def main():
    global telegram_app
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_from_user))
    telegram_app.add_handler(CallbackQueryHandler(button_click))

    threading.Thread(target=run_fastapi, daemon=True).start()
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
