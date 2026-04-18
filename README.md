# 윤어게인 LLM 위키

윤어게인(Yoon Again) 운동 관련 인물·단체·사건·주제를 LLM이 체계적으로 정리한 공개 지식 베이스입니다.

## 구조

```
raw/                 # Firestore에서 export된 위키 원시 데이터 (YAML frontmatter + 마크다운)
wiki/
  entity/            # 인물·단체 페이지
  topic/             # 주제·이슈 페이지
  event/             # 이벤트 페이지
  cluster/           # 클러스터(유사 역할 그룹) 페이지
  comparison/        # 비교 분석 페이지
  summary/           # 요약 페이지
  INDEX.md           # 전체 위키 페이지 카탈로그
scripts/
  export_firestore.py  # Firestore wikiPages → raw/ export
  compile.py           # raw/ 데이터로 wiki/ 크로스레퍼런스 컴파일
```

`raw/`에 변경이 감지되면 GitHub Actions가 자동으로 `wiki/`를 업데이트합니다.

## 데이터 흐름

```
yoonagain 앱 (Firestore wikiPages 컬렉션)
  → export_firestore.py → raw/*.md
  → GitHub Actions → compile.py → wiki/**/*.md + INDEX.md
  → yoonagain 앱 RAG Agent (github-reader.ts로 fetch)
```

## 위키 페이지 타입

| 타입 | 예시 | 설명 |
|------|------|------|
| entity | `entity/jeon-han-gil.md` | 개별 인물·단체 |
| topic | `topic/123-martial-law.md` | 주제·이슈 |
| event | `event/gwanghwamun-rally-2024.md` | 특정 이벤트 |
| cluster | `cluster/youtuber-conservative.md` | 유사 역할 그룹 |
| comparison | `comparison/activists-1225.md` | 비교 분석 |
| summary | `summary/yoon-again-overview.md` | 운동 전체 요약 |

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 면책 고지

[DISCLAIMER.md](DISCLAIMER.md)를 확인하세요.
이 위키는 공개된 정보를 바탕으로 작성되며, 특정 정치적 입장을 지지하지 않습니다.
