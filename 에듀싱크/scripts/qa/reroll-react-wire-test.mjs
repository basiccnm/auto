import { chromium } from 'playwright';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
const p=await b.newPage({viewport:{width:360,height:800}});
const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.goto('http://127.0.0.1:8789/index.mockup.html',{waitUntil:'networkidle'});
await p.evaluate(() => {
  window.__calls=[];
  const SRV = {
    rerollUsed:false,
    items:[{id:1,title:"수학 문제집 2장",stars:1,status:"done",area:"study",verify:"tap"},
           {id:2,title:"책 20분 읽기",stars:1,status:"waiting",area:"read",verify:"review"},
           {id:3,title:"이불 개기",stars:1,status:"open",area:"life",verify:"tap"}],
    reactions:[],
  };
  window.fetch = async (url, opt={}) => {
    const u=String(url).replace(/^.*\/api\/v1/,''), m=opt.method||'GET';
    window.__calls.push(`${m} ${u}`);
    const J=o=>({ok:true,json:async()=>o});
    if (m==='GET' && /\/missions$/.test(u))
      return J({ok:true,data:{items:SRV.items,stars:12,reroll_used:SRV.rerollUsed}});
    if (m==='POST' && /\/missions\/reroll$/.test(u)) {
      if (SRV.rerollUsed) return J({ok:false,error:{code:"LIMIT_EXCEEDED",message:"리롤은 하루에 한 번이에요. 내일 또 할 수 있어요."}});
      SRV.rerollUsed=true;
      SRV.items=SRV.items.filter(x=>x.status!=='open').concat(
        [{id:9,title:"신발 정리하기",stars:1,status:"open",area:"life",verify:"tap"}]);
      return J({ok:true,data:{items:SRV.items,changed:1,stars:12}});
    }
    if (m==='POST' && /\/reactions$/.test(u)) {
      const t=JSON.parse(opt.body).sticker_type;
      if (t!=='thumb_up'&&t!=='heart') return J({ok:false,error:{code:"VALIDATION",message:"없는 스티커예요."}});
      SRV.reactions.push(t); return J({ok:true,data:{reaction_id:"rc1"}});
    }
    if (m==='GET' && /\/verify/.test(u)) return J({ok:true,data:{items:[{verify_id:"v1",title:"수학 문제집",step1:"10~20쪽",photo:true,bonus:2}]}});
    if (m==='GET' && /\/store$/.test(u)) return J({ok:true,data:{items:[],stars:12}});
    if (m==='GET' && /\/rewards$/.test(u)) return J({ok:true,data:{items:[],stars:12}});
    return J({ok:true,data:{items:[]}});
  };
  window.__srv=SRV;
  TOKENS.access="fake"; S.loggedIn=true; S.serverAuth=true;
  STUB.children=[{id:1,server_id:7,nickname:"하늘",grade:"3",school:{name:"서울초"},counts:{},pass:{active:true}}];
  S.currentChildId=1; S.missions=null; S.missionStars=12;
  try{localStorage.setItem('eduthink.coachSeen','1')}catch(e){}; S.coach=null;
});
const ck=async(n,f)=>{const r=await p.evaluate(f);console.log((r.pass?'✅':'🔴'),n,'—',r.msg);if(!r.pass)process.exitCode=1;};

await p.evaluate(()=>{location.hash='#mission';App.render()}); await p.waitForTimeout(500);
await ck('① 미션 화면 — 🎲 버튼이 카드 위에 뜬다', ()=>{
  const b=document.querySelector('.rr-btn');
  return {pass:!!b&&!b.disabled&&b.innerText.includes('바꾸기'), msg:JSON.stringify(b?.innerText.replace(/\n/g,' '))}});

await p.evaluate(()=>App.rerollAsk()); await p.waitForTimeout(200);
await ck('② 확인 모달 (⛔ alert 아님)', ()=>({pass:S.rerollAsk&&!!document.querySelector('.modal .modal-card'),
  msg:document.querySelector('.modal-card h2')?.innerText||''}));

await p.evaluate(()=>App.rerollGo()); await p.waitForTimeout(400);
await ck('③ 리롤 — open 만 바뀌고 done/waiting 은 그대로', ()=>{
  const t=(S.missions||[]).map(x=>`${x.title}:${x.status}`);
  return {pass:t.includes('수학 문제집 2장:done')&&t.includes('책 20분 읽기:waiting')&&t.some(x=>x.startsWith('신발 정리하기')),
          msg:t.join(', ')}});

await ck('④ 두 번째는 서버가 막고 버튼도 잠긴다', ()=>{
  const b=document.querySelector('.rr-btn');
  return {pass:S.rerollUsed&&b.disabled&&b.innerText.includes('다 썼어요'), msg:b.innerText.replace(/\n/g,' ')}});

await p.evaluate(()=>App.rerollAsk()); await p.waitForTimeout(250);
await ck('⑤ 잠긴 버튼을 코드로 눌러도 모달이 안 열린다', ()=>({pass:!S.rerollAsk, msg:`rerollAsk=${S.rerollAsk}`}));

await ck('⑥ 칭찬 스티커 줄이 «확인해 주세요» 위에 있다', ()=>{
  const rc=document.querySelector('.rc-row'), rw=document.querySelector('.rw-h');
  return {pass:!!rc&&!!rw&&(rc.compareDocumentPosition(rw)&Node.DOCUMENT_POSITION_FOLLOWING)>0,
          msg:rc?rc.innerText.replace(/\n/g,' '):'없음'}});

await p.evaluate(()=>App.react('heart')); await p.waitForTimeout(350);
await ck('⑦ ❤️ 전송 → 서버 도달 + 눌린 표시', ()=>({pass:window.__srv.reactions.includes('heart')&&S.reactSent==='heart',
  msg:`reactions=${JSON.stringify(window.__srv.reactions)}`}));

console.log('\n호출:', (await p.evaluate(()=>window.__calls)).filter(c=>/reroll|reactions|missions$/.test(c)).join(' | '));
console.log('JS 오류:', errs.length?errs:'없음');
await b.close();
