"""
F1: 기록 저장/조회 Lambda
- POST /records       → 텍스트 기록 저장
- GET  /records       → 내 기록 목록 조회
- GET  /records/{id}  → 기록 상세 조회
- PATCH /records/{id}/followup → 이어 생각 추가 (F3)
- DELETE /records/{id} → 기록 삭제
"""
import os
import uuid
import logging
import boto3
from boto3.dynamodb.conditions import Key

# 공통 유틸 (Lambda Layer 또는 직접 임포트)
import sys
sys.path.insert(0, "/opt/python")  # Lambda Layer 경로
try:
    from utils import success, error, parse_body, get_user_id, get_path_param, get_query_param, now_iso
except ImportError:
    # 로컬 개발용 fallback
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "layers", "common"))
    from utils import success, error, parse_body, get_user_id, get_path_param, get_query_param, now_iso

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
RECORDS_TABLE = os.environ["RECORDS_TABLE"]


def lambda_handler(event: dict, context) -> dict:
    """단일 Lambda로 HTTP 메서드와 경로를 분기합니다."""
    method = event.get("httpMethod", "")
    path = event.get("path", "")
    resource = event.get("resource", "")

    logger.info(f"[record_api] {method} {path}")

    user_id = get_user_id(event)
    if not user_id:
        return error("인증이 필요합니다.", 401)

    # 라우팅
    if method == "POST" and resource == "/records":
        return create_record(event, user_id)

    if method == "GET" and resource == "/records":
        return list_records(event, user_id)

    if method == "GET" and resource == "/records/{id}":
        return get_record(event, user_id)

    if method == "PATCH" and resource == "/records/{id}/followup":
        return add_followup(event, user_id)

    if method == "DELETE" and resource == "/records/{id}":
        return delete_record(event, user_id)

    return error("존재하지 않는 경로입니다.", 404)


# ─────────────────────────────────────────
# POST /records — 텍스트 기록 저장
# ─────────────────────────────────────────
def create_record(event: dict, user_id: str) -> dict:
    body = parse_body(event)
    raw_text = body.get("rawText", "").strip()

    if not raw_text:
        return error("rawText는 필수입니다.")

    record_id = str(uuid.uuid4())
    created_at = now_iso()

    item = {
        "userId": user_id,
        "recordId": record_id,
        "rawText": raw_text,
        "summaryLine": "",   # F2 Bedrock 처리 후 채워짐
        "tags": [],          # F2 Bedrock 처리 후 채워짐
        "followups": [],     # F3 이어 생각 목록
        "audioS3Key": "",    # F1 음성 업로드 후 채워짐
        "isProcessed": False,  # Bedrock 처리 여부
        "createdAt": created_at,
        "updatedAt": created_at,
    }

    table = dynamodb.Table(RECORDS_TABLE)
    table.put_item(Item=item)

    logger.info(f"[record_api] 기록 생성: userId={user_id}, recordId={record_id}")
    return success({"record": item}, 201)


# ─────────────────────────────────────────
# GET /records — 내 기록 목록 조회
# ─────────────────────────────────────────
def list_records(event: dict, user_id: str) -> dict:
    limit = int(get_query_param(event, "limit", 20))
    last_key = get_query_param(event, "lastKey")  # 페이지네이션용

    table = dynamodb.Table(RECORDS_TABLE)

    query_kwargs = {
        "IndexName": "userId-createdAt-index",
        "KeyConditionExpression": Key("userId").eq(user_id),
        "ScanIndexForward": False,  # 최신순 정렬
        "Limit": limit,
    }
    if last_key:
        import json
        query_kwargs["ExclusiveStartKey"] = json.loads(last_key)

    response = table.query(**query_kwargs)
    items = response.get("Items", [])
    next_key = response.get("LastEvaluatedKey")

    return success({
        "records": items,
        "nextKey": next_key,
        "count": len(items),
    })


# ─────────────────────────────────────────
# GET /records/{id} — 기록 상세 조회
# ─────────────────────────────────────────
def get_record(event: dict, user_id: str) -> dict:
    record_id = get_path_param(event, "id")
    if not record_id:
        return error("recordId가 필요합니다.")

    table = dynamodb.Table(RECORDS_TABLE)
    response = table.get_item(Key={"userId": user_id, "recordId": record_id})
    item = response.get("Item")

    if not item:
        return error("기록을 찾을 수 없습니다.", 404)

    # 다른 사용자의 기록 접근 방지
    if item["userId"] != user_id:
        return error("접근 권한이 없습니다.", 403)

    return success({"record": item})


# ─────────────────────────────────────────
# PATCH /records/{id}/followup — 이어 생각 추가 (F3)
# ─────────────────────────────────────────
def add_followup(event: dict, user_id: str) -> dict:
    record_id = get_path_param(event, "id")
    body = parse_body(event)
    followup_text = body.get("text", "").strip()

    if not record_id or not followup_text:
        return error("recordId와 text가 필요합니다.")

    table = dynamodb.Table(RECORDS_TABLE)

    # 먼저 해당 기록이 존재하고 본인 것인지 확인
    response = table.get_item(Key={"userId": user_id, "recordId": record_id})
    item = response.get("Item")

    if not item:
        return error("기록을 찾을 수 없습니다.", 404)

    followup_entry = {
        "text": followup_text,
        "addedAt": now_iso(),
    }

    table.update_item(
        Key={"userId": user_id, "recordId": record_id},
        UpdateExpression="SET followups = list_append(if_not_exists(followups, :empty), :new_followup), updatedAt = :now",
        ExpressionAttributeValues={
            ":new_followup": [followup_entry],
            ":empty": [],
            ":now": now_iso(),
        },
    )

    logger.info(f"[record_api] 이어 생각 추가: userId={user_id}, recordId={record_id}")
    return success({"message": "이어 생각이 추가되었습니다.", "followup": followup_entry})


# ─────────────────────────────────────────
# DELETE /records/{id} — 기록 삭제
# ─────────────────────────────────────────
def delete_record(event: dict, user_id: str) -> dict:
    record_id = get_path_param(event, "id")
    if not record_id:
        return error("recordId가 필요합니다.")

    table = dynamodb.Table(RECORDS_TABLE)
    response = table.get_item(Key={"userId": user_id, "recordId": record_id})
    item = response.get("Item")

    if not item:
        return error("기록을 찾을 수 없습니다.", 404)

    table.delete_item(Key={"userId": user_id, "recordId": record_id})
    logger.info(f"[record_api] 기록 삭제: userId={user_id}, recordId={record_id}")
    return success({"message": "삭제되었습니다."})
