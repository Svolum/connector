const express = require('express');
const http = require('http');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.json());
app.use(express.static(__dirname));

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

// Эндпоинт для отправки вопроса в Telegram
app.post('/message', (req, res) => {
  const chat_id = req.body.chat_id;
  const sending_text  = req.body.sending_text;
  if (chat_id && sending_text) {
    fetch('http://telegram-bot:8080/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id, sending_text })
    })
      .then(response => response.json())
      .then(data => res.status(200).json(data))
      .catch(error => res.status(500).json({ error: 'Не удалось отправить вопрос' }));
  } else {
    res.status(400).send('Не указаны chat_id или question');
  }
});

// Сервируем HTML
app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

server.listen(3000, () => {
  console.log('Веб-сервер запущен на порту 3000');
});