# 기여 가이드

## raw/ 데이터 기여

`raw/` 디렉토리의 마크다운 파일을 PR로 제출할 수 있습니다.

### 파일 형식

```markdown
---
pageId: entity:jeon-han-gil
pageType: entity
title: 전한길
slug: jeon-han-gil
tags: [유튜버, 강사]
keywords: [전한길, 한국사, 유튜브]
source: community
updatedAt: YYYY-MM-DD
---

## 개요

내용...
```

### pageType별 파일 위치

| pageType | 파일 경로 |
|----------|-----------|
| entity | `raw/entity/{slug}.md` |
| topic | `raw/topic/{slug}.md` |
| event | `raw/event/{slug}.md` |
| cluster | `raw/cluster/{slug}.md` |
| comparison | `raw/comparison/{slug}.md` |
| summary | `raw/summary/{slug}.md` |

### 기여 원칙

- **공개된 사실만 서술**: 공개된 뉴스, 기사, 공식 발표에 기반한 내용만
- **중립적 서술**: 특정 정치적 입장을 지지하거나 비방하는 내용 금지
- **출처 명시**: 가능하면 근거 URL 포함 (`sourceUrls` 필드)
- **개인정보 보호**: 공인이 아닌 개인의 민감한 정보 포함 금지

## wiki/ 페이지 직접 수정

`wiki/` 디렉토리 파일은 GitHub Actions가 자동 생성하므로 직접 수정해도 덮어씌워집니다.
내용 개선을 원하면 `raw/` 파일을 수정하거나 issue를 등록해 주세요.

## 이슈 등록

오류 제보, 내용 추가 요청, 삭제 요청은 GitHub Issues를 이용해 주세요.
