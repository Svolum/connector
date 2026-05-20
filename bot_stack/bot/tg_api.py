from fastapi import FastAPI, Body, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import PlainTextResponse, Response
from starlette.responses import JSONResponse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackContext


import base64, io


application: Application = None

fast_api_app: FastAPI = FastAPI(root_path="/tg_bot")

# Эндпоинт для обычных сообщений из Telegram
@fast_api_app.post("/telegram")
async def telegram(data: dict = Body()) -> Response:
    update = Update.de_json(data=data, bot=application.bot)
    # Здесь какая-то внутренняя очередь PTB, которая нужна для работы CommandHandler и прочее
    await application.process_update(update)
    return Response()

@fast_api_app.get("/healthcheck")
async def health() -> PlainTextResponse:
    return PlainTextResponse("everythin is working right now", status_code=200)


@fast_api_app.post("/message")
async def send_message_api(data: dict = Body()) -> JSONResponse:
    print("/message")
    print(data)
    try:
        chat_id = int(data["place"]["chat_id"])
        text = data["text"]
    except Exception as e:
        message: dict = {
                          "code": 0,
                          "message": "не передан chat_id"
        }
        return JSONResponse(content=jsonable_encoder(message), status_code=500)
    try:
        sent_message = await application.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        message: dict = {
            "code": 0,
            "message": "не удалось отправить сообщение"
        }
        return JSONResponse(content=jsonable_encoder(message), status_code=500)

    return JSONResponse(content=jsonable_encoder({
        "user_id": data["user_id"],
        "place": {
            "chat_id": str(chat_id),
            "message_id": str(sent_message.message_id)
        },
        "date_time": sent_message.date.isoformat()
    }), status_code=200)


@fast_api_app.post("/keyboard/create")
async def create_keyboard(data: dict = Body()) -> JSONResponse:
    keyboard: list = list()
    print("/message")
    print(data)
    try:
        for i in data["buttons"]:
            keyboard.append([InlineKeyboardButton(text=i["text"], callback_data=i["text"])])
        reply_markup = InlineKeyboardMarkup(keyboard)
    except Exception as e:
        return JSONResponse(content=jsonable_encoder(
            {
                "code": 0,
                "message": "не переданы кнопки\n" + e.__str__(),
            }
        ), status_code=500)
    sent_message = await application.bot.send_message(
        chat_id=data["place"]["chat_id"],
        text=data["title"],
        reply_markup=reply_markup
    )
    return JSONResponse(content=jsonable_encoder(
        {
            "user_id": data["user_id"],
            "place": {
                "chat_id": data["place"]["chat_id"],
                "message_id": str(sent_message.message_id)
            },
            "date_time": sent_message.date.isoformat()
        }
    ), status_code=200)


@fast_api_app.post("/keyboard/update")
async def create_keyboard(data: dict = Body()) -> JSONResponse:
    print("/message")
    print(data)
    keyboard: list = list()
    try:
        for i in data["buttons"]:
            keyboard.append([InlineKeyboardButton(text=i["text"], callback_data=i["text"])])
        reply_markup = InlineKeyboardMarkup(keyboard)
    except Exception as e:
        return JSONResponse(content=jsonable_encoder(
            {
                "code": 0,
                "message": "не переданы кнопки\n" + e.__str__(),
            }
        ), status_code=500)
    sent_message = await application.bot.edit_message_text(
        chat_id=data["place"]["place"]["chat_id"],
        message_id=data["place"]["place"]["message_id"],
        text=data["title"],
        reply_markup=reply_markup
    )
    return JSONResponse(content=jsonable_encoder({
        "user_id": data["user_id"],
        "place": {
            "chat_id": str(sent_message.chat.id),
            "message_id": str(sent_message.message_id)
        },
        "date_time": sent_message.date.isoformat()
    }), status_code=200)


@fast_api_app.post("/image")
async def create_keyboard_with_photo(data: dict = Body()):
    # Декодируем base64 в байты (img_data)
    img_str = data["attachments_base64"][0]
    img_data = base64.b64decode(img_str)

    # создаем "виртуальный файл" для Telegram
    photo_file = io.BytesIO(img_data)
    photo_file.name = "image.jpg"  # Имя важно для корректного распознавания типа

    sent_message = await application.bot.send_photo(
        chat_id=data["place"]["chat_id"],
        photo=photo_file,
        caption=data.get("title", ""),  # Используем title как подпись к фото
    )
    return JSONResponse(content=jsonable_encoder(
            {
                "user_id": data["user_id"],
                "place": {
                    "chat_id": data["place"]["chat_id"],
                    "message_id": sent_message.message_id
                },
                "date_time": sent_message.date.isoformat()
            }
        ), status_code=200)


@fast_api_app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def catch_all(request: Request, full_path: str):
    print('стучатся не туда', request.url.path)
    return JSONResponse(
        status_code=404,
        content={"message": f"Путь /{full_path} с методом {request.method} не существует."}
    )