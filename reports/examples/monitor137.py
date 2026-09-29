"""교육용 변경 감지기. UTF-8 HTML의 고유 id 하나만 비교한다."""
import argparse
import difflib
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

LIMIT = 1_000_000
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
BLOCK = set("div p li section article h1 h2 h3 h4 tr br".split())


class TargetText(HTMLParser):
    def __init__(self, target):
        super().__init__(convert_charrefs=True)
        self.target, self.stack, self.parts, self.matches = target, [], [], 0

    def handle_starttag(self, tag, attrs):
        matched = dict(attrs).get("id") == self.target
        if matched:
            self.matches += 1
            if self.stack or tag in VOID:
                raise ValueError("대상 id는 일반 컨테이너에 한 번만 사용하세요.")
            self.stack = [tag]
        elif self.stack and tag not in VOID:
            self.stack.append(tag)
        if self.stack and tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if not self.stack or tag in VOID:
            return
        if self.stack[-1] != tag:
            raise ValueError("대상 내부의 HTML 종료 태그를 확인하세요.")
        self.stack.pop()
        if tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.stack and not any(t in {"script", "style"} for t in self.stack):
            self.parts.append(data)

    def result(self):
        text = "\n".join(
            re.sub(r"\s+", " ", line).strip()
            for line in "".join(self.parts).splitlines() if line.strip()
        )
        if self.matches != 1 or self.stack or not text:
            raise ValueError("대상은 닫힌 태그·고유 id·비어 있지 않은 텍스트여야 합니다.")
        return text


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("source", help="HTTP(S) URL 또는 --html-file로 읽을 파일")
    cli.add_argument("--html-file", action="store_true")
    cli.add_argument("--target-id", default="watch-target")
    cli.add_argument("--state", default="state.json")
    args = cli.parse_args()
    state_path = Path(args.state)
    scope = [str(Path(args.source).resolve()) if args.html_file else args.source,
             args.target_id, args.html_file]
    try:
        if args.html_file:
            if Path(args.source).resolve() == state_path.resolve():
                raise ValueError("입력 HTML과 상태 파일은 다른 파일이어야 합니다.")
            with Path(args.source).open("rb") as stream:
                raw = stream.read(LIMIT + 1)
        else:
            if urlsplit(args.source).scheme not in {"http", "https"}:
                raise ValueError("공개 HTTP(S) URL만 입력하세요.")
            request = Request(args.source, headers={"User-Agent": "ChangeMonitorDemo/1.0"})
            with urlopen(request, timeout=10) as response:
                if response.headers.get_content_type() != "text/html":
                    raise ValueError("HTML 응답이 아닙니다.")
                raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError("HTML이 1MB 상한을 넘었습니다.")
        parser = TargetText(args.target_id)
        parser.feed(raw.decode("utf-8"))
        parser.close()
        current = parser.result()
        digest = hashlib.sha256(current.encode("utf-8")).hexdigest()
        previous = None
        if state_path.exists():
            previous = json.loads(state_path.read_text(encoding="utf-8"))
            if (not isinstance(previous, dict) or previous.get("scope") != scope
                    or not isinstance(previous.get("text"), str)
                    or previous.get("hash") != hashlib.sha256(
                        previous["text"].encode("utf-8")).hexdigest()):
                raise ValueError("상태 파일이 손상되었거나 다른 대상의 기준입니다.")
        status = ("BASELINE" if previous is None else
                  "UNCHANGED" if previous["hash"] == digest else "CHANGED")
        temp = state_path.with_name(state_path.name + ".tmp")
        # 한 대상에 한 프로세스만 실행한다. 임시 파일도 실험 전용 이름을 쓴다.
        with temp.open("x", encoding="utf-8") as stream:
            json.dump({"scope": scope, "hash": digest, "text": current},
                      stream, ensure_ascii=False, indent=2)
        temp.replace(state_path)
        print(status)
        if status == "CHANGED":
            print("알림 대상 (외부 전송 없음)")
            print("\n".join(difflib.unified_diff(
                previous["text"].splitlines(), current.splitlines(),
                fromfile="이전", tofile="현재", lineterm="")))
        return 0
    except (OSError, ValueError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
