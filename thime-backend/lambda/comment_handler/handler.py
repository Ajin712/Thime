"""
버블(Bubble) 메커니즘 — 댓글 & 선택적 답장 Lambda

데이터 구조:
  comments 테이블
  PK: feedId (= "{questionId}#{answererUserId}")  ← 어느 답변에 달린 댓글인지
  SK: commentId (= "{timestamp}#{commenterUserId}")

  각 아이템:
    feedId          : "{questionId}#{answererUserId}"
    commentId       : "{createdAt}#{commenterUserId}"
    commenterUserId : 댓글 작성자
    commentText     : 댓글 내용
    replyText       : 답변자의 답장 (없으면 None)
    repliedAt       : 답장 시각
    createdAt       : 댓글 작성 시각

접근 규칙:
  댓글 작성  → 누구나 (단, 내 답 먼저 있어야 — 기존 F5 규칙 유지)
  댓글 조회  → 답변자(answerer)만 전체 목록 볼 수 있음
  댓글 확인  → 댓글 작성자는 자기 댓글 + 답장 여부만 볼 수 있음
  답장 작성  → 답변자만 가능, 댓글 1개당 1번만

API:
  POST /feeds/{questionId}/{answererUserId}/comments
    → 해당 답변에 댓글 달기

  GET  /feeds/{questionId}/{answererUserId}/comments
    → 답변자: 내 답변에 달린 전체 댓글 목록
    → 댓글 작성자: 내가 남긴 댓글 + 답장 여부

  POST /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
    → 답변자만: 특정 댓글에 답장

  GET  /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
    → 댓글 작성자: 내 댓글에 온 답장 확인
"""
import os
import uuid
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr

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
COMMENTS_TABLE = os.environ["COMMENTS_TABLE"]
FEEDS_TABLE = os.environ["FEEDS_TABLE"]


def lambda_handler(event: dict, context) -> dict:
    method = event.get("httpMethod", "")
    resource = event.get("resource", "")

    user_id = get_user_id(event)
    if not user_id:
        return error("인증이 필요합니다.", 401)

    logger.info(f"[comment] {method} {resource}, userId={user_id}")

    # POST /feeds/{questionId}/{answererUserId}/comments
    if method == "POST" and resource == "/feeds/{questionId}/{answererUserId}/comments":
        return post_comment(event, user_id)

    # GET /feeds/{questionId}/{answererUserId}/comments
    if method == "GET" and resource == "/feeds/{questionId}/{answererUserId}/comments":
        return get_comments(event, user_id)

    # POST /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
    if method == "POST" and resource == "/feeds/{questionId}/{answererUserId}/comments/{commentId}/reply":
        return post_reply(event, user_id)

    # GET /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
    if method == "GET" and resource == "/feeds/{questionId}/{answererUserId}/comments/{commentId}/reply":
        return get_reply(event, user_id)

    return error("존재하지 않는 경로입니다.", 404)


def _make_feed_id(question_id: str, answerer_user_id: str) -> str:
    """feedId = "{questionId}#{answererUserId}" 형식으로 생성합니다."""
    return f"{question_id}#{answerer_user_id}"


def _get_feed(question_id: str, answerer_user_id: str) -> dict | None:
    """feeds 테이블에서 해당 답변이 실제로 존재하고 공개 상태인지 확인합니다."""
    feeds_table = dynamodb.Table(FEEDS_TABLE)
    response = feeds_table.get_item(
        Key={"questionId": question_id, "userId": answerer_user_id}
    )
    return response.get("Item")


# ─────────────────────────────────────────
# POST /feeds/{questionId}/{answererUserId}/comments
# 해당 답변에 댓글 달기
# ─────────────────────────────────────────
def post_comment(event: dict, user_id: str) -> dict:
    question_id = get_path_param(event, "questionId")
    answerer_user_id = get_path_param(event, "answererUserId")
    body = parse_body(event)
    comment_text = body.get("commentText", "").strip()

    if not question_id or not answerer_user_id or not comment_text:
        return error("questionId, answererUserId, commentText가 필요합니다.")

    # 자기 자신의 답변에는 댓글 불가
    if user_id == answerer_user_id:
        return error("자신의 답변에는 댓글을 달 수 없습니다.")

    # 해당 답변이 존재하고 공개 상태인지 확인
    feed = _get_feed(question_id, answerer_user_id)
    if not feed:
        return error("존재하지 않는 답변입니다.", 404)
    if not feed.get("isPublic", False):
        return error("비공개 답변에는 댓글을 달 수 없습니다.", 403)

    # 댓글 작성자도 이 질문에 답변한 사람이어야 함 (F5 원칙 유지)
    my_feed = _get_feed(question_id, user_id)
    if not my_feed:
        return error("이 질문에 먼저 내 생각을 남겨야 댓글을 달 수 있어요.", 403)

    feed_id = _make_feed_id(question_id, answerer_user_id)
    created_at = now_iso()
    comment_id = f"{created_at}#{user_id}"  # 시간순 정렬 + 작성자 식별

    item = {
        "feedId": feed_id,
        "commentId": comment_id,
        "commenterUserId": user_id,
        "commentText": comment_text,
        "replyText": None,       # 답변자가 답장하기 전까지 None
        "repliedAt": None,
        "isRead": False,         # 답변자가 확인 전
        "createdAt": created_at,
    }

    comments_table = dynamodb.Table(COMMENTS_TABLE)
    comments_table.put_item(Item=item)

    logger.info(f"[comment] 댓글 작성: feedId={feed_id}, commenter={user_id}")
    return success({
        "message": "댓글이 등록되었습니다. 답변자가 선택적으로 답장할 수 있어요.",
        "commentId": comment_id,
    }, 201)


# ─────────────────────────────────────────
# GET /feeds/{questionId}/{answererUserId}/comments
# 답변자 → 내 답변에 달린 전체 댓글
# 댓글 작성자 → 내가 남긴 댓글 + 답장 여부
# ─────────────────────────────────────────
def get_comments(event: dict, user_id: str) -> dict:
    question_id = get_path_param(event, "questionId")
    answerer_user_id = get_path_param(event, "answererUserId")

    if not question_id or not answerer_user_id:
        return error("questionId, answererUserId가 필요합니다.")

    feed_id = _make_feed_id(question_id, answerer_user_id)
    comments_table = dynamodb.Table(COMMENTS_TABLE)

    is_answerer = (user_id == answerer_user_id)

    response = comments_table.query(
        KeyConditionExpression=Key("feedId").eq(feed_id),
        ScanIndexForward=True,  # 오래된 순서 (댓글 흐름)
    )
    all_comments = response.get("Items", [])

    if is_answerer:
        # 답변자: 전체 댓글 목록 + 안 읽은 댓글 수
        # 읽음 처리
        unread_ids = [c["commentId"] for c in all_comments if not c.get("isRead", False)]
        for comment_id in unread_ids:
            comments_table.update_item(
                Key={"feedId": feed_id, "commentId": comment_id},
                UpdateExpression="SET isRead = :t",
                ExpressionAttributeValues={":t": True},
            )

        result = []
        for c in all_comments:
            result.append({
                "commentId": c["commentId"],
                "commenterUserId": c["commenterUserId"],  # 답변자에게는 작성자 ID 공개
                "commentText": c["commentText"],
                "replyText": c.get("replyText"),
                "hasReplied": c.get("replyText") is not None,
                "repliedAt": c.get("repliedAt"),
                "createdAt": c["createdAt"],
                "isRead": True,
            })

        logger.info(f"[comment] 답변자 댓글 조회: feedId={feed_id}, count={len(result)}")
        return success({
            "role": "answerer",
            "comments": result,
            "unreadCount": len(unread_ids),
            "totalCount": len(result),
        })

    else:
        # 댓글 작성자: 내가 남긴 댓글 + 답장 여부만
        my_comments = [c for c in all_comments if c["commenterUserId"] == user_id]

        result = []
        for c in my_comments:
            has_reply = c.get("replyText") is not None
            result.append({
                "commentId": c["commentId"],
                "commentText": c["commentText"],
                "hasReply": has_reply,
                # 답장이 있을 때만 내용 공개
                "replyText": c.get("replyText") if has_reply else None,
                "repliedAt": c.get("repliedAt") if has_reply else None,
                "createdAt": c["createdAt"],
            })

        logger.info(f"[comment] 댓글 작성자 조회: feedId={feed_id}, commenter={user_id}, count={len(result)}")
        return success({
            "role": "commenter",
            "comments": result,
            "totalCount": len(result),
        })


# ─────────────────────────────────────────
# POST /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
# 답변자만: 특정 댓글에 답장 (1:1, 비공개)
# ─────────────────────────────────────────
def post_reply(event: dict, user_id: str) -> dict:
    question_id = get_path_param(event, "questionId")
    answerer_user_id = get_path_param(event, "answererUserId")
    comment_id = get_path_param(event, "commentId")
    body = parse_body(event)
    reply_text = body.get("replyText", "").strip()

    if not question_id or not answerer_user_id or not comment_id or not reply_text:
        return error("questionId, answererUserId, commentId, replyText가 필요합니다.")

    # 답변자 본인만 답장 가능
    if user_id != answerer_user_id:
        return error("답장은 해당 답변을 작성한 사람만 할 수 있습니다.", 403)

    feed_id = _make_feed_id(question_id, answerer_user_id)
    comments_table = dynamodb.Table(COMMENTS_TABLE)

    # 댓글 존재 여부 확인
    response = comments_table.get_item(Key={"feedId": feed_id, "commentId": comment_id})
    comment = response.get("Item")

    if not comment:
        return error("존재하지 않는 댓글입니다.", 404)

    # 이미 답장한 경우 — 수정 허용 (버블처럼 답장 수정 가능)
    replied_at = now_iso()
    comments_table.update_item(
        Key={"feedId": feed_id, "commentId": comment_id},
        UpdateExpression="SET replyText = :reply, repliedAt = :at",
        ExpressionAttributeValues={
            ":reply": reply_text,
            ":at": replied_at,
        },
    )

    is_update = comment.get("replyText") is not None
    logger.info(f"[comment] 답장 {'수정' if is_update else '작성'}: feedId={feed_id}, commentId={comment_id}")

    return success({
        "message": "답장이 전송되었습니다." if not is_update else "답장이 수정되었습니다.",
        "commentId": comment_id,
        "repliedAt": replied_at,
        "isUpdated": is_update,
    })


# ─────────────────────────────────────────
# GET /feeds/{questionId}/{answererUserId}/comments/{commentId}/reply
# 댓글 작성자: 내 댓글에 온 답장 확인
# ─────────────────────────────────────────
def get_reply(event: dict, user_id: str) -> dict:
    question_id = get_path_param(event, "questionId")
    answerer_user_id = get_path_param(event, "answererUserId")
    comment_id = get_path_param(event, "commentId")

    if not question_id or not answerer_user_id or not comment_id:
        return error("questionId, answererUserId, commentId가 필요합니다.")

    feed_id = _make_feed_id(question_id, answerer_user_id)
    comments_table = dynamodb.Table(COMMENTS_TABLE)

    response = comments_table.get_item(Key={"feedId": feed_id, "commentId": comment_id})
    comment = response.get("Item")

    if not comment:
        return error("존재하지 않는 댓글입니다.", 404)

    # 댓글 작성자 본인 또는 답변자만 조회 가능
    if user_id != comment["commenterUserId"] and user_id != answerer_user_id:
        return error("접근 권한이 없습니다.", 403)

    has_reply = comment.get("replyText") is not None

    return success({
        "commentId": comment_id,
        "commentText": comment["commentText"],
        "hasReply": has_reply,
        "replyText": comment.get("replyText") if has_reply else None,
        "repliedAt": comment.get("repliedAt") if has_reply else None,
        "createdAt": comment["createdAt"],
    })
