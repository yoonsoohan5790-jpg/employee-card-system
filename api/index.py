"""Vercel Python 서버리스 진입점. vercel.json의 builds/routes가 이 파일을 가리킨다."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402

# Vercel 런타임이 WSGI callable `app`을 그대로 사용한다.
