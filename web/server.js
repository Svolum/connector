const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const fileUpload = require('express-fileupload');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Создаем папку для хранения изображений
const IMAGES_DIR = path.join(__dirname, 'images');
if (!fs.existsSync(IMAGES_DIR)) {
  fs.mkdirSync(IMAGES_DIR);
}

// Middleware
app.use(express.json());
app.use(express.static(__dirname));
app.use('/images', express.static(IMAGES_DIR));
app.use(fileUpload());


// Эндпоинт для получения сообщений от бота
app.post('/user_message', (req, res) => {
  const chat_id = req.body.chat_id;
  const sender_nick = req.body.sender_nick;
  const text = req.body.text;
  if (chat_id && sender_nick && text) {
    io.emit('newMessage', chat_id, sender_nick, text);
    res.status(200).send('Сообщение получено');
  } else {
    res.status(400).send('Сообщение не предоставлено');
  }
});

// Эндпоинт для получения изображений от бота
app.post('/image', (req, res) => {
  const chat_id = req.body.chat_id;
  const sender_nick = req.body.sender_nick;
  const file_id = req.body.file_id;
  const image = req.files && req.files.image;
  if (chat_id && sender_nick && file_id && image) {
    const file_path = path.join(IMAGES_DIR, `${file_id}.jpg`);
    image.mv(file_path, (err) => {
      if (err) {
        console.error('Ошибка при сохранении изображения:', err);
        return res.status(500).send('Ошибка при сохранении изображения');
      }
      io.emit('newImage', chat_id, sender_nick, file_id);
      res.status(200).send('Изображение получено');
    });
  } else {
    res.status(400).send('Изображение или параметры не предоставлены');
  }
});

// Эндпоинт для обработки нажатий на клавиатуру
app.post('/keyboard/input', (req, res) => {
  const chat_id = req.body.chat_id;
  const sender_nick = req.body.sender_nick;
  const button = req.body.button;
  if (chat_id && sender_nick && button) {
    io.emit('newMessage', chat_id, sender_nick, button);
    res.status(200).send('Сообщение получено');
  } else {
    res.status(400).send('Сообщение не предоставлено');
  }
});

// Эндпоинт для отправки текста в Telegram
app.post('/message', (req, res) => {
  const chat_id = req.body.chat_id;
  const text = req.body.text; // Исправлено с sending_text на text для согласованности
  if (chat_id && text) {
    fetch('http://telegram-bot:8080/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, text })
    })
      .then(response => response.json())
      .then(data => res.status(200).json(data))
      .catch(error => res.status(500).json({ error: 'Не удалось отправить текст' }));
  } else {
    res.status(400).send('Не указаны chat_id или text');
  }
});

// Эндпоинт для отправки изображения в Telegram
app.post('/send_image', (req, res) => {
  const chat_id = req.body.chat_id;
  const image_url = req.body.image_url;
  if (chat_id && image_url) {
    fetch('http://telegram-bot:8080/image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, image_url })
    })
      .then(response => response.json())
      .then(data => res.status(200).json(data))
      .catch(error => res.status(500).json({ error: 'Не удалось отправить изображение' }));
  } else {
    res.status(400).send('Не указаны chat_id или image_url');
  }
});

// Эндпоинт для отправки клавиатуры в Telegram
app.post('/keyboard/create', (req, res) => {
  const chat_id = req.body.chat_id;
  const title = req.body.title;
  const buttons = req.body.buttons;
  if (!chat_id || !title || !buttons || buttons.length < 2) {
    return res.status(400).json({ error: 'Не указаны chat_id, title или недостаточно кнопок' });
  }
  fetch('http://telegram-bot:8080/keyboard/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id, title, buttons })
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        res.status(500).json({ error: data.error });
      } else {
        res.status(200).json({ message: 'Клавиатура успешно отправлена' });
      }
    })
    .catch(error => {
      console.error('Ошибка при отправке клавиатуры:', error);
      res.status(500).json({ error: 'Не удалось отправить клавиатуру' });
    });
});

// Сервируем HTML
app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

server.listen(3000, () => {
  console.log('Веб-сервер запущен на порту 3000');
});