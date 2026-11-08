"""
F3·F4: 알림 Lambda
- GET /questions/today        → 오늘의 질문 조회
- EventBridge: daily-question → 매일 밤 10시 오늘의 질문 생성·저장
- EventBridge: morning-recall → 매일 아침 8시 어젯밤 기록 알림
"""
import os
import uuid
import json
import logging
import boto3
from datetime import datetime, timezone, timedelta

import sys
sys.path.insert(0, "/opt/python")
try:
    from utils import success, error, get_user_id, now_iso, today_kst
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "layers", "common"))
    from utils import success, error, get_user_id, now_iso, today_kst

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "ap-northeast-2"))
dynamodb = boto3.resource("dynamodb")

QUESTIONS_TABLE = os.environ["QUESTIONS_TABLE"]
RECORDS_TABLE = os.environ["RECORDS_TABLE"]
BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# 기본 질문 세트 (초기에 사용, 오닷 카드 스타일)
DEFAULT_QUESTIONS = [
    "오늘 하루 중 가장 오래 생각한 것은 무엇인가요?",
    "지금 가장 해결하고 싶은 고민이 있다면?",
    "오늘 누군가에게 고맙다고 느낀 순간이 있었나요?",
    "최근 내 행동 중 후회되는 것이 있다면?",
    "10년 뒤 나는 어떤 사람이 되어 있을까요?",
    "지금 두려운 것이 있다면 무엇인가요?",
    "오늘 배운 것 중 가장 인상 깊은 것은?",
    "내가 자주 미루는 일이 있다면 왜 그럴까요?",
    "지금 가장 그립거나 보고 싶은 것은?",
    "나는 어떤 상황에서 가장 나답다고 느끼나요?",
]


def lambda_handler(event: dict, context) -> dict:
    # EventBridge 스케줄 이벤트
    if event.get("source") in ["daily-question", "morning-recall"]:
        return handle_scheduled_event(event)

    # API Gateway 요청
    if "httpMethod" in event:
        return handle_api_request(event)

    logger.warning(f"[notification] 알 수 없는 이벤트: {json.dumps(event)[:200]}")
    return {"statusCode": 200}


# ─────────────────────────────────────────
# GET /questions/today — 오늘의 질문 조회
# ─────────────────────────────────────────
def handle_api_request(event: dict) -> dict:
    user_id = get_user_id(event)
    if not user_id:
        return error("인증이 필요합니다.", 401)

    today = today_kst()
    table = dynamodb.Table(QUESTIONS_TABLE)

    # 오늘 날짜로 질문 조회
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("date").eq(today),
        Limit=1,
        ScanIndexForward=False,
    )
    items = response.get("Items", [])

    if items:
        return success({"question": items[0]})

    # 오늘 질문이 없으면 기본 질문에서 랜덤 반환
    import random
    question_text = random.choice(DEFAULT_QUESTIONS)
    question = {
        "date": today,
        "questionId": str(uuid.uuid4()),
        "content": question_text,
        "isDefault": True,
        "createdAt": now_iso(),
    }
    return success({"question": question})


# ─────────────────────────────────────────
# EventBridge 스케줄 처리
# ─────────────────────────────────────────
def handle_scheduled_event(event: dict) -> dict:
    source = event.get("source")

    if source == "daily-question":
        return generate_daily_question()

    if source == "morning-recall":
        return send_morning_recall()

    return {"statusCode": 200}


def generate_daily_question() -> dict:
    """
    F4: 매일 밤 10시 — 오늘의 질문 생성 후 DynamoDB 저장
    Bedrock으로 다양한 주제의 질문 생성
    """
    today = today_kst()
    table = dynamodb.Table(QUESTIONS_TABLE)

    # 이미 오늘 질문이 있으면 스킵
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("date").eq(today),
        Limit=1,
    )
    if response.get("Items"):
        logger.info(f"[notification] 오늘({today}) 질문 이미 존재, 스킵")
        return {"statusCode": 200}

    # Bedrock으로 오늘의 질문 생성
    question_text = generate_question_with_bedrock()

    question = {
        "date": today,
        "questionId": str(uuid.uuid4()),
        "content": question_text,
        "isDefault": False,
        "createdAt": now_iso(),
    }

    table.put_item(Item=question)
    logger.info(f"[notification] 오늘의 질문 생성: {question_text}")

    # TODO: SNS 푸시 알림 추가 (프론트엔드 연동 후)
    return {"statusCode": 200}


def generate_question_with_bedrock() -> str:
    """Claude에게 오늘의 질문을 요청합니다."""
    import random

    topics = [
        "관계와 소통", "미래와 진로", "가치관과 신념", "일상과 루틴",
        "두려움과 용기", "배움과 성장", "감사와 행복", "변화와 선택",
    ]
    topic = random.choice(topics)

    prompt = f"""당신은 사람들이 자신의 생각을 깊게 탐색하도록 돕는 질문 출제자입니다.
주제: {topic}

조건:
- 답이 명확하지 않고 스스로 생각해 볼 수 있는 질문
- 너무 어렵거나 추상적이지 않게
- 30자 이내의 짧은 질문 하나만
- 질문 외에 아무것도 출력하지 마세요

질문:"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
    }

    try:
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        question_text = result["content"][0]["text"].strip()
        # 따옴표 제거
        return question_text.strip('"').strip("'")
    except Exception as e:
        logger.error(f"[notification] Bedrock 질문 생성 실패: {e}")
        import random
        return random.choice(DEFAULT_QUESTIONS)


def send_morning_recall() -> dict:
    """
    F3: 매일 아침 8시 — 전날 밤 기록을 꺼내 알림
    TODO: SNS 푸시 알림 연동 (현재는 로깅만)
    """
    logger.info("[notification] 아침 알림 트리거 — 어젯밤 기록 알림 발송 (TODO: SNS 연동)")
    # 실제 구현: 모든 유저를 순회하며 어젯밤 기록이 있는 경우 SNS 발송
    # 해커톤 데모에서는 프론트엔드 폴링 방식으로 대체 가능
    return {"statusCode": 200}
