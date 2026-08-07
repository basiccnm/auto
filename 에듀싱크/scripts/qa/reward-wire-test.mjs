/* 보상 배선 검증 — 서버 계약(api_reward.js)대로 답하는 «가짜 API»를 물려
   화면이 실제로 왕복하는지 8항목을 돌린다. wrangler 없이 돌아간다.
     node scripts/qa/reward-wire-test.mjs      (앞서 app/www 를 정적 서버로 8789 에 띄워 둘 것)
   ⚠ 이건 «배선» 검사다. 서버 로직은 별도로 임시 SQLite 에 부어 검증한다.
   ⚠ 화면은 REWARD_STUB 를 안 쓴다(2026-08-07 배선 완료) — 목업 데이터가 실사용자에게
     «있지도 않은 상품»으로 보이면 빈 상태보다 나쁘다. 하네스만 rewardSeed() 를 손수 부른다. */
import { chromium } from 'playwright';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const p=await b.newPage({viewport:{width:360,height:800}});
const calls=[];
p.on('console',m=>{ if(m.type()==='error') calls.push('CONSOLE-ERR: '+m.text()); });
p.on('pageerror',e=>calls.push('PAGEERROR: '+e.message));
await p.goto('http://127.0.0.1:8789/index.mockup.html',{waitUntil:'networkidle'});

// ── 서버 계약대로 답하는 가짜 API (api_reward.js 응답 봉투 그대로) ──
await p.evaluate(() => {
  window.__calls = [];
  const DB = {
    store: [ {item_id:"s1",title:"유튜브 30분",stars_required:5,limit_type:"weekly",limit_count:2,used:1,can_buy:true,reason:null},
             {item_id:"s3",title:"용돈 2,000원",stars_required:15,limit_type:"monthly",limit_count:2,used:0,can_buy:false,reason:"stars"} ],
    tickets: [ {reward_order_id:"r1",item_title:"유튜브 30분",stars_spent:5,status:"requested",created_at:"오늘"} ],
    verify: [ {verify_id:"v1",title:"수학 문제집",step1:"10~20쪽",photo:true,bonus:2} ],
    stars: 12,
  };
  window.fetch = async (url, opt={}) => {
    const u = String(url).replace(/^.*\/api\/v1/,''); const m = opt.method || 'GET';
    window.__calls.push(`${m} ${u}`);
    const J = (o) => ({ ok:true, json: async()=>o });
    if (m==='GET'  && /^\/children\/\d+\/store$/.test(u))   return J({ok:true,data:{items:DB.store,stars:DB.stars}});
    if (m==='GET'  && /^\/children\/\d+\/rewards$/.test(u)) return J({ok:true,data:{items:DB.tickets,stars:DB.stars}});
    if (m==='GET'  && /^\/children\/\d+\/verify/.test(u))   return J({ok:true,data:{items:DB.verify}});
    if (m==='POST' && /^\/children\/\d+\/store$/.test(u)) {
      const bd=JSON.parse(opt.body); DB.store.push({item_id:"n1",...bd,used:0,can_buy:true,reason:null});
      return J({ok:true,data:{item_id:"n1"}}); }
    if (m==='DELETE' && /^\/store\//.test(u)) { DB.store=DB.store.filter(x=>x.item_id!==u.split('/')[2]); return J({ok:true,data:{}}); }
    if (m==='POST' && /\/store\/.+\/buy$/.test(u)) {
      DB.stars-=5; DB.tickets.unshift({reward_order_id:"r2",item_title:"유튜브 30분",stars_spent:5,status:"requested",created_at:"방금"});
      return J({ok:true,data:{reward_order_id:"r2",item_title:"유튜브 30분",stars_spent:5,stars_left:DB.stars}}); }
    if (m==='POST' && /^\/rewards\/.+\/fulfill$/.test(u)) {
      const t=DB.tickets.find(x=>x.reward_order_id===u.split('/')[2]); if(t)t.status='fulfilled';
      return J({ok:true,data:{status:'fulfilled'}}); }
    if (m==='POST' && /^\/verify\/.+\/bonus$/.test(u)) {
      DB.verify=[]; DB.stars+=2; return J({ok:true,data:{stars:DB.stars}}); }
    return J({ok:false,error:{code:"NOT_FOUND",message:"없어요"}});
  };
  // 서버 붙은 계정 흉내
  TOKENS.access="fake"; S.loggedIn=true; S.serverAuth=true;
  STUB.children=[{id:1,server_id:7,nickname:"하늘",grade:"3",school:{name:"서울초"},counts:{},pass:{active:true}}];
  S.currentChildId=1; S.missionStars=12;
  S.storeItems=null; S.tickets=null; S.verifyAsk=null;
  try{localStorage.setItem('eduthink.coachSeen','1')}catch(e){}; S.coach=null;
});

const step = async (name, fn, check) => {
  await p.evaluate(fn); await p.waitForTimeout(320);
  const r = await p.evaluate(check);
  console.log((r.pass?'✅':'🔴'), name, '—', r.msg);
  if(!r.pass) process.exitCode=1;
};

await step('① 진열대 진입 → 서버에서 목록', ()=>{location.hash='#storeset';App.render()},
  ()=>({pass:(S.storeItems||[]).length===2 && document.body.innerText.includes('유튜브 30분'),
        msg:`items=${(S.storeItems||[]).length} 호출=${window.__calls.join(', ')}`}));

await step('② 올리기 → POST 후 재조회', ()=>{S.storeAdd=true;App.render();
    document.getElementById('stTitle').value='편의점 과자';
    document.getElementById('stStars').value='8'; App.storeAddSave()},
  ()=>({pass:(S.storeItems||[]).some(x=>x.title==='편의점 과자') && !S.storeAdd,
        msg:`items=${(S.storeItems||[]).length}`}));

await step('③ 내리기 → DELETE', ()=>App.storeDel('s1'),
  ()=>({pass:!(S.storeItems||[]).some(x=>x.item_id==='s1'), msg:`items=${(S.storeItems||[]).length}`}));

await step('④ 아이 상점 — 서버 can_buy 반영(★부족은 흐리게)', ()=>{location.hash='#store';App.render()},
  ()=>{const off=[...document.querySelectorAll('.sp-card.off')].map(e=>e.innerText.replace(/\n/g,' '));
       return {pass:off.some(t=>t.includes('용돈')), msg:`off=${JSON.stringify(off)}`}});

await step('⑤ 바꾸기 → 별 차감 + 티켓 생김', ()=>{S.storeBuy='n1';location.hash='#storebuy';App.render();App.storeBuyGo()},
  ()=>({pass:S.missionStars===7 && (S.tickets||[]).some(t=>t.reward_order_id==='r2'),
        msg:`stars=${S.missionStars} tickets=${(S.tickets||[]).length}`}));

await step('⑥ 바꿔줬어요 → fulfilled', ()=>{location.hash='#mission';App.render();App.ticketGive('r1')},
  ()=>({pass:(S.tickets||[]).find(t=>t.reward_order_id==='r1')?.status==='fulfilled',
        msg:(S.tickets||[]).map(t=>t.status).join(',')}));

await step('⑦ 보너스 ★2 → 별 증가 + 목록에서 빠짐', ()=>App.verifyBonus('v1',2),
  ()=>({pass:S.missionStars===9 && (S.verifyAsk||[]).length===0,
        msg:`stars=${S.missionStars} verify=${(S.verifyAsk||[]).length}`}));

// 오류 경로 — 서버 메시지를 그대로 보여주는가
await p.evaluate(()=>{ const f=window.fetch;
  window.fetch=async(u,o)=>{ if(/\/buy$/.test(String(u))) return {ok:true,json:async()=>({ok:false,error:{code:"LIMIT_EXCEEDED",message:"이번 주에 살 수 있는 만큼 다 샀어요."}})}; return f(u,o); };
  S.storeBuy=(S.storeItems[0]||{}).item_id; location.hash='#storebuy'; App.render(); App.storeBuyGo(); });
await p.waitForTimeout(350);
const toastTxt = await p.evaluate(()=>document.querySelector('.toast')?.innerText || '');
console.log(toastTxt.includes('다 샀어요')?'✅':'🔴','⑧ 상한 초과 — 서버 문구 그대로 노출 —', JSON.stringify(toastTxt));
if(!toastTxt.includes('다 샀어요')) process.exitCode=1;

console.log('\n호출 로그:', (await p.evaluate(()=>window.__calls)).join('\n           '));
console.log('JS 오류:', calls.length? calls : '없음');
await b.close();
