'use strict';
let csrf = '';
const el = id => document.getElementById(id);
function notice(message) { el('notice').textContent = message; }
async function refresh() {
  const response = await fetch('/api/session');
  if (!response.ok) throw new Error('Could not read the session. Refresh the page.');
  const data = await response.json();
  csrf = data.csrf;
  el('identity').textContent = data.user ? `${data.user.username} · ${data.user.role}` : 'Public visitor · Not signed in';
  el('logout').hidden = !data.user;
}
async function call(path, method = 'GET', body) {
  const response = await fetch(path, {
    method,
    headers: method === 'GET' ? {} : {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
    ...(body ? {body: JSON.stringify(body)} : {})
  });
  const data = await response.json();
  el('status').textContent = `${response.status} ${response.statusText}`;
  el('status').classList.toggle('bad', !response.ok);
  el('result').textContent = JSON.stringify(data, null, 2);
  return {response, data};
}
function handle(action) {
  return async event => {
    event.preventDefault();
    try { await action(); } catch (error) { notice(error.message || 'Request failed. Check that the server is running.'); }
  };
}
async function authenticate(register) {
  const form = el('account-form');
  if (!form.reportValidity()) return;
  const password = el('password').value;
  if (register && password.length < 15) { notice('Registration requires a password of at least 15 characters.'); return; }
  const button = el(register ? 'register' : 'login');
  button.disabled = true;
  try {
    const {response, data} = await call(register ? '/api/register' : '/api/login', 'POST', {username: el('username').value, password});
    notice(data.error || data.message);
    if (response.ok) { el('password').value = ''; await refresh(); }
  } finally { button.disabled = false; }
}
el('account-form').addEventListener('submit', handle(() => authenticate(false)));
el('register').addEventListener('click', handle(() => authenticate(true)));
el('logout').addEventListener('click', handle(async () => {
  const {data} = await call('/api/logout', 'POST', {});
  notice(data.error || data.message);
  await refresh();
}));
el('dashboard').addEventListener('click', handle(() => call('/api/dashboard')));
el('admin').addEventListener('click', handle(() => call('/api/admin')));
refresh().then(() => notice('Ready. Create an account or sign in.')).catch(error => notice(error.message));
