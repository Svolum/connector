const socket = io();

let buttons = [];

function add_button() {
    const buttonText = prompt('Введите текст для кнопки:');
    if (buttonText) {
        buttons.push(buttonText);
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
                text
            })
        });

        const result = await response.json();

        if (response.ok) {
            addNewMessage(chat_id, 'Вы', text);
            showNotification('Текст отправлен: ' + (result.message || 'Успешно'), 'success');
            document.getElementById('sending_text').value = '';
        } else {
            showNotification('Ошибка отправки текста: ' + (result.error || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        showNotification('Ошибка отправки текста: ' + error.message, 'error');
        console.error('Ошибка отправки текста:', error);
    }
}

async function sendImage() {
    const chat_id = document.getElementById('image_chat_id').value.trim();
    const fileInput = document.getElementById('image_file');
    const file = fileInput.files[0];

    if (!chat_id || !file) {
        alert('Заполните chat_id и выберите файл');
        return;
    }

    try {
        const base64 = await fileToBase64(file);

        const response = await fetch('/send_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: chat_id,
                place: { chat_id },
                attachments_base64: [base64]
            })
        });

        const result = await response.json();

        if (response.ok) {
            showNotification('Изображение отправлено: ' + (result.message || 'Успешно'), 'success');
            fileInput.value = '';
        } else {
            showNotification('Ошибка отправки изображения: ' + (result.error || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        showNotification('Ошибка отправки изображения: ' + error.message, 'error');
        console.error('Ошибка отправки изображения:', error);
    }
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => {
            const result = String(reader.result);
            resolve(result.split(',')[1]);
        };

        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function sendKeyboard() {
    const chat_id = document.getElementById('keyboard_chat_id').value.trim();
    const title = document.getElementById('keyboard_title').value.trim();

    if (!chat_id || !title || buttons.length < 2) {
        alert('Заполните chat_id, title и добавьте хотя бы 2 кнопки');
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
                buttons: buttons.map(text => ({ text }))
            })
        });

        const result = await response.json();

        if (response.ok) {
            addNewMessage(chat_id, 'Оператор', `${title}: ${buttons.join(', ')}`);
            showNotification('Клавиатура отправлена: ' + (result.message || 'Успешно'), 'success');

            document.getElementById('keyboard_title').value = '';
            document.getElementById('keyboard_chat_id').value = '';
            buttons = [];
            updateButtonList();
        } else {
            showNotification('Ошибка отправки клавиатуры: ' + (result.error || 'Неизвестная ошибка'), 'error');
        }
    } catch (error) {
        showNotification('Ошибка отправки клавиатуры: ' + error.message, 'error');
        console.error('Ошибка отправки клавиатуры:', error);
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        z-index: 1000;
        max-width: 300px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: opacity 0.3s ease;
    `;

    if (type === 'success') {
        notification.style.backgroundColor = '#4CAF50';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#f44336';
    } else {
        notification.style.backgroundColor = '#2196F3';
    }

    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

function addNewMessage(chat_id, sender_nick, text) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';

    const strong = document.createElement('strong');
    strong.textContent = `${sender_nick} (${chat_id}):`;

    const span = document.createElement('span');
    span.textContent = ` ${text}`;

    messageDiv.appendChild(strong);
    messageDiv.appendChild(span);

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

socket.on('newMessage', (user_id, place, text) => {
    // console.log(chat_id);
    addNewMessage(user_id, 'Пользователь', text);
});

socket.on('newImage', (chat_id, image_url, date_time) => {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';

    const strong = document.createElement('strong');
    strong.textContent = `Пользователь (${chat_id}):`;

    const br = document.createElement('br');
    const img = document.createElement('img');
    img.src = image_url;
    img.alt = 'Изображение';
    img.style.maxWidth = '200px';

    messageDiv.appendChild(strong);
    messageDiv.appendChild(br);
    messageDiv.appendChild(img);

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});

socket.on('connect', () => {
    showNotification('Подключено к серверу', 'success');
});

socket.on('disconnect', () => {
    showNotification('Отключено от сервера', 'error');
});
