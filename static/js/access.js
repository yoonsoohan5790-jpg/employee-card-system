async function loadAccess() {
  const res = await fetch('/api/dashboard/access');
  const users = await res.json();
  render(users);
}

function render(users) {
  const head = document.getElementById('accessTableHead');
  const body = document.getElementById('accessTableBody');

  if (users.length > 0) {
    const areaHeaders = users[0].areas.map(a => `<th>${a.area_name}</th>`).join('');
    head.innerHTML = `<th>조직원</th><th>부서</th><th>직급</th><th>재직상태</th>${areaHeaders}<th>권한상태</th>`;
  }

  body.innerHTML = '';
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
    `;
    body.appendChild(tr);
  });
}

loadAccess();
