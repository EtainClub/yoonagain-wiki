#!/usr/bin/env python3
"""
compile.py - Karpathy LLM Wiki 패턴 기반 위키 크로스레퍼런스 컴파일

입력:
  raw/{pageType}/{slug}.md  ← export_firestore.py가 생성한 원시 데이터

출력:
  wiki/{pageType}/{slug}.md  ← 크로스레퍼런스가 보강된 위키 페이지
  wiki/INDEX.md              ← 전체 페이지 카탈로그
  wiki/log.md                ← 컴파일 로그

2-Pass 컴파일:
  Pass 1: raw/ 파일을 읽어 wiki/ 페이지로 변환 (크로스레퍼런스 보강)
  Pass 2: INDEX.md 생성 + 역링크(backlink) 감사

실행:
  uv run python scripts/compile.py               # 전체 재컴파일
  uv run python scripts/compile.py --changed-files raw/entity/jeon-han-gil.md
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import frontmatter
except ImportError:
    print("[오류] python-frontmatter가 필요합니다: uv add python-frontmatter")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("[오류] anthropic 패키지가 필요합니다: uv add anthropic")
    sys.exit(1)

RAW_DIR = Path(__file__).parent.parent / "raw"
WIKI_DIR = Path(__file__).parent.parent / "wiki"

VALID_PAGE_TYPES = ["entity", "topic", "event", "cluster", "comparison", "summary"]

# ──────────────────────── Prompts ────────────────────────

ENRICH_PROMPT = """\
당신은 한국 정치 운동 위키 편집자입니다.
아래 '{title}' 위키 페이지 초안을 다음 지침에 따라 개선하세요.

**핵심 규칙**:
- 입력된 데이터에 명시된 사실만 서술. 추측·보완 절대 금지
- 데이터 부족 시 해당 섹션 생략 또는 빈 내용으로 표시
- 공개된 정보만, 중립적 서술 유지

**크로스레퍼런스 (중요)**:
아래 위키 페이지 목록 중 내용적으로 관련된 페이지가 있으면
본문에서 자연스럽게 [[pageId|표시텍스트]] 형식으로 링크하세요.
예: "[[entity:jeon-han-gil|전한길]]과 함께 활동한 것으로 알려져 있습니다"

마지막에 반드시 아래 섹션을 추가하세요:

## 관련 페이지
관련된 다른 위키 페이지를 [[pageId|표시텍스트]] — 한줄설명 형식으로 나열
최소 2개 이상 포함

현재 위키의 다른 페이지들:
{other_pages_list}

---

{page_content}
"""

INDEX_HEADER = """\
# 윤어게인 위키 인덱스

윤어게인(Yoon Again) 운동 관련 인물·단체·사건·주제를 정리한 지식 베이스입니다.

> **면책 고지**: 공개된 정보 기반의 정보 제공 목적이며, 특정 정치적 입장을 지지하지 않습니다.

"""

# ──────────────────────── Helpers ────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _call_llm(prompt: str, client: anthropic.Anthropic, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < retries - 1:
                import time
                wait = 30 * (attempt + 1)
                print(f"  Rate limit 도달 — {wait}초 대기...")
                time.sleep(wait)
            else:
                raise
    return ""


def load_raw_page(file_path: Path) -> dict | None:
    """raw/ 파일 → 딕셔너리 (frontmatter + content)"""
    try:
        post = frontmatter.load(str(file_path))
        return {
            "meta": dict(post.metadata),
            "content": post.content,
            "path": file_path,
        }
    except Exception as e:
        print(f"  [경고] 파싱 실패: {file_path} — {e}")
        return None


def get_all_raw_pages() -> list[dict]:
    """raw/ 디렉토리의 모든 페이지 로드"""
    pages = []
    for page_type in VALID_PAGE_TYPES:
        type_dir = RAW_DIR / page_type
        if not type_dir.exists():
            continue
        for md_file in sorted(type_dir.glob("*.md")):
            page = load_raw_page(md_file)
            if page:
                pages.append(page)
    return pages


def build_other_pages_list(pages: list[dict], current_page_id: str) -> str:
    """현재 페이지를 제외한 다른 페이지 목록 (프롬프트용)"""
    lines = []
    for page in pages:
        meta = page["meta"]
        page_id = meta.get("pageId", "")
        title = meta.get("title", "")
        page_type = meta.get("pageType", "")
        if page_id == current_page_id:
            continue
        # 첫 100자 요약
        summary = page["content"][:100].replace("\n", " ").strip()
        lines.append(f"- [[{page_id}|{title}]] ({page_type}): {summary}...")
    return "\n".join(lines) if lines else "(아직 다른 페이지 없음)"


def enrich_page(page: dict, all_pages: list[dict], client: anthropic.Anthropic) -> str:
    """LLM으로 크로스레퍼런스 보강"""
    meta = page["meta"]
    page_id = meta.get("pageId", "")
    title = meta.get("title", "")
    content = page["content"]

    # 내용이 너무 짧으면 LLM 호출 없이 그대로 반환
    if len(content.strip()) < 50:
        print(f"  [건너뜀] 내용 부족: {page_id}")
        return content

    other_pages = build_other_pages_list(all_pages, page_id)

    prompt = ENRICH_PROMPT.format(
        title=title,
        other_pages_list=other_pages,
        page_content=content,
    )

    print(f"  LLM 보강 중: {page_id}...")
    return _call_llm(prompt, client)


def write_wiki_page(page: dict, enriched_content: str) -> Path:
    """wiki/ 경로에 페이지 저장"""
    meta = page["meta"]
    page_type = meta.get("pageType", "")
    slug = meta.get("slug", "")

    if not page_type or not slug:
        raise ValueError(f"pageType 또는 slug 누락: {page['path']}")

    output_dir = WIKI_DIR / page_type
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}.md"

    # frontmatter에 컴파일 날짜 추가
    wiki_meta = dict(meta)
    wiki_meta["compiled"] = _now()
    wiki_meta.pop("source", None)

    import yaml
    frontmatter_str = yaml.dump(wiki_meta, allow_unicode=True, default_flow_style=False)
    final_content = f"---\n{frontmatter_str}---\n\n{enriched_content}\n"
    output_path.write_text(final_content, encoding="utf-8")
    return output_path


def build_index(all_pages: list[dict], compiled_paths: list[Path]) -> str:
    """wiki/INDEX.md 생성"""
    lines = [INDEX_HEADER]
    by_type: dict[str, list[dict]] = {}

    for page in all_pages:
        meta = page["meta"]
        pt = meta.get("pageType", "other")
        by_type.setdefault(pt, []).append(page)

    type_labels = {
        "entity": "인물·단체",
        "topic": "주제·이슈",
        "event": "이벤트",
        "cluster": "클러스터",
        "comparison": "비교 분석",
        "summary": "요약",
    }

    for page_type in VALID_PAGE_TYPES:
        pages = by_type.get(page_type, [])
        if not pages:
            continue
        label = type_labels.get(page_type, page_type)
        lines.append(f"## {label}\n")
        for page in sorted(pages, key=lambda p: p["meta"].get("title", "")):
            meta = page["meta"]
            page_id = meta.get("pageId", "")
            title = meta.get("title", "")
            slug = meta.get("slug", "")
            keywords = ", ".join(meta.get("keywords", [])[:5])
            lines.append(f"- [[{page_id}|{title}]] — {keywords}")
        lines.append("")

    lines.append(f"\n---\n*마지막 컴파일: {_now()}*\n")
    return "\n".join(lines)


def audit_backlinks(all_pages: list[dict]) -> list[str]:
    """Pass 2: 역링크 감사 — 깨진 링크·고아 페이지 감지"""
    all_page_ids = {p["meta"].get("pageId", "") for p in all_pages}
    issues = []

    for page in all_pages:
        meta = page["meta"]
        page_id = meta.get("pageId", "")
        wiki_links = meta.get("wikiLinks", [])

        for link in wiki_links:
            target = link.get("targetPageId", "")
            if target and target not in all_page_ids:
                issues.append(f"[깨진 링크] {page_id} → {target} (존재하지 않음)")

    # 역링크 없는 페이지 (고아 페이지)
    linked_to: set[str] = set()
    for page in all_pages:
        for link in page["meta"].get("wikiLinks", []):
            linked_to.add(link.get("targetPageId", ""))

    for page in all_pages:
        page_id = page["meta"].get("pageId", "")
        if page_id not in linked_to:
            issues.append(f"[고아 페이지] {page_id} — 다른 페이지에서 링크되지 않음")

    return issues


def main():
    parser = argparse.ArgumentParser(description="yoonagain-wiki 컴파일러")
    parser.add_argument(
        "--changed-files",
        nargs="*",
        help="변경된 raw/ 파일만 처리 (미지정 시 전체 재컴파일)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLM 호출 없이 raw/ 내용 그대로 wiki/로 복사 (빠른 테스트용)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.no_llm:
        print("[오류] ANTHROPIC_API_KEY 환경변수가 필요합니다")
        print("  --no-llm 옵션으로 LLM 없이 실행할 수 있습니다")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key) if not args.no_llm else None

    # 전체 raw 페이지 로드 (다른 페이지 목록용)
    print("raw/ 페이지 로드 중...")
    all_pages = get_all_raw_pages()
    print(f"  총 {len(all_pages)}개 페이지 발견")

    # 처리할 페이지 결정
    if args.changed_files:
        changed_paths = {Path(f).resolve() for f in args.changed_files}
        target_pages = [p for p in all_pages if p["path"].resolve() in changed_paths]
        print(f"  변경된 파일 {len(target_pages)}개만 처리")
    else:
        target_pages = all_pages
        print(f"  전체 {len(target_pages)}개 페이지 처리")

    # Pass 1: 각 페이지 컴파일
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    compiled_paths = []
    log_entries = []

    for page in target_pages:
        meta = page["meta"]
        page_id = meta.get("pageId", str(page["path"]))
        title = meta.get("title", "")

        try:
            if args.no_llm or client is None:
                enriched = page["content"]
            else:
                enriched = enrich_page(page, all_pages, client)

            output_path = write_wiki_page(page, enriched)
            compiled_paths.append(output_path)
            log_entries.append(f"✓ {page_id} ({title})")
            print(f"  저장: {output_path.relative_to(WIKI_DIR.parent)}")

        except Exception as e:
            log_entries.append(f"✗ {page_id}: {e}")
            print(f"  [오류] {page_id}: {e}")

    # Pass 2: INDEX.md 생성
    print("\nINDEX.md 생성 중...")
    index_content = build_index(all_pages, compiled_paths)
    index_path = WIKI_DIR / "INDEX.md"
    index_path.write_text(index_content, encoding="utf-8")
    print(f"  저장: {index_path.relative_to(WIKI_DIR.parent)}")

    # Pass 2: 역링크 감사
    print("\n역링크 감사 중...")
    issues = audit_backlinks(all_pages)
    if issues:
        print(f"  감지된 이슈 {len(issues)}개:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print("  이슈 없음")

    # log.md 업데이트
    log_path = WIKI_DIR / "log.md"
    existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    new_log_entry = f"## {_now()}\n\n" + "\n".join(log_entries)
    if issues:
        new_log_entry += "\n\n### 감사 이슈\n" + "\n".join(issues)
    log_path.write_text(f"{new_log_entry}\n\n---\n\n{existing_log}", encoding="utf-8")

    print(f"\n완료: {len(compiled_paths)}개 페이지 컴파일")


if __name__ == "__main__":
    main()
