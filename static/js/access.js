let allUsersAccess = [];
let areaList = [];
const modalBackdrop = document.getElementById('exceptionModalBackdrop');
const areaSelect = document.getElementById('e_area_id');
const searchInput = document.getElementById('searchInput');

async function loadAreas() {
  const res = await fetch('/api/access-areas');
  areaList = await res.json();
  areaSelect.innerHTML = areaList.map(a => `<option value="${a.id}">${a.area_name}</option>`).join('');
}

async function loadAccess() {
  const res = await fetch('/api/dashboard/access');
  allUsersAccess = await res.json();
  renderAccessTable();
}

function renderAccessTable() {
  const head = document.getElementById('accessTableHead');
  const body = document.getElementById('accessTableBody');
  const keyword = searchInput.value.trim().toLowerCase();

  const users = allUsersAccess.filter(u =>
    !keyword || u.name.toLowerCase().includes(keyword)
  );

  if (allUsersAccess.length > 0) {
    const areaHeaders = allUsersAccess[0].areas.map(a => `<th>${a.area_name}</th>`).join('');
    head.innerHTML = `<th>조직원</th><th>부서</th><th>직급</th><th>재직상태</th>${areaHeaders}<th>권한상태</th><th>관리</th>`;
  }

  body.innerHTML = '';
  if (users.length === 0) {
    body.innerHTML = `<tr><td colspan="${(allUsersAccess[0]?.areas.length || 0) + 6}" class="alert-empty">검색 결과가 없습니다.</td></tr>`;
    return;
  }

  users.forEach(u => {
    const areaCells = u.areas.map(a =>
      `<td class="${a.allowed ? 'access-yes' : 'access-no'}">${a.allowed ? '허용' : '차단'}</td>`
    ).join('');
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${u.name}</td>
      <td>${u.department}</td>
      <td>${u.position}</td>
      <td><span class="badge ${u.employment_status}">${u.employment_status}</span></td>
      ${areaCells}
      <td><span class="badge ${u.access_status}">${u.access_status}</span></td>
      <td><button class="btn small" onclick="openExceptionModal(${u.user_id}, '${u.name.replace(/'/g, "\\'")}')">예외 설정</button></td>
    `;
    body.appendChild(tr);
  });
}

window.openExceptionModal = function (userId, name) {
  document.getElementById('e_user_id').value = userId;
  document.getElementById('exceptionModalTitle').textContent = `출입권한 예외처리 - ${name}`;
  document.getElementById('e_reason').value = '';
  const expiresInput = document.getElementById('e_expires_at');
  expiresInput.value = '';
  expiresInput.min = new Date().toISOString().slice(0, 10);
  areaSelect.value = areaList[0]?.id || '';
  document.getElementById('e_allowed').value = 'true';
  modalBackdrop.classList.add('open');
};

document.getElementById('btnCancelException').addEventListener('click', () => {
  modalBackdrop.classList.remove('open');
});

document.getElementById('btnSaveException').addEventListener('click', async () => {
  const userId = document.getElementById('e_user_id').value;
  const areaId = parseInt(areaSelect.value, 10);
  const allowed = document.getElementById('e_allowed').value === 'true';
  const reason = document.getElementById('e_reason').value.trim();
  const expiresAt = document.getElementById('e_expires_at').value || null;

  if (!reason) {
    alert('예외처리 사유를 입력해주세요.');
    return;
  }

  const res = await fetch(`/api/users/${userId}/access`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ area_id: areaId, allowed, reason, expires_at: expiresAt }),
  });

  if (res.ok) {
    modalBackdrop.classList.remove('open');
    loadAccess();
    loadExceptions();
  } else {
    const data = await res.json();
    alert(data.error || '저장에 실패했습니다.');
  }
});

async function loadExceptions() {
  const res = await fetch('/api/access-exceptions');
  const exceptions = await res.json();
  const body = document.getElementById('exceptionTableBody');
  body.innerHTML = '';

  if (exceptions.length === 0) {
    body.innerHTML = '<tr><td colspan="9" class="alert-empty">예외처리된 출입권한이 없습니다.</td></tr>';
    return;
  }

  exceptions.forEach(e => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${e.user_name || '-'}</td>
      <td>${e.department || '-'}</td>
      <td>${e.position || '-'}</td>
      <td>${e.employment_status ? `<span class="badge ${e.employment_status}">${e.employment_status}</span>` : '-'}</td>
      <td>${e.area_name}</td>
      <td class="${e.allowed ? 'access-yes' : 'access-no'}">${e.allowed ? '허용' : '차단'}</td>
      <td>${e.reason || '-'}</td>
      <td>${e.expires_at ? `${e.expires_at}까지` : '무기한'}</td>
      <td>${(e.updated_at || '').replace('T', ' ').slice(0, 16)}</td>
    `;
    body.appendChild(tr);
  });
}

searchInput.addEventListener('input', renderAccessTable);

(async function init() {
  await loadAreas();
  await loadAccess();
  await loadExceptions();
})();
