#1344678447
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from fastapi import FastAPI
import uvicorn
import threading

TELEGRAM_TOKEN = '1873920038:AAGbA5l5Uv0qqLRxYrcs1iShTaZ0MBH7eM4'
WEB_SERVER_URL = 'http://web-server:3000/message'
telegram_app = None

app = FastAPI()

@app.post("/send_question")
async def send_question(data: dict):
    chat_id = data.get("chat_id")
    question = data.get("question")
    if not chat_id or not question:
        return {"error": "chat_id и question обязательны"}
    try:
        await telegram_app.bot.send_message(chat_id=chat_id, text=question)
        # Отправляем вопрос в веб-интерфейс для отображения
        requests.post(WEB_SERVER_URL, json={'message': f"Вопрос отправлен пользователю: {question}"})
        return {"message": "Вопрос отправлен"}
    except Exception as e:
        return {"error": f"Не удалось отправить вопрос: {str(e)}"}

async def start(update: Update, context):
    await update.message.reply_text("Привет! Отправляй сообщения, они появятся в веб-интерфейсе. Вопросы придут от веб-интерфейса.")

async def handle_message(update: Update, context):
    if update.message and update.message.text:
        message_text = update.message.text
        sender = update.message.from_user.username or update.message.from_user.full_name
        payload = {'message': f"{sender}: {message_text}"}
        ###
        print(update.message.chat_id)
        ###
        try:
            response = requests.post(WEB_SERVER_URL, json=payload)
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
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем FastAPI в отдельном потоке
    threading.Thread(target=run_fastapi, daemon=True).start()

    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()