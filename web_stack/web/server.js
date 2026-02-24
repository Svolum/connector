const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Конфигурация
const TELEGRAM_BOT_URL = process.env.TELEGRAM_BOT_URL || 'http://localhost:8080';
const IMAGES_DIR = path.join(__dirname, 'images');

// Создаем папку для хранения изображений
if (!fs.existsSync(IMAGES_DIR)) {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });
}

// Middleware
app.use(express.json());
app.use(express.static(__dirname));
app.use('/images', express.static(IMAGES_DIR));

// Эндпоинт для получения сообщений от бота
app.post('/user_message', (req, res) => {
  const { user_id, place, text } = req.body;

  const chat_id = place?.chat_id;

  if (user_id && chat_id && text) {
    io.emit('newMessage', user_id, text);
    res.status(200).json({ status: 'success' });
  } else {
    res.status(400).json({ error: 'Некорректные данные' });
  }
});

// Эндпоинт для получения изображений от бота
app.post('/image', (req, res) => {
  const { user_id, place, attachments_base64, date_time } = req.body;
  const chat_id = place?.chat_id;

  if (!user_id || !chat_id || !attachments_base64?.length) {
    return res.status(400).json({ error: 'Некорректные данные' });
  }

  try {
    const buffer = Buffer.from(attachments_base64[0], 'base64');
    const fileName = `${Date.now()}.jpg`;
    const filePath = path.join(IMAGES_DIR, fileName);

    fs.writeFileSync(filePath, buffer);

    const image_url = `http://${req.headers.host}/images/${fileName}`;

    io.emit('newImage', user_id, image_url, date_time);

    res.status(200).json({ status: 'success' });

  } catch (err) {
    console.error('Ошибка сохранения изображения:', err);
    res.status(500).json({ error: 'Ошибка сохранения изображения' });
  }
});

// Эндпоинт для обработки нажатий на клавиатуру
app.post('/keyboard/input', (req, res) => {
  const { user_id, button, place, date_time } = req.body;
  const chat_id = place?.chat_id;

  if (user_id && chat_id && button) {
    io.emit('newMessage', user_id, button);
    res.status(200).json({ status: 'success' });
  } else {
    res.status(400).json({ error: 'Некорректные данные' });
  }
});

// Эндпоинт для отправки текста в Telegram
app.post('/message', async (req, res) => {
  const { user_id, place, text } = req.body;
  const chat_id = place?.chat_id;

  if (!user_id || !chat_id || !text) {
    return res.status(400).json({ error: 'Некорректные данные' });
  }

  try {
    const response = await fetch(`${TELEGRAM_BOT_URL}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        place: { chat_id },
        text
      })
    });

    const data = await response.json();
    res.status(response.status).json(data);

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Эндпоинт для отправки изображения в Telegram
app.post('/send_image', async (req, res) => {
  const { chat_id, image_url } = req.body;
  if (!chat_id || !image_url) {
    return res.status(400).json({ error: 'Не указаны chat_id или image_url' });
  }

  try {
    const response = await fetch(`${TELEGRAM_BOT_URL}/image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, image_url })
    });
    
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error('Ошибка при отправке изображения в Telegram бот:', error);
    res.status(500).json({ error: 'Не удалось отправить изображение', details: error.message });
  }
});

// Эндпоинт для отправки клавиатуры в Telegram
app.post('/keyboard/create', async (req, res) => {
  const { user_id, place, title, buttons } = req.body;
  const chat_id = place?.chat_id;

  if (!user_id || !chat_id || !title || !buttons || buttons.length < 2) {
    return res.status(400).json({ error: 'Некорректные данные' });
  }

  try {
    const response = await fetch(`${TELEGRAM_BOT_URL}/keyboard/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        place: { chat_id },
        title,
        buttons
      })
    });

    const data = await response.json();
    res.status(response.status).json(data);

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Сервируем HTML
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`🌐 Веб-сервер запущен на порту ${PORT}`);
  console.log(`🤖 URL бота: ${TELEGRAM_BOT_URL}`);
});
