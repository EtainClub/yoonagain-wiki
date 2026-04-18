#!/usr/bin/env python3
"""
export_firestore.py - Firestore wikiPages 컬렉션을 raw/ 디렉토리로 export

디렉토리 구조:
  raw/
    entity/{slug}.md      ← 인물·단체 페이지
    topic/{slug}.md       ← 주제·이슈 페이지
    event/{slug}.md       ← 이벤트 페이지
    cluster/{slug}.md     ← 클러스터 페이지
    comparison/{slug}.md  ← 비교 분석 페이지
    summary/{slug}.md     ← 요약 페이지

실행:
  uv run python scripts/export_firestore.py \\
    --output raw/ \\
    --credentials ../yoon-again/serviceAccountKey.json

  # 특정 타입만 export
  uv run python scripts/export_firestore.py --type entity

  # 기존 내용 삭제 후 전체 재export
  uv run python scripts/export_firestore.py --clean
"""

import argparse
import sys
from pathlib import Path

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    print("[오류] firebase-admin 패키지가 필요합니다: uv add firebase-admin")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("[오류] pyyaml 패키지가 필요합니다: uv add pyyaml")
    sys.exit(1)

VALID_PAGE_TYPES = ["entity", "topic", "event", "cluster", "comparison", "summary"]


def timestamp_to_str(ts) -> str:
    """Firestore Timestamp → ISO 날짜 문자열"""
    if ts is None:
        return ""
    try:
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return str(ts)


def sections_to_markdown(sections: list) -> str:
    """WikiSection 배열 → 마크다운 본문"""
    parts = []
    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        if title:
            parts.append(f"## {title}\n\n{content}")
        else:
            parts.append(content)
    return "\n\n".join(parts)


def format_wiki_page(page: dict) -> str:
    """WikiPage → YAML frontmatter + 마크다운 내용"""
    metadata = {
        "pageId": page.get("pageId", ""),
        "pageType": page.get("pageType", ""),
        "title": page.get("title", ""),
        "slug": page.get("slug", ""),
        "tags": page.get("tags", []),
        "keywords": page.get("keywords", []),
        "relatedEntityIds": page.get("relatedEntityIds", []),
        "wikiLinks": [
            {"targetPageId": lnk.get("targetPageId", ""), "linkText": lnk.get("linkText", "")}
            for lnk in page.get("wikiLinks", [])
        ],
        "backlinks": page.get("backlinks", []),
        "generatedBy": page.get("generatedBy", ""),
        "generatedAt": timestamp_to_str(page.get("generatedAt")),
        "lastUpdatedAt": timestamp_to_str(page.get("lastUpdatedAt")),
        "version": page.get("version", 1),
        "source": "firestore",
    }
    if page.get("entityId"):
        metadata["entityId"] = page["entityId"]

    frontmatter = yaml.dump(metadata, allow_unicode=True, default_flow_style=False)
    sections = page.get("sections", [])
    body = sections_to_markdown(sections)

    return f"---\n{frontmatter}---\n\n{body}\n"


def main():
    parser = argparse.ArgumentParser(description="Firestore wikiPages → raw/ export")
    parser.add_argument("--output", default="raw/", help="출력 디렉토리 (기본: raw/)")
    parser.add_argument(
        "--credentials",
        default="../yoon-again/serviceAccountKey.json",
        help="Firebase 서비스 계정 JSON 경로",
    )
    parser.add_argument(
        "--type",
        choices=VALID_PAGE_TYPES,
        help="특정 pageType만 export (미지정 시 전체)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="출력 디렉토리를 비우고 시작",
    )
    parser.add_argument(
        "--published-only",
        action="store_true",
        default=True,
        help="isPublished=True 페이지만 export (기본: True)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.clean:
        import shutil
        for page_type in VALID_PAGE_TYPES:
            type_dir = output_dir / page_type
            if type_dir.exists():
                shutil.rmtree(type_dir)
        print(f"[정리] {output_dir}/ 비움 완료")

    # 타입별 출력 디렉토리 생성
    for page_type in VALID_PAGE_TYPES:
        (output_dir / page_type).mkdir(exist_ok=True)

    cred_path = Path(args.credentials)
    if not cred_path.exists():
        print(f"[오류] 서비스 계정 파일을 찾을 수 없습니다: {cred_path}")
        print("  --credentials 옵션으로 경로를 지정하거나 환경변수 GOOGLE_APPLICATION_CREDENTIALS를 설정하세요")
        sys.exit(1)

    print(f"Firebase 초기화: {cred_path.name}")
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    print("Firestore wikiPages 컬렉션에서 페이지 가져오는 중...")
    query = db.collection("wikiPages")

    if args.type:
        query = query.where("pageType", "in", [args.type])
    else:
        query = query.where("pageType", "in", VALID_PAGE_TYPES)

    if args.published_only:
        query = query.where("isPublished", "==", True)

    docs = query.stream()

    total = 0
    by_type: dict[str, int] = {}

    for doc in docs:
        page = doc.to_dict()
        page_type = page.get("pageType", "")
        slug = page.get("slug", "")

        if page_type not in VALID_PAGE_TYPES:
            continue
        if not slug:
            print(f"  [경고] slug 없는 페이지 건너뜀: {doc.id}")
            continue

        file_path = output_dir / page_type / f"{slug}.md"
        content = format_wiki_page(page)
        file_path.write_text(content, encoding="utf-8")

        by_type[page_type] = by_type.get(page_type, 0) + 1
        total += 1

        title = page.get("title", doc.id)
        print(f"  ✓ {page_type}/{slug}.md  ← {title}")

    print(f"\n완료: {total}개 페이지 → {output_dir}/")
    for pt, count in sorted(by_type.items()):
        print(f"  {pt}: {count}개")


if __name__ == "__main__":
    main()
