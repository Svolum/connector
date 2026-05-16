const socket = io();

let buttons = [];

function add_button() {
  const buttonText = prompt('Введите текст для кнопки:');

  if (buttonText && buttonText.trim()) {
    buttons.push(buttonText.trim());
    updateButtonList();
  }
}

function updateButtonList() {
  const buttonList = document.getElementById('button_vals');
  buttonList.innerHTML = '';

  buttons.forEach((button, index) => {
    const li = document.createElement('li');
    li.textContent = button + ' ';

    const removeBtn = document.createElement('button');
    removeBtn.textContent = 'Удалить';
    removeBtn.onclick = () => {
      buttons.splice(index, 1);
      updateButtonList();
    };

    li.appendChild(removeBtn);
    buttonList.appendChild(li);
  });
}

async function readJsonResponse(response) {
  const text = await response.text();

  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function getErrorMessage(result) {
  return result.error || result.detail || result.message || 'Неизвестная ошибка';
}

async function sendText() {
  const chat_id = document.getElementById('chat_id').value.trim();
  const text = document.getElementById('sending_text').value.trim();

  if (!chat_id || !text) {
    alert('Заполните chat_id и текст');
    return;
  }

  try {
    const response = await fetch('/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: chat_id,
        place: { chat_id },
        text,
      }),
    });

    const result = await readJsonResponse(response);

    if (response.ok) {
      addNewMessage({
        chat_id,
        sender_nick: 'Оператор',
        text,
        type: 'operator_message',
      });

      showNotification('Текст отправлен', 'success');
      document.getElementById('sending_text').value = '';
    } else {
      showNotification('Ошибка отправки текста: ' + getErrorMessage(result), 'error');
    }
  } catch (error) {
    showNotification('Ошибка отправки текста: ' + error.message, 'error');
    console.error('Ошибка отправки текста:', error);
  }
}

async function sendImage() {
  showNotification(
    'Отправка изображения в Telegram не поддерживается текущим API бота',
    'error'
  );
}

async function sendKeyboard() {
  const chat_id = document.getElementById('keyboard_chat_id').value.trim();
  const title = document.getElementById('keyboard_title').value.trim();

  if (!chat_id || !title || buttons.length === 0) {
    alert('Заполните chat_id, title и добавьте хотя бы одну кнопку');
    return;
  }

  try {
    const response = await fetch('/keyboard/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: chat_id,
        place: { chat_id },
        title,
        buttons: buttons.map((text) => ({ text })),
      }),
    });

    const result = await readJsonResponse(response);

    if (response.ok) {
      const message_id = result?.place?.message_id;

      addNewMessage({
        chat_id,
        sender_nick: 'Оператор',
        text: `${title}: ${buttons.join(', ')}`,
        type: 'operator_keyboard',
        message_id,
      });

      showNotification('Клавиатура отправлена', 'success');

      document.getElementById('keyboard_title').value = '';
      document.getElementById('keyboard_chat_id').value = '';

      // Заполняем поля update формы
      if (message_id) {
        document.getElementById('update_chat_id').value = chat_id;
        document.getElementById('update_message_id').value = message_id;
      }

      buttons = [];
      updateButtonList();
    } else {
      showNotification('Ошибка отправки клавиатуры: ' + getErrorMessage(result), 'error');
    }
  } catch (error) {
    showNotification('Ошибка отправки клавиатуры: ' + error.message, 'error');
    console.error('Ошибка отправки клавиатуры:', error);
  }
}

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');

  notification.className = `notification ${type}`;
  notification.textContent = message;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.opacity = '0';

    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 4000);
}

function addNewMessage({ chat_id, sender_nick, text, type = 'message', date_time = null, message_id = null }) {

  const messagesDiv = document.getElementById('messages');

  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${type}`;

  const strong = document.createElement('strong');
  strong.textContent = `${sender_nick} (${chat_id ?? 'null'}):`;

  const span = document.createElement('span');
  span.textContent = ` ${text}`;

  messageDiv.appendChild(strong);
  messageDiv.appendChild(span);
  if (message_id) {
    const mid = document.createElement('div');
    mid.className = 'message-meta';
    mid.textContent = `message_id: ${message_id}`;
    messageDiv.appendChild(mid);
  }

  if (date_time) {
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = date_time;
    messageDiv.appendChild(time);
  }

  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addNewImage({ chat_id, image_url, date_time = null }) {
  const messagesDiv = document.getElementById('messages');

  const messageDiv = document.createElement('div');
  messageDiv.className = 'message image-message';

  const strong = document.createElement('strong');
  strong.textContent = `Пользователь (${chat_id ?? 'null'}):`;

  const br = document.createElement('br');

  const img = document.createElement('img');
  img.src = image_url;
  img.alt = 'Изображение';
  img.className = 'message-image';

  const link = document.createElement('a');
  link.href = image_url;
  link.target = '_blank';
  link.textContent = 'Открыть изображение';

  messageDiv.appendChild(strong);
  messageDiv.appendChild(br);
  messageDiv.appendChild(img);
  messageDiv.appendChild(document.createElement('br'));
  messageDiv.appendChild(link);

  if (date_time) {
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = date_time;
    messageDiv.appendChild(time);
  }

  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendKeyboardUpdate() {
  const chat_id = document.getElementById('update_chat_id').value.trim();
  const message_id = document.getElementById('update_message_id').value.trim();
  const title = document.getElementById('update_keyboard_title').value.trim();

  if (!chat_id || !message_id || !title || buttons_update.length === 0) {
    alert('Заполните все поля и добавьте хотя бы одну кнопку');
    return;
  }

  try {
    const response = await fetch('/keyboard/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: chat_id,
        place: {
          place: { chat_id, message_id },
        },
        title,
        buttons: buttons_update.map((text) => ({ text })),
      }),
    });

    if (response.ok) {
      addNewMessage({
        chat_id,
        sender_nick: 'Оператор',
        text: `[обновление] ${title}: ${buttons_update.join(', ')}`,
        type: 'operator_keyboard',
      });

      showNotification('Клавиатура обновлена', 'success');

      document.getElementById('update_keyboard_title').value = '';
      buttons_update = [];
      updateButtonUpdateList();
    } else {
      const result = await readJsonResponse(response);
      console.log('keyboard/create result in browser:', result);
      showNotification('Ошибка обновления~: ' + getErrorMessage(result), 'error');
    }
  } catch (error) {
    showNotification('Ошибка обновления: ' + error.message, 'error');
  }
}

let buttons_update = [];

function add_button_update() {
  const buttonText = prompt('Введите текст для кнопки:');
  if (buttonText && buttonText.trim()) {
    buttons_update.push(buttonText.trim());
    updateButtonUpdateList();
  }
}

function updateButtonUpdateList() {
  const buttonList = document.getElementById('button_update_vals');
  buttonList.innerHTML = '';

  buttons_update.forEach((button, index) => {
    const li = document.createElement('li');
    li.textContent = button + ' ';

    const removeBtn = document.createElement('button');
    removeBtn.textContent = 'Удалить';
    removeBtn.onclick = () => {
      buttons_update.splice(index, 1);
      updateButtonUpdateList();
    };

    li.appendChild(removeBtn);
    buttonList.appendChild(li);
  });
}

socket.on('newMessage', (payload) => {
  const user_id = payload.user_id;
  const chat_id = payload.place?.chat_id || user_id;
  const text = payload.text;
  const type = payload.type || 'message';
  const date_time = payload.date_time;

  const sender =
    type === 'keyboard_input' ? 'Пользователь нажал кнопку' :
    type === 'command'        ? 'Команда' :
    type === 'action'         ? 'Действие над сообщением' :
    'Пользователь';


  addNewMessage({
    chat_id,
    sender_nick: sender,
    text,
    type,
    date_time,
  });
});

socket.on('newImage', (payload) => {
  const user_id = payload.user_id;
  const chat_id = payload.place?.chat_id || user_id;

  addNewImage({
    chat_id,
    image_url: payload.image_url,
    date_time: payload.date_time,
  });
});

socket.on('connect', () => {
  showNotification('Подключено к серверу', 'success');
});

socket.on('disconnect', () => {
  showNotification('Отключено от сервера', 'error');
});