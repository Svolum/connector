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
        li.textContent = button;
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
    const chat_id = document.getElementById('chat_id').value;
    const text = document.getElementById('sending_text').value;
    
    if (!chat_id || !text) {
        alert('Заполните chat_id и текст');
        return;
    }

    try {
        const response = await fetch('/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id, text })
        })
        .then(response => response.json())
        .then(data => {
            // const messageElement = document.createElement('div');
            // messageElement.classList.add('message');
            // messageElement.textContent = data.message || 'Ошибка: ' + data.error;
            // messagesDiv.appendChild(messageElement);
            // messagesDiv.scrollTop = messagesDiv.scrollHeight;
            // if (data.message) {
            //     document.getElementById('sending_text').value = ''; // Очищаем поле вопроса
            // }
            addNewMessage ("оператор", "вы", text)
        });
        const result = await response.json();
        showNotification('Текст отправлен: ' + (result.message || 'Успешно'), 'success');
        console.log('Текст отправлен:', result);
    } catch (error) {
        showNotification('Ошибка отправки текста: ' + error.message, 'error');
        console.error('Ошибка отправки текста:', error);
    }
}

async function sendImage() {
    const chat_id = document.getElementById('image_chat_id').value;
    const fileInput = document.getElementById('image_file');
    const file = fileInput.files[0];
    
    if (!chat_id || !file) {
        alert('Заполните chat_id и выберите файл');
        return;
    }

    const formData = new FormData();
    formData.append('chat_id', chat_id);
    formData.append('image', file);

    try {
        const response = await fetch('/send_image', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Изображение отправлено: ' + (result.message || 'Успешно'), 'success');
            // Очищаем поле файла после успешной отправки
            fileInput.value = '';
        } else {
            showNotification('Ошибка отправки изображения: ' + (result.error || 'Неизвестная ошибка'), 'error');
        }
        console.log('Изображение отправлено:', result);
    } catch (error) {
        showNotification('Ошибка отправки изображения: ' + error.message, 'error');
        console.error('Ошибка отправки изображения:', error);
    }
}

async function sendKeyboard() {
    const chat_id = document.getElementById('keyboard_chat_id').value;
    const title = document.getElementById('keyboard_title').value;
    
    if (!chat_id || !title || buttons.length < 2) {
        alert('Заполните chat_id, title и добавьте хотя бы 2 кнопки');
        return;
    }

    try {
        const response = await fetch('/keyboard/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id, title, buttons })
        }).then(response => response.json()).then(data => {
            addNewMessage ('оператор/клавиатура', 'Вы', buttons)
        });
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Клавиатура отправлена: ' + (result.message || 'Успешно'), 'success');
            // Очищаем форму после успешной отправки
            document.getElementById('keyboard_title').value = '';
            document.getElementById('keyboard_chat_id').value = '';
            buttons = [];
            updateButtonList();
        } else {
            showNotification('Ошибка отправки клавиатуры: ' + (result.error || 'Неизвестная ошибка'), 'error');
        }
        console.log('Клавиатура отправлена:', result);
    } catch (error) {
        showNotification('Ошибка отправки клавиатуры: ' + error.message, 'error');
        console.error('Ошибка отправки клавиатуры:', error);
    }
}

// Функция для показа уведомлений
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
    
    // Цвета в зависимости от типа уведомления
    if (type === 'success') {
        notification.style.backgroundColor = '#4CAF50';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#f44336';
    } else {
        notification.style.backgroundColor = '#2196F3';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Обработка входящих сообщений
socket.on('newMessage', addNewMessage);

function addNewMessage (chat_id, sender_nick, text){
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.innerHTML = `<strong>${sender_nick} (${chat_id}):</strong> ${text}`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

socket.on('newImage', (chat_id, sender_nick, file_id) => {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.innerHTML = `<strong>${sender_nick} (${chat_id}):</strong> 
                           <img src="/images/${file_id}.jpg" alt="Изображение" style="max-width: 200px;">`;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});

// Показываем уведомление при подключении к серверу
socket.on('connect', () => {
    showNotification('Подключено к серверу', 'success');
});

socket.on('disconnect', () => {
    showNotification('Отключено от сервера', 'error');
});