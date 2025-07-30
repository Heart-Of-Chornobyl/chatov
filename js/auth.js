// Перемикання між формами
const SITE_KEY = '6LejYZQrAAAAAF6KjC63ymhGuoU5lNRdpRt4Hkln';
const loginToggle = document.getElementById("loginToggle");
const registerToggle = document.getElementById("registerToggle");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");

loginToggle.addEventListener("click", () => {
  loginToggle.classList.add("active");
  registerToggle.classList.remove("active");
  loginForm.classList.add("active");
  registerForm.classList.remove("active");
});

registerToggle.addEventListener("click", () => {
  registerToggle.classList.add("active");
  loginToggle.classList.remove("active");
  registerForm.classList.add("active");
  loginForm.classList.remove("active");
});

document.getElementById("toRegister").onclick = () => registerToggle.click();
document.getElementById("toLogin").onclick = () => loginToggle.click();

// 🎨 Слогани
const sloganElement = document.getElementById("slogan");
const slogans = [
  "Ніч. Тиша. Лише твої слова.",
  "Пиши, коли мовчать усі.",
  "Справжні думки народжуються в темряві.",
  "Нічне світло — для душевних розмов.",
  "Тиша ночі говорить більше.",
  "Пиши просто. Пиши щиро.",
  "Твої слова залишаються тут."
];

function changeSlogan() {
  let newSlogan;
  do {
    newSlogan = slogans[Math.floor(Math.random() * slogans.length)];
  } while (newSlogan === sloganElement.innerText);
  sloganElement.innerText = newSlogan;
}
sloganElement.innerText = slogans[Math.floor(Math.random() * slogans.length)];

// 🎨 Градієнт
const gradients = [
  "radial-gradient(ellipse at bottom, #0a0f1c 0%, #070c16 70%, #060b13 100%)",
  "radial-gradient(ellipse at center, #0b101d 0%, #09131f 80%, #070e18 100%)",
  "radial-gradient(ellipse at top, #0c121f 0%, #0a111d 70%, #070d16 100%)"
];
let currentGradient = 0;
document.body.addEventListener("click", (e) => {
  const box = document.querySelector(".auth-box");
  if (!box.contains(e.target)) {
    currentGradient = (currentGradient + 1) % gradients.length;
    document.body.style.background = gradients[currentGradient];
  }
});

// 🔐 Відновлення доступу
const recoverToggle = document.getElementById("recoverToggle");
const recoverForm = document.getElementById("recoverForm");
recoverToggle.addEventListener("click", () => {
  recoverForm.style.display = recoverForm.style.display === "flex" ? "none" : "flex";
});

// --- Invisible reCAPTCHA callbacks ---
function onLoginSubmit(token) {
  loginForm.dataset.recaptchaToken = token;
  loginForm.requestSubmit();
}

function onRegisterSubmit(token) {
  registerForm.dataset.recaptchaToken = token;
  registerForm.requestSubmit();
}

// ✅ Обробка входу
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const token = loginForm.dataset.recaptchaToken;
  if (!token) {
    grecaptcha.execute(); // Запускаємо invisible reCAPTCHA
    return;
  }

  const email = loginForm.querySelector("input[name='email']").value.trim();
  const password = loginForm.querySelector("input[name='password']").value;

  // Перевіряємо email тільки якщо він не пустий
  if (email !== '' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    alert("Некоректний email");
    return;
  }

  if (password.length < 6) {
    alert("Пароль має містити щонайменше 6 символів");
    return;
  }

  const res = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: email, password, recaptcha_token: token }),
  });

  const result = await res.json();

  if (result.success) {
    window.location.href = "home.html";
  } else {
    alert(result.message);
  }

  delete loginForm.dataset.recaptchaToken;
});

// ✅ Обробка реєстрації
registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const token = registerForm.dataset.recaptchaToken;
  if (!token) {
    grecaptcha.execute(); // Запускаємо invisible reCAPTCHA
    return;
  }

  const username = registerForm.querySelector("input[name='username']").value.trim();
  const email = registerForm.querySelector("input[name='email']").value.trim();
  const password = registerForm.querySelector("input[name='password']").value;
  const password2 = registerForm.querySelector("input[name='password2']").value;

  if (!username) {
    alert("Введіть логін");
    return;
  }

  // Перевіряємо email тільки якщо він не пустий
  if (email !== '' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    alert("Некоректний email");
    return;
  }

  if (password.length < 6) {
    alert("Пароль має містити щонайменше 6 символів");
    return;
  }

  if (password !== password2) {
    alert("Паролі не співпадають");
    return;
  }

  const res = await fetch("/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, recaptcha_token: token }),
  });

  const result = await res.json();

  if (result.success) {
    alert("Успішна реєстрація! Тепер увійдіть.");
    loginToggle.click();
  } else {
    alert(result.message);
  }

  delete registerForm.dataset.recaptchaToken;
});
