const tableBody = document.getElementById('cardTableBody');
const filterStatus = document.getElementById('filterStatus');

async function loadCards() {
  const status = filterStatus.value;
  const url = status ? `/api/cards?status=${status}` : '/api/cards';
  const res = await fetch(url);
  const cards = await res.json();
  render(cards);
}

function render(cards) {
  tableBody.innerHTML = '';
  cards.forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${c.card_id}</td>
      <td>${c.user_name || '-'}</td>
      <td>${c.department || '-'}</td>
      <td>${c.position || '-'}</td>
      <td>${c.issue_date || '-'}</td>
      <td><span class="badge ${c.status}">${c.status_label}</span></td>
      <td>
        <button class="btn small" onclick="activateCard(${c.id})">활성화</button>
        <button class="btn small secondary" onclick="suspendCard(${c.id})">중지</button>
        <button class="btn small danger" onclick="revokeCard(${c.id})">폐기</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

window.activateCard = async function (id) {
  await fetch(`/api/cards/${id}/activate`, { method: 'POST' });
  loadCards();
};

window.suspendCard = async function (id) {
  const reason = prompt('중지 사유를 입력하세요 (선택)') || '관리자 수동 중지';
  await fetch(`/api/cards/${id}/suspend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  loadCards();
};

window.revokeCard = async function (id) {
  if (!confirm('사원증을 폐기하시겠습니까? 되돌릴 수 없습니다.')) return;
  await fetch(`/api/cards/${id}/revoke`, { method: 'POST' });
  loadCards();
};

filterStatus.addEventListener('change', loadCards);
loadCards();
