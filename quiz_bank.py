"""Curated, deterministic Information Processing Engineer quiz questions."""

import copy
import hashlib


QUIZ_BANK = [
    {
        "category": "소프트웨어 설계",
        "question": "UML 다이어그램 중 객체 사이의 메시지 교환을 시간 순서에 따라 표현하는 것은?",
        "options": ["시퀀스 다이어그램", "클래스 다이어그램", "배치 다이어그램", "패키지 다이어그램"],
        "answer": 0,
        "explain_kr": "시퀀스 다이어그램은 객체 사이에 오가는 메시지를 시간의 흐름에 따라 표현하는 동적 다이어그램입니다.",
    },
    {
        "category": "소프트웨어 설계",
        "question": "한 모듈이 다른 모듈의 내부 데이터를 직접 참조하거나 수정할 때의 결합도는?",
        "options": ["내용 결합도", "공통 결합도", "외부 결합도", "스탬프 결합도"],
        "answer": 0,
        "explain_kr": "내용 결합도는 한 모듈이 다른 모듈의 내부 자료나 내부 기능을 직접 사용하는 가장 강한 결합도입니다.",
    },
    {
        "category": "소프트웨어 개발",
        "question": "화이트박스 테스트에서 각 결정문의 참과 거짓 결과를 최소 한 번씩 실행하는 기준은?",
        "options": ["분기 커버리지", "문장 커버리지", "조건 커버리지", "변경 조건·결정 커버리지"],
        "answer": 0,
        "explain_kr": "분기 커버리지는 결정문이 가질 수 있는 참과 거짓 분기를 각각 최소 한 번 실행하도록 하는 기준입니다.",
    },
    {
        "category": "소프트웨어 개발",
        "question": "가장 나중에 삽입된 자료가 가장 먼저 삭제되는 LIFO 방식의 자료구조는?",
        "options": ["스택", "큐", "트리", "그래프"],
        "answer": 0,
        "explain_kr": "스택은 한쪽 끝에서 삽입과 삭제가 이루어지며 마지막에 넣은 자료를 먼저 꺼내는 LIFO 구조입니다.",
    },
    {
        "category": "데이터베이스 구축",
        "question": "트랜잭션의 연산이 모두 반영되거나 전혀 반영되지 않아야 한다는 ACID 특성은?",
        "options": ["원자성", "일관성", "독립성", "지속성"],
        "answer": 0,
        "explain_kr": "원자성은 트랜잭션을 하나의 작업 단위로 보고 모든 연산을 수행하거나 모두 취소해야 한다는 특성입니다.",
    },
    {
        "category": "데이터베이스 구축",
        "question": "관계형 데이터베이스에서 이행적 함수 종속을 제거한 정규형은?",
        "options": ["제3정규형", "제1정규형", "제2정규형", "보이스-코드 정규형"],
        "answer": 0,
        "explain_kr": "제3정규형은 제2정규형을 만족하면서 기본키가 아닌 속성 사이의 이행적 함수 종속을 제거한 형태입니다.",
    },
    {
        "category": "프로그래밍 언어 활용",
        "question": "프로세스 스케줄링 방식 중 비선점 방식에 해당하는 것은?",
        "options": ["HRN", "Round Robin", "SRT", "다단계 피드백 큐"],
        "answer": 0,
        "explain_kr": "HRN은 대기 시간과 서비스 시간을 이용해 우선순위를 정하는 비선점 스케줄링 방식입니다.",
    },
    {
        "category": "프로그래밍 언어 활용",
        "question": "C 언어에서 헤더 파일의 내용을 소스에 포함할 때 사용하는 전처리기 지시어는?",
        "options": ["#include", "#define", "#ifdef", "#pragma"],
        "answer": 0,
        "explain_kr": "#include 지시어는 지정한 헤더 파일의 내용을 현재 소스 파일에 포함하도록 전처리기에 지시합니다.",
    },
    {
        "category": "정보시스템 구축관리",
        "question": "OSI 7계층에서 경로 선택과 패킷 전달을 담당하는 계층은?",
        "options": ["네트워크 계층", "데이터 링크 계층", "전송 계층", "세션 계층"],
        "answer": 0,
        "explain_kr": "네트워크 계층은 논리 주소를 기반으로 통신 경로를 선택하고 패킷을 목적지까지 전달합니다.",
    },
    {
        "category": "정보시스템 구축관리",
        "question": "암호화와 복호화에 동일한 키를 사용하는 암호화 방식은?",
        "options": ["대칭키 암호화", "공개키 암호화", "해시 함수", "전자서명"],
        "answer": 0,
        "explain_kr": "대칭키 암호화는 암호화와 복호화에 같은 비밀키를 사용하며 키를 안전하게 공유하는 과정이 필요합니다.",
    },
]


def select_quiz(day_id, recent_questions=None):
    """Select a stable question for the day while avoiding recent repeats."""
    ordered_recent = [
        " ".join(str(item or "").split()) for item in recent_questions or []
    ]
    recent = set(ordered_recent)
    digest = hashlib.sha256(str(day_id).encode("utf-8")).hexdigest()
    start = int(digest[:8], 16) % len(QUIZ_BANK)
    selected = None
    for offset in range(len(QUIZ_BANK)):
        quiz = QUIZ_BANK[(start + offset) % len(QUIZ_BANK)]
        if quiz["question"] not in recent:
            selected = copy.deepcopy(quiz)
            break
    if selected is None:
        last_seen = {quiz["question"]: -1 for quiz in QUIZ_BANK}
        for index, question in enumerate(ordered_recent):
            if question in last_seen:
                last_seen[question] = index
        oldest_index = min(last_seen.values())
        for offset in range(len(QUIZ_BANK)):
            quiz = QUIZ_BANK[(start + offset) % len(QUIZ_BANK)]
            if last_seen[quiz["question"]] == oldest_index:
                selected = copy.deepcopy(quiz)
                break

    rotation = int(digest[8:10], 16) % len(selected["options"])
    if rotation:
        selected["options"] = (
            selected["options"][rotation:] + selected["options"][:rotation]
        )
        selected["answer"] = (selected["answer"] - rotation) % len(
            selected["options"]
        )
    return selected
