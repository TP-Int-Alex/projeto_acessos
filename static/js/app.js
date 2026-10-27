document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('toggleSidebar');
  const sidebar = document.getElementById('sidebar');
  if (btn) btn.addEventListener('click', () => sidebar.classList.toggle('open'));

  // Loader global em submits
  document.querySelectorAll('form').forEach(f => {
    f.addEventListener('submit', () => {
      const l = document.getElementById('loader');
      if (l) l.classList.remove('d-none');
    });
  });
});

function togglePassword() {
  const p = document.getElementById('password');
  const i = document.getElementById('eyeIcon');
  if (!p) return;
  if (p.type === 'password') { p.type = 'text'; i.className = 'bi bi-eye-slash'; }
  else { p.type = 'password'; i.className = 'bi bi-eye'; }
}

document.addEventListener('submit', (e) => {
  const msg = e.target.getAttribute('data-confirm');
  if (msg && !confirm(msg)) e.preventDefault();
});

function toggleSecret(id) {
  const el = document.getElementById('sec-' + id);
  if (!el) return;
  if (el.dataset.shown === '1') {
    el.textContent = '••••••••';
    el.dataset.shown = '0';
    return;
  }
  fetch(`/clientes/acesso/${id}/senha`)
    .then(r => {
      if (!r.ok) throw new Error('Sem permissão');
      return r.json();
    })
    .then(d => {
      el.textContent = d.senha || '—';
      el.dataset.shown = '1';
    })
    .catch(() => alert('Sem permissão para revelar a senha.'));
}