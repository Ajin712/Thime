"""
F2: 생각 정리 Lambda — Amazon Bedrock(Claude)으로 요약·태그 추출
- POST /records/{id}/summarize → 텍스트 요약 + 태그 3개 추출
"""
import os
import json
import logging
import boto3

import sys
sys.path.insert(0, "/opt/python")
try:
    from utils import success, error, parse_body, get_user_id, get_path_param, now_iso
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "layers", "common"))
    from utils import success, error, parse_body, get_user_id, get_path_param, now_iso

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "ap-northeast-2"))
dynamodb = boto3.resource("dynamodb")

RECORDS_TABLE = os.environ["RECORDS_TABLE"]

# Claude 3 Haiku — 빠르고 저렴, 해커톤에 적합
# 프로덕션에서는 Claude 3 Sonnet 고려
BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"


def lambda_handler(event: dict, context) -> dict:
    user_id = get_user_id(event)
    if not user_id:
        return error("인증이 필요합니다.", 401)

    record_id = get_path_param(event, "id")
    if not record_id:
        return error("recordId가 필요합니다.")

    # DynamoDB에서 원본 텍스트 조회
    table = dynamodb.Table(RECORDS_TABLE)
    response = table.get_item(Key={"userId": user_id, "recordId": record_id})
    item = response.get("Item")

    if not item:
        return error("기록을 찾을 수 없습니다.", 404)

    raw_text = item.get("rawText", "")
    if not raw_text:
        return error("처리할 텍스트가 없습니다.")

    # Bedrock 호출
    summary_line, tags = call_bedrock_summarize(raw_text)

    # DynamoDB 업데이트
    table.update_item(
        Key={"userId": user_id, "recordId": record_id},
        UpdateExpression="SET summaryLine = :summary, tags = :tags, isProcessed = :done, updatedAt = :now",
        ExpressionAttributeValues={
            ":summary": summary_line,
            ":tags": tags,
            ":done": True,
            ":now": now_iso(),
        },
    )

    logger.info(f"[bedrock] 요약 완료: userId={user_id}, recordId={record_id}")
    return success({
        "summaryLine": summary_line,
        "tags": tags,
        "recordId": record_id,
    })


def call_bedrock_summarize(raw_text: str) -> tuple[str, list[str]]:
    """
    Claude에게 요약 한 줄과 태그 3개를 요청합니다.
    AI 역할 원칙: 요약·분류만 한다. 결론·평가는 주지 않는다.
    """
    prompt = f"""당신은 사용자의 생각을 요약하고 분류하는 도우미입니다.
절대로 답이나 결론, 평가, 조언을 주지 마세요. 오직 요약과 분류만 하세요.

다음 내용에서:
1. 핵심 질문이나 생각을 한 줄(50자 이내)로 요약하세요.
2. 주제 태그를 최대 3개 추출하세요. (예: #일상, #관계, #진로)

응답은 반드시 아래 JSON 형식으로만 답하세요:
{{
  "summaryLine": "요약된 한 줄",
  "tags": ["#태그1", "#태그2", "#태그3"]
}}

사용자 내용:
{raw_text}"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 256,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # 일관성 있는 요약을 위해 낮게 설정
    }

    try:
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        content = result["content"][0]["text"]

        # JSON 파싱
        parsed = json.loads(content)
        summary_line = parsed.get("summaryLine", "")
        tags = parsed.get("tags", [])[:3]  # 최대 3개

        return summary_line, tags

    except json.JSONDecodeError:
        # JSON 파싱 실패 시 텍스트 앞 50자를 요약으로 사용
        logger.warning("[bedrock] JSON 파싱 실패, 기본 요약 사용")
        return raw_text[:50] + "..." if len(raw_text) > 50 else raw_text, []

    except Exception as e:
        logger.error(f"[bedrock] Bedrock 호출 실패: {e}")
        raise
