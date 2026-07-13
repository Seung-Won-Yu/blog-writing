"""Shared, deterministic visual direction for daily editorial images."""

import re

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
    (
        "security",
        (
            "보안",
            "security",
            "취약",
            "권한",
            "privacy",
            "개인정보",
            "인스타",
            "사진",
            "공격",
            "attack",
        ),
    ),
    ("network", ("통신", "telecom", "5g", "network", "네트워크", "분산")),
    ("memory", ("메모리", "memory", "기억", "context", "컨텍스트", "rag", "검색")),
    ("hardware", ("gpu", "npu", "chip", "칩", "반도체", "하드웨어")),
    ("cloud", ("cloud", "클라우드", "server", "서버", "kubernetes", "인프라")),
    ("data", ("database", "데이터베이스", "데이터", "분석", "vector", "벡터", "clickhouse")),
    (
        "agent",
        (
            "agent",
            "에이전트",
            "세션",
            "session",
            "autonomous",
            "자율",
            "anthropic",
            "앤트로픽",
            "claude",
            "클로드",
        ),
    ),
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
SCENE_RULES = (
    (
        "privacy_photo",
        ("인스타", "instagram", "사진 ai", "photo ai"),
    ),
    (
        "observability",
        ("opentelemetry", "telemetry", "observability", "tracing", "관측", "모니터링"),
    ),
    (
        "datacenter",
        ("데이터센터", "data center", "datacenter", "inference", "gpu"),
    ),
    (
        "benchmark_gap",
        ("swe-bench", "벤치마크", "benchmark", "코딩 평가", "평가 한계"),
    ),
    (
        "model_choice",
        ("모델 3종", "gpt-5.6", "sol", "terra", "luna", "목적별 최적화"),
    ),
    (
        "code_workflow",
        ("pull request", "code review", "github actions", "workflow", "워크플로", "코드 리뷰"),
    ),
)
SCENE_SUBJECTS = {
    "privacy_photo": "사진과 AI 연동",
    "observability": "개발 도구 관측",
    "datacenter": "AI 토큰의 여정",
    "model_choice": "AI 모델 선택",
    "benchmark_gap": "코딩 평가의 빈틈",
    "code_workflow": "코드 변경의 흐름",
}
SCENE_HOOKS = {
    "privacy_photo": "내 사진은 어디까지 연결될까?",
    "observability": "개발 도구의 기록은 어디로 갈까?",
    "datacenter": "AI 답변 전 토큰은 어디를 지날까?",
    "model_choice": "빠른 모델과 깊은 모델, 무엇을 고를까?",
    "benchmark_gap": "점수는 실제 코딩을 얼마나 보여줄까?",
}
SCENE_LABELS = {
    "privacy_photo": "사진 데이터의 흐름",
    "observability": "개발 도구의 관측 흐름",
    "datacenter": "AI 요청의 처리 흐름",
    "model_choice": "세 모델의 선택 기준",
    "benchmark_gap": "벤치마크와 실제 차이",
    "code_workflow": "코드 변경의 검토 흐름",
}
SCENE_STEPS = {
    "privacy_photo": "사진 → AI 연동 → 사용자 통제",
    "observability": "개발 도구 → 관측 데이터 → 관리",
    "datacenter": "요청 토큰 → 데이터센터 → 응답",
    "model_choice": "속도·비용·정확도에 따른 모델 선택",
    "benchmark_gap": "평가 점수와 실제 코드 검증의 간극",
    "code_workflow": "코드 변경 → 검토 → 실행",
}
MOTIF_STEPS = {
    "network": "서비스 요청 → 경로 분산 → 연결 완료",
    "agent": "작업 목표 → 에이전트 수행 → 사람의 검토",
    "memory": "대화 맥락 → 기억 저장·검색 → 답변 반영",
    "security": "접근 요청 → 권한·위험 검사 → 허용·차단",
    "data": "원천 데이터 → 저장·분석 → 판단 근거",
    "code": "개발 의도 → 코드 작성 → 테스트 결과",
    "cloud": "서비스 트래픽 → 클라우드 자원 → 사용자 응답",
    "hardware": "AI 연산 → 칩 병렬 처리 → 성능 향상",
    "research": "연구 질문 → 실험·비교 → 검증된 결과",
    "signal": "변화 감지 → 의미 해석 → 다음 행동",
}
BANNED_VISUAL_HOOKS = (
    "충격",
    "소름",
    "무조건",
    "절대",
    "대박",
    "지금 안 보면",
    "미래는?",
    "전망은?",
    "결정적 변화",
    "새로운 방향",
    "무엇이 달라졌",
)
GENERIC_VISUAL_SUBJECTS = {
    "ai 이미지 생성",
    "오늘의 ai",
    "ai 뉴스",
    "개발 뉴스",
    "it 뉴스",
}


def motif_for_text(text):
    normalized = str(text or "").casefold()
    for motif, keywords in VISUAL_KEYWORDS:
        if any(_keyword_matches(normalized, keyword) for keyword in keywords):
            return motif
    return "signal"


def scene_for_text(text):
    normalized = str(text or "").casefold()
    for scene, keywords in SCENE_RULES:
        if any(_keyword_matches(normalized, keyword) for keyword in keywords):
            return scene
    return motif_for_text(text)


def scene_label(scene, motif="signal"):
    return SCENE_LABELS.get(scene, VISUAL_LABELS.get(motif, VISUAL_LABELS["signal"]))


def scene_steps(scene, motif="signal"):
    if scene in SCENE_STEPS:
        return SCENE_STEPS[scene]
    if scene in MOTIF_STEPS:
        return MOTIF_STEPS[scene]
    return MOTIF_STEPS.get(motif, MOTIF_STEPS["signal"])


def _keyword_matches(normalized, keyword):
    if keyword.isascii():
        pattern = r"(?<![a-z0-9]){}(?![a-z0-9])".format(re.escape(keyword))
        return re.search(pattern, normalized) is not None
    return keyword in normalized


def fallback_visual(reference):
    motif = motif_for_text(reference)
    scene = scene_for_text(reference)
    return {
        "subject": SCENE_SUBJECTS.get(scene, VISUAL_LABELS[motif]),
        "hook": SCENE_HOOKS.get(scene, VISUAL_HOOKS[motif]),
        "motif": motif,
    }


def _clean_text(value, limit):
    text = " ".join(str(value or "").replace("\x00", " ").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def validate_visual(raw, reference):
    fallback = fallback_visual(reference)
    if not isinstance(raw, dict):
        return fallback
    motif = _clean_text(raw.get("motif"), 20).lower()
    if motif not in VISUAL_MOTIFS:
        motif = fallback["motif"]
    hook = _clean_text(raw.get("hook"), 48)
    subject = _clean_text(raw.get("subject"), 24)
    lowered = hook.casefold()
    if (
        not hook
        or any(term in hook for term in BANNED_VISUAL_HOOKS)
        or any(term in lowered for term in ("http://", "https://", "<", ">", "```"))
    ):
        hook = fallback["hook"]
    if (
        not subject
        or subject.casefold() in GENERIC_VISUAL_SUBJECTS
        or any(term in subject for term in BANNED_VISUAL_HOOKS)
        or any(term in subject.casefold() for term in ("http://", "https://", "<", ">", "```"))
    ):
        subject = fallback["subject"]
    return {"subject": subject, "hook": hook, "motif": motif}
