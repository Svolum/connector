const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// =========================
// Config
// =========================

const TELEGRAM_BOT_URL = process.env.TELEGRAM_BOT_URL || 'http://localhost:8000';
const IMAGES_DIR = path.join(__dirname, 'images');

// =========================
// Init
// =========================

if (!fs.existsSync(IMAGES_DIR)) {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });
}

// =========================
// Middleware
// =========================

app.use(express.json({ limit: '50mb' }));
app.use(express.static(__dirname));
app.use('/images', express.static(IMAGES_DIR));

// =========================
// Helpers
// =========================

async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function readResponseBody(response) {
  const raw = await response.text();

  if (!raw) {
    return {};
  }

  try {
    return JSON.parse(raw);
  } catch {
    return { raw };
  }
}

function getPublicBaseUrl(req) {
  const proto = req.headers['x-forwarded-proto'] || req.protocol;
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  return `${proto}://${host}`;
}

function stripBase64Prefix(value) {
  if (typeof value !== 'string') {
    return '';
  }

  const commaIndex = value.indexOf(',');

  if (value.startsWith('data:') && commaIndex !== -1) {
    return value.slice(commaIndex + 1);
  }

  return value;
}

function detectImageExtension(buffer) {
  if (buffer.length >= 4) {
    const hex = buffer.subarray(0, 4).toString('hex');

    if (hex.startsWith('ffd8ff')) return 'jpg';
    if (hex === '89504e47') return 'png';
    if (hex === '47494638') return 'gif';
    if (buffer.subarray(0, 4).toString() === 'RIFF') return 'webp';
  }

  return 'jpg';
}

function validateCommonPayload(user_id, place) {
  const chat_id = place?.chat_id;

  if (!user_id || !chat_id) {
    return {
      ok: false,
      error: 'Некорректные данные: нужны user_id и place.chat_id',
    };
  }

  return {
    ok: true,
    chat_id,
  };
}

function emitMessage({ user_id, place, text, type = 'message', date_time }) {
  io.emit('newMessage', {
    user_id,
    place,
    text,
    type,
    date_time: date_time || new Date().toISOString(),
  });
}

function emitImage({ user_id, place, image_url, date_time }) {
  io.emit('newImage', {
    user_id,
    place,
    image_url,
    date_time: date_time || new Date().toISOString(),
  });
}

// =========================
// API веб-интерфейса
// Эти endpoints вызывает Telegram bot
// =========================

app.post('/user_message', (req, res) => {
  const { user_id, place, text, date_time } = req.body;
  const validation = validateCommonPayload(user_id, place);

  console.log('POST /user_message BODY:', req.body);

  if (!validation.ok || !text) {
    return res.status(400).json({
      error: 'Некорректные данные: нужны user_id, place.chat_id и text',
    });
  }

  emitMessage({
    user_id,
    place,
    text,
    type: 'user_message',
    date_time,
  });

  return res.status(200).json({
    status: 'success',
  });
});

app.post('/image', (req, res) => {
  const { user_id, place, attachments_base64, date_time } = req.body;
  const validation = validateCommonPayload(user_id, place);

  console.log('POST /image BODY:', {
    user_id,
    place,
    attachments_count: Array.isArray(attachments_base64) ? attachments_base64.length : 0,
    date_time,
  });

  if (!validation.ok || !Array.isArray(attachments_base64) || attachments_base64.length === 0) {
    return res.status(400).json({
      error: 'Некорректные данные: нужны user_id, place.chat_id и attachments_base64',
    });
  }

  const savedImages = [];

  try {
    for (const attachment of attachments_base64) {
      if (!attachment) {
        continue;
      }

      const clearBase64 = stripBase64Prefix(attachment);
      const buffer = Buffer.from(clearBase64, 'base64');

      if (!buffer.length) {
        continue;
      }

      const ext = detectImageExtension(buffer);
      const fileName = `${Date.now()}-${Math.random().toString(16).slice(2)}.${ext}`;
      const filePath = path.join(IMAGES_DIR, fileName);

      fs.writeFileSync(filePath, buffer);

      const image_url = `${getPublicBaseUrl(req)}/images/${fileName}`;
      savedImages.push(image_url);

      emitImage({
        user_id,
        place,
        image_url,
        date_time,
      });
    }

    if (savedImages.length === 0) {
      return res.status(400).json({
        error: 'Не удалось сохранить изображения',
      });
    }

    return res.status(200).json({
      status: 'success',
      image_urls: savedImages,
    });
  } catch (err) {
    console.error('Ошибка сохранения изображения:', err);

    return res.status(500).json({
      error: 'Ошибка сохранения изображения',
      details: err.message,
    });
  }
});

app.post('/keyboard/input', (req, res) => {
  const { user_id, button, place, date_time } = req.body;
  const validation = validateCommonPayload(user_id, place);

  console.log('POST /keyboard/input BODY:', req.body);

  if (!validation.ok || !button) {
    return res.status(400).json({
      error: 'Некорректные данные: нужны user_id, place.chat_id и button',
    });
  }

  emitMessage({
    user_id,
    place,
    text: button,
    type: 'keyboard_input',
    date_time,
  });

  return res.status(200).json({
    status: 'success',
  });
});

// =========================
// API заглушки
// Эти endpoints вызывает браузерный интерфейс
// Они проксируют запросы в Telegram bot
// =========================

app.post('/message', async (req, res) => {
  const { user_id, place, text } = req.body;
  const validation = validateCommonPayload(user_id, place);

  console.log('POST /message BODY:', req.body);

  if (!validation.ok || !text) {
    return res.status(400).json({
      error: 'Некорректные данные: нужны user_id, place.chat_id и text',
    });
  }

  try {
    const response = await fetchWithTimeout(`${TELEGRAM_BOT_URL}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        place: {
          chat_id: validation.chat_id,
        },
        text,
      }),
    });

    const data = await readResponseBody(response);

    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Ошибка при отправке сообщения в Telegram bot:', error);

    if (error.name === 'AbortError') {
      return res.status(504).json({
        error: 'Таймаут при обращении к Telegram bot service',
      });
    }

    return res.status(500).json({
      error: 'Не удалось отправить сообщение',
      details: error.message,
    });
  }
});

app.post('/keyboard/create', async (req, res) => {
  const { user_id, place, title, buttons } = req.body;
  const validation = validateCommonPayload(user_id, place);

  console.log('POST /keyboard/create BODY:', req.body);

  if (!validation.ok || !title || !Array.isArray(buttons) || buttons.length === 0) {
    return res.status(400).json({
      error: 'Некорректные данные: нужны user_id, place.chat_id, title и buttons',
    });
  }

  const normalizedButtons = buttons
    .map((button) => {
      if (typeof button === 'string') {
        return { text: button };
      }

      return button;
    })
    .filter((button) => button && typeof button.text === 'string' && button.text.trim());

  if (normalizedButtons.length === 0) {
    return res.status(400).json({
      error: 'Некорректные данные: buttons должны содержать text',
    });
  }

  try {
    const response = await fetchWithTimeout(`${TELEGRAM_BOT_URL}/keyboard/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        place: {
          chat_id: validation.chat_id,
        },
        title,
        buttons: normalizedButtons,
      }),
    });

    const data = await readResponseBody(response);

    return res.status(response.status).json(data);
  } catch (error) {
    console.error('Ошибка при отправке клавиатуры в Telegram bot:', error);

    if (error.name === 'AbortError') {
      return res.status(504).json({
        error: 'Таймаут при обращении к Telegram bot service',
      });
    }

    return res.status(500).json({
      error: 'Не удалось отправить клавиатуру',
      details: error.message,
    });
  }
});

// Этот endpoint оставлен специально, чтобы интерфейс явно говорил,
// что отправка изображений из web в Telegram невозможна с текущим API бота.
app.post('/send_image', (req, res) => {
  console.log('POST /send_image BODY:', req.body);

  return res.status(501).json({
    error: 'Отправка изображения из web в Telegram не поддерживается текущим API бота',
    details: 'В готовом боте есть /message и /keyboard/create, но нет endpoint для отправки изображения в Telegram.',
  });
});

// =========================
// Pages / health
// =========================

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    telegram_bot_url: TELEGRAM_BOT_URL,
  });
});

// =========================
// Socket.IO
// =========================

io.on('connection', (socket) => {
  console.log('Socket connected:', socket.id);

  socket.on('disconnect', () => {
    console.log('Socket disconnected:', socket.id);
  });
});

// =========================
// Start
// =========================

server.listen(3000, '0.0.0.0', () => {
  console.log(`Веб-заглушка запущена на порту 3000`);
  console.log(`Telegram bot URL: ${TELEGRAM_BOT_URL}`);
});