const tableBody = document.getElementById('policyTableBody');
const modalBackdrop = document.getElementById('policyModalBackdrop');
const areaSelect = document.getElementById('p_area_id');

let areas = [];

async function loadAreas() {
  const res = await fetch('/api/access-areas');
  areas = await res.json();
  areaSelect.innerHTML = areas.map(a => `<option value="${a.id}">${a.area_name}</option>`).join('');
}

async function loadPolicies() {
  const res = await fetch('/api/access-policies');
  const policies = await res.json();
  render(policies);
}

function render(policies) {
  tableBody.innerHTML = '';
  policies.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${p.department}</td>
      <td>${p.position}</td>
      <td>${p.area_name}</td>
      <td>${p.allowed ? '<span class="access-yes">허용</span>' : '<span class="access-no">차단</span>'}</td>
      <td>
        <button class="btn small" onclick="togglePolicy(${p.id}, ${!p.allowed})">${p.allowed ? '차단으로 변경' : '허용으로 변경'}</button>
        <button class="btn small danger" onclick="deletePolicy(${p.id})">삭제</button>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

window.togglePolicy = async function (id, allowed) {
  await fetch(`/api/access-policies/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ allowed }),
  });
  loadPolicies();
};

window.deletePolicy = async function (id) {
  if (!confirm('정책을 삭제하시겠습니까?')) return;
  await fetch(`/api/access-policies/${id}`, { method: 'DELETE' });
  loadPolicies();
};

document.getElementById('btnNewPolicy').addEventListener('click', () => {
  document.getElementById('p_department').value = '';
  document.getElementById('p_position').value = '';
  document.getElementById('p_allowed').value = 'true';
  modalBackdrop.classList.add('open');
});

document.getElementById('btnCancelPolicy').addEventListener('click', () => {
  modalBackdrop.classList.remove('open');
});

document.getElementById('btnSavePolicy').addEventListener('click', async () => {
  const payload = {
    department: document.getElementById('p_department').value.trim(),
    position: document.getElementById('p_position').value.trim(),
    area_id: parseInt(areaSelect.value, 10),
    allowed: document.getElementById('p_allowed').value === 'true',
  };
  if (!payload.department || !payload.position) {
    alert('부서와 직급을 입력해주세요.');
    return;
  }
  await fetch('/api/access-policies', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  modalBackdrop.classList.remove('open');
  loadPolicies();
});

(async function init() {
  await loadAreas();
  await loadPolicies();
})();
