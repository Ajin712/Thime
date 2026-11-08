"""Thime MVP 로컬 서버.

- thime-frontend/public 폴더의 파일(thime-mvp.html)을 http://localhost:8000 으로 보여 준다.
- /api/ai 로 들어온 요청을 ChatGPT(OpenAI) API로 전달한다.
  API 키는 브라우저에 노출되지 않도록 이 서버에서만 읽는다.
  키 위치: 환경 변수 OPENAI_API_KEY 또는 이 파일과 같은 폴더의 openai_key.txt
- 파이썬 기본 라이브러리만 사용한다. (pip 설치 필요 없음)
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "thime-frontend", "public")
PORT = 8000
# 위에서부터 차례로 시도하고, 쓸 수 없는 모델이면 다음 모델로 넘어간다.
MODELS = [m for m in os.environ.get("THIME_MODELS", "gpt-5-mini,gpt-4.1-mini,gpt-4o-mini").split(",") if m]


def load_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    path = os.path.join(ROOT, "openai_key.txt")
    if os.path.exists(path):
        found = re.findall(r"sk-[A-Za-z0-9_\-]{20,}", open(path, encoding="utf-8", errors="ignore").read())
        if found:
            return found[0]
    return ""


KEY = load_key()
state = {"model": None}

COACH_RULES = (
    "너는 Thime 앱의 '생각 코치'다. 목표는 사용자가 AI에 기대지 않고 스스로 깊이 생각하도록 돕는 것이다.\n"
    "규칙:\n"
    "- 절대 답, 정보, 사실, 의견, 예시 답안, 정리, 칭찬을 주지 않는다. 오직 질문만 한다.\n"
    "- 한국어 해요체로, 60자 이내의 질문 한 문장만 쓴다.\n"
)

PROBE_PROMPT = COACH_RULES + (
    "- 지금 단계(생각 기법의 관점)를 벗어나지 않는 질문을 한다.\n"
    "- 사용자의 이번 답에 쓰인 말을 붙잡아, 이유·근거·예·반례·전제를 한 걸음 더 파고들게 한다.\n"
    "- 이번 답이 이미 구체적이고 근거까지 있으면 더 묻지 않는다(deeper=false).\n"
    '출력은 JSON 하나: {"deeper": true 또는 false, "question": "질문"}'
)

RECOMMEND_PROMPT = (
    "너는 생각 훈련 앱 Thime의 질문 추천기다. 사용자가 스스로 깊이 생각하도록 만드는 질문 하나를 만든다.\n"
    "규칙:\n"
    "- 하나의 정답이 없고, 검색으로 바로 답할 수 없는 열린 질문.\n"
    "- 주어진 '생각 근육'을 집중해서 쓰게 만드는 질문.\n"
    "- 사용자가 최근 남긴 질문들의 관심사와 이어지되, 같은 질문을 반복하지 않는다.\n"
    "- 일상에서 바로 떠올릴 수 있는 쉬운 말로, 한국어 45자 이내 한 문장.\n"
    '출력은 JSON 하나: {"question": "질문"}'
)


HINT_PROMPT = COACH_RULES + (
    "- 사용자가 자기 답과 맞지 않는 경우(반례)를 찾지 못했다. 반례를 절대 직접 말하지 않는다.\n"
    "- 사용자가 스스로 찾도록 범위를 좁히는 질문 하나만 한다. 특정 결론으로 이끌지 않는다.\n"
    "- 힌트 1단계: 주변의 사람이나 상황을 떠올리게 한다.\n"
    "- 힌트 2단계: 사용자 답의 핵심 단어 하나를 그대로 따옴표로 인용해, 그 단어가 통하지 않는 상황을 묻는다.\n"
    "- 이 질문만은 반말(~볼까?, ~있을까?)로 쓴다.\n"
    '출력은 JSON 하나: {"question": "질문"}'
)


def call_openai(system, user):
    if not KEY:
        raise RuntimeError("no_key")
    models = [state["model"]] if state["model"] else MODELS
    last = None
    for model in models:
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": 1200,
        }
        if model.startswith("gpt-5"):
            body["reasoning_effort"] = "low"
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.load(r)
            state["model"] = model
            return json.loads(data["choices"][0]["message"]["content"] or "{}")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")[:300]
            last = f"{model}: HTTP {e.code} {msg}"
            print("[AI]", last, file=sys.stderr)
            if e.code in (400, 404) and not state["model"]:
                continue  # 이 모델을 쓸 수 없으면 다음 모델 시도
            raise RuntimeError(last)
    raise RuntimeError(last or "no_model")


def handle_ai(p):
    task = p.get("task")
    if task == "probe":
        prev = "\n".join(f"- {s}: {a}" for s, a in p.get("previous", []) if a) or "(없음)"
        user = (
            f"오늘의 질문: {p.get('question', '')}\n"
            f"생각 기법: {p.get('technique', '')}\n"
            f"지금 단계: {p.get('step', '')}\n"
            f"앞 단계에서 사용자가 한 말:\n{prev}\n"
            f"이번 단계에서 사용자의 답: {p.get('answer', '')}"
        )
        out = call_openai(PROBE_PROMPT, user)
        return {"deeper": bool(out.get("deeper")), "question": str(out.get("question", "")).strip()}
    if task == "hint":
        user = (
            f"오늘의 질문: {p.get('question', '')}\n"
            f"사용자의 첫 답: {p.get('first', '')}\n"
            f"그렇게 생각한 이유: {p.get('reason', '')}\n"
            f"힌트 단계: {p.get('level', 1)}"
        )
        out = call_openai(HINT_PROMPT, user)
        return {"question": str(out.get("question", "")).strip()}
    if task == "recommend":
        recent = "\n".join(f"- {q}" for q in p.get("recent", [])) or "(아직 없음)"
        user = (
            f"기를 생각 근육: {p.get('type', '')} ({p.get('desc', '')})\n"
            f"사용자가 최근 남긴 질문:\n{recent}"
        )
        out = call_openai(RECOMMEND_PROMPT, user)
        return {"question": str(out.get("question", "")).strip()}
    if task == "status":
        return {"ok": bool(KEY)}
    raise RuntimeError("unknown_task")


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/ai":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            res, code = handle_ai(payload), 200
        except Exception as e:  # 실패하면 앱이 규칙 기반으로 대신 동작한다
            res, code = {"error": str(e)[:300]}, 502
        data = json.dumps(res, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            sys.stderr.write("[요청] %s\n" % (args[0],))


if __name__ == "__main__":
    url = f"http://localhost:{PORT}/thime-mvp.html"
    print("Thime MVP 서버:", url)
    print("ChatGPT API 키:", "불러옴" if KEY else "없음 (AI 없이 규칙 기반으로 동작)")
    print("이 창을 닫으면 서버가 꺼져요.")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=PUBLIC))
    try:
        webbrowser.open(url)
    except Exception:
        pass
    server.serve_forever()
