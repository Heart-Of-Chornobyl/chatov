const menuItems = document.querySelectorAll('.menu-item');
const contentContainer = document.getElementById('pageContainer');
const chatMain = document.getElementById("chatMain");
const backBtn = document.getElementById("backBtn");

// Завантаження розділів
async function loadSection(fileName) {
  try {
    const response = await fetch(fileName);
    if (!response.ok) throw new Error('Файл не знайдено.');
    const html = await response.text();
    contentContainer.innerHTML = html;

    // Якщо general.html — підключаємо general.js
    if (fileName.includes('general.html')) {
      const script = document.createElement('script');
      script.src = 'js/general.js';
      script.defer = true;
      document.body.appendChild(script);
    }
  } catch (error) {
    contentContainer.innerHTML = `<div class="fallback">⚠️ Не вдалося завантажити контент.</div>`;
    console.error(error);
  }
}

// Меню секцій
menuItems.forEach(item => {
  item.addEventListener('click', () => {
    menuItems.forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    const section = item.dataset.page;
    loadSection(section);

    const title = item.textContent.trim();
    document.querySelector('.chat-title').textContent = title;

    if (window.innerWidth <= 768) {
      chatMain.classList.add("active");
    }
  });
});

// Кнопка Назад (мобільна)
backBtn?.addEventListener('click', () => {
  if (window.innerWidth <= 768) {
    chatMain.classList.remove("active");
  }
});

// Swipe-навігація (←) — мобільна з фільтром emoji
let touchStartX = 0;
let touchEndX = 0;

chatMain.addEventListener("touchstart", e => {
  if (window.innerWidth > 768) return;

  // 🛑 Якщо свайп почався в emojiPicker — ігноруємо
  if (e.target.closest('#emojiPicker')) return;

  touchStartX = e.changedTouches[0].screenX;
});

chatMain.addEventListener("touchend", e => {
  if (window.innerWidth > 768) return;

  // 🛑 Якщо свайп завершився в emojiPicker — ігноруємо
  if (e.target.closest('#emojiPicker')) return;

  touchEndX = e.changedTouches[0].screenX;
  if (touchEndX - touchStartX > 50) {
    chatMain.classList.remove("active");
  }
});

// Профіль для мобілки
const profileMobileBtn = document.getElementById('profileMobileBtn');
profileMobileBtn?.addEventListener('click', () => {
  loadSection("pages/profile.html");
  document.querySelector('.chat-title').textContent = "Профіль";
  if (window.innerWidth <= 768) {
    chatMain.classList.add("active");
  }
});

// Профіль для десктопа
const profileDesktopBtn = document.getElementById('profileIcon');
profileDesktopBtn?.addEventListener('click', () => {
  loadSection("pages/profile.html");
  document.querySelector('.chat-title').textContent = "Профіль";
});
