# app.py
# -------------------------------------------------------------
# Flask 기반 서버 메인 파일
# 주요 기능:
#   - Firebase Admin 초기화
#   - 사용자 인증 미들웨어 적용
#   - 세션 시작/종료, 이벤트 기록, 통계 조회 라우트 등록
# -------------------------------------------------------------
from dotenv import load_dotenv
# .env 파일에서 환경 변수 로드
load_dotenv()

import os
from flask import Flask, jsonify
from auth import require_auth
from routes import sessions, events, stats, users



app = Flask(__name__)

# ----- 공통 라우트 -----
@app.get("/health")
def health_check():
    """서버 헬스 체크용 엔드포인트"""
    return jsonify({"ok": True})


# ----- 프론트 테스트용 -------
@app.get("/test")
def serve_test():
    """로컬 테스트용 HTML 페이지"""
    return open("testFront.html", encoding="utf-8").read()


# ----- 블루프린트 등록 -----
app.register_blueprint(users.bp)
app.register_blueprint(sessions.bp)
app.register_blueprint(events.bp)
app.register_blueprint(stats.bp)

# ----- 서버 실행 -----
if __name__ == "__main__":
    app.run(debug=True)
