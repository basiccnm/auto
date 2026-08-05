# -*- coding: utf-8 -*-
"""네이버 개발자센터 API 클라이언트 모음 (의존성 0).

현재: shopping — 쇼핑 검색으로 시세(단위당 가격) 산출
향후: 블로그·뉴스 검색도 같은 인증(client_id/secret)을 쓰므로 이 패키지에 파일만 추가하면 된다.
"""
from .shopping import market_price, market_prices, parse_spec, search  # noqa: F401
