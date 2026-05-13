document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.role-card');

    const handleRoleSelection = (role) => {
        sessionStorage.setItem('user_role', role);

        // анимация кнопок
        const activeBtn = document.querySelector(`[data-role="${role}"]`);
        activeBtn.style.transform = 'scale(0.97)';
        activeBtn.style.borderColor = 'var(--primary)';

        /*
        setTimeout(() => {
            // возврат состояния
            activeBtn.style.transform = '';
            activeBtn.style.borderColor = '';
        }, 400);
        */
    };

    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            handleRoleSelection(btn.dataset.role);
        });
    });
});