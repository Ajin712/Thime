# Thime Backend

> Thinking time — 잠들기 전 떠오른 생각을 남기고, 나중에 다시 만나 이어 가는 서비스

## 프로젝트 구조

```
thime-backend/
├── infra/                   # AWS CDK 인프라 코드
│   ├── app.py               # CDK 앱 진입점
│   ├── thime_stack.py       # 메인 스택 (Cognito + API GW + Lambda + DynamoDB)
│   └── requirements.txt
├── lambda/
│   ├── layers/common/       # 공통 유틸리티 (응답 형식, 에러 처리)
│   ├── record_api/          # F1: 기록 저장/조회
│   ├── transcribe_handler/  # F1: 음성 → 텍스트
│   ├── bedrock_handler/     # F2: 요약·태그 추출
│   ├── notification_handler/# F3·F4: 알림 발송
│   └── feed_handler/        # F5: 다른 생각 보기
└── requirements-dev.txt
```

## 빠른 시작

### 1. 사전 준비
```powershell
# Node.js LTS 설치 후
npm install -g aws-cdk

# AWS CLI 설정
aws configure
# Region: ap-northeast-2 (서울)
```

### 2. CDK 가상환경 세팅
```powershell
cd infra
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 배포
```powershell
# 최초 1회만
cdk bootstrap

# 배포
cdk deploy
```

### 4. 배포 후 출력값 확인
- `ThimeStack.UserPoolId`
- `ThimeStack.UserPoolClientId`
- `ThimeStack.ApiUrl`

이 값들을 프론트엔드 `.env`에 입력합니다.

## API 엔드포인트

| Method | Path | Lambda | 기능 |
|--------|------|--------|------|
| POST | /records | record_api | 텍스트 기록 저장 |
| GET | /records | record_api | 내 기록 목록 조회 |
| GET | /records/{id} | record_api | 기록 상세 조회 |
| PATCH | /records/{id}/followup | record_api | 이어 생각 추가 |
| POST | /records/audio-url | transcribe_handler | 음성 업로드 presigned URL 발급 |
| POST | /records/{id}/summarize | bedrock_handler | 요약·태그 추출 |
| GET | /questions/today | notification_handler | 오늘의 질문 조회 |
| GET | /feeds/{questionId} | feed_handler | 다른 사람 생각 보기 |
| POST | /feeds/{questionId} | feed_handler | 내 답 공유 |
