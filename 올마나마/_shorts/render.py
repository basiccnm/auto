# -*- coding: utf-8 -*-
"""쇼츠 렌더 — HTML → 프레임 → mp4 (2026-07-21)

왜 이렇게 하나:
  Flow로 영상을 뽑으면 크레딧이 나가고 스타일이 매번 흔들린다.
  올마·숫자·인트로가 전부 HTML/CSS/SVG라 **브라우저를 그대로 찍으면** 된다.
  비용 0, 100% 재현, 수정은 코드 한 줄.

🔴 실시간 녹화가 아니라 **한 프레임씩 시간을 밀어** 찍는다.
   실시간이면 렌더가 느릴 때 프레임이 빠져 영상이 튄다.
   time_ms를 주입해 CSS 애니메이션을 그 시점으로 고정한 뒤 찍는다.

  python render.py                 # 기본 33초 · 30fps
  python render.py --fps 24        # 가볍게
  python render.py --sec 6         # 앞 6초만 (시험용)
"""
import argparse
import asyncio
import os
import shutil
import subprocess
import sys

import imageio_ffmpeg
from playwright.async_api import async_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(BASE, "editor.html")
FRAMES = os.path.join(BASE, "frames")
OUT = os.path.join(BASE, "out")
W, H = 1080, 1920


async def shoot(fps, sec, out_name):
    total = int(fps * sec)
    # 폴더째 지우면 윈도우에서 권한 오류가 난다 — 안의 png만 비운다
    os.makedirs(FRAMES, exist_ok=True)
    for f in os.listdir(FRAMES):
        if f.endswith(".png"):
            try: os.remove(os.path.join(FRAMES, f))
            except OSError: pass
    os.makedirs(OUT, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--force-device-scale-factor=1",
                                                 "--disable-lcd-text"])
        page = await browser.new_page(viewport={"width": W, "height": H},
                                      device_scale_factor=1)
        await page.goto("file:///" + HTML.replace("\\", "/"))
        await page.wait_for_timeout(700)

        # 편집기 UI를 걷어내고 무대만 1:1로 남긴다
        await page.evaluate("""() => {
          for (let i=1;i<9999;i++){clearInterval(i);clearTimeout(i);}
          document.getElementById('right')?.remove();
          document.getElementById('ctl')?.remove();
          document.getElementById('bar')?.remove();
          document.getElementById('tabs')?.remove();
          document.querySelectorAll('.handle,#insp').forEach(e=>e.remove());
          // 🔴 무대를 화면 좌상단에 1:1로 딱 붙인다.
          //    --z만 1로 바꾸면 프레임/좌측패널 크기가 안 맞아 그림이 구석으로 쪼그라든다.
          document.documentElement.style.setProperty('--z','1');
          const f=document.getElementById('frame');
          Object.assign(f.style,{position:'fixed',left:'0',top:'0',
            width:'1080px',height:'1920px',borderRadius:'0',boxShadow:'none',margin:'0',overflow:'hidden'});
          const l=document.getElementById('left');
          Object.assign(l.style,{position:'static',width:'1080px',height:'1920px',
            padding:'0',minWidth:'0',display:'block',overflow:'visible'});
          const stg=document.getElementById('stage');
          Object.assign(stg.style,{position:'absolute',left:'0',top:'0',
            transform:'none',width:'1080px',height:'1920px'});
          document.body.style.cssText='margin:0;padding:0;overflow:hidden;background:#000;width:1080px';
          document.documentElement.style.cssText='margin:0;padding:0;overflow:hidden;width:1080px';
          // 🔴 전환(transition)을 즉시 끝나게 한다. 안 그러면 seek 후 화면이 바래거나 안 올라온다.
          const st=document.createElement('style');
          st.textContent='*,*::before,*::after{transition-duration:0s !important;transition-delay:0s !important}';
          document.head.appendChild(st);
        }""")

        print(f"  {total} 프레임 캡처 ({sec}초 · {fps}fps)")
        for i in range(total):
            t = i / fps
            # 🔴 그 시각의 상태로 고정한 뒤 찍는다
            await page.evaluate("(t)=>{ if(typeof seek==='function') seek(t); }", t)
            # CSS 애니메이션(회전·둥둥)도 같은 시각으로 맞춘다
            # 반복 애니(둥둥·깜빡임·회전)만 그 시각에 맞춘다.
            # 한 번짜리(pop·punch)는 끝난 상태로 둬야 화면이 안 튄다.
            await page.evaluate("""(t)=>{
              document.getAnimations().forEach(a=>{
                try{
                  const ti=a.effect?.getTiming?.()||{};
                  const dur=ti.duration||600;
                  a.pause();
                  a.currentTime = (ti.iterations===Infinity) ? (t*1000)%dur : dur;
                }catch(e){}
              });
            }""", t)
            # 스타일이 확정되도록 한 프레임 넘긴다 (팔 회전이 중간에 걸리는 것 방지)
            await page.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
            await page.screenshot(path=os.path.join(FRAMES, f"f{i:05d}.png"))
            if i % 30 == 0:
                print(f"    {i}/{total}")
        await browser.close()

    # ── ffmpeg 인코딩 ──
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    out = os.path.join(OUT, out_name)
    cmd = [exe, "-y", "-framerate", str(fps),
           "-i", os.path.join(FRAMES, "f%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-preset", "medium", "-crf", "20",
           "-movflags", "+faststart", out]
    print("  인코딩...")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(r.stderr.decode("utf-8", "replace")[-1500:])
        sys.exit(1)
    mb = os.path.getsize(out) / 1024 / 1024
    print(f"\n✅ 완료: {out}  ({mb:.1f}MB, {W}x{H}, {sec}초)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--sec", type=float, default=33)
    ap.add_argument("--name", default="shorts.mp4")
    a = ap.parse_args()
    asyncio.run(shoot(a.fps, a.sec, a.name))
