const applyForm = document.getElementById('applyForm');
const applyError = document.getElementById('applyError');
const formArea = document.getElementById('formArea');
const resultArea = document.getElementById('resultArea');
const resultMessage = document.getElementById('resultMessage');

applyForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  applyError.textContent = '';

  const payload = {
    name: document.getElementById('f_name').value.trim(),
    employee_number: document.getElementById('f_employee_number').value.trim(),
    department: document.getElementById('f_department').value.trim(),
    position: document.getElementById('f_position').value.trim(),
    note: document.getElementById('f_note').value.trim(),
  };

  try {
    const res = await fetch('/api/card-applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      applyError.textContent = data.error || '신청에 실패했습니다.';
      return;
    }

    formArea.style.display = 'none';
    resultArea.style.display = 'block';

    if (data.auto_approved) {
      resultMessage.innerHTML = `
        <p style="color:#16a34a; font-weight:bold;">✓ 사원증이 자동 발급되었습니다.</p>
        <p>사번(<strong>${payload.employee_number}</strong>)으로 로그인해주세요.</p>
        <p>초기 비밀번호: <strong>changeme123</strong></p>
      `;
    } else {
      resultMessage.innerHTML = `
        <p style="color:#d97706; font-weight:bold;">⏳ 신청이 접수되었습니다.</p>
        <p>기타사항이 포함되어 있어 관리자 검토 후 발급됩니다. 승인되면 사번으로 로그인하실 수 있습니다.</p>
      `;
    }
  } catch (err) {
    applyError.textContent = '서버와 통신할 수 없습니다.';
  }
});
