"""
F1: 음성 기록 Lambda
- POST /records/audio-url  → S3 presigned URL 발급
- S3 이벤트 트리거         → Amazon Transcribe 작업 시작 → 완료 시 기록 업데이트
"""
import os
import uuid
import json
import logging
import boto3

import sys
sys.path.insert(0, "/opt/python")
try:
    from utils import success, error, parse_body, get_user_id, now_iso
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "layers", "common"))
    from utils import success, error, parse_body, get_user_id, now_iso

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
transcribe = boto3.client("transcribe", region_name=os.environ.get("REGION", "ap-northeast-2"))
dynamodb = boto3.resource("dynamodb")

AUDIO_BUCKET = os.environ["AUDIO_BUCKET"]
RECORDS_TABLE = os.environ["RECORDS_TABLE"]
REGION = os.environ.get("REGION", "ap-northeast-2")


def lambda_handler(event: dict, context) -> dict:
    # API Gateway 요청인지 S3 이벤트인지 구분
    if "Records" in event and event["Records"][0].get("eventSource") == "aws:s3":
        return handle_s3_event(event)

    if "httpMethod" in event:
        return handle_api_request(event)

    logger.warning(f"[transcribe] 알 수 없는 이벤트 형식: {json.dumps(event)[:200]}")
    return error("알 수 없는 요청", 400)


# ─────────────────────────────────────────
# POST /records/audio-url — S3 presigned URL 발급
# ─────────────────────────────────────────
def handle_api_request(event: dict) -> dict:
    user_id = get_user_id(event)
    if not user_id:
        return error("인증이 필요합니다.", 401)

    body = parse_body(event)
    record_id = body.get("recordId")
    file_ext = body.get("fileExt", "webm").lower()  # webm, mp4, m4a

    if not record_id:
        return error("recordId가 필요합니다.")

    if file_ext not in ["webm", "mp4", "m4a", "wav"]:
        return error("지원하지 않는 파일 형식입니다. (webm, mp4, m4a, wav)")

    # S3 키 형식: audio/{userId}/{recordId}.{ext}
    s3_key = f"audio/{user_id}/{record_id}.{file_ext}"

    # Presigned URL 발급 (5분 유효)
    presigned_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": AUDIO_BUCKET,
            "Key": s3_key,
            "ContentType": f"audio/{file_ext}",
            # 메타데이터로 userId, recordId 저장 (S3 이벤트에서 활용)
            "Metadata": {
                "user-id": user_id,
                "record-id": record_id,
            },
        },
        ExpiresIn=300,
    )

    logger.info(f"[transcribe] presigned URL 발급: userId={user_id}, recordId={record_id}, key={s3_key}")
    return success({
        "uploadUrl": presigned_url,
        "s3Key": s3_key,
        "expiresIn": 300,
    })


# ─────────────────────────────────────────
# S3 이벤트 트리거 — Transcribe 작업 시작
# ─────────────────────────────────────────
def handle_s3_event(event: dict) -> dict:
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        logger.info(f"[transcribe] S3 이벤트: bucket={bucket}, key={key}")

        # S3 키에서 userId, recordId 추출 (audio/{userId}/{recordId}.ext)
        parts = key.split("/")
        if len(parts) < 3:
            logger.error(f"[transcribe] 잘못된 S3 키 형식: {key}")
            continue

        user_id = parts[1]
        record_id = parts[2].split(".")[0]

        # DynamoDB에 audio S3 키 업데이트
        table = dynamodb.Table(RECORDS_TABLE)
        table.update_item(
            Key={"userId": user_id, "recordId": record_id},
            UpdateExpression="SET audioS3Key = :key, updatedAt = :now",
            ExpressionAttributeValues={":key": key, ":now": now_iso()},
        )

        # Transcribe 작업 시작
        job_name = f"thime-{record_id}-{uuid.uuid4().hex[:8]}"
        media_uri = f"s3://{bucket}/{key}"

        try:
            transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": media_uri},
                MediaFormat=key.split(".")[-1],
                LanguageCode="ko-KR",
                OutputBucketName=bucket,
                OutputKey=f"transcripts/{user_id}/{record_id}.json",
                Settings={
                    "ShowSpeakerLabels": False,
                    "MaxSpeakerLabels": 1,
                },
                # 완료 시 SNS 알림 (선택: 여기서는 폴링 방식 사용)
            )
            logger.info(f"[transcribe] 작업 시작: jobName={job_name}, recordId={record_id}")

            # DynamoDB에 Transcribe 작업명 저장
            table.update_item(
                Key={"userId": user_id, "recordId": record_id},
                UpdateExpression="SET transcribeJobName = :job, transcribeStatus = :status, updatedAt = :now",
                ExpressionAttributeValues={
                    ":job": job_name,
                    ":status": "IN_PROGRESS",
                    ":now": now_iso(),
                },
            )
        except Exception as e:
            logger.error(f"[transcribe] Transcribe 작업 시작 실패: {e}")

    return {"statusCode": 200}
