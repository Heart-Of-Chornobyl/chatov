function initGeneralPage() {
    const sendBtn = document.getElementById('sendBtnGeneral');
    const inputField = document.getElementById('messageInput');
    const emojiToggleBtn = document.getElementById('emojiToggle');
    const emojiPicker = document.getElementById('emojiPicker');
    const emojiCategories = document.getElementById('emojiCategories');
    const emojiList = document.getElementById('emojiList');

    if (!sendBtn || !inputField || !emojiToggleBtn || !emojiPicker) return;

    // Закрити emojiPicker при кліку поза ним
    document.addEventListener('click', (e) => {
        if (!emojiPicker.contains(e.target) && !emojiToggleBtn.contains(e.target)) {
            emojiPicker.classList.remove('show');
        }
    });

    // Відкрити/закрити емодзі
    emojiToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        emojiPicker.classList.toggle('show');
    });

    // Надіслати повідомлення
    sendBtn.addEventListener('click', () => {
        const text = inputField.value.trim();
        if (text !== '') {
            const msg = document.createElement('div');
            msg.className = 'message outgoing';
            msg.textContent = text;
            document.getElementById('messages').appendChild(msg);
            inputField.value = '';
        }
    });

    // ✅ Завантажити emoji з правильного шляху
    fetch('js/emoji.json')
        .then((res) => res.json())
        .then((data) => initEmojiPicker(data))
        .catch((err) => console.error('Помилка завантаження emoji.json:', err));

    function initEmojiPicker(emojiData) {
        const categories = Object.keys(emojiData);

        emojiCategories.innerHTML = '';
        emojiList.innerHTML = '';

        categories.forEach((cat, idx) => {
            const btn = document.createElement('button');
            btn.className = 'emoji-category-btn';
            btn.textContent = cat;
            if (idx === 0) btn.classList.add('active');

            btn.addEventListener('click', () => {
                document.querySelectorAll('.emoji-category-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderEmojis(emojiData[cat]);
            });

            emojiCategories.appendChild(btn);
        });

        renderEmojis(emojiData[categories[0]]);
    }

    function renderEmojis(emojiArray) {
        emojiList.innerHTML = '';
        emojiArray.forEach((emoji) => {
            const span = document.createElement('span');
            span.className = 'emoji-item';
            span.textContent = emoji;
            span.addEventListener('click', () => {
                inputField.value += emoji;
                inputField.focus();
            });
            emojiList.appendChild(span);
        });
    }
}

// 🚀 Автоматичний запуск
initGeneralPage();
