import { chromium } from 'playwright';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const p=await b.newPage({viewport:{width:360,height:800}});
const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.goto('http://127.0.0.1:8789/index.mockup.html',{waitUntil:'networkidle'});
await p.evaluate(() => {
  window.__calls=[];
  const SRV = { pin:null, fail:0, lockedUntil:null, MAX:5 };
  window.fetch = async (url, opt={}) => {
    const u=String(url).replace(/^.*\/api\/v1/,''), m=opt.method||'GET';
    window.__calls.push(`${m} ${u}`);
    const J=o=>({ok:true,json:async()=>o});
    const body = opt.body? JSON.parse(opt.body) : {};
    if (u==='/child-mode/pin' && m==='GET')
      return J({ok:true,data:{is_set:!!SRV.pin, locked:!!(SRV.lockedUntil&&SRV.lockedUntil>Date.now())}});
    if (u==='/child-mode/pin' && m==='POST') {
      if (!/^\d{4}$/.test(body.pin||'')) return J({ok:false,error:{code:"VALIDATION",message:"숫자 4자리로 정해 주세요."}});
      if (/^(\d)\1{3}$/.test(body.pin) || ["1234","4321","0123"].includes(body.pin))
        return J({ok:false,error:{code:"VALIDATION",message:"너무 쉬운 번호예요. 다른 번호로 정해 주세요."}});
      SRV.pin=body.pin; SRV.fail=0; SRV.lockedUntil=null; return J({ok:true,data:{is_set:true}});
    }
    if (u==='/child-mode/unlock' && m==='POST') {
      if (!SRV.pin) return J({ok:true,data:{unlocked:true,is_set:false}});
      if (SRV.lockedUntil && SRV.lockedUntil>Date.now())
        return J({ok:false,error:{code:"LOCKED",message:"여러 번 틀렸어요. 5분 뒤에 다시 해 주세요."}});
      if (body.pin===SRV.pin) { SRV.fail=0; return J({ok:true,data:{unlocked:true,is_set:true}}); }
      SRV.fail++;
      if (SRV.fail>=SRV.MAX) { SRV.lockedUntil=Date.now()+3e5; SRV.fail=0;
        return J({ok:false,error:{code:"LOCKED",message:"여러 번 틀렸어요. 5분 뒤에 다시 해 주세요."}}); }
      return J({ok:false,error:{code:"VALIDATION",message:`번호가 달라요. ${SRV.MAX-SRV.fail}번 남았어요.`}});
    }
    return J({ok:false,error:{code:"NOT_FOUND",message:"없어요"}});
  };
  TOKENS.access="fake"; S.loggedIn=true; S.serverAuth=true;
  STUB.children=[{id:1,server_id:7,nickname:"하늘",grade:"3",school:{name:"서울초"},counts:{},pass:{active:true}}];
  S.currentChildId=1; S.missionStars=12;
  try{localStorage.setItem('eduthink.coachSeen','1')}catch(e){}; S.coach=null;
});
const type = async (pin) => { for (const d of pin) { await p.evaluate(x=>App.pinPush(x), d); await p.waitForTimeout(90);} await p.waitForTimeout(260); };
const ck = async (name, fn) => { const r = await p.evaluate(fn);
  console.log((r.pass?'✅':'🔴'), name, '—', r.msg); if(!r.pass) process.exitCode=1; };

await p.evaluate(()=>App.kidModeOn()); await p.waitForTimeout(400);
await ck('① 아이 모드 진입 → PIN 미설정이면 «정하기»가 뜬다', ()=>({pass:S.pinAsk==='set'&&S.kidMode, msg:`pinAsk=${S.pinAsk}`}));

await type('1234');
await ck('② 쉬운 번호 1234 거절 — 서버 문구 그대로', ()=>({pass:S.pinAsk==='set'&&/쉬운 번호/.test(S.pinErr), msg:JSON.stringify(S.pinErr)}));

await type('2749');
await ck('③ 정하기 성공 → 모달 닫힘', ()=>({pass:S.pinAsk===null&&S.kidMode, msg:`pinAsk=${S.pinAsk} kidMode=${S.kidMode}`}));

await ck('④ 아이 모드 문지기 — 부모 화면 주소를 눌러도 못 나간다', ()=>{
  location.hash='#mypage'; App.render();
  return {pass:location.hash==='#childview', msg:`hash=${location.hash}`}});

await p.evaluate(()=>App.kidModeOut()); await p.waitForTimeout(200);
await type('1111');
await ck('⑤ 틀린 번호 → 남은 횟수를 서버가 세어 알려준다', ()=>({pass:/4번 남았어요/.test(S.pinErr)&&S.kidMode, msg:JSON.stringify(S.pinErr)}));

for (let i=0;i<4;i++) await type('1111');
await ck('⑥ 5번 틀리면 잠금 — 서버가 막는다', ()=>({pass:/5분 뒤에/.test(S.pinErr), msg:JSON.stringify(S.pinErr)}));

await type('2749');
await ck('⑦ 잠금 중엔 맞는 번호도 안 통한다', ()=>({pass:S.kidMode&&/5분 뒤에/.test(S.pinErr), msg:`kidMode=${S.kidMode}`}));

await p.evaluate(()=>{ window.fetch.__unlock=1;
  const f=window.fetch; window.fetch=async(u,o)=>{ if(/unlock/.test(String(u)))
    return {ok:true,json:async()=>({ok:true,data:{unlocked:true,is_set:true}})}; return f(u,o); }; });
await type('2749');
await ck('⑧ 맞는 번호 → 부모 화면 복귀', ()=>({pass:!S.kidMode&&!S.childView&&location.hash==='#home', msg:`kidMode=${S.kidMode} hash=${location.hash}`}));

console.log('\n호출:', (await p.evaluate(()=>window.__calls)).join(' | '));
console.log('JS 오류:', errs.length?errs:'없음');
await b.close();
