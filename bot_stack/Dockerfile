FROM python:3.10-slim

WORKDIR /app

COPY ./bot/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./bot/bot.py ./

EXPOSE 8000

CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8001"]