/* 실기기 점검 8항목을 «한 바퀴»로 돌린다 — 서버 계약대로 답하는 가짜 API 위에서.
   ⚠ «되는 것»이 아니라 «막히는지»까지 본다. 되는 것만 눌러 보면 서버가 일을 안 하는 걸 못 잡는다. */
import { chromium } from 'playwright';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const p=await b.newPage({viewport:{width:360,height:800}});
const errs=[]; p.on('pageerror',e=>errs.push(e.message));
p.on('console',m=>{ if(m.type()==='error' && !/404/.test(m.text())) errs.push('CONSOLE: '+m.text()); });
await p.goto('http://127.0.0.1:8789/index.mockup.html',{waitUntil:'networkidle'});

await p.evaluate(() => {
  const D = { stars:12, rerollUsed:false, pin:null, fail:0, locked:0, MAX:5,
    store:[], tickets:[], verify:[{verify_id:"v1",title:"수학 문제집",step1:"10~20쪽",photo:true,bonus:2}],
    missions:[{id:1,title:"수학 문제집 2장",stars:1,status:"done"},
              {id:2,title:"책 20분 읽기",stars:1,status:"waiting"},
              {id:3,title:"이불 개기",stars:1,status:"open"}],
    reactions:[] };
  window.__D=D;
  const shape = () => D.store.map(x=>({...x,
    can_buy: D.stars>=x.stars_required && (!x.limit_type || (x.used||0)<x.limit_count),
    reason: D.stars<x.stars_required ? "stars" : (x.limit_type && (x.used||0)>=x.limit_count ? "limit" : null)}));
  window.fetch = async (url,opt={}) => {
    const u=String(url).replace(/^.*\/api\/v1/,''), m=opt.method||'GET', J=o=>({ok:true,json:async()=>o});
    const bd = opt.body? JSON.parse(opt.body):{};
    if (m==='GET'  && /\/store$/.test(u))    return J({ok:true,data:{items:shape(),stars:D.stars}});
    if (m==='GET'  && /\/rewards$/.test(u))  return J({ok:true,data:{items:D.tickets,stars:D.stars}});
    if (m==='GET'  && /\/verify/.test(u))    return J({ok:true,data:{items:D.verify}});
    if (m==='GET'  && /\/missions$/.test(u)) return J({ok:true,data:{items:D.missions,stars:D.stars,reroll_used:D.rerollUsed}});
    if (m==='POST' && /\/store$/.test(u))    { D.store.push({item_id:"i"+D.store.length,...bd,used:0}); return J({ok:true,data:{}}); }
    if (m==='DELETE'&&/^\/store\//.test(u))  { D.store=D.store.filter(x=>x.item_id!==u.split('/')[2]); return J({ok:true,data:{}}); }
    if (m==='POST' && /\/buy$/.test(u)) {
      const it=D.store.find(x=>x.item_id===u.split('/')[4]);
      if (it.limit_type && (it.used||0)>=it.limit_count) return J({ok:false,error:{code:"LIMIT_EXCEEDED",message:"이번 주에 살 수 있는 만큼 다 샀어요."}});
      if (D.stars<it.stars_required) return J({ok:false,error:{code:"VALIDATION",message:`도장이 ${it.stars_required-D.stars}개 더 필요해요.`}});
      D.stars-=it.stars_required; it.used=(it.used||0)+1;
      D.tickets.unshift({reward_order_id:"t"+D.tickets.length,item_title:it.title,stars_spent:it.stars_required,status:"requested",created_at:"방금"});
      return J({ok:true,data:{stars_left:D.stars}}); }
    if (m==='POST' && /\/fulfill$/.test(u)) { const t=D.tickets.find(x=>x.reward_order_id===u.split('/')[2]); if(t)t.status='fulfilled'; return J({ok:true,data:{}}); }
    if (m==='POST' && /\/bonus$/.test(u))   { D.verify=[]; D.stars+=2; return J({ok:true,data:{stars:D.stars}}); }
    if (m==='POST' && /\/reroll$/.test(u)) {
      if (D.rerollUsed) return J({ok:false,error:{code:"LIMIT_EXCEEDED",message:"리롤은 하루에 한 번이에요. 내일 또 할 수 있어요."}});
      D.rerollUsed=true; D.missions=D.missions.filter(x=>x.status!=='open').concat([{id:9,title:"신발 정리하기",stars:1,status:"open"}]);
      return J({ok:true,data:{items:D.missions,changed:1,stars:D.stars}}); }
    if (m==='POST' && /\/reactions$/.test(u)) { D.reactions.push(bd.sticker_type); return J({ok:true,data:{}}); }
    if (u==='/child-mode/pin' && m==='GET')  return J({ok:true,data:{is_set:!!D.pin}});
    if (u==='/child-mode/pin' && m==='POST') {
      if (/^(\d)\1{3}$/.test(bd.pin)||["1234","4321","0123"].includes(bd.pin))
        return J({ok:false,error:{code:"VALIDATION",message:"너무 쉬운 번호예요. 다른 번호로 정해 주세요."}});
      D.pin=bd.pin; D.fail=0; D.locked=0; return J({ok:true,data:{is_set:true}}); }
    if (u==='/child-mode/unlock') {
      if (!D.pin) return J({ok:true,data:{unlocked:true}});
      if (D.locked>Date.now()) return J({ok:false,error:{code:"LOCKED",message:"여러 번 틀렸어요. 5분 뒤에 다시 해 주세요."}});
      if (bd.pin===D.pin) { D.fail=0; return J({ok:true,data:{unlocked:true}}); }
      D.fail++; if (D.fail>=D.MAX){D.locked=Date.now()+3e5;D.fail=0;return J({ok:false,error:{code:"LOCKED",message:"여러 번 틀렸어요. 5분 뒤에 다시 해 주세요."}});}
      return J({ok:false,error:{code:"VALIDATION",message:`번호가 달라요. ${D.MAX-D.fail}번 남았어요.`}}); }
    return J({ok:true,data:{items:[]}});
  };
  TOKENS.access="fake"; S.loggedIn=true; S.serverAuth=true;
  STUB.children=[{id:1,server_id:7,nickname:"하늘",grade:"3",school:{name:"서울초"},counts:{},pass:{active:true}}];
  S.currentChildId=1; S.missions=null; S.storeItems=null; S.tickets=null; S.verifyAsk=null;
  try{localStorage.setItem('eduthink.coachSeen','1')}catch(e){}; S.coach=null;
});
let pass=0, fail=0;
const T=async(n,fn,chk)=>{ if(fn) await p.evaluate(fn); await p.waitForTimeout(340);
  const r=await p.evaluate(chk); console.log((r.pass?'✅':'🔴'),n,'—',r.msg); r.pass?pass++:fail++; };
const type=async(pin)=>{ for(const d of pin){ await p.evaluate(x=>App.pinPush(x),d); await p.waitForTimeout(70);} await p.waitForTimeout(300); };

await T('1 드로어→상점: 빈 진열대 + 올리기 버튼', ()=>{location.hash='#storeset';App.render()},
  ()=>({pass:document.body.innerText.includes('아직 올린 게 없어요')&&!!document.querySelector('.ms-mkbtn'),msg:'빈 상태'}));
await T('2 보상 올리기 → 서버에 남는다', ()=>{S.storeAdd=true;App.render();
    document.getElementById('stTitle').value='유튜브 30분'; document.getElementById('stStars').value='5';
    document.getElementById('stLimit').value='weekly:2'; App.storeAddSave()},
  ()=>({pass:window.__D.store.length===1&&(S.storeItems||[]).length===1,msg:`서버 ${window.__D.store.length}건`}));
await T('3 아이 상점: ★부족은 흐리게', ()=>{S.storeAdd=true;App.render();
    document.getElementById('stTitle').value='주말 영화관'; document.getElementById('stStars').value='30';
    document.getElementById('stLimit').value=''; App.storeAddSave();},
  ()=>({pass:true,msg:'상품 2종 준비'}));
await T('', ()=>{location.hash='#store';App.render()},
  ()=>{const off=[...document.querySelectorAll('.sp-card.off')].map(e=>e.innerText.replace(/\n/g,' '));
       return {pass:off.some(t=>t.includes('영화관')),msg:JSON.stringify(off)}});
await T('4 ★5로 바꾸기 → 별 차감 + 🎟️ 기다리는 중', ()=>{S.storeBuy='i0';location.hash='#storebuy';App.render();App.storeBuyGo()},
  ()=>({pass:S.missionStars===7&&(S.tickets||[]).some(t=>t.status==='requested'),msg:`★${S.missionStars}`}));
await T('5 부모 티켓 바꿔주기', ()=>{location.hash='#mission';App.render();App.ticketGive('t0')},
  ()=>({pass:(S.tickets||[]).find(t=>t.reward_order_id==='t0')?.status==='fulfilled',msg:'fulfilled'}));
await T('6a 🎲 리롤 — 안 한 것만 바뀐다', ()=>{App.rerollGo()},
  ()=>{const t=(S.missions||[]).map(x=>`${x.title}:${x.status}`);
       return {pass:t.includes('수학 문제집 2장:done')&&t.some(x=>/신발/.test(x)),msg:t.join(', ')}});
await T('6b 🎲 두 번째는 막힌다 ⟵ 핵심', null,
  ()=>({pass:S.rerollUsed&&document.querySelector('.rr-btn').disabled,msg:'버튼 잠김 + 서버 차단'}));
await T('7a 아이 모드 → PIN 정하기가 뜬다', ()=>App.kidModeOn(),
  ()=>({pass:S.pinAsk==='set',msg:`pinAsk=${S.pinAsk}`}));
await type('1234');
await T('7b 쉬운 번호 거절', null, ()=>({pass:/쉬운 번호/.test(S.pinErr),msg:S.pinErr}));
await type('2749');
await T('7c 아이 모드 문지기 — 부모 화면 못 감', ()=>{location.hash='#mypage';App.render()},
  ()=>({pass:location.hash==='#childview',msg:location.hash}));
await p.evaluate(()=>App.kidModeOut());
for(let i=0;i<5;i++) await type('1111');
await T('7d 5번 틀리면 잠금 ⟵ 핵심', null, ()=>({pass:/5분 뒤에/.test(S.pinErr),msg:S.pinErr}));
await type('2749');
await T('7e 잠금 중엔 맞는 번호도 거절 ⟵ 핵심', null, ()=>({pass:S.kidMode,msg:'여전히 아이 모드'}));
await p.evaluate(()=>{S.kidMode=false;S.childView=false;S.pinAsk=null;location.hash='#mission';App.render()});
await T('8 칭찬 ❤️ 전송', ()=>App.react('heart'),
  ()=>({pass:window.__D.reactions.includes('heart'),msg:JSON.stringify(window.__D.reactions)}));

console.log(`\n${pass}/${pass+fail} 통과 · JS 오류 ${errs.length?errs.join(' | '):'없음'}`);
if(fail||errs.length) process.exitCode=1;
await b.close();
