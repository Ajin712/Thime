"""
공통 유틸리티 — 모든 Lambda 함수에서 공유
"""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ─────────────────────────────────────────
# HTTP 응답 헬퍼
# ─────────────────────────────────────────

def success(body: dict | list, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def error(message: str, status_code: int = 400) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"error": message}, ensure_ascii=False),
    }


# ─────────────────────────────────────────
# 이벤트 파싱 헬퍼
# ─────────────────────────────────────────

def parse_body(event: dict) -> dict:
    """API Gateway 이벤트에서 body를 파싱합니다."""
    body = event.get("body", "{}")
    if isinstance(body, str):
        return json.loads(body) if body else {}
    return body or {}


def get_user_id(event: dict) -> str | None:
    """Cognito JWT에서 userId(sub)를 추출합니다."""
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )
    return claims.get("sub")


def get_path_param(event: dict, name: str) -> str | None:
    return (event.get("pathParameters") or {}).get(name)


def get_query_param(event: dict, name: str, default=None):
    return (event.get("queryStringParameters") or {}).get(name, default)


# ─────────────────────────────────────────
# 시간 헬퍼
# ─────────────────────────────────────────

def now_iso() -> str:
    """현재 UTC 시간을 ISO 8601 문자열로 반환합니다."""
    return datetime.now(timezone.utc).isoformat()


def today_kst() -> str:
    """오늘 날짜를 KST 기준 YYYY-MM-DD 문자열로 반환합니다."""
    from datetime import timedelta
    kst_now = datetime.now(timezone.utc) + timedelta(hours=9)
    return kst_now.strftime("%Y-%m-%d")
