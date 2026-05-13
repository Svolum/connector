import asyncio

import uvicorn
from fastapi import FastAPI, Body, Response
from fastapi.responses import PlainTextResponse

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

import tg_api
import tg_handlers

import load_env


SELF_URL = load_env.SELF_URL
WEB_URL: str = load_env.WEB_URL
PORT = load_env.PORT
TOKEN = load_env.TOKEN
WEBHOO_PATH = load_env.WEBHOO_PATH
PROXY_URL = load_env.PROXY_URL

async def main() -> None:
    # Создаем приложение бота
    application = (
        Application.builder()
        .token(TOKEN)
        .proxy(PROXY_URL)
        .build()
    )
    # Регистрируем функции обработчики команд
    application.add_handler(CommandHandler("start", tg_handlers.command_start))
    application.add_handler(CommandHandler("help", tg_handlers.command_help))
    application.add_handler(CallbackQueryHandler(tg_handlers.handle_button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_handlers.handle_message_text))
    application.add_handler(MessageHandler(filters.PHOTO, tg_handlers.handle_image))

    # Настраиваем вебхук для Telegram
    await application.bot.set_webhook(url=f"{SELF_URL}/{WEBHOO_PATH}", allowed_updates=Update.ALL_TYPES)

    # Создаем приложение FastAPI, который интернет слушает
    tg_api.application = application
    tg_handlers.bot = tg_api.application.bot
    tg_handlers.WEB_URL = WEB_URL


    webserver = uvicorn.Server(
        config=uvicorn.Config(app=tg_api.fast_api_app, port=PORT, host="0.0.0.0")
    )

    # Запуск
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())