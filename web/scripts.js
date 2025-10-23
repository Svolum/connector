
const socket = io();
const messagesDiv = document.getElementById('messages');

socket.on('newMessage', (chat_id, sender_nick, text) => {
    const message = `${chat_id}|${sender_nick}: ${text}`;
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.textContent = message;
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});

function sendText() {
    const chat_id = document.getElementById('chat_id').value;
    const sending_text = document.getElementById('sending_text').value;
    if (!chat_id || !sending_text) {
        alert('Пожалуйста, введите chat_id и sending_text');
        return;
    }
    fetch('/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id, sending_text })
    })
    .then(response => response.json())
    .then(data => {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        messageElement.textContent = data.message || 'Ошибка: ' + data.error;
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        if (data.message) {
            document.getElementById('sending_text').value = ''; // Очищаем поле вопроса
        }
    })
    .catch(error => {
        console.error('Ошибка при отправке вопроса:', error);
        alert('Ошибка при отправке вопроса');
    });
}

function add_button() {
    // Запрашиваем текст для новой кнопки
    const buttonText = prompt("Введите текст для кнопки:");

    if (buttonText) {
        const ul = document.querySelector("#send-keyboard-form ul");
        const li = document.createElement("li");
        li.textContent = buttonText;
        ul.appendChild(li);
    }
}
    
function sendKeyboard() {
    const chat_id = document.getElementById('keyboard_chat_id').value;
    const title = document.getElementById('keyboard_title').value;
    const li_elts = document.getElementById("button_vals").querySelectorAll("li");

    // Проверка на наличие кнопок
    if (li_elts.length < 2) {
        alert('Добавьте как минимум 2 кнопки');
        return;
    }

    const buttons = Array.from(li_elts).map(li => li.textContent);

    if (!chat_id || !title) {
        alert('Пожалуйста, введите chat_id и keyboard_title');
        return;
    }

    fetch('/keyboard/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id, title, buttons })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Ошибка: ${data.error}`);
        } else {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message');
            messageElement.textContent = `Клавиатура отправлена: ${data.message}`;
            messagesDiv.appendChild(messageElement);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    })
    .catch(error => {
        console.error('Ошибка при отправке клавиатуры:', error);
        alert('Ошибка при отправке клавиатуры');
    });
}
