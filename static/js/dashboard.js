let cardChart, deptChart;

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('요청 실패: ' + url);
  return res.json();
}

async function loadSummary() {
  const data = await fetchJSON('/api/dashboard/summary');
  document.getElementById('sumTotal').textContent = data.total_users;
  document.getElementById('sumActive').textContent = data.active_cards;
  document.getElementById('sumSuspended').textContent = data.suspended_cards;
  document.getElementById('sumAnomaly').textContent = data.anomaly_count;
}

async function loadCardChart() {
  const data = await fetchJSON('/api/dashboard/cards');
  const ctx = document.getElementById('cardStatusChart');
  if (cardChart) {
    cardChart.data.datasets[0].data = data.values;
    cardChart.update();
    return;
  }
  cardChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.values,
        backgroundColor: ['#2563eb', '#d97706', '#6b7280', '#dc2626'],
      }],
    },
    options: { plugins: { legend: { position: 'bottom' } } },
  });
}

async function loadDeptChart() {
  const data = await fetchJSON('/api/dashboard/departments');
  const ctx = document.getElementById('departmentChart');
  const labels = data.map(d => d.department);
  const active = data.map(d => d.active);
  const suspended = data.map(d => d.suspended);

  if (deptChart) {
    deptChart.data.labels = labels;
    deptChart.data.datasets[0].data = active;
    deptChart.data.datasets[1].data = suspended;
    deptChart.update();
    return;
  }

  deptChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: '활성', data: active, backgroundColor: '#2563eb' },
        { label: '중지', data: suspended, backgroundColor: '#dc2626' },
      ],
    },
    options: {
      responsive: true,
      scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
    },
  });
}

async function loadAlerts() {
  const data = await fetchJSON('/api/dashboard/alerts');
  const list = document.getElementById('alertList');
  list.innerHTML = '';

  const items = [
    ...data.resigned_with_access.map(u => ({ ...u, tag: '위험', text: `퇴사자 권한 잔존` })),
    ...data.leave_with_access.map(u => ({ ...u, tag: '위험', text: `휴직자 권한 잔존` })),
    ...data.policy_mismatch.map(u => ({ ...u, tag: '주의', text: `정책 불일치` })),
  ];

  if (items.length === 0) {
    list.innerHTML = '<li class="alert-empty">이상 알림이 없습니다.</li>';
    return;
  }

  items.forEach(item => {
    const li = document.createElement('li');
    const tagClass = item.tag === '위험' ? 'tag' : 'tag warn';
    li.innerHTML = `<span>⚠ ${item.name} (${item.department} / ${item.position}) - ${item.text}</span><span class="${tagClass}">${item.tag}</span>`;
    list.appendChild(li);
  });
}

async function refreshAll() {
  try {
    await Promise.all([loadSummary(), loadCardChart(), loadDeptChart(), loadAlerts()]);
  } catch (e) {
    console.error(e);
  }
}

refreshAll();
setInterval(refreshAll, 5000);
