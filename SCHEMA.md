# 위키 스키마

## raw/ 파일 형식

`raw/{pageType}/{slug}.md` 파일은 YAML frontmatter + 마크다운 본문으로 구성됩니다.

```yaml
---
pageId: entity:jeon-han-gil      # pageType:slug 형식
pageType: entity                  # entity | topic | event | cluster | comparison | summary
title: 전한길                      # 표시 이름
slug: jeon-han-gil                # URL-friendly 슬러그
entityId: abc123                  # entity 타입 전용 - Firestore entities/{id}
tags:
  - 유튜버
  - 강사
keywords:
  - 전한길
  - 한국사
  - 유튜브
relatedEntityIds:
  - entity-id-1
wikiLinks:
  - targetPageId: topic:123-martial-law
    linkText: 12.3 비상계엄
backlinks:
  - entity:ko-sung-guk
generatedBy: claude-haiku-4-5-20251001
generatedAt: 2024-12-15
lastUpdatedAt: 2025-01-10
version: 3
source: firestore
---

## 개요

페이지 본문...

## 관련 페이지

- [[topic:123-martial-law|12.3 비상계엄]] — 전한길이 관련된 주요 사건
```

## pageType별 설명

| pageType | 슬러그 예시 | 설명 |
|----------|------------|------|
| `entity` | `jeon-han-gil` | 개인 또는 단체 |
| `topic` | `123-martial-law` | 주제·이슈·운동 |
| `event` | `gwanghwamun-rally-2024` | 특정 시점의 사건 |
| `cluster` | `youtuber-conservative` | 유사 역할 그룹 |
| `comparison` | `activists-1225` | 복수 엔티티 비교 |
| `summary` | `yoon-again-overview` | 운동 전체 요약 |

## wiki/ 파일 형식

컴파일 후 생성되는 `wiki/{pageType}/{slug}.md` 파일은 raw/ 파일에 `compiled` 날짜가 추가되고
크로스레퍼런스가 보강된 형태입니다.

```yaml
---
# ... (raw와 동일한 frontmatter)
compiled: 2025-04-18         # 컴파일 날짜 (compile.py가 추가)
---

## 개요

보강된 본문 (LLM이 크로스레퍼런스 링크 추가)...

## 관련 페이지

- [[entity:ko-sung-guk|고성국]] — 같은 운동에 참여한 유튜버
- [[topic:123-martial-law|12.3 비상계엄]] — 관련 주요 사건
```

## wiki/INDEX.md 형식

전체 페이지 카탈로그. `compile.py`가 자동 생성합니다.

```markdown
# 윤어게인 위키 인덱스

## 인물·단체

- [[entity:jeon-han-gil|전한길]] — 전한길, 한국사, 유튜브...
- [[entity:ko-sung-guk|고성국]] — 고성국, 시사, 보수...

## 주제·이슈

- [[topic:123-martial-law|12.3 비상계엄]] — 계엄, 비상, 탄핵...
```

## Firestore 연결

| Firestore 컬렉션 | 위키 경로 | 설명 |
|-----------------|----------|------|
| `wikiPages/{pageType:slug}` | `raw/{pageType}/{slug}.md` | export_firestore.py로 동기화 |
| `wikiIndex/main` | `wiki/INDEX.md` | compile.py로 재생성 |
