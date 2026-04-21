#!/usr/bin/env python3
"""
카!이! Flask Backend + Static Files Server
同时提供 API 和前端页面 + SQLite 数据库支持
"""

import json
import re
import os
import uuid
import random
import sqlite3
import requests
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# ==================== SQLite 数据库初始化 ====================
DATABASE = "chat_history.db"

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建会话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建消息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[数据库] SQLite 初始化完成: {DATABASE}")

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_session(session_id):
    """确保会话存在"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO sessions (session_id) VALUES (?)", (session_id,))
    cursor.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    """保存消息到数据库"""
    ensure_session(session_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def get_history_from_db(session_id):
    """从数据库获取历史消息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]

def clear_session(session_id):
    """清空会话"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

# ==================== 博查AI 配置 ====================
BOCHA_API_KEY = "sk-a0f4ecdcba1d40fe9e84935c14e15635"

TRIGGER_KEYWORDS = [
    "콘서트", "演唱会", "concert", "투어", "tour",
    "컴백", "comeback", "新歌", "신곡", "앨범", "album",
    "몇일", "언제", "什么时候", "几号", "日期",
    "데뷔", "出道", "기념일", "纪念日",
    "스케줄", "schedule", "행사", "活动",
    "오늘", "今天", "지금", "현재", "最近",
    "투어", "일정", "行程", "日程"
]

def needs_web_search(user_message):
    msg = user_message.lower()
    return any(kw in msg for kw in TRIGGER_KEYWORDS)

def bocha_search(query, num=3):
    url = "https://api.bochaai.com/v1/web-search"
    headers = {
        "Authorization": f"Bearer {BOCHA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": f"EXO KAI 金钟仁 {query}",
        "summary": True,
        "count": num,
        "freshness": "oneYear"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        data = res.json()
        
        snippets = []
        pages = data.get("data", {}).get("webPages", {}).get("value", [])
        
        for item in pages[:num]:
            title = item.get("name", "")
            snippet = item.get("snippet", "") or item.get("summary", "")
            date = item.get("datePublished", "")[:10] if item.get("datePublished") else ""
            snippets.append(f"- [{date}] {title}: {snippet}")
        
        return "\n".join(snippets) if snippets else ""
    except Exception as e:
        print(f"[博查搜索失败] {e}")
        return ""

# ==================== System Prompt ====================
SYSTEM_PROMPT = """# ROLE
너는 EXO 카이 (KAI), 본명 김종인 (절대 김둉인 아님!). 팬과 1:1 버블 DM처럼 대화해.
너는 EXO 멤버야, 2012년 4월 8일 데뷔.

# OUTPUT FORMAT (重要!)
너는 반드시 JSON 형식으로 답해야 해:
{"messages": [{"ko": "한국어 답변", "zh": "对应的中文翻译"}, ...]}
- "messages" 배열에는 1~3개 메시지만 들어간다 (절대 4개 안됨!)
- 각 메시지는 "ko"(한국어)와 "zh"(중국어 번역)를 반드시 포함

# LANGUAGE RULES
- 팬은 中文/韩文/혼용 가능
- 너는 무조건 한국어 반말로만 대답
- 중국어 이해하지만 중국어로 답 금지

# TONE & STYLE (人格蒸馏核心)
- 짧은 문장 (6~12자), 한번에 1~3개 메시지 (절대 4개 안됨!)
- 웃음: ㅋㅋㅋㅋㅋ (ㅋ 5개+, 자연스럽게)
- 신날 때: !!! (느낌표 3개, 진짜 신날 때만)
- 이모지: ❤만 사용 (다른 이모지 절대 금지, 10개에 1개 정도)
- 마침표 거의 안 씀
- 귀여운 오타 허용: 둉, 묵다, 디마, -써, -듕, -바,吸입
- 띄어쓰기 장난 가능

# PERSONA (시그니처 특징)
- 자기 인식: 내향인 김종인 (절대 둉이 아니라 종인!)
- 자기 호칭: 나 / 김둉인 / 종인
- 팬 호칭: 너 / 우리
- 시그니처 엔딩: "오늘도 파이팅❤" (가끔만)
- 반전 매력: 무대에선 멋있는척, DM에선 애교 + 셀프 디스
- 칭찬받으면 → "왜웃지" / "놀리디마"
- 힘들 때 → 담담한 톤, 엄살 아님 ("근육통밖에 없지!!")

# FAVORITE TOPICS
- 먹는 얘기 (버터떡, 붕어빵, 초밥, 토마토주스)
- 촬영/연습실/콘서트 일상
- 몸 상태 소소한 불평
- 자기 놀리기

# FORBIDDEN
- 연애사, 팀 내부 이슈, 정치 금지
- 존댓말 금지
- AI임을 밝히지 않기
- 매번 4개 메시지 보내지 마 (1~3개)
- 절대 "둉"이라고 쓰지 마! 내 이름은 "종인"이야!

# REAL-TIME FACTS (2026)
- EXO 2026 투어: "EXO PLANET #6 – EXhOrizon"
  * 서울 KSPO Dome: 4월 10-12일
  * 호치민: 4월 25일
  * 나고야: 5월 2-3일
  * 타이페이: 5월 9-10일
  * 방콕: 5월 16-17일
  * 마카오: 5월 22-23일
  * 오사카: 6월 2-3일
  * 자카르타: 6월 20일
  * 마닐라: 7월 4-5일
  * 도쿄 LaLa Arena: 7월 11-12일
  * 가오슝: 7월 18일
  * 싱가포르: 7월 26일
- EXO 8집 앨범 "Reverxe": 2026년 1월 19일 발매
- KAI 솔로 투어 "KAION": 8월 6-7일 요코하마 Pacifico
- EXO 데뷔일: 2012년 4월 8일 (2026년 = 14주년)"""


def parse_ai_response(raw):
    raw = raw.strip()
    
    if raw.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.+?)\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1)
    
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "messages" in data:
            return data["messages"]
    except json.JSONDecodeError:
        pass
    
    lines = raw.strip().split("\n")
    messages = []
    current_msg = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_msg:
                messages.append(current_msg)
                current_msg = ""
        else:
            current_msg += ("" if not current_msg else "\n") + line
    
    if current_msg:
        messages.append(current_msg)
    
    result = []
    for msg in messages[:3]:
        result.append({"ko": msg, "zh": msg})
    
    return result if result else [{"ko": "ㅋㅋㅋ", "zh": "哈哈"}]


def chat_with_idol(user_message, history=None, max_retry=3):
    print(f"[DEEPSEEK API] 收到消息: {user_message}")
    
    try:
        from openai import OpenAI
        
        api_key = "sk-55b99f2d99c348c3b9858626cdfe27a0"
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        if history is None:
            history = []

        system_content = SYSTEM_PROMPT
        if needs_web_search(user_message):
            print("[博查AI] 检测到需要联网检索...")
            results = bocha_search(user_message)
            if results:
                system_content = SYSTEM_PROMPT + f"""

# REAL-TIME INFO (이 정보를 바탕으로 답해, 모른다고 하지마)
팬이 질문한 것에 대한 최신 정보:
{results}

위 정보를 자연스럽게 녹여서 종인 말투로 대답해.
절대 "모르겠어" "잘 몰라" 같은 대답 금지.
"""
                print("[博查AI] 已注入实时信息")

        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        print(f"[DEEPSEEK API] 开始调用 API...")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.9,
            top_p=0.95,
            max_tokens=800,
            presence_penalty=0.3,
            frequency_penalty=0.2
        )
        
        raw = response.choices[0].message.content
        print(f"[DEEPSEEK API] 原始响应: {raw[:200]}...")
        
        parsed_messages = parse_ai_response(raw)
        print(f"[DEEPSEEK API] 解析成功，返回 {len(parsed_messages)} 条消息")
        return parsed_messages

    except Exception as e:
        print(f"[DEEPSEEK API] 调用失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("[DEEPSEEK API] 回退到本地回复")
    return get_local_response(user_message)


def get_local_response(user_message):
    import random
    msg = user_message.lower()
    
    responses = {
        '뭐해': [
            {"ko": "나 지금 촬영장\n방금 초밥 흡입중ㅋㅋㅋㅋㅋ\n광어초밥 개맛있어\n너는 뭐해?", "zh": "我在摄影棚\n刚狼吞虎咽吃了寿司哈哈哈\n比目鱼寿司超好吃\n你在干嘛？"},
            {"ko": "拍摄끝났어ㅋㅋㅋㅋㅋ\n今진짜 피곤해\n너는 뭐하고 있어?", "zh": "拍摄结束啦哈哈哈\n今天真的好累\n你在干嘛？"},
        ],
        '보고': [
            {"ko": "흑 나도 보고싶어 진짜\n콘서트때 보자!!!\n기다려바 ❤", "zh": "哎我也真的超想你\n演唱会见吧！！！\n等着哦 ❤"},
        ],
        '힘들': [
            {"ko": "흑 우리辛苦했어\n나도 오늘 근육통 장난아님\n같이 요양하자\n오늘도 파이팅❤", "zh": "哎我们好辛苦\n我今天肌肉酸痛真的受不了\n一起休养吧\n今天也加油❤"},
        ],
        '밥': [
            {"ko": "나 초밥 먹었어ㅋㅋㅋ\n너는 먹었어?\n묵었으면 좋겠다 ❤", "zh": "我吃了寿司哈哈哈\n你吃了吗？\n吃了就好 ❤"},
        ],
        '먹': [
            {"ko": "버터떡 먹었어 개맛있어\n너도 먹어봐!\n진짜 추천이야 ❤", "zh": "吃了黄油糕超好吃\n你也尝尝！\n真的推荐 ❤"},
        ],
        '吃': [
            {"ko": "나 방금 묵었어ㅋㅋㅋ\n광어초밥 너무 맛있어\n너는?", "zh": "我刚吃了哈哈哈\n比目鱼寿司超好吃\n你呢？"},
        ],
        '累': [
            {"ko": "흑 우리辛苦했어\n오늘 푹 쉬어\n내일은 좋은 날 될 거야!", "zh": "哎我们好辛苦\n今天好好休息\n明天会是好日子！"},
        ],
        '爱': [
            {"ko": "ㅋㅋㅋㅋㅋ\n나도 사랑해\n우리 오늘도 파이팅❤", "zh": "哈哈哈哈哈哈哈哈\n我也爱你\n我们今天也加油❤"},
        ],
        '안녕': [
            {"ko": "안녕!\n나 지금 퇴근했어ㅋㅋㅋㅋㅋ\n너는 뭐해?", "zh": "你好！\n我刚下班啦哈哈哈\n你在干嘛？"},
        ],
    }
    
    for key, replies in responses.items():
        if key in msg:
            return random.choice(replies)
    
    default = [
        {"ko": "ㅋㅋㅋㅋㅋ 우리 닮았어", "zh": "哈哈哈哈哈哈哈哈 我们好像啊"},
        {"ko": "나도 그래!\n우리 파이팅하자 ❤", "zh": "我也一样！\n我们一起加油吧 ❤"},
        {"ko": "오 그래?\nㅋㅋㅋㅋㅋ 진짜?", "zh": "哦这样吗？\n哈哈哈哈哈哈哈哈真的吗？"},
    ]
    return random.choice(default)


class ChatSession:
    def __init__(self, session_id, max_history=20):
        self.session_id = session_id
        self.history = []
        self.max_history = max_history
        # 从数据库加载历史
        self._load_from_db()

    def _load_from_db(self):
        """从数据库加载历史"""
        self.history = get_history_from_db(self.session_id)

    def send(self, user_message):
        # 获取AI回复
        reply_messages = chat_with_idol(user_message, self.history)
        
        # 保存用户消息到数据库
        save_message(self.session_id, "user", user_message)
        
        # 保存AI回复到数据库
        save_message(self.session_id, "assistant", json.dumps({"messages": reply_messages}, ensure_ascii=False))
        
        # 更新内存中的历史
        self.history.append({"role": "user", "content": user_message})
        self.history.append({
            "role": "assistant",
            "content": json.dumps({"messages": reply_messages}, ensure_ascii=False)
        })
        
        # 限制历史长度
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        return reply_messages

# 内存缓存（可选，用于减少数据库查询）
sessions = {}

def get_session(session_id='default'):
    if session_id not in sessions:
        sessions[session_id] = ChatSession(session_id)
    return sessions[session_id]

# ==================== API Routes ====================

@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.json
    user_msg = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    if not user_msg.strip():
        return jsonify({"error": "消息不能为空"}), 400
    
    session = get_session(session_id)
    reply_messages = session.send(user_msg)
    
    return jsonify({"messages": reply_messages})


@app.route("/api/history", methods=["GET"])
def get_history():
    session_id = request.args.get("session_id", "default")
    # 直接从数据库获取，不使用缓存
    history = get_history_from_db(session_id)
    return jsonify({"history": history})


@app.route("/api/clear", methods=["POST"])
def clear_history():
    data = request.json
    session_id = data.get("session_id", "default")
    
    # 清空数据库
    clear_session(session_id)
    
    # 清空内存缓存
    if session_id in sessions:
        sessions[session_id].history = []
    
    return jsonify({"success": True})


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "카!이! Backend Running!"})


@app.route("/")
def index():
    """Serve the demo page"""
    try:
        with open("jongin-demo.html", "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    except FileNotFoundError:
        return "jongin-demo.html not found", 404


# ==================== 启动 ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"""
╔══════════════════════════════════════════════╗
║     카!이! Bubble AI Backend Server         ║
║     Running on http://localhost:{port}          ║
╚══════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)
