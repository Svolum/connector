import os
import asyncio

import uvicorn
from fastapi import FastAPI, Body, Response
from fastapi.responses import PlainTextResponse

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

import httpx

import base64
import io

import tg_api


SELF_URL = os.getenv("SELF_URL", "")
WEB_URL: str = os.getenv("WEB_URL", "")
PORT = int(os.getenv("PORT", "8000"))
TOKEN = os.getenv("TOKEN")
WEBHOO_PATH = os.getenv("WEBHOO_PATH", "telegram")
PROXY_URL = os.getenv("PROXY_URL", "NO")
HTTPX_TIMEOUT = float(os.getenv("HTTPX_TIMEOUT", "30.0"))
HEADER_NAME = os.getenv("HEADER_NAME", "X-Connector-Name")
HEADER_VALUE = os.getenv("HEADER_VALUE", "tg")
USE_HEADER = os.getenv("USE_HEADER", "YES")


header = {
    HEADER_NAME: HEADER_VALUE
}
if (USE_HEADER == "NO"):
    header = dict()

bot: telegram.Bot = None


async def main() -> None:
    if (PROXY_URL == "NO"):
        application = (
            Application.builder()
            .token(TOKEN)
            .build()
        )
    else:
        application = (
            Application.builder()
            .token(TOKEN)
            .proxy(PROXY_URL)
            .build()
        )
    application.add_handler(MessageHandler(filters.COMMAND, handle_command))
    application.add_handler(CallbackQueryHandler(handle_button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    bot = application.bot

    # Настраиваем вебхук для Telegram
    await bot.set_webhook(url=f"{SELF_URL}/{WEBHOO_PATH}", allowed_updates=Update.ALL_TYPES)

    tg_api.application = application


    webserver = uvicorn.Server(
        config=uvicorn.Config(app=tg_api.fast_api_app, port=PORT, host="0.0.0.0")
    )

    # Запуск
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 1. Получаем полный текст (например, "/start", "/help" или "/z 123")
    command = update.message.text
    if not command:
        return


    command = command.replace('/', '')
    print("команда от")
    print(update.message.chat_id, command)

    async with httpx.AsyncClient(trust_env=False, headers=header) as client:
        payload = {
                "user_id": update.message.from_user.id,
                "place": {
                    "chat_id": update.message.chat_id
                },
                "name": command,
                "date_time": update.message.date.isoformat()
        }
        response = await client.post(url=f"{WEB_URL}/command", json=payload, timeout=HTTPX_TIMEOUT)


async def handle_message_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("ТЕКСТ от")
    print(update.message.chat_id, update.message.text)
    async with httpx.AsyncClient(trust_env=False, headers=header) as client:
        payload = {
                "user_id": update.message.from_user.id,
                "place": {
                    "chat_id": update.message.chat_id
                },
                "text": update.message.text,
                "date_time": update.message.date.isoformat()
        }
        response = await client.post(url=f"{WEB_URL}/user_message", json=payload, timeout=HTTPX_TIMEOUT)


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
            response = await client.post(url=f"{WEB_URL}/keyboard/input", json=payload, timeout=HTTPX_TIMEOUT)
            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка при отправке в FastAPI: {e}")


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
            timeout=HTTPX_TIMEOUT * 10
        )


if __name__ == "__main__":
    asyncio.run(main())