# auth.py
# -------------------------------------------------------------
# Firebase Authentication ID 토큰 검증용 데코레이터
# 앱에서 전달한 Bearer 토큰을 검증하여 request.user에 정보 저장
# -------------------------------------------------------------

import os
from functools import wraps
from flask import request, jsonify
import firebase_admin
from firebase_admin import credentials, auth

# Firebase Admin 초기화 (앱 실행 시 1회)
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    firebase_admin.initialize_app(cred)

def require_auth(f):
    """Firebase ID 토큰 검증 데코레이터"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Authorization 헤더 확인
        hdr = request.headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            return jsonify({"error": "Missing Bearer token"}), 401

        id_token = hdr.split(" ", 1)[1]
        try:
            # 토큰 검증 및 사용자 정보 추출
            decoded = auth.verify_id_token(id_token)
            request.user = {
                "uid": decoded["uid"],
                "email": decoded.get("email")
            }
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        # 다음 함수 실행
        return f(*args, **kwargs)
    return wrapper
