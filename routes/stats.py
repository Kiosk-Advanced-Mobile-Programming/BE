# routes/stats.py
# -------------------------------------------------------------
# 통계/집계 조회 API
#
# 제공 엔드포인트
#   - GET /v1/stats/summary?windowDays=7
#       : 로그인 사용자 기준, 최근 N일 이벤트를 스캔하여
#         성공률(successRate)과 평균 반응시간(avgReactionTime)을 계산
#   - GET /v1/stats/session/<sessionId>
#       : 특정 세션의 성공률/평균 반응시간 등 요약
#
# 주의:
# - 본 구현은 이해를 위한 "직접 스캔 방식"이라 데이터가 많아지면 느려질 수 있음.
# - 운영 단계에서는 다음 중 하나로 전환 권장:
#     1) Cloud Functions/Cloud Run으로 이벤트 발생 시 집계 문서 업데이트(준실시간)
#     2) 스케줄러가 일 단위로 집계하여 캐시 컬렉션(stats_daily 등)에 저장
# -------------------------------------------------------------

from flask import Blueprint, jsonify, request
from firebase_admin import firestore
from auth import require_auth

bp = Blueprint("stats", __name__, url_prefix="/v1/stats")

def _calc_metrics(events: list[dict]) -> dict:
    """
    이벤트 리스트로부터 간단 지표 계산:
      - successRate: success=true 비율 (meta.success)
      - avgReactionTime: meta.duration 평균(초)
    """
    if not events:
        return {"successRate": 0.0, "avgReactionTime": 0.0, "count": 0}

    # 성공/실패 집계
    succ_cnt = 0
    dur_sum = 0.0
    dur_cnt = 0

    for ev in events:
        meta = ev.get("meta") or {}
        # 성공여부(없으면 미집계)
        if isinstance(meta.get("success"), bool):
            succ_cnt += 1 if meta["success"] else 0
        # 반응시간(숫자면 평균 대상)
        dur = meta.get("duration")
        if isinstance(dur, (int, float)):
            dur_sum += float(dur)
            dur_cnt += 1

    total_for_succ = sum(1 for ev in events if isinstance((ev.get("meta") or {}).get("success"), bool))
    success_rate = (succ_cnt / total_for_succ) if total_for_succ else 0.0
    avg_rt = (dur_sum / dur_cnt) if dur_cnt else 0.0

    return {
        "successRate": round(success_rate, 4),
        "avgReactionTime": round(avg_rt, 4),
        "count": len(events)
    }


@bp.get("/summary")
@require_auth
def summary():
    """
    사용자 단위 기간 통계.
    Query:
      - windowDays (optional, int, default=7)
    계산 대상:
      - 로그인 사용자의 최근 windowDays 동안 생성된 모든 세션 하위 이벤트
    """
    try:
        window_days = int(request.args.get("windowDays", 7))
    except ValueError:
        return jsonify({"error": "windowDays must be an integer"}), 400

    uid = request.user["uid"]
    db = firestore.client()

    # 기간 기준 타임스탬프(초 단위 → Firestore Timestamp로 변환)
    # 여기서는 이벤트의 ts(Unix epoch 초)를 사용하므로, 쿼리 후 파이썬에서 필터링
    from datetime import datetime, timedelta, timezone
    since_epoch = int((datetime.now(timezone.utc) - timedelta(days=window_days)).timestamp())

    # 1) 현재 사용자 세션 목록 가져오기(최근 생성 순 정렬)
    session_snaps = db.collection("sessions").where("uid", "==", uid).order_by("startedAt", direction=firestore.Query.DESCENDING).stream()

    # 2) 각 세션의 events 서브컬렉션을 긁어서 기간 내 이벤트만 추출
    all_events: list[dict] = []
    for s in session_snaps:
        sid = s.id
        ev_snaps = db.collection(f"sessions/{sid}/events").stream()
        for ev in ev_snaps:
            data = ev.to_dict() or {}
            # ts가 since_epoch 이후인 것만 집계
            if int(data.get("ts", 0)) >= since_epoch:
                all_events.append(data)

    metrics = _calc_metrics(all_events)

    # (선택) 간단 추천/힌트(예시 데이터, 실제는 AI/규칙 기반으로 대체)
    hints = []
    if metrics["avgReactionTime"] > 3:
        hints.append("평균 반응시간이 길어요. 안내 속도를 느리게 하거나 단계 구분을 더 명확히 해보세요.")
    if metrics["successRate"] < 0.7:
        hints.append("성공률이 낮아요. 결제 단계 재연습 시나리오를 추천합니다.")

    return jsonify({
        "windowDays": window_days,
        "eventsCount": metrics["count"],
        "successRate": metrics["successRate"],
        "avgReactionTime": metrics["avgReactionTime"],
        "recommendations": hints
    })


@bp.get("/session/<session_id>")
@require_auth
def session_stats(session_id: str):
    """
    특정 세션의 간단 통계.
    Path:
      - session_id : 세션 문서 ID
    """
    db = firestore.client()

    # 세션 존재/권한 확인(본인 소유 세션만 조회)
    s_ref = db.collection("sessions").document(session_id)
    s_doc = s_ref.get()
    if not s_doc.exists:
        return jsonify({"error": "session not found"}), 404
    s_data = s_doc.to_dict() or {}
    if s_data.get("uid") != request.user["uid"]:
        return jsonify({"error": "forbidden"}), 403

    # 세션 하위 이벤트 모두 로드 후 지표 계산
    ev_snaps = db.collection(f"sessions/{session_id}/events").stream()
    events = [e.to_dict() or {} for e in ev_snaps]
    metrics = _calc_metrics(events)

    return jsonify({
        "sessionId": session_id,
        "status": s_data.get("status"),
        "category": s_data.get("category"),
        "startedAt": str(s_data.get("startedAt")),   # 클라이언트 표현 편의상 문자열화
        "finishedAt": str(s_data.get("finishedAt")),
        "eventsCount": metrics["count"],
        "successRate": metrics["successRate"],
        "avgReactionTime": metrics["avgReactionTime"]
    })
