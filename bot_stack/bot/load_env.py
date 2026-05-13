import os


SELF_URL = os.getenv("SELF_URL", "https://tgbot.xmilitary.ru")
WEB_URL: str = os.getenv("WEB_URL", "http://127.0.0.1:8000")
PORT = os.getenv("PORT", "8000")
TOKEN = os.getenv("TOKEN")
WEBHOO_PATH = os.getenv("WEBHOO_PATH", "telegram")
PROXY_URL = os.getenv("PROXY_URL", "http://89.232.185.113:3128")
HTTPX_HEADER_NAME = 'X-Connector-Name'
HTTPX_HEADER_CONNECTOR_NAME = 'tg'