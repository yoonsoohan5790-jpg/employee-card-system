const tableBody = document.getElementById('userTableBody');
const filterDept = document.getElementById('filterDept');
const filterStatus = document.getElementById('filterStatus');
const modalBackdrop = document.getElementById('userModalBackdrop');
const modalTitle = document.getElementById('userModalTitle');
const employmentStatusSelect = document.getElementById('f_employment_status');

let allUsers = [];

function statusBadge(text) {
  return `<span class="badge ${text}">${text}</span>`;
}

function cardBadge(card) {
  if (!card) return '<span class="badge revoked">미발급</span>';
  const label = { active: '활성', suspended: '중지', expired: '만료', revoked: '폐기' }[card.status] || card.status;
  return `<span class="badge ${card.status}">${label}</span>`;
}

function render(users) {
  tableBody.innerHTML = '';
  users.forEach(u => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${u.id}</td>
      <td>${u.name}</td>
      <td>${u.department}</td>
      <td>${u.position}</td>
      <td>${u.email || '-'}</td>
      <td>${statusBadge(u.employment_status)}</td>
      <td>${cardBadge(u.card)}</td>
      <td>${statusBadge(u.access_status)}</td>
      <td>
        <button class="btn small" onclick="editUser(${u.id})">수정</button>
        <button class="btn small danger" onclick="deleteUser(${u.id})">삭제</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

function applyFilter() {
  const dept = filterDept.value;
  const status = filterStatus.value;
  const filtered = allUsers.filter(u =>
    (!dept || u.department === dept) && (!status || u.employment_status === status)
  );
  render(filtered);
}

function populateDeptFilter(users) {
  const depts = [...new Set(users.map(u => u.department))];
  filterDept.innerHTML = '<option value="">전체 부서</option>' + depts.map(d => `<option value="${d}">${d}</option>`).join('');
}

async function loadUsers() {
  const res = await fetch('/api/users');
  allUsers = await res.json();
  populateDeptFilter(allUsers);
  applyFilter();
}

filterDept.addEventListener('change', applyFilter);
filterStatus.addEventListener('change', applyFilter);

function toggleConditionalFields() {
  const status = employmentStatusSelect.value;
  document.getElementById('leaveFields').style.display = status === '휴직' ? 'block' : 'none';
  document.getElementById('resignFields').style.display = status === '퇴사' ? 'block' : 'none';
}
employmentStatusSelect.addEventListener('change', toggleConditionalFields);

function openModal(user) {
  modalBackdrop.classList.add('open');
  document.getElementById('userId').value = user ? user.id : '';
  document.getElementById('f_username').value = user ? user.username : '';
  document.getElementById('f_username').disabled = !!user;
  document.getElementById('f_password').value = '';
  document.getElementById('f_name').value = user ? user.name : '';
  document.getElementById('f_department').value = user ? user.department : '';
  document.getElementById('f_position').value = user ? user.position : '';
  document.getElementById('f_email').value = user ? (user.email || '') : '';
  document.getElementById('f_phone').value = user ? (user.phone || '') : '';
  document.getElementById('f_hire_date').value = user ? (user.hire_date || '') : '';
  document.getElementById('f_leave_start_date').value = user ? (user.leave_start_date || '') : '';
  document.getElementById('f_leave_end_date').value = user ? (user.leave_end_date || '') : '';
  document.getElementById('f_resign_date').value = user ? (user.resign_date || '') : '';
  employmentStatusSelect.value = user ? user.employment_status : '재직';
  toggleConditionalFields();
  modalTitle.textContent = user ? `조직원 수정 - ${user.name}` : '조직원 등록';
}

function closeModal() {
  modalBackdrop.classList.remove('open');
}

document.getElementById('btnNewUser').addEventListener('click', () => openModal(null));
document.getElementById('btnCancelUser').addEventListener('click', closeModal);

window.editUser = function (id) {
  const user = allUsers.find(u => u.id === id);
  openModal(user);
};

window.deleteUser = async function (id) {
  if (!confirm('정말 삭제하시겠습니까?')) return;
  const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
  if (res.ok) loadUsers();
  else alert('삭제에 실패했습니다.');
};

document.getElementById('btnSaveUser').addEventListener('click', async () => {
  const id = document.getElementById('userId').value;
  const payload = {
    name: document.getElementById('f_name').value.trim(),
    department: document.getElementById('f_department').value.trim(),
    position: document.getElementById('f_position').value.trim(),
    email: document.getElementById('f_email').value.trim(),
    phone: document.getElementById('f_phone').value.trim(),
    hire_date: document.getElementById('f_hire_date').value || null,
    employment_status: employmentStatusSelect.value,
    leave_start_date: document.getElementById('f_leave_start_date').value || null,
    leave_end_date: document.getElementById('f_leave_end_date').value || null,
    resign_date: document.getElementById('f_resign_date').value || null,
  };

  const password = document.getElementById('f_password').value;
  if (password) payload.password = password;

  let res;
  if (id) {
    res = await fetch(`/api/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } else {
    payload.username = document.getElementById('f_username').value.trim();
    payload.password = password || 'changeme123';
    res = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  if (res.ok) {
    closeModal();
    loadUsers();
  } else {
    const data = await res.json();
    alert(data.error || '저장에 실패했습니다.');
  }
});

loadUsers();
