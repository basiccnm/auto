/* auth.js — 회원가입/로그인 위젯 로직.
 * 프레임워크 없음. .auth-widget 이 있는 어떤 페이지에서든 동작.
 * 서버 REST 규격에만 의존하므로 백엔드(Flask/Workers)와 무관하게 재사용. */
(function () {
  const root = document.querySelector('.auth-widget');
  if (!root) return;

  const API = root.dataset.apiBase || '';
  const providers = (root.dataset.providers || '').split(',').map(s => s.trim()).filter(Boolean);

  const $ = (sel, ctx = root) => ctx.querySelector(sel);
  const status = $('[data-status]');

  function api(path, body) {
    return fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body || {}),
    }).then(async r => ({ status: r.status, data: await r.json().catch(() => ({})) }));
  }

  function setStatus(msg, kind) {
    status.textContent = msg || '';
    status.className = 'aw-status' + (kind ? ' ' + kind : '');
  }

  // --- 소셜 버튼 렌더 --------------------------------------------------------
  const LABELS = {
    kakao:  '카카오로 시작하기',
    google: 'Google로 시작하기',
    naver:  '네이버로 시작하기',
    apple:  'Apple로 시작하기',
  };
  const socialWrap = $('[data-social]');
  if (providers.length === 0) {
    socialWrap.style.display = 'none';
    $('.aw-divider').style.display = 'none';
  } else {
    providers.forEach(p => {
      const a = document.createElement('a');
      a.className = 'aw-social-btn';
      a.dataset.p = p;
      a.href = API + '/auth/start/' + p;
      a.textContent = LABELS[p] || (p + '로 시작하기');
      socialWrap.appendChild(a);
    });
  }

  // --- 탭 전환 ---------------------------------------------------------------
  const tabs = root.querySelectorAll('.aw-tab');
  const forms = { login: $('[data-form="login"]'), signup: $('[data-form="signup"]') };
  tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.classList.toggle('is-active', x === t));
    const key = t.dataset.tab;
    forms.login.classList.toggle('is-hidden', key !== 'login');
    forms.signup.classList.toggle('is-hidden', key !== 'signup');
    setStatus('');
  }));

  // --- 휴대폰 인증 -----------------------------------------------------------
  const phoneBox   = $('[data-phone]');
  const phoneInput = $('[data-phone-input]');
  const sendBtn    = $('[data-send-code]');
  const codeRow    = $('[data-code-row]');
  const codeInput  = $('[data-code-input]');
  const verifyBtn  = $('[data-verify-code]');
  const phoneMsg   = $('[data-phone-msg]');
  const timerEl    = $('[data-timer]');
  const signupBtn  = $('[data-signup-submit]');

  let phoneToken = null;   // 인증 완료 증표
  let timer = null;

  function pmsg(text, kind) { phoneMsg.textContent = text || ''; phoneMsg.className = 'aw-phone-msg ' + (kind || ''); }

  // 010-1234-5678 자동 하이픈
  phoneInput.addEventListener('input', () => {
    let v = phoneInput.value.replace(/\D/g, '').slice(0, 11);
    if (v.length >= 8) v = v.replace(/(\d{3})(\d{4})(\d{0,4})/, '$1-$2-$3').replace(/-$/, '');
    else if (v.length >= 4) v = v.replace(/(\d{3})(\d{0,4})/, '$1-$2').replace(/-$/, '');
    phoneInput.value = v;
    if (phoneToken) { phoneToken = null; signupBtn.disabled = true; pmsg('번호가 변경되어 재인증이 필요합니다.', 'info'); }
  });

  function startTimer(sec) {
    clearInterval(timer);
    let left = sec;
    const tick = () => {
      const m = String(Math.floor(left / 60)).padStart(1, '0');
      const s = String(left % 60).padStart(2, '0');
      timerEl.textContent = `${m}:${s}`;
      if (left <= 0) { clearInterval(timer); timerEl.textContent = '만료'; pmsg('인증번호가 만료되었습니다. 다시 발송하세요.', 'err'); }
      left--;
    };
    tick();
    timer = setInterval(tick, 1000);
  }

  sendBtn.addEventListener('click', async () => {
    const phone = phoneInput.value.trim();
    if (phone.replace(/\D/g, '').length < 10) { pmsg('휴대폰 번호를 정확히 입력하세요.', 'err'); return; }
    sendBtn.disabled = true;
    pmsg('발송 중…', 'info');
    const { status: st, data } = await api('/api/phone/send', { phone, purpose: 'signup' });
    if (st !== 200 || !data.ok) { pmsg(data.error || '발송 실패', 'err'); sendBtn.disabled = false; return; }

    codeRow.classList.remove('is-hidden');
    sendBtn.textContent = '재발송';
    startTimer(data.ttl || 180);
    let hint = '인증번호를 발송했습니다.';
    if (data.dev_code) hint += ` (개발용 코드: ${data.dev_code})`;
    pmsg(hint, 'info');
    codeInput.focus();
    setTimeout(() => { sendBtn.disabled = false; }, 3000);  // 재발송 쿨다운(서버가 최종 판정)
  });

  verifyBtn.addEventListener('click', async () => {
    const phone = phoneInput.value.trim();
    const code = codeInput.value.trim();
    if (code.length < 4) { pmsg('인증번호를 입력하세요.', 'err'); return; }
    verifyBtn.disabled = true;
    const { status: st, data } = await api('/api/phone/verify', { phone, code, purpose: 'signup' });
    verifyBtn.disabled = false;
    if (st !== 200 || !data.ok) { pmsg(data.error || '인증 실패', 'err'); return; }
    phoneToken = data.phone_token;
    clearInterval(timer);
    timerEl.textContent = '';
    pmsg('휴대폰 인증이 완료되었습니다.', 'ok');
    signupBtn.disabled = false;
    codeInput.disabled = true;
    verifyBtn.disabled = true;
    sendBtn.disabled = true;
  });

  // --- 로그인 제출 -----------------------------------------------------------
  forms.login.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(forms.login);
    setStatus('로그인 중…');
    const { status: st, data } = await api('/api/auth/login', {
      email: fd.get('email'), password: fd.get('password'),
    });
    if (st !== 200 || !data.ok) { setStatus(data.error || '로그인 실패', 'err'); return; }
    setStatus(`${data.user.name || data.user.email}님, 환영합니다!`, 'ok');
    onAuthed(data.user);
  });

  // --- 회원가입 제출 ---------------------------------------------------------
  forms.signup.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(forms.signup);
    const requirePhone = phoneBox && !phoneBox.classList.contains('is-hidden');
    if (requirePhone && !phoneToken) { setStatus('휴대폰 인증을 완료해주세요.', 'err'); return; }
    setStatus('가입 중…');
    const { status: st, data } = await api('/api/auth/signup', {
      name: fd.get('name'), email: fd.get('email'),
      password: fd.get('password'), phone_token: phoneToken,
    });
    if (st !== 200 || !data.ok) { setStatus(data.error || '가입 실패', 'err'); return; }
    setStatus(`${data.user.name || data.user.email}님, 가입이 완료되었습니다!`, 'ok');
    onAuthed(data.user);
  });

  // 인증 성공 후 훅. 다른 프로젝트에선 window.AuthWidget.onAuthed 를 덮어써 커스텀 처리.
  function onAuthed(user) {
    if (window.AuthWidget && typeof window.AuthWidget.onAuthed === 'function') {
      window.AuthWidget.onAuthed(user);
    }
  }

  // 로그인 상태로 진입했는지 확인
  fetch(API + '/api/auth/me', { credentials: 'include' })
    .then(r => r.json()).then(d => {
      if (d.ok && d.user) setStatus(`${d.user.name || d.user.email}님으로 로그인됨`, 'ok');
    }).catch(() => {});

  window.AuthWidget = window.AuthWidget || {};
})();
