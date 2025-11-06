# routes/sessions.py
# -------------------------------------------------------------
# 세션 관련 API
#   - /v1/sessions/start : 학습 세션 시작
#   - /v1/sessions/finish : 학습 세션 종료
# -------------------------------------------------------------

from flask import Blueprint, jsonify, request
from firebase_admin import firestore
from auth import require_auth
from services.firestore import add_doc

bp = Blueprint("sessions", __name__, url_prefix="/v1/sessions")

@bp.post("/start")
@require_auth
def start_session():
    """학습 세션 시작: 카테고리와 함께 Firestore에 문서 생성"""
    payload = request.get_json() or {}
    category = payload.get("category")

    # Firestore에 세션 문서 추가
    doc_id = add_doc("sessions", {
        "uid": request.user["uid"],
        "category": category,
        "startedAt": firestore.SERVER_TIMESTAMP,
        "status": "RUNNING"
    })
    return jsonify({"sessionId": doc_id, "status": "RUNNING"})


@bp.post("/finish")
@require_auth
def finish_session():
    """학습 세션 종료: 상태 업데이트"""
    payload = request.get_json() or {}
    sid = payload.get("sessionId")
    if not sid:
        return jsonify({"error": "sessionId required"}), 400

    add_doc("sessions", {
        "status": "DONE",
        "finishedAt": firestore.SERVER_TIMESTAMP
    }, doc_id=sid)

    return jsonify({"sessionId": sid, "status": "DONE"})
