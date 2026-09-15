function formatValue(raw) {
  if (!raw) return '-';
  try {
    const obj = JSON.parse(raw);
    return `<code>${JSON.stringify(obj)}</code>`;
  } catch (e) {
    return raw;
  }
}

async function loadLogs() {
  const res = await fetch('/api/audit-logs');
  const logs = await res.json();
  const body = document.getElementById('auditTableBody');
  body.innerHTML = '';
  logs.forEach(l => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${(l.created_at || '').replace('T', ' ').slice(0, 19)}</td>
      <td>${l.user_id ?? '-'}</td>
      <td>${l.card_id || '-'}</td>
      <td>${l.action}</td>
      <td style="max-width:260px; white-space:normal;">${formatValue(l.before_value)}</td>
      <td style="max-width:260px; white-space:normal;">${formatValue(l.after_value)}</td>
      <td>${l.actor}</td>
    `;
    body.appendChild(tr);
  });
}

loadLogs();
