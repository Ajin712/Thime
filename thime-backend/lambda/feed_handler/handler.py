"""
F5: 다른 생각 보기 Lambda
- GET  /feeds/{questionId} → 같은 질문에 대한 다른 사람들의 답 조회
                             (단, 내 답이 먼저 있어야 열림)
- POST /feeds/{questionId} → 내 답 공유 (공개/비공개 선택)
"""
import os
import json
import logging
import boto3
from boto3.dynamodb.conditions import Key

import sys
sys.path.insert(0, "/opt/python")
try:
    from utils import success, error, parse_body, get_user_id, get_path_param, now_iso
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "layers", "common"))
    from utils import success, error, parse_body, get_user_id, get_path_param, now_iso

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
FEEDS_TABLE = os.environ["FEEDS_TABLE"]


def lambda_handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "")
    user_id = get_user_id(event)
    if not user_id:
        return error("인증이 필요합니다.", 401)

    if method == "POST":
        return submit_answer(event, user_id)
    if method == "GET":
        return get_feeds(event, user_id)

    return error("허용되지 않는 메서드입니다.", 405)


# ─────────────────────────────────────────
# POST /feeds/{questionId} — 내 답 공유
# ─────────────────────────────────────────
def submit_answer(event: dict, user_id: str) -> dict:
    question_id = get_path_param(event, "questionId")
    body = parse_body(event)

    answer_text = body.get("answerText", "").strip()
    is_public = body.get("isPublic", True)   # 기본값: 공개
    is_anonymous = body.get("isAnonymous", True)  # 기본값: 익명

    if not question_id or not answer_text:
        return error("questionId와 answerText가 필요합니다.")

    table = dynamodb.Table(FEEDS_TABLE)

    # 이미 답한 경우 업데이트
    existing = table.get_item(Key={"questionId": question_id, "userId": user_id})
    item = existing.get("Item")

    if item:
        # 기존 답 업데이트
        table.update_item(
            Key={"questionId": question_id, "userId": user_id},
            UpdateExpression="SET answerText = :text, isPublic = :pub, isAnonymous = :anon, updatedAt = :now",
            ExpressionAttributeValues={
                ":text": answer_text,
                ":pub": is_public,
                ":anon": is_anonymous,
                ":now": now_iso(),
            },
        )
        logger.info(f"[feed] 답 업데이트: userId={user_id}, questionId={question_id}")
        return success({"message": "답이 업데이트되었습니다.", "isUpdated": True})

    # 새 답 저장
    feed_item = {
        "questionId": question_id,
        "userId": user_id,
        "answerText": answer_text,
        "isPublic": is_public,
        "isAnonymous": is_anonymous,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    table.put_item(Item=feed_item)
    logger.info(f"[feed] 새 답 저장: userId={user_id}, questionId={question_id}")

    return success({"message": "답이 공유되었습니다. 이제 다른 사람들의 생각을 볼 수 있어요."}, 201)


# ─────────────────────────────────────────
# GET /feeds/{questionId} — 다른 사람들 답 조회
# F5 핵심 규칙: 내 답이 먼저 있어야 열림
# ─────────────────────────────────────────
def get_feeds(event: dict, user_id: str) -> dict:
    question_id = get_path_param(event, "questionId")
    if not question_id:
        return error("questionId가 필요합니다.")

    table = dynamodb.Table(FEEDS_TABLE)

    # 내 답이 있는지 먼저 확인 (F5 핵심 규칙)
    my_response = table.get_item(Key={"questionId": question_id, "userId": user_id})
    my_answer = my_response.get("Item")

    if not my_answer:
        # 내 답 없음 → 잠긴 상태 반환
        return success({
            "locked": True,
            "message": "내 생각을 먼저 남겨야 다른 사람들의 생각을 볼 수 있어요.",
            "feeds": [],
            "myAnswer": None,
        })

    # 내 답이 있으면 공개된 다른 사람들의 답 조회
    response = table.query(
        KeyConditionExpression=Key("questionId").eq(question_id),
        FilterExpression=boto3.dynamodb.conditions.Attr("isPublic").eq(True),
        Limit=50,
    )
    all_feeds = response.get("Items", [])

    # 다른 사람들의 답만 필터링 + 익명 처리
    other_feeds = []
    for feed in all_feeds:
        if feed["userId"] == user_id:
            continue  # 내 답은 제외

        feed_copy = {
            "questionId": feed["questionId"],
            "answerText": feed["answerText"],
            "createdAt": feed["createdAt"],
            # 익명 설정에 따라 userId 노출 여부 결정
            "userId": None if feed.get("isAnonymous", True) else feed["userId"],
            # 버블 메커니즘: 댓글 달기 위해 answererUserId 노출 (익명이어도 필요)
            # 단, 실제 userId 대신 내부 식별자를 프론트에서 사용
            "answererUserId": feed["userId"],
        }
        other_feeds.append(feed_copy)

    logger.info(f"[feed] 피드 조회: userId={user_id}, questionId={question_id}, count={len(other_feeds)}")

    return success({
        "locked": False,
        "feeds": other_feeds,
        "myAnswer": {
            "answerText": my_answer["answerText"],
            "createdAt": my_answer["createdAt"],
            "isPublic": my_answer.get("isPublic", True),
        },
        "count": len(other_feeds),
    })
