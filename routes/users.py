# routes/users.py
# -------------------------------------------------------------
# 사용자 관련 API
#
# 제공 엔드포인트
#   - GET  /v1/users/me        : 내 기본 정보 (토큰 검증 결과)
#   - GET  /v1/users/prefs     : 내 접근성/환경 설정 가져오기
#   - PUT  /v1/users/prefs     : 내 접근성/환경 설정 저장(병합)
#
# Firestore 구조(권장):
#   users/{uid}  문서 예시:
#     {
#       "email": "test@example.com",
#       "prefs": {
#         "ttsSpeed": 1.0,           # 음성 안내 속도
#         "ttsEnabled": true,         # 음성 안내 사용
#         "fontScale": 1.0            # 글자 크기 배율
#       },
#       "updatedAt": <server ts>
#     }
# -------------------------------------------------------------

from flask import Blueprint, jsonify, request
from firebase_admin import firestore
from auth import require_auth
from services.firestore import add_doc, get_doc

bp = Blueprint("users", __name__, url_prefix="/v1/users")


@bp.get("/me")
@require_auth
def me():
    """
    내 기본 정보.
    - 토큰 검증으로 얻은 uid/email만 반환
    - 필요 시, Firestore의 users/{uid}를 함께 읽어와도 되지만
      여기서는 가볍게 토큰 기반 정보만 제공
    """
    return jsonify({
        "uid": request.user["uid"],
        "email": request.user.get("email"),
    })


@bp.get("/prefs")
@require_auth
def get_prefs():
    """
    내 접근성/환경 설정 조회.
    - users/{uid} 문서의 prefs 필드를 반환
    - 문서가 없거나 prefs가 없으면 기본값 제공
    """
    uid = request.user["uid"]
    doc = get_doc("users", uid) or {}
    prefs = doc.get("prefs") or {}
    # 기본값(초간단)
    prefs.setdefault("ttsSpeed", 1.0)
    prefs.setdefault("ttsEnabled", True)
    prefs.setdefault("fontScale", 1.0)

    return jsonify({"uid": uid, "prefs": prefs})


@bp.put("/prefs")
@require_auth
def update_prefs():
    """
    내 접근성/환경 설정 저장(병합).
    Body 예시:
      {
        "ttsSpeed": 0.9,
        "ttsEnabled": true,
        "fontScale": 1.1
      }

    - 전달된 키만 병합 저장
    - users/{uid} 문서에 email, updatedAt도 같이 갱신
    """
    uid = request.user["uid"]
    body = request.get_json() or {}

    # 최소 유효성(숫자/불리언만 허용 - 엄격 검증은 추후 확장)
    allowed_keys = {"ttsSpeed", "ttsEnabled", "fontScale"}
    update = {k: v for k, v in body.items() if k in allowed_keys}

    # 아무 키도 없으면 400
    if not update:
        return jsonify({"error": "no valid fields in body"}), 400

    # 병합 저장: users/{uid}
    add_doc("users", {
        "email": request.user.get("email"),
        "prefs": update,
        "updatedAt": firestore.SERVER_TIMESTAMP
    }, doc_id=uid)

    # 저장 후 최신값 반환
    doc = get_doc("users", uid) or {}
    return jsonify({"uid": uid, "prefs": doc.get("prefs", {})})
