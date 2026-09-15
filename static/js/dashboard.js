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
        borderWidth: 2,
        borderColor: '#ffffff',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, padding: 14, font: { size: 12 } },
        },
      },
    },
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
        { label: '활성', data: active, backgroundColor: '#2563eb', borderRadius: 4, maxBarThickness: 36 },
        { label: '중지', data: suspended, backgroundColor: '#dc2626', borderRadius: 4, maxBarThickness: 36 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 14, font: { size: 12 } } } },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#f1f3f6' } },
      },
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
    li.innerHTML = `
      <span>⚠ ${item.name} (${item.department} / ${item.position}) - ${item.text}</span>
      <span style="display:flex; align-items:center; gap:8px;">
        <button class="btn small secondary" onclick="notifyAnomaly(${item.user_id}, '${item.name}')">메일 발송</button>
        <span class="${tagClass}">${item.tag}</span>
      </span>
    `;
    list.appendChild(li);
  });
}

window.notifyAnomaly = async function (userId, name) {
  const ok = confirm(
    `${name}님의 권한 이상 내역을 관리자 알림 메일로 발송합니다.\n` +
    `(메일에는 즉시 사원증을 중지할 수 있는 조치 링크가 포함됩니다.)\n\n` +
    `발송하시겠습니까?`
  );
  if (!ok) return;

  try {
    const res = await fetch('/api/alerts/notify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || '메일 발송에 실패했습니다.');
      return;
    }
    alert('알림 메일을 발송했습니다.');
  } catch (e) {
    alert('메일 발송 중 오류가 발생했습니다.');
  }
};

async function refreshAll() {
  try {
    await Promise.all([loadSummary(), loadCardChart(), loadDeptChart(), loadAlerts()]);
  } catch (e) {
    console.error(e);
  }
}

refreshAll();
setInterval(refreshAll, 5000);
