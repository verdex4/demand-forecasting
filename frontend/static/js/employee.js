// 1. Переключение активного пункта меню
const navItems = document.querySelectorAll('.nav-item');
navItems.forEach(item => {
    item.addEventListener('click', function() {
        // Убираем active у всех
        navItems.forEach(nav => nav.classList.remove('active'));
        // Добавляем текущему (если это не специальная логика для "Отчётов", но для MVP сойдет)
        this.classList.add('active');
    });
});

// 2. Обработка кнопки "Сформировать отчёт"
const btnGenerate = document.getElementById('btnGenerate');
btnGenerate.addEventListener('click', () => {
    // Имитация загрузки
    const originalText = btnGenerate.innerHTML;
    btnGenerate.innerHTML = '⏳ Загрузка...';
    btnGenerate.disabled = true;

    setTimeout(() => {
        alert('Запрос отправлен на сервер FastAPI! Данные для отчёта собираются.');
        btnGenerate.innerHTML = originalText;
        btnGenerate.disabled = false;
    }, 1000);
});

// 3. Обработка кнопки "Сбросить фильтры"
const btnReset = document.getElementById('btnReset');
const selects = document.querySelectorAll('select');

btnReset.addEventListener('click', () => {
    selects.forEach(select => {
        select.selectedIndex = 0; // Возвращаем к первому элементу
    });
});