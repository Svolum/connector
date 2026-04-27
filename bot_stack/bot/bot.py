import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# =========================
# ENV
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_MODE = os.getenv("BOT_MODE", "polling").lower()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEB_API_URL = os.getenv("WEB_API_URL")

HTTP_TIMEOUT = float(15)


telegram_app: Application | None = None
http_client: httpx.AsyncClient | None = None


# =========================
# Pydantic models
# =========================

class PlaceChat(BaseModel):
    chat_id: str | int | None = None


class PlaceMessage(BaseModel):
    chat_id: str | int | None = None
    message_id: str | int | None = None


class SendMessageRequest(BaseModel):
    user_id: str | int | None = None
    place: PlaceChat
    text: str


class KeyboardButtonPayload(BaseModel):
    text: str


class CreateKeyboardRequest(BaseModel):
    user_id: str | int | None = None
    place: PlaceChat
    title: str
    buttons: list[KeyboardButtonPayload] = Field(default_factory=list)


class ApiResponse(BaseModel):
    ok: bool
    detail: str | None = None
    data: dict[str, Any] | None = None


# =========================
# Helpers
# =========================

def require_telegram_app() -> Application:
    if telegram_app is None:
        raise HTTPException(
            status_code=500,
            detail="Telegram application is not initialized",
        )
    return telegram_app


def require_http_client() -> httpx.AsyncClient:
    if http_client is None:
        raise RuntimeError("HTTP client is not initialized")
    return http_client


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def telegram_datetime_iso(dt: datetime | None) -> str:
    if dt is None:
        return now_iso()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


async def post_to_web_api(path: str, payload: dict[str, Any]) -> None:
    """
    Отправляет событие из Telegram в готовый веб-интерфейс.
    """
    if not WEB_API_URL:
        logger.warning("WEB_API_URL is not set. Payload was not sent: %s", payload)
        return

    client = require_http_client()

    url = f"{normalize_base_url(WEB_API_URL)}{path}"

    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.exception("Failed to send payload to web api %s: %s", url, error)


async def download_telegram_file_as_base64(file_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Скачивает файл из Telegram и возвращает base64-строку.
    """
    tg_file = await context.bot.get_file(file_id)

    buffer = io.BytesIO()
    await tg_file.download_to_memory(out=buffer)

    file_bytes = buffer.getvalue()
    return base64.b64encode(file_bytes).decode("ascii")


def get_user_id(update: Update) -> str | None:
    if update.effective_user is None:
        return None
    return str(update.effective_user.id)


def get_chat_id(update: Update) -> str | None:
    if update.effective_chat is None:
        return None
    return str(update.effective_chat.id)


# =========================
# Telegram handlers
# =========================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Бот запущен.")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("pong")


async def handle_user_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Telegram -> bot -> WEB_API_URL/user_message
    """
    message = update.message

    if message is None:
        return

    if message.text is None:
        return

    payload = {
        "user_id": get_user_id(update),
        "place": {
            "chat_id": get_chat_id(update),
        },
        "text": message.text,
    }

    await post_to_web_api("/user_message", payload)


async def handle_user_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Поддержка обычных Telegram-фото.

    Telegram photo -> base64 -> WEB_API_URL/image
    """
    message = update.message

    if message is None:
        return

    if not message.photo:
        return

    # Берём самый большой вариант фото.
    photo = message.photo[-1]

    try:
        image_base64 = await download_telegram_file_as_base64(photo.file_id, context)
        attachments_base64 = [image_base64]
    except Exception as error:
        logger.exception("Failed to download Telegram photo: %s", error)
        attachments_base64 = [None]

    payload = {
        "user_id": get_user_id(update),
        "place": {
            "chat_id": get_chat_id(update),
        },
        "attachments_base64": attachments_base64,
        "date_time": telegram_datetime_iso(message.date),
    }

    await post_to_web_api("/image", payload)


async def handle_user_image_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Поддержка изображений, отправленных как документ.

    Telegram document image/* -> base64 -> WEB_API_URL/image
    """
    message = update.message

    if message is None:
        return

    document = message.document

    if document is None:
        return

    mime_type = document.mime_type or ""

    if not mime_type.startswith("image/"):
        return

    try:
        image_base64 = await download_telegram_file_as_base64(document.file_id, context)
        attachments_base64 = [image_base64]
    except Exception as error:
        logger.exception("Failed to download Telegram image document: %s", error)
        attachments_base64 = [None]

    payload = {
        "user_id": get_user_id(update),
        "place": {
            "chat_id": get_chat_id(update),
        },
        "attachments_base64": attachments_base64,
        "date_time": telegram_datetime_iso(message.date),
    }

    await post_to_web_api("/image", payload)


async def handle_keyboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Telegram inline button click -> WEB_API_URL/keyboard/input
    """
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    message = query.message

    payload = {
        "user_id": str(query.from_user.id) if query.from_user else None,
        "button": query.data,
        "place": {
            "chat_id": str(message.chat_id) if message else None,
            "message_id": str(message.message_id) if message else None,
        },
        "date_time": now_iso(),
    }

    await post_to_web_api("/keyboard/input", payload)


def create_telegram_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ping", ping_command))

    application.add_handler(CallbackQueryHandler(handle_keyboard_callback))

    application.add_handler(MessageHandler(filters.PHOTO, handle_user_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_user_image_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text_message))

    return application


# =========================
# FastAPI lifespan
# =========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app
    global http_client

    if BOT_MODE not in {"polling", "webhook"}:
        raise RuntimeError("BOT_MODE must be either 'polling' or 'webhook'")

    if BOT_MODE == "webhook" and not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is required when BOT_MODE=webhook")

    telegram_app = create_telegram_app()
    http_client = httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        trust_env=False,
    )

    logger.info("Initializing Telegram application")
    await telegram_app.initialize()
    await telegram_app.start()

    if BOT_MODE == "polling":
        logger.info("Starting Telegram bot in polling mode")
        await telegram_app.bot.delete_webhook(drop_pending_updates=True)

        if telegram_app.updater is None:
            raise RuntimeError("Telegram updater is not available")

        await telegram_app.updater.start_polling()

    elif BOT_MODE == "webhook":
        logger.info("Starting Telegram bot in webhook mode: %s", WEBHOOK_URL)
        await telegram_app.bot.set_webhook(url=WEBHOOK_URL)

    try:
        yield

    finally:
        logger.info("Shutting down application")

        if telegram_app is not None:
            if BOT_MODE == "polling" and telegram_app.updater is not None:
                await telegram_app.updater.stop()

            if BOT_MODE == "webhook":
                await telegram_app.bot.delete_webhook(drop_pending_updates=False)

            await telegram_app.stop()
            await telegram_app.shutdown()

        if http_client is not None:
            await http_client.aclose()


app = FastAPI(lifespan=lifespan)


# =========================
# FastAPI endpoints
# =========================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "bot_mode": BOT_MODE,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


@app.post("/message", response_model=ApiResponse)
async def send_message(payload: SendMessageRequest):
    """
    API тг бота.

    Внешний сервис вызывает /message,
    бот отправляет сообщение пользователю в Telegram.
    """
    application = require_telegram_app()

    chat_id = payload.place.chat_id

    if chat_id is None:
        raise HTTPException(
            status_code=400,
            detail="place.chat_id is required",
        )

    try:
        sent_message = await application.bot.send_message(
            chat_id=chat_id,
            text=payload.text,
        )

        return ApiResponse(
            ok=True,
            data={
                "chat_id": str(sent_message.chat_id),
                "message_id": str(sent_message.message_id),
            },
        )

    except Exception as error:
        logger.exception("Failed to send Telegram message: %s", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to send Telegram message",
        )


@app.post("/keyboard/create", response_model=ApiResponse)
async def create_keyboard(payload: CreateKeyboardRequest):
    """
    API тг бота.

    Внешний сервис вызывает /keyboard/create,
    бот отправляет inline-клавиатуру пользователю в Telegram.
    """
    application = require_telegram_app()

    chat_id = payload.place.chat_id

    if chat_id is None:
        raise HTTPException(
            status_code=400,
            detail="place.chat_id is required",
        )

    if not payload.buttons:
        raise HTTPException(
            status_code=400,
            detail="buttons must not be empty",
        )

    keyboard = [
        [
            InlineKeyboardButton(
                text=button.text,
                callback_data=button.text,
            )
        ]
        for button in payload.buttons
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        sent_message = await application.bot.send_message(
            chat_id=chat_id,
            text=payload.title,
            reply_markup=reply_markup,
        )

        return ApiResponse(
            ok=True,
            data={
                "chat_id": str(sent_message.chat_id),
                "message_id": str(sent_message.message_id),
            },
        )

    except Exception as error:
        logger.exception("Failed to send Telegram keyboard: %s", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to send Telegram keyboard",
        )


@app.post("/telegram/webhook", response_model=ApiResponse)
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.

    Используется только при BOT_MODE=webhook.
    Секреты не проверяются, как договорились.
    """
    if BOT_MODE != "webhook":
        raise HTTPException(
            status_code=400,
            detail="Webhook endpoint is disabled because BOT_MODE is not 'webhook'",
        )

    application = require_telegram_app()

    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)

        await application.process_update(update)

        return ApiResponse(ok=True)

    except Exception as error:
        logger.exception("Failed to process Telegram webhook update: %s", error)

        raise HTTPException(
            status_code=500,
            detail="Failed to process Telegram webhook update",
        )