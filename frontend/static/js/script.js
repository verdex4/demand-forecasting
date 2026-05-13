document.addEventListener('DOMContentLoaded', () => {
    const roleButtons = document.querySelectorAll('.role-card');
    const continueBtn = document.getElementById('continue-btn');
    
    let selectedRole = null;

    const selectRole = (role) => {
        const btn = document.querySelector(`[data-role="${role}"]`);
        
        // если кликнули по уже выбранной роли - снимаем выбор
        if (selectedRole === role) {
            btn.classList.add('deselecting');
            setTimeout(() => {
                btn.classList.remove('selected', 'selecting', 'deselecting');
            }, 250);
            
            selectedRole = null;
            continueBtn.disabled = true;
            sessionStorage.removeItem('user_role');
            return;
        }

        // снимаем выделение со всех кнопок
        roleButtons.forEach(b => {
            if (b !== btn) {
                b.classList.remove('selected', 'selecting');
            }
        });

        // добавляем выделение и анимацию нажатой кнопке
        btn.classList.add('selected', 'selecting');
        setTimeout(() => btn.classList.remove('selecting'), 300);

        // обновляем состояние
        selectedRole = role;
        continueBtn.disabled = false;
        sessionStorage.setItem('user_role', role);
    };

    const handleContinue = () => {
        if (!selectedRole) return;
        
        // визуальный отклик
        continueBtn.style.transform = 'scale(0.98)';
        setTimeout(() => continueBtn.style.transform = '', 150);
    };

    roleButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            selectRole(btn.dataset.role);
        });
        
        btn.setAttribute('tabindex', '0');
        btn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectRole(btn.dataset.role);
            }
        });
    });

    continueBtn.addEventListener('click', handleContinue);
    
    const savedRole = sessionStorage.getItem('user_role');
    if (savedRole && ['employee', 'applicant'].includes(savedRole)) {
        selectRole(savedRole);
    }
});