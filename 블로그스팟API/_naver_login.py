# -*- coding: utf-8 -*-
"""네이버 최초 로그인용 스크립트 — 네이버_로그인.bat 더블클릭으로 실행됨.

주의: 이 검은 창(CMD)을 직접 닫으면 브라우저도 같이 꺼집니다.
로그인만 완료하면 브라우저와 이 창 모두 자동으로 닫힙니다.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from naver_publish import ensure_login

if __name__ == "__main__":
    print("=" * 50)
    print("  이 창을 직접 닫지 마세요! (브라우저도 같이 꺼짐)")
    print("  브라우저에서 로그인만 하면 전부 자동으로 닫힙니다.")
    print("=" * 50)
    try:
        ensure_login(wait_minutes=10)
        print("\n로그인 세션 저장 완료! 3초 후 자동으로 닫힙니다.")
        time.sleep(3)
    except Exception as e:
        print(f"\n오류: {e}")
        input("\n오류 내용 확인 후 엔터를 누르면 종료합니다...")
