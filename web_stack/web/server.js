const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const fileUpload = require('express-fileupload');

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
app.use(fileUpload({
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB max
}));

// Эндпоинт для получения сообщений от бота
app.post('/user_message', (req, res) => {
  const { chat_id, sender_nick, text } = req.body;
  if (chat_id && sender_nick && text) {
    io.emit('newMessage', chat_id, sender_nick, text);
    res.status(200).json({ status: 'success', message: 'Сообщение получено' });
  } else {
    res.status(400).json({ error: 'Сообщение не предоставлено' });
  }
});

// Эндпоинт для получения изображений от бота
app.post('/image', (req, res) => {
  const { chat_id, sender_nick, file_id } = req.body;
  const image = req.files?.image;
  
  if (chat_id && sender_nick && file_id && image) {
    const file_path = path.join(IMAGES_DIR, `${file_id}.jpg`);
    
    image.mv(file_path, (err) => {
      if (err) {
        console.error('Ошибка при сохранении изображения:', err);
        return res.status(500).json({ error: 'Ошибка при сохранении изображения' });
      }
      
      // Создаем URL для доступа к изображению
      const image_url = `http://${req.headers.host}/images/${file_id}.jpg`;
      io.emit('newImage', chat_id, sender_nick, file_id, image_url);
      res.status(200).json({ status: 'success', message: 'Изображение получено' });
    });
  } else {
    res.status(400).json({ error: 'Изображение или параметры не предоставлены' });
  }
});

// Эндпоинт для обработки нажатий на клавиатуру
app.post('/keyboard/input', (req, res) => {
  const { chat_id, sender_nick, button } = req.body;
  if (chat_id && sender_nick && button) {
    io.emit('newMessage', chat_id, sender_nick, button);
    res.status(200).json({ status: 'success', message: 'Сообщение получено' });
  } else {
    res.status(400).json({ error: 'Сообщение не предоставлено' });
  }
});

// Эндпоинт для отправки текста в Telegram
app.post('/message', async (req, res) => {
  const { chat_id, text } = req.body;
  if (!chat_id || !text) {
    return res.status(400).json({ error: 'Не указаны chat_id или text' });
  }

  try {
    const response = await fetch(`${TELEGRAM_BOT_URL}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, text })
    });
    
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error('Ошибка при отправке в Telegram бот:', error);
    res.status(500).json({ error: 'Не удалось отправить текст', details: error.message });
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
  const { chat_id, title, buttons } = req.body;
  
  if (!chat_id || !title || !buttons || buttons.length < 2) {
    return res.status(400).json({ error: 'Не указаны chat_id, title или недостаточно кнопок' });
  }

  try {
    const response = await fetch(`${TELEGRAM_BOT_URL}/keyboard/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, title, buttons })
    });
    
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    console.error('Ошибка при отправке клавиатуры в Telegram бот:', error);
    res.status(500).json({ error: 'Не удалось отправить клавиатуру', details: error.message });
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