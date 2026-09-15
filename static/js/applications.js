const tableBody = document.getElementById('applicationTableBody');
const filterStatus = document.getElementById('filterStatus');

async function loadApplications() {
  const status = filterStatus.value;
  const url = status ? `/api/card-applications?status=${status}` : '/api/card-applications';
  const res = await fetch(url);
  const applications = await res.json();
  render(applications);
}

function render(applications) {
  tableBody.innerHTML = '';

  if (applications.length === 0) {
    tableBody.innerHTML = '<tr><td colspan="9" class="alert-empty">신청 내역이 없습니다.</td></tr>';
    return;
  }

  applications.forEach(a => {
    const tr = document.createElement('tr');
    const actions = a.status === 'pending'
      ? `<button class="btn small" onclick="approveApplication(${a.id}, '${a.name.replace(/'/g, "\\'")}')">승인</button>
         <button class="btn small danger" onclick="rejectApplication(${a.id}, '${a.name.replace(/'/g, "\\'")}')">반려</button>`
      : (a.status === 'rejected' ? `사유: ${a.reject_reason || '-'}` : '-');

    tr.innerHTML = `
      <td>${(a.created_at || '').replace('T', ' ').slice(0, 16)}</td>
      <td>${a.name}</td>
      <td>${a.employee_number}</td>
      <td>${a.department}</td>
      <td>${a.position}</td>
      <td style="max-width:220px; white-space:normal;">${a.note || '-'}</td>
      <td><span class="badge ${a.status === 'pending' ? '주의' : (a.status === 'approved' ? '정상' : '위험')}">${a.status_label}</span></td>
      <td>${a.reviewed_by || '-'}</td>
      <td>${actions}</td>
    `;
    tableBody.appendChild(tr);
  });
}

window.approveApplication = async function (id, name) {
  if (!confirm(`${name}님의 신청을 승인하고 사원증을 발급하시겠습니까?`)) return;
  const res = await fetch(`/api/card-applications/${id}/approve`, { method: 'POST' });
  const data = await res.json();
  if (res.ok) {
    loadApplications();
  } else {
    alert(data.error || '승인에 실패했습니다.');
  }
};

window.rejectApplication = async function (id, name) {
  const reason = prompt(`${name}님의 신청을 반려하는 사유를 입력해주세요 (선택)`) || '';
  const res = await fetch(`/api/card-applications/${id}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  const data = await res.json();
  if (res.ok) {
    loadApplications();
  } else {
    alert(data.error || '반려에 실패했습니다.');
  }
};

filterStatus.addEventListener('change', loadApplications);
loadApplications();
