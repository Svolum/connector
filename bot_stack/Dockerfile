FROM python:3.10-slim

# Рабочая директория (лучше не в корень /)
WORKDIR /app

# Сначала копируются только зависимости (для слоев контейнера)
COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Всё остальное
COPY bot/main.py bot/tg_api.py bot/tg_handlers.py bot/load_env.py .

EXPOSE 8000

CMD ["python", "main.py"]