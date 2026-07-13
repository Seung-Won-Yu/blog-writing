"""Shared, deterministic visual direction for daily editorial images."""

VISUAL_MOTIFS = {
    "network",
    "agent",
    "memory",
    "security",
    "data",
    "code",
    "cloud",
    "hardware",
    "research",
    "signal",
}
VISUAL_KEYWORDS = (
    ("security", ("보안", "security", "취약", "권한", "privacy", "공격", "attack")),
    ("network", ("통신", "telecom", "5g", "network", "네트워크", "분산")),
    ("memory", ("메모리", "memory", "기억", "context", "컨텍스트", "rag", "검색")),
    ("hardware", ("gpu", "npu", "chip", "칩", "반도체", "하드웨어")),
    ("cloud", ("cloud", "클라우드", "server", "서버", "kubernetes", "인프라")),
    ("data", ("database", "데이터베이스", "데이터", "분석", "vector", "벡터")),
    ("agent", ("agent", "에이전트", "세션", "session", "autonomous", "자율")),
    ("code", ("코드", "coding", "코딩", "github", "개발", "프레임워크", "cli")),
    ("research", ("논문", "paper", "arxiv", "연구", "benchmark", "벤치마크")),
)
VISUAL_HOOKS = {
    "network": "연결의 중심이 AI로 바뀐다면?",
    "agent": "AI는 어디까지 스스로 일할까?",
    "memory": "AI는 얼마나 오래 기억할까?",
    "security": "자동화, 어디까지 믿어도 될까?",
    "data": "데이터가 먼저 움직이기 시작한다면?",
    "code": "코드를 쓰는 방식이 달라진다면?",
    "cloud": "클라우드의 다음 병목은 어디일까?",
    "hardware": "AI의 속도는 결국 칩에서 갈릴까?",
    "research": "논문 속 변화가 제품이 된다면?",
    "signal": "오늘, 개발의 기준이 바뀐 지점은?",
}
VISUAL_LABELS = {
    "network": "연결 × AI",
    "agent": "AI 에이전트",
    "memory": "기억하는 AI",
    "security": "자동화 보안",
    "data": "데이터 흐름",
    "code": "코딩 방식",
    "cloud": "클라우드 운영",
    "hardware": "AI 하드웨어",
    "research": "연구의 다음 단계",
    "signal": "새로운 신호",
}
BANNED_VISUAL_HOOKS = ("충격", "소름", "무조건", "절대", "대박", "지금 안 보면")


def motif_for_text(text):
    normalized = str(text or "").casefold()
    for motif, keywords in VISUAL_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return motif
    return "signal"


def fallback_visual(reference):
    motif = motif_for_text(reference)
    return {"hook": VISUAL_HOOKS[motif], "motif": motif}


def _clean_text(value, limit):
    text = " ".join(str(value or "").replace("\x00", " ").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def validate_visual(raw, reference):
    fallback = fallback_visual(reference)
    if not isinstance(raw, dict):
        return fallback
    hook = _clean_text(raw.get("hook"), 48)
    lowered = hook.casefold()
    if (
        not hook
        or any(term in hook for term in BANNED_VISUAL_HOOKS)
        or any(term in lowered for term in ("http://", "https://", "<", ">", "```"))
    ):
        hook = fallback["hook"]
    motif = _clean_text(raw.get("motif"), 20).lower()
    if motif not in VISUAL_MOTIFS:
        motif = fallback["motif"]
    return {"hook": hook, "motif": motif}
