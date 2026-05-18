document.addEventListener('DOMContentLoaded', async () => {
    // ПЕРЕКЛЮЧЕНИЕ АКТИВНОГО РАЗДЕЛА В ЛЕВОМ МЕНЮ
    const navItems = document.querySelectorAll('.nav-item');
    
    const sectionIds = [
        'section-forecast',
        'section-specialties',
        'section-applications',
        'section-reports',
        'section-model-settings',
        'section-model-test'
    ];

    navItems.forEach((item, index) => {
        if (sectionIds[index]) {
            item.setAttribute('data-target', sectionIds[index]);
        }
    });

    // Функция переключения видимости секций
    function switchSection(targetId) {
        // Убираем активный класс у всех пунктов меню
        navItems.forEach(nav => nav.classList.remove('active'));
        
        // Скрываем все секции
        sectionIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });

        // Показываем целевую секцию
        const targetSection = document.getElementById(targetId);
        if (targetSection) {
            targetSection.style.display = 'block';
        }

        // Подсвечиваем активный пункт меню
        const activeNav = document.querySelector(`.nav-item[data-target="${targetId}"]`);
        if (activeNav) {
            activeNav.classList.add('active');
        }
    }

    // Навешиваем обработчики кликов
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetId = item.getAttribute('data-target');
            if (targetId) switchSection(targetId);
        });
    });

    // Активируем первый раздел при начальной загрузке страницы
    if (navItems.length > 0 && sectionIds[0]) {
        switchSection(sectionIds[0]);
    }
    

    // ПОКАЗ ВСЕХ СПЕЦИАЛЬНОСТЕЙ В РАЗДЕЛЕ "Прогнозирование"
    const API_URL = 'http://127.0.0.1:8000/api/v1/specialties/short';

    const select = document.querySelector('#speciality-select select');
    if (!select) return; // Защита, если элемент не найден

    // Блокируем селект на время загрузки (UX)
    select.disabled = true;

    // Временная опция загрузки
    const loadingOpt = document.createElement('option');
    loadingOpt.disabled = true;
    select.appendChild(loadingOpt);

    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error(`HTTP ошибка: ${response.status}`);
    }

    const data = await response.json();

    // Удаляем опцию загрузки
    select.removeChild(loadingOpt);

    // Добавляем специальности
    data.forEach(spec => {
        if (spec.code === "nan" || spec.code == null) {
            return;
        }
        const option = document.createElement('option');
        
        option.value = spec.code;
        option.textContent = spec.code + ' ' + spec.name;
        
        select.appendChild(option);
    });

    } catch (error) {
        console.error('Ошибка загрузки специальностей:', error);
        loadingOpt.textContent = 'Не удалось загрузить список';
        loadingOpt.value = 'error';
    } finally {
        select.disabled = false;
    }
});