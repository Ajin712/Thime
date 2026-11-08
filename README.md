# Thime · 질문할까말까

> AI가 답을 대신해 주는 시대, **답 대신 질문만 던지는 AI**와 함께 스스로 생각하는 근육을 기르는 생각 훈련 서비스

2026 충남대학교 AWS KIRO 기반 AI 빌더스 챌린지 출품작

## 문제

- AI에 과의존하면서 스스로 생각하는 시간이 줄어든다.
- AI가 공감 위주로 답해 줘서, 내 생각을 비판적으로 돌아볼 기회가 적다.
- 잠들기 전에 떠오른 생각은 다음 날이면 잊힌다.

## 해결

1. **생각 훈련**: 질문 하나를 정하고, 정한 시간 동안 생각 코치와 문답하며 스스로 생각한다.
2. **답하지 않는 AI 코치**: AI는 질문만 던진다. 답·정보·의견·판정을 주지 않고, 결론은 사용자가 직접 쓴다.
3. **다시 꺼내기**: 정한 날(1·2·3주 뒤)에 그때의 생각이 돌아오고, "지금도 같은 생각이야?"로 다시 문답한다.
4. **생각 게시판**(부가 기능): 다른 사람의 결론을 보고, 작성자에게 질문을 보낸다. 작성자는 골라서 답한다.

## 생각 기법

| 기법 | 진행 | 출처 |
|---|---|---|
| 소크라테스식 문답 (기본) | 첫 답 → 이유 → 반대되는 경우 → 수정 → 내 결론 | 플라톤의 대화편(『메논』, 『에우티프론』 등); R. Paul & L. Elder, *The Thinker's Guide to the Art of Socratic Questioning* (2006) |
| 여섯 가지 모자 | 파랑 → 하양 → 빨강 → 노랑 → 검정 → 초록 → 파랑 | E. de Bono, *Six Thinking Hats* (1985) |

### AI(ChatGPT)가 하는 일

- 사용자의 답을 읽고 **한 걸음 더 파고드는 질문**을 만든다.
- 소크라테스식 문답 3단계에서 반례를 못 찾으면, 반례를 대신 말하지 않고 **범위를 좁히는 힌트 질문**을 만든다 (최대 2번).
- 사용자의 최근 기록을 보고 **덜 써 본 생각 근육을 기르는 질문**을 추천한다.
- AI 호출이 실패하면 앱은 규칙 기반으로 계속 동작한다.

## 실행 방법 (Windows)

1. [Python 3](https://www.python.org/)이 설치되어 있어야 합니다. 추가 패키지는 필요 없습니다.
2. `openai_key.example.txt`를 참고해 `openai_key.txt`에 OpenAI API 키를 넣습니다. (없으면 AI 없이 규칙 기반으로 동작)
3. `run-mvp.bat`을 더블클릭합니다.
4. 브라우저에서 http://localhost:8000/thime-mvp.html 이 열립니다.

명령어로 실행하려면:

```
cd Thime
python server.py
```

## 폴더 구조

```
Thime/
├─ thime-frontend/public/thime-mvp.html  # MVP 앱 (HTML 한 파일)
├─ server.py                             # 로컬 서버 + ChatGPT API 중계 (키는 서버만 읽음)
├─ run-mvp.bat                           # 실행 파일
├─ .kiro/steering/                       # Kiro 스티어링 문서 (제품·기술·코드 구조)
├─ thime-frontend/src/                   # React 앱 초안 (현재 미사용)
└─ thime-backend/                        # AWS Lambda·CDK 초안 (현재 미사용)
```

## 기술

- 프론트엔드: HTML·CSS·JavaScript 단일 파일, Web Speech API(음성 인식), localStorage·IndexedDB
- AI: OpenAI ChatGPT API (`server.py`에서 중계)
- 개발 도구: AWS Kiro
