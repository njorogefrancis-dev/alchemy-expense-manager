/* ============================================================
   app.js — ExpenseIQ Frontend Logic
   Handles: dark mode, password toggle, strength meter,
            flash auto-dismiss, form helpers
   ============================================================ */

// ── Dark Mode ─────────────────────────────────────────────────────────────────

(function initTheme() {
  const saved = localStorage.getItem('expenseiq-theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', saved);
  updateThemeIcon(saved);
})();

function updateThemeIcon(theme) {
  const icon = document.getElementById('themeIcon');
  if (!icon) return;
  icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
}

document.addEventListener('DOMContentLoaded', function () {

  // ── Theme toggle button ───────────────────────────────────────────────────
  const themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-bs-theme');
      const next    = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', next);
      localStorage.setItem('expenseiq-theme', next);
      updateThemeIcon(next);
    });
  }

  // ── Auto-dismiss flash messages after 5 seconds ───────────────────────────
  const flashContainer = document.getElementById('flash-container');
  if (flashContainer) {
    setTimeout(function () {
      flashContainer.querySelectorAll('.alert').forEach(function (el) {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
        bsAlert.close();
      });
    }, 5000);
  }

  // ── Password strength meter (register page) ───────────────────────────────
  const pwdInput = document.getElementById('password');
  const bar      = document.getElementById('pwdStrengthBar');
  const text     = document.getElementById('pwdStrengthText');

  if (pwdInput && bar && text) {
    pwdInput.addEventListener('input', function () {
      const val = pwdInput.value;
      const score = calcStrength(val);
      const levels = [
        { pct: 0,   cls: 'bg-secondary', label: 'Enter a password (min 8 chars)' },
        { pct: 25,  cls: 'bg-danger',    label: 'Weak — add length or symbols' },
        { pct: 50,  cls: 'bg-warning',   label: 'Fair — getting better' },
        { pct: 75,  cls: 'bg-info',      label: 'Good — nearly there!' },
        { pct: 100, cls: 'bg-success',   label: 'Strong password ✓' },
      ];
      const lvl = levels[score];
      bar.style.width = lvl.pct + '%';
      bar.className   = 'progress-bar ' + lvl.cls;
      text.textContent = lvl.label;
    });
  }

  // ── Confirm delete shortcut (keyboard: Escape closes modal) ──────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      const modal = document.getElementById('deleteModal');
      if (modal) bootstrap.Modal.getInstance(modal)?.hide();
    }
  });

  // ── Amount field: format on blur ──────────────────────────────────────────
  const amountInput = document.getElementById('amount');
  if (amountInput) {
    amountInput.addEventListener('blur', function () {
      const val = parseFloat(amountInput.value);
      if (!isNaN(val) && val > 0) {
        amountInput.value = val.toFixed(2);
      }
    });
  }

});

// ── Password visibility toggle ────────────────────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isText = input.type === 'text';
  input.type = isText ? 'password' : 'text';
  btn.querySelector('i').className = isText ? 'bi bi-eye' : 'bi bi-eye-slash';
}

// ── Password strength scorer ──────────────────────────────────────────────────
function calcStrength(pwd) {
  if (!pwd) return 0;
  let score = 0;
  if (pwd.length >= 8)  score++;
  if (pwd.length >= 12) score++;
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd)) score++;
  if (/[^A-Za-z0-9]/.test(pwd)) score++;
  return Math.min(4, Math.ceil(score * 0.8));
}
