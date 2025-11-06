# routes/events.py
# -------------------------------------------------------------
# 이벤트(사용자 조작 로그) 관련 API
#
# 제공 엔드포인트
#   - POST /v1/events/track   : 단일 이벤트 기록
#   - POST /v1/events/batch   : 여러 이벤트 일괄 업로드(오프라인 → 온라인 동기화 시 사용)
#
# 이벤트 공통 스키마(권장):
#   {
#     "type": "MENU_ADD" | "PAYMENT" | "NAV_CLICK" ...  # 이벤트 유형
#     "ts": 1730871000,                                  # Unix epoch (초) - 클라이언트 기준 발생 시각
#     "meta": { "duration": 1.23, "success": true, ... } # 추가 메타데이터(반응시간, 성공여부 등)
#   }
#
# 참고:
# - 실서비스에서는 멱등성(idempotency) 키를 받아 중복 업로드를 방지하는 것을 권장
#   (예: payload.idempotencyKey 를 받아 세션 하위 __batches/ 키로 마킹)
# - 본 초안은 이해를 돕기 위해 간결한 구현을 제공
# -------------------------------------------------------------

from flask import Blueprint, jsonify, request
from firebase_admin import firestore
from auth import require_auth
from services.firestore import add_doc

bp = Blueprint("events", __name__, url_prefix="/v1/events")

def _validate_event(ev: dict) -> tuple[bool, str]:
    """이벤트 페이로드 최소 유효성 검사"""
    if not isinstance(ev, dict):
        return False, "event must be an object"
    if "type" not in ev:
        return False, "event.type is required"
    if "ts" not in ev:
        return False, "event.ts is required"
    # meta는 선택이지만 dict면 더 좋음
    if "meta" in ev and not isinstance(ev["meta"], dict):
        return False, "event.meta must be an object"
    return True, ""


@bp.post("/track")
@require_auth
def track_event():
    """
    단일 이벤트 기록 엔드포인트.
    Body 예시:
      {
        "sessionId": "abc123",
        "event": {"type": "MENU_ADD", "ts": 1730871000, "meta": {"duration": 1.2, "success": true}}
      }
    """
    payload = request.get_json() or {}
    sid = payload.get("sessionId")
    ev = payload.get("event")

    if not sid:
        return jsonify({"error": "sessionId required"}), 400
    ok, msg = _validate_event(ev or {})
    if not ok:
        return jsonify({"error": msg}), 400

    # 세션 하위 컬렉션에 이벤트 저장
    add_doc(f"sessions/{sid}/events", {
        "uid": request.user["uid"],
        **ev
    })
    return jsonify({"inserted": 1})


@bp.post("/batch")
@require_auth
def batch_events():
    """
    여러 이벤트를 한 번에 저장(오프라인 기록을 나중에 업로드하는 시나리오).
    Body 예시:
      {
        "sessionId": "abc123",
        "events": [
          {"type":"MENU_ADD","ts":1730871000,"meta":{"duration":1.2,"success":true}},
          {"type":"PAYMENT","ts":1730871020,"meta":{"method":"CARD","duration":4.6,"success":false,"error":"PIN_TIMEOUT"}}
        ],
        "idempotencyKey": "optional-uuid-string"   // (선택) 멱등성 키
      }
    """
    payload = request.get_json() or {}
    sid = payload.get("sessionId")
    events = payload.get("events", [])
    # idempotencyKey 수신은 하지만, 간단 구현이라 실제 중복방지는 미구현(TODO)
    _idempotency = payload.get("idempotencyKey")

    if not sid:
        return jsonify({"error": "sessionId required"}), 400
    if not isinstance(events, list) or not events:
        return jsonify({"error": "events array required"}), 400

    # 각 이벤트 유효성 검사 → 유효한 것만 저장
    valid = []
    errors = []
    for idx, ev in enumerate(events):
        ok, msg = _validate_event(ev)
        if ok:
            valid.append(ev)
        else:
            errors.append({"index": idx, "reason": msg})

    # 일괄 저장(단순 루프 → Firestore batch 쓰기도 가능)
    for ev in valid:
        add_doc(f"sessions/{sid}/events", {
            "uid": request.user["uid"],
            **ev
        })

    return jsonify({
        "inserted": len(valid),
        "skipped": len(errors),
        "errors": errors
    })
