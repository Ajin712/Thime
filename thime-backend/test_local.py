"""
로컬 Lambda 테스트 스크립트
실제 AWS 없이 이벤트 구조를 확인할 때 사용합니다.
"""
import json
import sys
import os

# 공통 유틸 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lambda", "layers", "common"))


def make_api_event(
    method: str,
    path: str,
    resource: str,
    body: dict = None,
    path_params: dict = None,
    query_params: dict = None,
    user_id: str = "test-user-123",
) -> dict:
    """API Gateway 이벤트 형식을 만들어 줍니다."""
    return {
        "httpMethod": method,
        "path": path,
        "resource": resource,
        "body": json.dumps(body) if body else None,
        "pathParameters": path_params or {},
        "queryStringParameters": query_params or {},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                    "email": "test@example.com",
                }
            }
        },
        "headers": {"Content-Type": "application/json"},
    }


# ─────────────────────────────────────────
# 테스트 케이스들
# ─────────────────────────────────────────

def test_record_api_create():
    """F1: 텍스트 기록 저장 이벤트 구조 확인"""
    event = make_api_event(
        method="POST",
        path="/records",
        resource="/records",
        body={"rawText": "오늘 갑자기 왜 사람들은 남들 시선을 그렇게 신경 쓰는지 궁금해졌다. 나도 그런 것 같고..."},
    )
    print("=== POST /records 이벤트 ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_audio_upload_url():
    """F1: presigned URL 발급 이벤트 구조 확인"""
    event = make_api_event(
        method="POST",
        path="/records/audio-url",
        resource="/records/audio-url",
        body={"recordId": "abc-123", "fileExt": "webm"},
    )
    print("=== POST /records/audio-url 이벤트 ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_summarize():
    """F2: 요약·태그 추출 이벤트 구조 확인"""
    event = make_api_event(
        method="POST",
        path="/records/abc-123/summarize",
        resource="/records/{id}/summarize",
        path_params={"id": "abc-123"},
    )
    print("=== POST /records/{id}/summarize 이벤트 ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_feed_submit():
    """F5: 내 답 공유 이벤트 구조 확인"""
    event = make_api_event(
        method="POST",
        path="/feeds/question-456",
        resource="/feeds/{questionId}",
        path_params={"questionId": "question-456"},
        body={
            "answerText": "나는 타인의 시선보다 내가 나를 어떻게 보는지가 더 중요한 것 같다.",
            "isPublic": True,
            "isAnonymous": True,
        },
    )
    print("=== POST /feeds/{questionId} 이벤트 ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_feed_get_locked():
    """F5: 내 답 없을 때 잠긴 상태 확인"""
    event = make_api_event(
        method="GET",
        path="/feeds/question-456",
        resource="/feeds/{questionId}",
        path_params={"questionId": "question-456"},
    )
    print("=== GET /feeds/{questionId} (내 답 없음) 이벤트 ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_post_comment():
    """버블: 남의 답변에 댓글 달기"""
    event = make_api_event(
        method="POST",
        path="/feeds/question-456/user-answerer-789/comments",
        resource="/feeds/{questionId}/{answererUserId}/comments",
        path_params={
            "questionId": "question-456",
            "answererUserId": "user-answerer-789",
        },
        body={"commentText": "저도 비슷하게 느꼈어요. 좀 더 여쭤봐도 될까요?"},
        user_id="test-commenter-111",
    )
    print("=== POST /feeds/{questionId}/{answererUserId}/comments ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_get_comments_as_answerer():
    """버블: 답변자가 내 답변에 달린 댓글 조회"""
    event = make_api_event(
        method="GET",
        path="/feeds/question-456/user-answerer-789/comments",
        resource="/feeds/{questionId}/{answererUserId}/comments",
        path_params={
            "questionId": "question-456",
            "answererUserId": "user-answerer-789",
        },
        user_id="user-answerer-789",  # 답변자 본인
    )
    print("=== GET /feeds/{questionId}/{answererUserId}/comments (답변자) ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


def test_post_reply():
    """버블: 답변자가 댓글에 선택적 답장"""
    event = make_api_event(
        method="POST",
        path="/feeds/question-456/user-answerer-789/comments/2026-11-08T00:00:00+00:00#test-commenter-111/reply",
        resource="/feeds/{questionId}/{answererUserId}/comments/{commentId}/reply",
        path_params={
            "questionId": "question-456",
            "answererUserId": "user-answerer-789",
            "commentId": "2026-11-08T00:00:00+00:00#test-commenter-111",
        },
        body={"replyText": "네, 저도 그게 궁금한데 아직 답을 못 찾겠더라고요 😅"},
        user_id="user-answerer-789",  # 답변자만 가능
    )
    print("=== POST .../reply (답변자 답장) ===")
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return event


if __name__ == "__main__":
    print("Thime Lambda 로컬 테스트 — 이벤트 구조 확인\n")
    test_record_api_create()
    print()
    test_audio_upload_url()
    print()
    test_summarize()
    print()
    test_feed_submit()
    print()
    test_feed_get_locked()
    print()
    print("─── 버블 메커니즘 ───")
    test_post_comment()
    print()
    test_get_comments_as_answerer()
    print()
    test_post_reply()
    print("\n✅ 이벤트 구조 확인 완료. 실제 Lambda는 AWS에서 실행됩니다.")
