# NEXUS 설계서

> **버전:** Phase 1 v1.3 | **최종 수정:** 2026-03-19
> **리포지토리:** aihwangso/NEXUS (private) | **브랜치:** main
> **이 문서의 목적:** (1) 사람이 프로젝트 전체를 이해한다 (2) AI가 이 문서만 읽고 즉시 작업을 이어간다

---

## 목차

- [Part 1: NEXUS란 무엇인가](#part-1-nexus란-무엇인가)
- [Part 2: 전체 아키텍처](#part-2-전체-아키텍처)
- [Part 3: Phase 1 v1.0 (구현 완료)](#part-3-phase-1-v10-구현-완료)
- [Part 4: Phase 1 v1.1~v1.3 (Core 확장)](#part-4-phase-1-v11v13-core-확장)
  - [4.6 RAG 엔진 품질 개선 (Phase 1 v1.3)](#46-rag-엔진-품질-개선-phase-1-v13)
- [Part 5: Phase 2 -- Knowledge Graph (미래)](#part-5-phase-2--knowledge-graph-미래)
- [Part 6: Phase 3 -- Proactive Intelligence (미래)](#part-6-phase-3--proactive-intelligence-미래)
- [Part 7: 의사결정 기록](#part-7-의사결정-기록)
- [Part 8: 현재 상태 + 다음 할 일](#part-8-현재-상태--다음-할-일)
- [부록](#부록)

---

## Part 1: NEXUS란 무엇인가

### 1.1 한 문장 정의

**비기술자 버전:**
조직의 문서와 업무 지식을 AI가 이해하고, 질문하면 출처와 함께 정확한 답을 주는 시스템.

**기술자 버전:**
하이브리드 검색(Dense+Sparse) + ONNX 리랭킹 + MCP 기반 도구 호출로 구성된 도메인 특화 RAG 플랫폼. NFD(Nurture-First Development) 아키텍처를 통해 대화 경험이 자동으로 구조화된 지식으로 결정화(Crystallization)된다.

### 1.2 기존 RAG와 본질적 차이

| 구분 | 기존 RAG | NEXUS |
|------|----------|-------|
| **입력** | 문서 | 업무 프로세스 + 도메인 데이터 + 문서 |
| **출력** | 검색 결과 | 도메인 전문가 AI |
| **동작** | "문서 넣으면 검색해줌" | "프로세스+데이터 넣으면 전문가 AI가 만들어짐" |
| **성장** | 문서 추가 시 수동 재인덱싱 | 대화로 자동 성장 (경험이 지식이 됨) |
| **지식** | 정적 문서 | 경험 축적 + 자동 승격 |
| **도메인 확장** | 코드 수정 필요 | Domain Builder로 입력만 교체 |

### 1.3 3-Layer 비전

NEXUS는 3개 레이어로 진화한다.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Proactive Intelligence          [Phase 3 - 미래]   │
│  자동 알림, 다이제스트, 고아 문서 감지                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Knowledge Graph                 [Phase 2 - 미래]   │
│  엔티티 추출, 관계 매핑, 그래프 탐색                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Retrieval Engine                [Phase 1 - 완료]   │
│  하이브리드 검색 + 리랭킹 + 출처 포함 답변                      │
└─────────────────────────────────────────────────────────────┘
```

| 레이어 | 기능 | 구현 상태 |
|--------|------|----------|
| **Layer 1: Retrieval Engine** | 하이브리드 검색 + 리랭킹 + 출처 포함 답변 | **Phase 1 완료** |
| **Layer 2: Knowledge Graph** | 엔티티 추출, 관계 매핑, 그래프 탐색 | **미구현** (Neo4j 예약, 후크 준비) |
| **Layer 3: Proactive Intelligence** | 자동 분석, 알림, 다이제스트 생성 | **미구현** |

### 1.4 서비스 핵심 코어

NEXUS를 서비스로 배포할 때 **두 축이 핵심 코어**이다.

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXUS 서비스 핵심 코어                       │
├──────────────────────────┬──────────────────────────────────┤
│  Domain Builder          │  Docker 인덱싱 파이프라인            │
│  (도메인 생성 엔진)        │  (문서 → 검색 가능 상태)            │
│                          │                                  │
│  process.md + Excel      │  Watchdog → Redis 큐 → Worker    │
│  → 컨설팅 → skill/soul   │  → 파싱 → 청킹 → 임베딩 → Qdrant  │
│  → config → 인덱싱       │                                  │
│                          │  Embedding 서버 (BGE-M3)          │
│  "입력만 넣으면            │  "문서만 넣으면                     │
│   전문가 AI가 만들어짐"    │   검색 가능 상태가 됨"              │
└──────────────────────────┴──────────────────────────────────┘
```

| 핵심 코어 | 역할 | 배포 형태 |
|-----------|------|----------|
| **Domain Builder** | 도메인 정의(프로세스+데이터) → 전문가 AI 생성 | MCP 서버 (로컬/클라우드) |
| **Docker 파이프라인** | 문서 인덱싱 + 벡터 검색 인프라 | Docker Compose → EC2/ECS 이전 가능 |

**설계 근거:**
- Domain Builder는 NEXUS만의 차별점 — "코드 없이 도메인 전문가 AI를 만든다"
- Docker 파이프라인은 모든 도메인이 공유하는 공통 인프라 — 환경 이식성과 스케일링의 기반
- 이 두 축이 동작하면 나머지(OpenClaw, Telegram, MCP 서버)는 교체 가능한 인터페이스에 불과하다

---

## Part 2: 전체 아키텍처

### 2.1 Core-Domain 분리 구조

NEXUS는 **Core**(모든 도메인 공통 엔진)와 **Domain**(도메인별 고유 설정/데이터)으로 분리된다.

```
NEXUS/
├── core/                              <-- 모든 도메인 공통
│   ├── services/
│   │   ├── embedding/                 <-- 임베딩 + 리랭커 서버
│   │   ├── indexing/                  <-- 파서, 청커, 워커, Watchdog
│   │   └── mcp-servers/              <-- 범용 MCP (도메인 무관)
│   │       ├── doc-search/            <-- 하이브리드 문서 검색
│   │       ├── doc-summary/           <-- 문서 요약
│   │       ├── data-analysis/         <-- 스프레드시트 분석
│   │       ├── indexing-admin/        <-- 인덱싱 관리
│   │       ├── domain-search/         <-- [v1.1] JSON 지식 검색
│   │       ├── domain-add/            <-- [v1.1] JSON 지식 추가
│   │       └── domain-export/         <-- [v1.1] JSON -> Excel 내보내기
│   ├── domain-builder/                <-- [v1.1] Domain Builder 엔진
│   │   ├── analyzer.py
│   │   ├── converter.py
│   │   ├── skill_generator.py
│   │   ├── soul_generator.py
│   │   ├── process_refiner.py
│   │   └── crystallizer.py
│   ├── scripts/
│   ├── docker-compose.yml
│   └── nexus.config.yaml
│
├── domains/                           <-- 도메인별 고유
│   └── {domain-name}/
│       ├── process.md                 <-- 업무 프로세스 정의 (입력 + Phase 1 정교화)
│       ├── domain_knowledge.xlsx      <-- 도메인 지식 Excel (입력) [고정 파일명]
│       ├── skill.md                   <-- AI 행동 지침서 (Domain Builder 생성)
│       ├── soul.md                    <-- AI 정체성/원칙 (Domain Builder 생성)
│       ├── config.yaml                <-- 도메인 설정 (Domain Builder 생성)
│       ├── domain_knowledge.json      <-- 구조화된 지식 (생성 + 운영 중 성장)
│       ├── soul_answers.json          <-- soul.md 생성용 답변 (Domain Builder 생성)
│       ├── logs/                      <-- 대화 로그 + 빌드 로그 (운영 데이터)
│       └── exports/                   <-- 내보내기 결과물 (운영 데이터)
└── docs/
```

**참고:** 위는 v1.1 목표 구조이다. 현재(v1.0) 코드는 아직 이 구조로 재구성되기 전 상태이며, `nexus/` 디렉토리 아래 플랫하게 배치되어 있다 (Part 2.5 현재 폴더 트리 참조).

### 2.2 MCP = 레고 블록, Skill md = 조립 설명서

MCP 서버는 범용 도구(레고 블록)이고, Skill md는 그 도구를 어떤 순서로 쓸지 정의하는 조립 설명서이다.

```
MCP (레고 블록):                    Skill md (조립 설명서):
┌──────────────┐                   ┌─────────────────────────────┐
│ doc-search   │                   │ {도메인} Skill:              │
│ doc-summary  │                   │ 1. 접수/파악                 │
│ data-analysis│  <-- 조합 ------  │ 2. domain-search로 기존 지식 │
│ domain-search│                   │ 3. doc-search로 문서 검색    │
│ domain-add   │                   │ 4. 결과 안내                 │
│ domain-export│                   │ 5. 결과 확인                 │
└──────────────┘                   │ 6. domain-add로 지식 저장    │
                                   └─────────────────────────────┘
```

핵심 원칙:
- **MCP는 범용 도구** -- 어떤 도메인에서든 사용 가능
- **Skill md는 도메인별 절차** -- 어떤 MCP를 어떤 순서로 쓸지 정의
- **도메인마다 같은 MCP를 쓰되 Skill md만 다르다**

| 도메인 유형 | 사용 MCP (동일) | Skill md (다름) |
|------------|----------------|----------------|
| CS/트러블슈팅 | doc-search, domain-search, domain-add | 접수→진단→원인분석→조치→해결확인→학습 |
| 영업/상담 | doc-search, domain-search, domain-add | 니즈파악→제안→협상→계약→팔로우업 |
| R&D/자료탐색 | doc-search, domain-search, domain-add | 목표설정→탐색→검증→정제→보고 |

### 2.3 NFD Three-Layer Cognitive Architecture

NFD 논문(arxiv 2603.10808)이 제안한 3계층 인지 아키텍처를 NEXUS에 적용한다.

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Constitutional (soul.md)              │
│  ─────────────────────────────────────────────  │
│  정체성, 원칙, 행동 규칙                          │
│  변동성: 낮음 (거의 안 바뀜)                      │
│  로드 시점: 매 세션 시작                          │
│  변경 주체: Domain Builder 또는 관리자             │
├─────────────────────────────────────────────────┤
│  Layer 2: Skill (skill.md + 구조화된 지식)       │
│  ─────────────────────────────────────────────  │
│  업무 절차, 대응 가이드, MCP 도구 매핑            │
│  변동성: 중간 (Crystallization으로 업데이트)       │
│  로드 시점: 관련 업무 요청 시                     │
│  변경 주체: 자동 승격 또는 관리자                  │
├─────────────────────────────────────────────────┤
│  Layer 3: Experiential (JSON + 대화 로그)        │
│  ─────────────────────────────────────────────  │
│  매일 쌓이는 경험 데이터                          │
│  변동성: 높음 (실시간 축적)                       │
│  Layer 3-A: logs/YYYY-MM-DD.jsonl (원본 로그)    │
│  Layer 3-B: domain_knowledge.json (구조화 지식)  │
└─────────────────────────────────────────────────┘
```

Knowledge Crystallization Cycle (지식 결정화 사이클):

```
    ┌──────────┐
    │  대화     │ <-- 원시 데이터 수집
    └────┬─────┘
         v
    ┌──────────┐
    │  축적     │ <-- 로그로 저장
    └────┬─────┘
         v
    ┌──────────┐
    │  구조화   │ <-- JSON으로 정리
    └────┬─────┘
         v
    ┌──────────┐
    │  검증     │ <-- 사용 통계 추적
    └────┬─────┘
         v
    ┌──────────┐
    │  적용     │ <-- Skill md에 승격
    └──────────┘
         │
         └───────> 다시 대화로 (순환)
```

### 2.4 전체 데이터 흐름

```
[문서 파일] --(Watchdog)--> [Redis 큐] --(Worker)--> [파서 -> 청커 -> 임베딩 서버] --(저장)--> [Qdrant]
                                                                                                 |
[사용자] --> [Telegram/WebChat] --> [OpenClaw + SOUL.md] --> [MCP 서버들] --> [Qdrant + 임베딩 리랭킹]
                                                                                 |
                                                                         [LLM이 답변 생성]
```

### 2.5 현재 폴더 트리 (v1.0 실제 코드 기준)

아래는 현재 `nexus/` 디렉토리의 전체 파일 목록이다 (models, __pycache__ 제외).

```
nexus/
├── .env                                          # 환경변수 (DOCS_PATH, API키 등)
├── .env.example                                  # 환경변수 템플릿
├── .gitignore                                    # Git 제외 규칙
├── docker-compose.yml                            # Docker 오케스트레이션 (qdrant, redis, embedding, worker)
├── nexus.config.yaml                             # 전체 시스템 설정 (LLM, 검색, 인덱싱, RBAC)
│
├── config/
│   ├── openclaw/
│   │   ├── openclaw.yaml                         # OpenClaw 에이전트 설정 (MCP 서버 등록, 모델)
│   │   └── soul.md                               # AI 에이전트 시스템 프롬프트 (인격, 규칙, 도구)
│   └── prometheus/
│       └── prometheus.yml                        # Prometheus 모니터링 설정
│
├── models/
│   ├── bge-m3-onnx/                              # BGE-M3 임베딩 모델 (ONNX, ~1.1GB)
│   │   ├── onnx/
│   │   │   ├── config.json                       # 모델 설정
│   │   │   ├── model.onnx                        # ONNX 모델 본체
│   │   │   ├── model.onnx_data                   # 모델 가중치
│   │   │   ├── sentencepiece.bpe.model            # SentencePiece 토크나이저
│   │   │   ├── tokenizer.json                    # 토크나이저 설정
│   │   │   └── ...                               # 기타 설정 파일
│   │   ├── tokenizer.json                        # 루트 레벨 토크나이저 (폴백)
│   │   └── ...
│   └── qwen3-reranker-0.6b-onnx/                 # Qwen3 리랭커 모델 (ONNX, ~600MB)
│       ├── model.onnx                            # ONNX 모델 본체
│       ├── tokenizer.json                        # 토크나이저 설정
│       ├── config.json                           # 모델 설정
│       ├── vocab.json                            # 어휘 사전
│       ├── merges.txt                            # BPE 병합 규칙
│       └── ...                                   # 기타 설정 파일
│
├── scripts/
│   ├── setup.sh                                  # 원클릭 설치 (.env -> 모델 -> Docker -> Qdrant)
│   ├── download_models.sh                        # HuggingFace에서 ONNX 모델 다운로드
│   ├── init_qdrant.sh                            # Qdrant 컬렉션 + 페이로드 인덱스 초기화
│   └── backup_qdrant.sh                          # Qdrant 스냅샷 백업 (7일 보관, cron용)
│
├── services/
│   ├── embedding/
│   │   ├── server.py                             # FastAPI 임베딩+리랭커 서버 (/embed, /rerank, /health)
│   │   ├── Dockerfile                            # python:3.11-slim 기반, uvicorn 실행
│   │   └── requirements.txt                      # fastapi, onnxruntime, tokenizers, numpy 등
│   │
│   ├── indexing/
│   │   ├── worker.py                             # 인덱싱 워커 (파싱->청킹->임베딩->Qdrant 저장)
│   │   ├── watchdog_service.py                   # 파일시스템 변경 감지 -> Redis 큐 추가
│   │   ├── Dockerfile                            # 인덱싱 서비스 Docker 이미지
│   │   ├── requirements.txt                      # 인덱싱 의존성
│   │   ├── supervisord.conf                      # supervisord 설정 (worker + watchdog)
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                           # 파서 인터페이스 (ParsedPage, ParsedDocument, BaseParser)
│   │   │   ├── factory.py                        # 파일 확장자별 파서 팩토리 (get_parser)
│   │   │   ├── pdf_parser.py                     # DoclingParser: PDF/DOCX/PPTX/HTML (PyMuPDF 폴백)
│   │   │   ├── excel_parser.py                   # ExcelParser: XLSX/XLS/CSV (openpyxl)
│   │   │   └── text_parser.py                    # TextParser: TXT/MD/LOG/JSON/XML/YAML
│   │   ├── chunkers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                           # 청커 인터페이스 (Chunk, BaseChunker)
│   │   │   ├── factory.py                        # 설정별 청커 팩토리 (get_chunker)
│   │   │   └── semantic_chunker.py               # 고정크기 슬라이딩윈도우 + 테이블 분리 청커
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── config_loader.py                  # nexus.config.yaml 로더 (캐싱 싱글턴)
│   │       └── path_utils.py                     # 워크스페이스 매핑, 기밀 판별, 경로 정규화
│   │
│   └── mcp-servers/
│       ├── doc-search/
│       │   ├── server.py                         # 7단계 하이브리드 검색 MCP (search_documents, get_document_info)
│       │   └── requirements.txt                  # MCP 서버 의존성
│       ├── doc-summary/
│       │   └── server.py                         # 문서 요약 MCP (summarize_document, summarize_topic)
│       ├── data-analysis/
│       │   └── server.py                         # Excel/CSV 분석 MCP (analyze_spreadsheet, query_data, compare_values)
│       ├── indexing-admin/
│       │   └── server.py                         # 인덱싱 관리 MCP (index_file, index_folder, get_indexing_status)
│       ├── domain-search/                        # [v1.1] JSON 지식 검색 MCP
│       │   └── server.py
│       ├── domain-add/                           # [v1.1] JSON 지식 추가 MCP
│       │   └── server.py
│       ├── domain-export/                        # [v1.1] JSON -> Excel 내보내기 MCP
│       │   └── server.py
│       └── domain-builder/                       # [v1.1] Domain Builder MCP
│           └── server.py
│
├── test-docs/                                    # 평가용 테스트 문서 (11개)
│   ├── 개발팀/
│   │   ├── 2025년_신제품_개발_로드맵.pptx
│   │   ├── API_서버_설계문서.txt
│   │   ├── 신입사원_온보딩_가이드.docx
│   │   └── 직원현황.xlsx
│   ├── 영업팀/
│   │   ├── 2024년_상반기_매출현황.xlsx
│   │   ├── 2024년_월별_손익.csv
│   │   └── 2024년_하반기_영업전략.txt
│   └── 품질팀/
│       ├── 2024년_3분기_품질관리_보고서.txt
│       ├── 2024년_생산실적.xlsx
│       ├── HACCP_준비_체크리스트.txt
│       └── 제조공정_SOP_A라인.pdf
│
└── tests/
    └── eval/
        ├── run_eval.py                           # 검색 품질 평가 (Recall@K, MRR@K, Hit Rate)
        └── eval_dataset.json                     # 평가 데이터셋 (15개 질의)
```

---

## Part 3: Phase 1 v1.0 (구현 완료)

### 3.1 기술 스택

| 구성 요소 | 기술 | 버전/사양 | 실행 위치 |
|---------|------|---------|---------|
| 임베딩 모델 | BGE-M3 ONNX | Dense 1024d + Sparse | Docker (ONNX CPU) |
| 리랭커 | Qwen3-Reranker-0.6B ONNX | 0.6B params, yes/no logits + softmax | Docker (ONNX CPU) |
| 벡터 DB | Qdrant | 1.13, "documents" 컬렉션 | Docker (6333) |
| 작업 큐 | Redis | 7 Alpine | Docker (6379) |
| 에이전트 | OpenClaw + mcp-bridge | MCP 플러그인 방식 (openclaw-mcp-bridge vendoring) | Windows 네이티브 (18789) |
| 온라인 LLM | GPT-5.4 via Codex | openai-codex/gpt-5.4 | API |
| 오프라인 LLM | Qwen3:4b via Ollama | 4B params | Windows 네이티브 (11434) |
| 임베딩 서버 | FastAPI + ONNX Runtime | uvicorn, workers=1 | Docker (8080) |
| MCP SDK | mcp[cli] | 1.9.2 | 각 MCP 서버 |
| 문서 파싱 | Docling + PyMuPDF 폴백 | - | Docker (worker) |
| 토크나이저 | tiktoken cl100k_base | - | Docker (worker) |
| 컨테이너 | Docker Compose | - | 로컬 |
| 채널 | Telegram + WebChat | 포트 3000 | Windows 네이티브 |

**임베딩 서버 Python 의존성 (버전 고정):**

| 패키지 | 버전 |
|--------|------|
| fastapi | 0.115.6 |
| uvicorn[standard] | 0.34.0 |
| onnxruntime | 1.20.1 |
| tokenizers | 0.21.0 |
| numpy | 1.26.4 |
| huggingface-hub | 0.27.1 |

### 3.2 검색 파이프라인 (7단계)

코드 감사 기준 `doc-search/server.py`에서 확인한 정확한 값.

```
단계 1: 쿼리 임베딩
  BGE-M3 query instruction: "Represent this sentence for searching relevant passages"
  임베딩 서버 POST /embed 호출
  결과: dense vector (1024d) + sparse vector

단계 2: RBAC 필터
  workspace 필터 적용 (Qdrant must 조건)
  include_confidential: 미구현 (Phase 2)

단계 3: Dense 벡터 검색
  Cosine 유사도, SEARCH_LIMIT=20

단계 4: Sparse 벡터 검색
  IDF modifier, SEARCH_LIMIT=20

단계 5: RRF 점수 결합
  DENSE_WEIGHT=0.7, SPARSE_WEIGHT=0.3
  RRF k=60
  공식: score = w * (1 / (k + rank))

단계 6: Qwen3 리랭킹
  임베딩 서버 POST /rerank 호출
  yes/no logits에서 softmax로 점수 계산
  RERANK_TOP_K=10 (상위 10개 반환)

단계 7: 결과 포맷팅
  출처(file_path, file_name) + 텍스트(text) + 점수(score) 반환
```

**검색 파라미터 정리:**

| 파라미터 | 값 | 위치 |
|---------|-----|------|
| Dense 가중치 | 0.7 | doc-search/server.py |
| Sparse 가중치 | 0.3 | doc-search/server.py |
| RRF k 상수 | 60 | doc-search/server.py |
| 검색 후보 수 (SEARCH_LIMIT) | 20 | doc-search/server.py |
| 리랭킹 출력 수 (RERANK_TOP_K) | 10 | doc-search/server.py |
| BGE-M3 max seq length | 512 | embedding/server.py |
| Qwen3 리랭커 max length | 2048 | embedding/server.py |
| 리랭커 max_doc_chars | 1500 | embedding/server.py |

### 3.3 인덱싱 파이프라인

코드 감사 기준 `worker.py`, `semantic_chunker.py` 기반.

```
파일 감지 (Watchdog)
    |
    v
Redis 큐 (nexus:indexing:queue)
    |
    v
SHA-256 해시 체크 (변경 감지, 기존 벡터 삭제 후 재인덱싱)
    |
    v
파싱 (형식별 파서 -- 3.4 참조)
    |
    v
청킹 (SemanticChunker)
  - chunk_size=1536 토큰 (tiktoken cl100k_base)
  - overlap=256 토큰
  - 테이블: 별도 청크로 분리 (잘리지 않음, chunk_type="table")
  - 본문: 슬라이딩 윈도우 (chunk_type="text")
  - chunk_size 이하면 분할 없이 그대로
    |
    v
임베딩 (BGE-M3)
  - 배치: 32개씩 HTTP 호출 (POST /embed)
  - 결과: dense vector (1024d) + sparse vector
    |
    v
Qdrant 저장
  - 컬렉션: "documents"
  - 배치 업서트: 100개 포인트 단위
  - named vectors: dense, sparse
```

**인덱싱 설정 정리:**

| 파라미터 | 값 | 출처 |
|---------|-----|------|
| 청크 크기 | 1536 토큰 | nexus.config.yaml, semantic_chunker.py |
| 청크 겹침 | 256 토큰 | nexus.config.yaml, semantic_chunker.py |
| 토크나이저 | tiktoken cl100k_base | semantic_chunker.py |
| 임베딩 배치 | 32개 | worker.py, nexus.config.yaml |
| Qdrant 업서트 배치 | 100개 | worker.py |
| 디바운스 | 3초(config) / 5초(코드 기본값) | nexus.config.yaml / watchdog_service.py |
| 최대 재시도 | 3회 | worker.py |
| 감시 경로 | /documents | nexus.config.yaml |

**Redis 큐:**

| 큐 | 용도 |
|----|------|
| `nexus:indexing:queue` | 메인 처리 대기 |
| `nexus:indexing:retry` | 재시도 대기 (최대 3회) |
| `nexus:indexing:dead_letter` | 최종 실패 |

**지원 파일 형식 (15종):**

`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.md`, `.log`, `.json`, `.xml`, `.yaml`, `.yml`, `.html`, `.htm`

### 3.4 파서 상세

3개 파서가 팩토리 패턴으로 관리된다 (`parsers/factory.py`).

#### 3.4.1 DoclingParser (`pdf_parser.py`)

| 항목 | 값 |
|------|-----|
| 지원 확장자 | `.pdf`, `.docx`, `.pptx`, `.html`, `.htm` |
| 1차 엔진 | Docling (DocumentConverter -> Markdown 내보내기) |
| 2차 엔진 (폴백) | PyMuPDF (fitz) -- Docling 실패 시 자동 전환 |
| 테이블 추출 | Docling find_tables() 또는 PyMuPDF find_tables() |
| 테이블 형식 | pandas to_markdown (가능 시) 또는 수동 마크다운 변환 |
| 메타데이터 | title, author (PyMuPDF에서 추출) |
| 제한 사항 | Docling 모드에서 페이지 구분 미지원 (전체를 1페이지로 처리) |

#### 3.4.2 ExcelParser (`excel_parser.py`)

| 항목 | 값 |
|------|-----|
| 지원 확장자 | `.xlsx`, `.xls`, `.csv` |
| Excel 엔진 | openpyxl (read_only=True, data_only=True) |
| CSV 인코딩 | utf-8 -> cp949 -> euc-kr -> latin-1 순차 시도 |
| 출력 형식 | 시트별 ParsedPage, 마크다운 테이블 + 전체 텍스트 |
| 시트 처리 | 모든 시트 순회, 빈 시트 건너뜀 |

#### 3.4.3 TextParser (`text_parser.py`)

| 항목 | 값 |
|------|-----|
| 지원 확장자 | `.txt`, `.md`, `.log`, `.json`, `.xml`, `.yaml`, `.yml` |
| 인코딩 | utf-8 -> cp949 -> euc-kr -> latin-1 순차 시도 |
| 처리 | 전체 내용을 하나의 ParsedPage로 반환 |

### 3.5 MCP 서버 7종

코드 감사 기준 정확한 도구명, 파라미터, 의존성.

#### 3.5.1 doc-search (문서 검색)

| 항목 | 값 |
|------|-----|
| 파일 | `services/mcp-servers/doc-search/server.py` |
| 의존성 | qdrant_client, httpx, 임베딩 서버(8080), Qdrant(6333) |

**도구:**

| 도구명 | 파라미터 | 설명 |
|--------|---------|------|
| `search_documents` | `query` (str, 필수), `workspace` (str, 선택), `file_type` (str, 선택), `top_k` (int, 선택) | 7단계 하이브리드 검색 |
| `get_document_info` | `file_path` (str, 필수) | 특정 문서 인덱싱 정보 조회 |

#### 3.5.2 doc-summary (문서 요약)

| 항목 | 값 |
|------|-----|
| 파일 | `services/mcp-servers/doc-summary/server.py` |
| 의존성 | qdrant_client, httpx, 임베딩 서버(8080), Qdrant(6333) |

**도구:**

| 도구명 | 파라미터 | 설명 |
|--------|---------|------|
| `summarize_document` | `file_path` (str, 필수) | 파일의 모든 청크를 chunk_index 순 정렬 후 반환 (LLM이 요약) |
| `summarize_topic` | `topic` (str, 필수), `max_sources` (int, 기본 5) | Dense 검색 후 파일별 그룹핑, 상위 파일 반환 |

#### 3.5.3 data-analysis (데이터 분석)

| 항목 | 값 |
|------|-----|
| 파일 | `services/mcp-servers/data-analysis/server.py` |
| 의존성 | openpyxl (subprocess 내), DOCS_PATH 환경변수 |
| 특이사항 | subprocess로 파일 I/O 분리 (async 이벤트 루프 블로킹 방지) |

**도구:**

| 도구명 | 파라미터 | 설명 |
|--------|---------|------|
| `ping` | 없음 | 테스트용 |
| `analyze_spreadsheet` | `file_name` (str, 필수) | 시트 구조 분석 (컬럼, 행 수, 미리보기) |
| `query_data` | `file_name` (str), `sheet_name` (str), `column` (str), `operation` (str: list/sum/avg/max/min/count/filter), `filter_value` (str, 선택) | 집계/필터 |
| `compare_values` | `file_name` (str), `column` (str), `value1_label` (str), `value2_label` (str) | 두 행 비교 (차이, 변화율) |

#### 3.5.4 indexing-admin (인덱싱 관리)

| 항목 | 값 |
|------|-----|
| 파일 | `services/mcp-servers/indexing-admin/server.py` |
| 의존성 | httpx, redis, worker.py (subprocess) |
| 특이사항 | subprocess로 Python 스크립트 인라인 실행 (f-string 동적 생성) |

**도구:**

| 도구명 | 파라미터 | 설명 |
|--------|---------|------|
| `index_file` | `file_path` (str, 필수) | 단일 파일 수동 인덱싱 (subprocess) |
| `index_folder` | `folder_path` (str, 필수) | 폴더 전체 인덱싱 (timeout=600초) |
| `get_indexing_status` | 없음 | Qdrant 벡터 수, 파일별 통계, Redis 큐 상태, 임베딩 서버 헬스 |

#### 3.5.5~3.5.7 domain-skills (v1.1에서 삭제됨)

> **v1.1 변경:** domain-skills MCP 서버들(nse-cs, food-manufacturing, engineering-cs)은 하드코딩 데이터 기반이었으며, v1.1에서 삭제되었다.
> 대체: 범용 Core MCP(domain-search, domain-add, domain-export) + 도메인별 skill.md로 전환.
> 상세: Part 4.1 Domain Builder, Part 4.4 기존 코드 정리 계획 참조.

#### MCP 도구 호출 방식

OpenClaw 에이전트가 openclaw-mcp-bridge 플러그인을 통해 MCP 도구를 네이티브 도구로 직접 호출한다. CLI 명령어 불필요.

에이전트가 `mcp` 도구를 통해 라우팅:
```
mcp(action="call", server="domain-search", tool="search_knowledge", args={"domain_name": "도메인명", "keyword": "키워드"})
```

### 3.6 임베딩 서버

`services/embedding/server.py` 기반.

**엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/embed` | 텍스트 -> dense+sparse 벡터 (배치 지원) |
| POST | `/rerank` | 쿼리-문서 쌍 리랭킹 (yes/no logits + softmax) |
| GET | `/health` | 헬스체크 (모델 로드 상태) |

**ONNX 설정:**

| 파라미터 | 값 |
|---------|-----|
| Provider | CPUExecutionProvider |
| graph_optimization_level | ORT_ENABLE_ALL |
| inter_op_num_threads | 4 |
| intra_op_num_threads | 4 |

**임베딩 처리:**

| 항목 | 값 |
|------|-----|
| Dense 벡터 | mean pooling + L2 normalize, 1024d |
| Sparse 벡터 | token weight 기반 (hidden state L2 norm), 특수토큰(CLS/SEP/PAD) 제외 |
| MAX_SEQ_LENGTH | 512 |
| MAX_BATCH_SIZE | 32 |

**리랭커 OOM 방지 전략:**

| 전략 | 설명 |
|------|------|
| 단건 처리 | 문서 1개씩 개별 추론 (배치 X) |
| gc.collect() | 매 추론 후 가비지 컬렉션 실행 |
| max_doc_chars | 1500자로 문서 길이 제한 |
| RERANKER_MAX_LENGTH | 2048 토큰 |

**리랭킹 점수 계산:**
- Qwen3 리랭커 출력에서 "yes"/"no" 토큰의 logits 추출
- softmax(yes_logit, no_logit)에서 yes 확률을 점수로 사용
- 폴백: 일반 cross-encoder 방식도 지원

### 3.7 Qdrant 스키마

`scripts/init_qdrant.sh` + `worker.py` 기반.

**컬렉션: "documents"**

| 설정 | 값 |
|------|-----|
| Dense 벡터 | "dense", 1024 차원, Cosine, on_disk |
| Sparse 벡터 | "sparse", IDF modifier |
| indexing_threshold | 20000 |
| on_disk_payload | true |

**페이로드 인덱스 (8개):**

| 인덱스 | 타입 | 필드명 |
|--------|------|--------|
| Keyword | keyword | workspace |
| Keyword | keyword | confidential |
| Keyword | keyword | file_type |
| Keyword | keyword | file_hash |
| Keyword | keyword | file_path |
| Keyword | keyword | file_name |
| Keyword | keyword | language |
| Datetime | datetime | modified_at |
| Datetime | datetime | indexed_at |

**페이로드 필드 (17개, worker.py 기반):**

| 필드 | 타입 | 설명 |
|------|------|------|
| `text` | str | 청크 본문 |
| `file_path` | str | 파일 전체 경로 |
| `file_name` | str | 파일명 |
| `file_type` | str | 확장자 (.pdf 등) |
| `file_hash` | str | SHA-256 해시 |
| `workspace` | str | 워크스페이스 (영업팀, 개발팀 등) |
| `confidential` | bool | 기밀 여부 |
| `modified_at` | str | 파일 수정 시각 |
| `indexed_at` | str | 인덱싱 시각 |
| `language` | str | 언어 (ko/en/mixed) |
| `chunk_index` | int | 청크 순서 번호 |
| `chunk_type` | str | text 또는 table |
| `page_or_sheet` | int/str | 페이지 번호 또는 시트명 |
| `total_chunks` | int | 파일의 전체 청크 수 |
| `entities` | list | 엔티티 목록 (Phase 2 예약, 빈 리스트) |
| `doc_title` | str | 문서 제목 (메타데이터) |
| `doc_author` | str | 문서 작성자 (메타데이터) |

### 3.8 OpenClaw + Telegram 연동

#### soul.md 내용 요약

Domain Builder Phase 4가 자동 생성하는 soul.md 구조:

- **정체성:** 에이전트 이름, 역할 설명, 현재 도메인 (process.md에서 추출)
- **핵심 규칙:**
  - 출처 필수 명시
  - memory/workspace 파일 직접 검색 금지 (MCP 도구 사용)
  - 도메인별 금지사항, 안전 경고 (질문으로 수집)
  - 모르는 질문 대응 방식 (질문으로 수집)
- **도구 사용 규칙:**
  - 공통 도구: domain-search, domain-add, domain-export, doc-search, doc-summary, data-analysis, indexing-admin
  - 출처 충돌 시 우선순위 (질문으로 수집)
  - 검색 결과 없을 때 행동 (질문으로 수집)
- **답변 스타일:** 언어, 말투 (질문으로 수집)

※ 도메인 특화 내용(업무 프로세스, 절차)은 skill.md에 정의. soul.md는 정체성과 규칙만 담당.

#### MCP 연동 방식

openclaw-mcp-bridge (MIT 라이선스)를 vendoring하여 OpenClaw 플러그인으로 직접 통합.
에이전트가 MCP 도구를 네이티브 도구로 인식하고 직접 호출한다. CLI 명령어 불필요.

vendoring 위치: `nexus/vendor/openclaw-mcp-bridge/`
실행 위치: `~/.openclaw/extensions/openclaw-mcp-bridge/`

**커스텀 수정 사항:**
- `transport-stdio.js`: MCP 서버 startup 대기 로직 변경. 원본은 stdout 첫 데이터를 기다리는데, FastMCP는 stdin 요청 전까지 stdout에 아무것도 보내지 않아 교착 상태 발생. 프로세스 시작 후 1초 안정화 확인 방식으로 변경.

설정 위치: `openclaw.json` > `plugins.entries.openclaw-mcp-bridge.config.servers`

```json
{
  "plugins": {
    "entries": {
      "openclaw-mcp-bridge": {
        "config": {
          "mode": "router",
          "servers": {
            "domain-builder": {
              "transport": "stdio",
              "command": "python",
              "args": ["nexus/services/mcp-servers/domain-builder/server.py"],
              "env": { "DOMAINS_BASE": "domains", "BUILDER_PATH": "nexus/core/domain-builder" }
            }
          }
        }
      }
    }
  }
}
```

#### 채널 구성

| 채널 | 상태 | 포트 |
|------|------|------|
| Telegram | 활성 | - (webhook) |
| WebChat | 활성 | 3000 |

### 3.9 포트 매핑 테이블

코드 감사 기준 정확한 값.

| 서비스 | 포트 | 실행 위치 | 상태 |
|--------|------|---------|------|
| Qdrant | 6333 | Docker | **운영 중** |
| Redis | 6379 | Docker | **운영 중** |
| 임베딩 서버 | 8080 | Docker | **운영 중** |
| Ollama | 11434 | Windows 네이티브 | **운영 중** |
| OpenClaw Gateway | 18789 | Windows 네이티브 | **운영 중** |
| WebChat | 3000 | Windows 네이티브 | **운영 중** |
| Open WebUI | 8081 | Docker (profile: webui) | **비활성** |
| Neo4j HTTP | 7474 | Docker (profile: phase2) | **Phase 2 예약** |
| Neo4j Bolt | 7687 | Docker (profile: phase2) | **Phase 2 예약** |
| Grafana | 3001 | Docker (profile: monitoring) | **비활성** |

### 3.10 평가 결과

`tests/eval/run_eval.py` + `eval_dataset.json` (15개 질의) 기반.

**리랭킹 OFF/ON 비교:**

| 지표 | 리랭킹 OFF | 리랭킹 ON | 목표 |
|------|-----------|----------|------|
| Recall@5 | ~80-93% | ~93-100% | >= 80% |
| MRR@5 | ~0.637-0.65 | ~0.85-1.000 | >= 0.65 |
| Answer Hit Rate | ~73-93% | ~87-100% | - |
| 평균 응답 시간 | ~0.3-1.35s | ~1.5-19.29s | <= 5s (온라인) |

**파일 형식별 결과:**

| 형식 | Recall | 비고 |
|------|--------|------|
| TXT | ~100% | 최적 |
| PDF | ~100% | Docling/PyMuPDF 모두 양호 |
| DOCX | ~100% | Docling 처리 |
| PPTX | ~100% | Docling 처리 |
| XLSX/CSV | ~75% | 테이블 데이터의 벡터 표현 한계 |

---

## Part 4: Phase 1 v1.1~v1.3 (Core 확장)

### 4.1 Domain Builder

#### 4.1.1 개요 + 핵심 가치

**한 문장:** process.md + 데이터 Excel + 문서 폴더 경로를 입력하면, 해당 도메인에 최적화된 AI 전문가 시스템을 자동 생성하는 NEXUS Core 기능.

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXUS Domain Builder                      │
│                                                             │
│   입력:                          출력:                       │
│   ┌──────────────┐              ┌──────────────────────┐    │
│   │ process.md   │──┐           │ 정교화된 process.md  │    │
│   │ (업무 절차)   │  │           │ skill.md (기술 가이드)│    │
│   ├──────────────┤  ├──[빌드]-->│ soul.md (정체성)     │    │
│   │ Excel        │  │           │ config.yaml (설정)   │    │
│   │ (도메인 지식) │  │           │ domain_knowledge.json│    │
│   ├──────────────┤  │           │ 인덱싱된 문서 DB     │    │
│   │ 문서 폴더 경로│──┘           └──────────────────────┘    │
│   └──────────────┘                                          │
│              --> 도메인 전문가 AI 완성                        │
└─────────────────────────────────────────────────────────────┘
```

#### 4.1.2 NFD 이론적 기반

- **논문:** "Nurture-First Agent Development: Building Domain-Expert AI Agents Through Conversational Knowledge Crystallization"
- **출처:** arxiv 2603.10808 (2026-03-11)
- **핵심 주장:** 도메인 전문가 AI는 사전 학습이 아닌, 운영 중 대화를 통해 지식을 결정화(Crystallization)하는 방식으로 만들어야 한다.

**NFD 핵심 원칙:**
```
최소 시작 --> 대화로 성장 --> 경험이 지식이 됨
```

- **최소 시작:** process.md 초안 + Excel 하나면 시작 가능
- **대화로 성장:** 실제 업무 대화가 곧 학습 데이터
- **경험이 지식이 됨:** 성공/실패 경험이 구조화되어 Skill로 승격

#### 4.1.3 입력 형식

```
domains/{도메인명}/
├── process.md              <-- 업무 절차 초안 (불완전해도 됨) [고정 파일명]
└── domain_knowledge.xlsx   <-- 도메인 지식 (어떤 구조든) [고정 파일명]

+ 문서 경로 안내 (원본 위치 그대로, 옮기지 않음)
```

**"{도메인명} 도메인 스킬 생성해줘"** → `domains/{도메인명}/process.md` + `domains/{도메인명}/domain_knowledge.xlsx`를 읽어서 빌드. 결과물도 같은 폴더에 저장.

**process.md 초안 구조:**

```markdown
# 도메인명

## 역할
이 도메인에서 AI가 수행할 역할

## 업무 프로세스
전체 업무 흐름 개괄

## 각 단계 상세
업무 프로세스의 각 단계 상세

## 규칙
특수한 규칙이나 예외 사항
```

불완전해도 된다. Domain Builder Phase 1이 프로세스 특성에 맞는 프레임워크를 선택하여 질문으로 구체화한다 (4.1.4 Phase 1 참조).

**process.md 작성 가이드:**

| 섹션 | 목적 | 작성 예시 | Domain Builder 활용 |
|------|------|----------|-------------------|
| **역할** | AI가 이 도메인에서 무엇을 하는지 한 문장 정의 | "고객 문의를 접수하고 원인을 진단하여 조치를 안내" | soul.md의 정체성 생성에 사용 |
| **업무 프로세스** | 전체 업무 흐름을 단계별로 개괄 | "접수→분류→처리→확인→기록" | skill.md의 프로세스 골격 생성 |
| **각 단계 상세** | 각 단계에서 어떤 데이터를 보고, 어떤 판단을 하고, 어떤 행동을 하는지 | "2단계: 유형에 따라 분기 → A이면 X경로, B이면 Y경로" | skill.md의 각 단계별 MCP 도구 매핑에 사용 |
| **규칙** | 도메인 특화 규칙, 안전 경고, 에스컬레이션 기준 등 | "출처 필수 명시", "2회 미해결 시 전문가 연결" | soul.md 규칙 섹션 + skill.md 규칙 섹션에 반영 |

**참고:** 불완전해도 된다. Domain Builder Phase 1이 프레임워크 기반 질문으로 구체화한다.

**이전 process.md 구조에서 제거된 항목:**

| 제거 항목 | 이유 | 대체 방식 |
|----------|------|----------|
| 지식 추출 필드 | domain_knowledge.xlsx 컬럼이 곧 지식 필드 | Phase 2에서 Excel 분석 시 자동 파악 |
| 결과 판단 기준 | 도메인마다 다르므로 대화형 수집이 적합 | Phase 1 소크라테스식 질문으로 수집 |

**로그 저장 정책:**

| 대상 | 저장 시점 | 저장 위치 |
|------|----------|----------|
| Domain Builder (관리자) | 빌드 완료 또는 실패 시 | 빌드 로그 |
| 도메인 운영 (사용자) | 1건의 업무 단위 완료 시 | `domains/{도메인}/logs/YYYY-MM-DD.jsonl` |

"1건의 업무 단위"는 process.md의 업무 프로세스가 정의한다. skill.md에 "마지막 단계 완료 시 로그 저장" 지침이 자동 포함된다.

**domain_knowledge.xlsx 변환 규칙:**
- 시트 1개 -> JSON 배열 1개
- 행 1개 -> JSON 객체 1개
- 헤더행 -> JSON 키
- 한글 헤더 -> 영문 키로 매핑 (에러코드 -> error_code)
- 메타데이터 자동 부여 (id, source, created_at, usage_stats)

#### 4.1.4 실행 흐름 6단계

```
Phase 1          Phase 2          Phase 3
process.md  -->  Excel 분석  -->  skill.md
정교화            JSON 변환         자동 생성
    |                |                |
    v                v                v
Phase 4          Phase 5          Phase 6
soul.md     -->  config.yaml -->  문서
정교화            자동 생성         인덱싱
    |                |                |
    v                v                v
              도메인 완성!
```

**Phase 1: process.md 정교화 (프레임워크 기반)**

process.md의 프로세스 특성을 분석하여 7개 프레임워크 중 최적의 것을 선택하고, 해당 프레임워크의 관점으로 대화형 컨설팅을 통해 정교화한다. 질문은 하드코딩이 아니라, LLM이 프레임워크의 방법론과 질문 방향을 참고하여 도메인 맥락에 맞게 컨설턴트처럼 자유롭게 생성한다.

**MCP 도구:** `analyze_process`, `save_refined_process`
**LLM 레퍼런스:** `nexus/core/domain-builder/frameworks.md`

**실행 흐름 3단계:**

1단계 — 프레임워크 선택 + 승인:
- `analyze_process(domain_name)` 호출 → frameworks.md + process.md를 읽어서 프레임워크 선택 프롬프트 반환
- LLM이 7개 프레임워크 중 선택 + 선택 이유를 사용자에게 설명
- display_name도 이 시점에 수집
- 사용자 승인 후 다음 단계

2단계 — 대화형 컨설팅:
- LLM이 선택된 프레임워크의 방법론과 질문 방향(frameworks.md)을 참고하여 대화형 컨설팅 수행
- 도구 호출 없음 — LLM이 대화로 직접 수행
- process.md에 이미 있는 내용은 확인 질문 ("~라고 적혀있는데, 구체적으로...")
- process.md에 없는 내용은 탐색 질문 ("~에 대한 내용이 없는데, 어떻게...")
- 한 번에 2~3개씩 나눠서 자연스러운 대화체로 질문
- **완료 판단 기준:** scar_guide.md의 skill.md 범용 골격 + 선택된 프레임워크의 프로세스 구조 가이드를 충족할 수 있는 정보가 process.md에 모두 있는가

3단계 — 저장:
- `save_refined_process(domain_name, content)` 호출 → 정교화된 process.md 저장

**7개 프레임워크 카탈로그 요약:** (상세는 `nexus/core/domain-builder/frameworks.md` 참조)

| ID | 프레임워크 | 프로세스 특성 | 방법론 기반 | 밸류체인 예시 |
|----|-----------|-------------|-----------|-------------|
| A | Diagnostic-Branching | 판단/분기 중심 | Decision Tree + IDEF0(ICOM) + 5 Whys | CS/AS, 품질검사, IT헬프데스크 |
| B | Exploration-Discovery | 탐색/발견 중심 | OODA Loop + Design Thinking + MECE | R&D, 시장조사, 특허조사 |
| C | Sequential-Procedural | 순차/절차 중심 | SIPOC + VSM + BPMN | 제조공정, 온보딩, 회계결산 |
| D | Relational-Persuasive | 관계/설득 중심 | JTBD + RACI + Cynefin | B2B영업, 계약협상, CRM |
| E | Analytical-Decision | 분석/의사결정 중심 | DMAIC + MECE + Decision Matrix | 재무분석, 전략기획, 리스크평가 |
| F | Creative-Design | 창조/설계 중심 | Design Thinking + PDCA + Cynefin | 제품설계, UX, 캠페인기획 |
| G | Monitor-Respond | 모니터링/대응 중심 | OODA Loop + IDEF0 + PDCA | 시스템운영, 보안관제, 재고관리 |

**프레임워크 선택 방식:** LLM이 process.md를 읽고 직접 판단한다 (키워드 기반 아님). primary + secondary(선택)를 반환하며, 복합 프로세스는 두 프레임워크의 질문 방향을 결합한다.

**Phase 2: Excel 분석 + JSON 변환**
1. Excel 시트/컬럼 구조 분석
2. 사용자에게 구조 확인 ("이 구조로 JSON을 생성합니까?")
3. domain_knowledge.json 생성 (각 행 -> JSON 객체, 메타데이터 자동 부여)
4. 완료 보고

**Phase 3: skill.md 생성 (SCAR 원칙 + 프레임워크 가이드)**

Phase 1에서 정교화된 process.md를 AI 에이전트가 실행 가능한 행동 지침서(skill.md)로 변환한다.
변환은 LLM이 수행한다 (기계적 파싱이 아님). 고정된 템플릿에 내용을 채우는 것이 아니라, SCAR 작성 원칙과 프레임워크별 프로세스 구조 가이드를 참고하여 도메인에 맞게 자유롭게 작성한다.

**MCP 도구:** `prepare_skill_materials`, `save_skill`
**LLM 레퍼런스:** `nexus/core/domain-builder/scar_guide.md`, `nexus/core/domain-builder/frameworks.md`

**SCAR 4원칙** (작성 규칙이지 구조 템플릿이 아님):

| 원칙 | 차용 원천 | 역할 |
|------|---------|------|
| **S**OP | SOP-Agent + Grab SOP | 산문이 아닌 절차적 지시로 변환 |
| **C**onstraint | AWS Strands SOP (RFC 2119) | MUST/SHOULD/MAY로 제약 명시 |
| **A**gent Principles | Block 3원칙 | 결정적(도구 호출) vs 비결정적(추론) 분리 |
| **R**unbook | SRE Runbook | 런북 스타일 체크리스트 |

**skill.md 범용 골격** (상세는 `scar_guide.md` 참조):
```
# {도메인 표시명} Skill
## 역할
## 도구
## 프로세스           ← 내부 구조는 프레임워크가 결정 (frameworks.md 참조)
## 지식 추출 필드
## 결과 판단 기준
## 규칙
## 완료 시
```

프로세스 섹션의 내부 구조는 고정이 아니다. 선택된 프레임워크의 프로세스 구조 가이드(frameworks.md)를 따른다:
- Diagnostic-Branching → 분기 테이블 + 복귀 루프
- Exploration-Discovery → 탐색 사이클 + 종료 조건
- Sequential-Procedural → 순차 체크리스트 + 완료 확인
- Relational-Persuasive → 상태 기반 대화 + 반응별 전략
- Analytical-Decision → 평가 매트릭스 + 결정 기준
- Creative-Design → 반복 사이클 + 품질 게이트
- Monitor-Respond → 임계값 테이블 + 심각도별 대응

**실행 흐름:**
1. `prepare_skill_materials(domain_name, display_name, framework_id)` 호출 → scar_guide.md + frameworks.md + 정교화된 process.md + domain_knowledge.json 필드 목록 + MCP 도구 목록을 조합하여 변환 프롬프트 반환
2. LLM이 프롬프트를 읽고 skill.md를 작성
3. `save_skill(domain_name, content)` 호출 → skill.md 저장

**작성 가이드 (업계 베스트 프랙티스 기반):**
- 런북 스타일 (피곤한 새벽 3시 당직자에게 건네는 체크리스트)
- Third-Person Imperative ("~한다"로 작성)
- 결정적 단계(도구 호출)와 비결정적 단계(추론) 명확히 분리
- 각 단계에 검증 조건(pass/fail) 포함
- 500줄 이하, 5000단어 이하
- Progressive Disclosure (상세는 process.md 참조로 안내)

**Phase 4: soul.md 생성**

입력:
- process.md (역할, 규칙 섹션)
- soul_answers.json (대화형 질문 답변 — 에이전트가 파일로 저장)

생성 로직:
1. process.md에서 "역할" 섹션 → 정체성에 반영
2. process.md에서 "규칙" 섹션 → 핵심 규칙에 반영
3. soul_answers.json에서 이름, 말투, 금지사항 등 → 각 섹션에 반영
4. 공통 MCP 도구 목록 → 도구 사용 규칙에 자동 포함 (domain-builder 제외)

출력 구조:
```
# {에이전트명} — {역할}
## 정체성
## 핵심 규칙
## 도구 사용 규칙
## 답변 스타일
```

답변 수집 방식:
- get_soul_questions(domain_name) → 질문 목록 반환
- 에이전트가 사용자 답변 수집 → domains/{도메인}/soul_answers.json에 파일 저장
- generate_soul(domain_name, display_name) → 파일에서 답변 읽어 soul.md 생성
- ※ 한글 파라미터 인코딩 문제 방지를 위해 파라미터가 아닌 파일로 전달

**Phase 5: config.yaml 자동 생성**

자동 생성되는 config.yaml 구조:

```yaml
domain:
  name: {도메인명}
  display_name: "{표시 이름}"
  description: "{도메인 설명}"

documents:
  paths:
    - "{문서 폴더 경로}"
  workspace: "{워크스페이스 ID}"
  extensions: [".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".csv", ".txt"]

knowledge:
  json_path: "./domain_knowledge.json"
  log_path: "./logs/"
  export_path: "./exports/"

crystallization:
  auto_log: true
  auto_extract: true
  promotion:
    min_usage: 5
    min_success_rate: 0.8
    auto_promote: true
  schedule:
    realtime: ["log", "extract", "usage_stats"]
    weekly: ["promote", "report"]
    monthly: ["export"]

domain_builder:
  enabled: false          # 고객 배포 시 기본 비활성
  admin_key_required: true
```

**Phase 6: 문서 인덱싱**
- config.yaml의 paths에서 파일 수집
- 지원 확장자 필터링
- 기존 인덱싱 파이프라인 실행 (파서 -> 청커 -> 임베딩 -> Qdrant)

#### 4.1.5 배포 제어

Domain Builder는 고객에게 비활성화된다. 코드는 포함되지만 실행 불가.

| 환경 | enabled | 설명 |
|------|---------|------|
| 개발자 작업 환경 | `true` | Domain Builder 사용 가능 |
| 고객 배포 | `false` | 코드는 있지만 실행 불가 |

비활성화 이유: 코드를 빼면 서브모듈 분기가 복잡해지므로, 단일 코드베이스 유지 + 비활성화.

### 4.2 Knowledge Crystallization Cycle

#### 4.2.1 Layer 3 관리 체계

**Layer 3-A: 대화 로그**

저장 위치: `domains/{도메인}/logs/YYYY-MM-DD.jsonl` (append only)

자동 분류 6카테고리 (NFD 논문 기반):

| 카테고리 | 설명 | 예시 |
|---------|------|------|
| `operational` | 일반 업무 처리 기록 | "문의 접수 → 조치 완료" |
| `reasoning` | AI의 추론 과정 | "증상 A → 원인 B → 조치 C 추론" |
| `pattern` | 반복 패턴 관찰 | "이번 달 유사 건 3건째" |
| `error` | 틀린 답변/수정된 답변 | "처음 X로 안내 → 실제는 Y" |
| `context` | 환경/맥락 정보 | "특정 고객사는 항상 Z 환경을 사용" |
| `insight` | 인사이트 조각 | "이 문제는 특정 조건에서만 발생" |

로그 1건 구조:

```json
{
  "id": "log-2026-03-16-001",
  "timestamp": "2026-03-16T14:30:00",
  "session_id": "telegram-{user_id}-{session}",
  "user": "사용자명",
  "category": "operational",
  "conversation": [
    { "role": "user", "text": "문의 내용" },
    { "role": "nexus", "text": "조치 안내" },
    { "role": "user", "text": "결과 응답" }
  ],
  "extracted": {
    "필드1": "값1",
    "필드2": "값2"
  },
  "crystallization_status": "pending"
}
```

`extracted` 필드는 고정이 아니다. domain_knowledge.xlsx의 컬럼(= domain_knowledge.json의 키)이 곧 추출 필드다.

**Layer 3-B: 경험 JSON (구조화)**

저장 위치: `domains/{도메인}/domain_knowledge.json`

```json
{
  "_meta": {
    "domain": "{도메인명}",
    "schema_version": 1,
    "last_crystallized": "2026-03-16T18:00:00",
    "stats": {
      "total_items": 52,
      "from_excel": 38,
      "from_conversation": 12,
      "from_suggestion": 2
    }
  },
  "items": [
    {
      "id": "K-20260316-xxxxxxxx",
      "source": "excel_import",
      "created_at": "2026-03-16T10:00:00",
      "created_by": "domain_builder",
      "필드1": "값1 (domain_knowledge.xlsx 컬럼 기반)",
      "필드2": "값2",
      "usage_stats": {
        "suggested": 8,
        "resolved": 6,
        "failed": 2,
        "success_rate": 0.75
      }
    }
  ]
}
```

**참고:** `items`의 필드 구조는 도메인마다 다르다. domain_knowledge.xlsx의 컬럼이 곧 JSON 필드가 된다. `id`, `source`, `created_at`, `created_by`, `usage_stats`는 메타데이터로 자동 부여된다.

#### 4.2.2 지식 추가 경로 2가지

**경로 1: 대화 중 자연 발생**

```
사용자: "이런 문제가 있는데요"
NEXUS:  "이렇게 조치해보세요"
사용자: "해결됐어"
사용자: "이거 반영해줘"

--> 대화 범위: 업무 건 시작부터 "반영해줘"까지
--> NEXUS가 대화 맥락에서 지식을 추출
```

**경로 2: 담당자 직접 추가**

```
사용자: "지난주 건, 이런 원인이었어. 추가해줘"

--> 이 메시지에서 지식을 추출
```

#### 4.2.3 추가 프로세스 5단계 (범용)

두 경로 모두 동일한 프로세스를 거친다:

```
Step 1: 추출
  대화 맥락에서 저장할 내용 추출
  (추출할 필드는 domain_knowledge.xlsx 컬럼 = domain_knowledge.json 키)

Step 2: 검증
  사용자에게 구조화된 내용 확인
  "다음 내용을 저장하겠습니다: [내용] 맞습니까?"

Step 3: 중복 확인
  기존 JSON에 유사 항목 검색
  "유사 항목이 있습니다. 새로 추가합니까, 기존 항목을 수정합니까?"

Step 4: 승인
  사용자 최종 확인

Step 5: 저장
  domain-add MCP 호출 -> JSON에 추가
  "K-20260316-xxxxxxxx으로 저장 완료"
```

#### 4.2.4 자동 검증 (LLM 판단, 하드코딩 아님)

조치 제안 후 사용자 응답을 **LLM이 자동 분류**한다:

| 분류 | 의미 | 판별 예시 |
|------|------|---------|
| `resolved` | 해결됨 | "해결됐어", "됐다", "고마워" |
| `failed` | 안 됨 | "안 돼", "똑같아", "다른 방법?" |
| `ongoing` | 진행 중 | "해볼게", "잠깐만", "내일 해봄" |
| `unrelated` | 다른 주제 | "다른 건데", "그건 됐고" |

핵심: 분류 기준은 Phase 1 질문으로 수집한 결과 판단 기준이 정의한다. **하드코딩 아님.**

usage_stats 자동 업데이트:
```
조치 제안 --> 사용자 응답 --> LLM 분류
                              |
                              ├── resolved --> success +1
                              ├── failed   --> fail +1
                              ├── ongoing  --> (대기, 나중에 재분류)
                              └── unrelated --> (무시)

success_rate = success / (success + fail)
```

#### 4.2.5 다중 사용자 지원

- 누구든 "반영해줘" 가능 -> 저장
- 같은 증상, 다른 원인 -> 둘 다 저장 (충돌 아님, 후보 추가)
- 검색 시 usage_stats 기반 신뢰도 순으로 표시

#### 4.2.6 Layer 3 -> Layer 2 자동 승격

**승격 조건 (모두 충족):**

| 조건 | 기준 |
|------|------|
| 사용 횟수 | usage_stats.suggested >= 5 |
| 성공률 | usage_stats.success_rate >= 0.8 |
| 모순 없음 | 기존 skill.md와 충돌 없음 |

**승격 프로세스:**
1. 조건 충족 확인
2. 자동 반영 (승인 기다리지 않음) -- skill.md에 새 항목 추가
3. 주간 리포트에 포함 (참고용)
4. 문제 있으면 사후 조치 ("이거 빼줘" -> 제거)

**사람의 역할 변화:**
- 기존 방식: 사전 승인자 (매번 확인)
- NFD 방식: 사후 모니터링 (주간 리포트)

#### 4.2.7 Crystallization 주기

| 주기 | 작업 | 자동/수동 |
|------|------|----------|
| **실시간** | 로그 저장 | 자동 |
| **실시간** | 필드 추출 | 자동 |
| **실시간** | usage_stats 업데이트 | 자동 |
| **주간** | 승격 조건 충족 확인 -> skill.md 반영 | 자동 |
| **주간** | 리포트 생성 (승격 N건, 신규 N건, 성공률 변화) | 자동 |
| **월간** | JSON -> Excel 내보내기 (오프라인 검토용) | 자동 |

주간 리포트 예시:

```
═══════════════════════════════════════
  NEXUS {도메인명} 주간 리포트
  2026-03-10 ~ 2026-03-16
═══════════════════════════════════════

  총 대화: 47건
  신규 지식: 3건
  승격: 1건
    - K-20260310-xxx "조치 방법 A" --> skill.md 반영

  성공률 변화:
    전체: 78% --> 82% (+4%)

  주의 항목:
    - K-20260312-xxx "조치 방법 B" 성공률 33% (3회)
      --> 조치 방법 재검토 필요

═══════════════════════════════════════
```

### 4.3 Core-Domain 분리 + 멀티도메인 배포

#### 4.3.1 Git Submodule 구조

```
nexus-core (공유 엔진)
    ^ submodule
    |
┌───┴────┐────────┐────────┐
nexus-hr  nexus-mfg  nexus-cs  ...  (도메인별 리포)
(인사팀)   (제조팀)    (고객지원)
```

Git 리포지토리 구성:
```
aihwangso/nexus-core           <-- Core 리포 (공통)
aihwangso/nexus-{도메인A}       <-- 도메인 리포 (core를 submodule로 참조)
aihwangso/nexus-{도메인B}       <-- 또 다른 도메인 리포
```

**nexus-core 리포 구조:**

```
nexus-core/
├── services/
│   ├── embedding/              # 임베딩 + 리랭커 서버
│   ├── indexing/               # 워커, 와치독, 파서, 청커
│   └── mcp-servers/
│       ├── doc-search/         # 문서 검색 MCP
│       ├── doc-summary/        # 문서 요약 MCP
│       ├── data-analysis/      # 데이터 분석 MCP
│       └── indexing-admin/     # 인덱싱 관리 MCP
├── scripts/
├── docker-compose.core.yml     # 인프라 서비스 정의
├── config/prometheus/
└── README.md
```

**도메인 리포 구조:**

```
nexus-{domain}/
├── nexus-core/                 # <-- git submodule (nexus-core@태그)
├── domains/{domain-name}/      # 도메인 폴더 (Domain Builder 입출력)
│   ├── process.md              # 업무 프로세스 (입력, Domain Builder로 정교화)
│   ├── domain_knowledge.xlsx   # 도메인 지식 Excel (입력)
│   ├── skill.md                # AI 행동 지침서 (생성됨)
│   ├── soul.md                 # AI 정체성/원칙 (생성됨)
│   ├── config.yaml             # 도메인 설정 (생성됨)
│   ├── domain_knowledge.json   # 구조화된 지식 (생성 + 운영 중 성장)
│   ├── soul_answers.json       # soul.md 생성용 답변 (생성됨)
│   ├── logs/                   # 대화 로그 + 빌드 로그 (운영 데이터)
│   └── exports/                # 내보내기 결과물 (운영 데이터)
├── .env                        # 환경변수
├── docker-compose.yml          # core compose를 include + domain 오버라이드
├── models/                     # 임베딩/리랭커 모델 (git 미추적)
└── .gitignore
```

#### 4.3.2 분리 기준

| 구분 | 위치 | 포함 내용 |
|------|------|----------|
| **Core** (nexus-core) | 변경 빈도 낮음 | embedding, parsers, chunkers, worker, watchdog, doc-search, doc-summary, data-analysis, indexing-admin, domain-search, domain-add, domain-export, domain-builder, scripts, Dockerfile |
| **Domain** (nexus-{name}) | 도메인마다 다름 | process.md, domain_knowledge.xlsx (입력) + skill.md, soul.md, config.yaml, domain_knowledge.json (생성/운영) |
| **Models** (도메인 로컬) | 용량 큼, git 미추적 | bge-m3-onnx/, qwen3-reranker-0.6b-onnx/ |

#### 4.3.3 배포자 vs 고객 관점

```
관리자 (배포자):
  ┌─────────────────────────────────────────────┐
  │  Core (Domain Builder 포함) + 모든 도메인     │
  │  nexus/ --- Domain Builder 엔진 포함          │
  │  domains/{도메인A}/                           │
  │  domains/{도메인B}/                           │
  └─────────────────────────────────────────────┘

고객:
  ┌─────────────────────────────────────────────┐
  │  Core (Domain Builder 비활성) + 자기 도메인만  │
  │  nexus/ --- Domain Builder 비활성화            │
  │  domains/{자기 도메인}/ --- 자기 도메인만       │
  └─────────────────────────────────────────────┘
```

#### 4.3.4 버전 관리

```
Core 버전 관리:
  방식: Git 태그 (v1.0.0, v1.1.0, v2.0.0)
  각 도메인 리포의 submodule이 특정 태그를 가리킴
  예시:
    nexus-{도메인A} --> core@v1.0.0
    nexus-{도메인B} --> core@v1.1.0

Domain 버전 관리:
  Git으로 관리: process.md, skill.md, soul.md, config.yaml, data/
  Git 밖 (운영 데이터): domain_knowledge.json, logs/, exports/
  --> 코드 업데이트해도 축적된 지식은 건드리지 않음
```

#### 4.3.5 docker-compose.yml 통합 패턴

```yaml
# nexus-{domain}/docker-compose.yml
include:
  - path: ./nexus-core/docker-compose.core.yml

services:
  indexing-worker:
    volumes:
      - ./domain/data:/documents:ro
      - ./config.yaml:/app/nexus.config.yaml:ro

  # 도메인별 MCP 서버는 없음
  # Core MCP (domain-search, domain-add, domain-export) + 도메인별 skill.md
```

#### 4.3.6 새 도메인 추가 절차

1. `domains/{도메인명}/` 폴더 생성
2. `process.md` 초안 작성 (불완전해도 됨)
3. `domain_knowledge.xlsx` 배치 (도메인 지식 Excel)
4. 텔레그램에서 "{도메인명} 도메인 스킬 생성해줘" 실행
5. Domain Builder가 Phase 1~6 자동 수행
6. 완료 후 도메인 전문가 AI 사용 가능

#### 4.3.7 Core 업데이트 전파

```bash
# 일반 업데이트
cd nexus-core && git pull origin main && cd ..
docker-compose build --no-cache embedding indexing-worker
docker-compose up -d embedding indexing-worker

# Breaking Change (태그 고정)
cd nexus-core && git fetch --tags && git checkout v3.1.0 && cd ..
git add nexus-core && git commit -m "core를 v3.1.0으로 업데이트"
```

### 4.4 기존 코드 정리 계획

| 작업 | 상세 | 상태 |
|------|------|------|
| food-manufacturing, engineering-cs 삭제 | 하드코딩 데이터 기반 도메인 MCP | **완료** |
| nse-cs 하드코딩 제거 | Domain Builder로 재구축 | **완료** |
| domain-search MCP | JSON 지식 검색 (Core, DOMAINS_BASE 패턴) | **완료** |
| domain-add MCP | JSON 지식 추가 + 대화 로그 저장 (Core) | **완료** |
| domain-export MCP | JSON → Excel 내보내기 (Core) | **완료** |
| domain-builder MCP | Domain Builder 6 Phase 도구 (Core) | **완료** (Phase 1,3 재설계 완료) |
| domains/ 구조 적용 | Core MCP + domains/{도메인}/ 분리 | **완료** |
| nexus.config.yaml 정리 | 테스트 workspace_map 제거 | **완료** |

### 4.5 적용 사례: NSE CS (농심엔지니어링 X-Ray 검사장비 AS)

> Domain Builder 첫 적용 대상으로, 아래는 실제 빌드 결과 기반 사례이다.

**입력:**

| 입력 | 파일 | 설명 |
|------|------|------|
| process.md | 7단계 AS 프로세스 (접수→분류→진단→원인분석→조치안내→해결확인→지식등록) | 초안 작성 후 Domain Builder Phase 1에서 정교화 |
| domain_knowledge.xlsx | 7개 시트, 53건 에러코드 트러블슈팅 가이드 | Excel → JSON 자동 변환 |
| 문서 폴더 | nse_cs/ (1,257개 파일) | 매뉴얼, 도면, 사양서 |

**빌드 결과:**
- 프레임워크 선택: **Diagnostic-Branching** (판단/분기 중심 — CS/트러블슈팅에 적합)
- domain_knowledge.json: 53건 생성
- skill.md: 7단계 프로세스 + MCP 도구 매핑 + SCAR 구조
- soul.md: 에이전트 정체성 + 규칙 + 도구 사용 규칙
- config.yaml: 도메인 설정

**운영 시나리오:**

Day 1 (즉시 사용 가능):
```
사용자: "E2001 에러 나왔는데"

NEXUS:
  1. domain-search로 E2001 검색 → 기존 사례 찾기
  2. doc-search로 매뉴얼 검색 → 관련 문서 찾기
  3. 이중 출처 답변 제공
```

3개월 후 (자동 성장 — Crystallization):
```
특정 패턴의 사례 5건 이상 축적, 성공률 80% 이상
→ 자동 승격: skill.md에 새 조치 방법 반영
→ 이후 유사 문의 시 경험 기반 답변 제공
```

### 4.6 RAG 엔진 품질 개선 (Phase 1 v1.3)

#### 4.6.1 개요

현재 RAG 파이프라인의 한계를 단계적으로 개선한다. 모든 개선은 **nexus/ 엔진 레벨**에서 이루어지며, 도메인 무관하게 모든 도메인이 자동으로 혜택을 받는다.

**핵심 원칙:**
- 엔진이 능력을 제공하고, 도메인(skill.md)이 사용 방법을 결정한다
- 추가 GPU 불필요 (CPU 동작 가능한 기술만 채택)
- Tier 0부터 순서대로 — 입력 품질이 나쁘면 이후 단계 효과도 반감

**Tier 분류:**

| Tier | 이름 | 핵심 질문 | 개선 기술 |
|------|------|----------|----------|
| 0 | 입력 품질 | 문서를 제대로 읽었는가? | Docling + PaddleOCR, LLM Excel 구조 추론 |
| 1 | 가공 품질 | 읽은 텍스트를 잘 가공했는가? | Parent-Child Chunking, Contextual Chunking |
| 2 | 검색 품질 | 잘 찾았는가? | HyDE, Reranker 업그레이드 |
| 3 | 고급 기능 | 더 깊이 이해하는가? | GraphRAG, ColPali (보류) |

#### 4.6.2 Tier 0: 입력 품질 (파싱 개선)

**문제:** 현재 파서가 두 유형의 문서를 제대로 처리하지 못한다.

##### 스캔 PDF → Docling + PaddleOCR

| 항목 | 현재 | 개선 후 |
|------|------|---------|
| 스캔 PDF 처리 | Docling 텍스트 추출 (이미지인 경우 빈 결과) | Docling OCR 백엔드로 PaddleOCR 연결 |
| OCR 엔진 | 없음 | PaddleOCR (한국어 CER 0.11) |
| 속도 | - | CPU 12.7 FPS (이미지당 ~80ms) |
| 모델 크기 | - | ~15MB (경량) |
| 라이선스 | - | Apache 2.0 |

**OCR 엔진 비교 (한국어 기준):**

| 엔진 | 한국어 CER | CPU 속도 | VRAM/RAM | 라이선스 |
|------|-----------|---------|---------|---------|
| **PaddleOCR** ✓ | 0.11 | 12.7 FPS | 1.2GB | Apache 2.0 |
| EasyOCR | 0.11 | 3.1~4.2 FPS | 2.8~3.4GB | Apache 2.0 |
| Tesseract | 0.31 | 8.2 FPS | 300MB RAM | Apache 2.0 |
| Surya | 우수 | 느림 (CPU) | 9GB+ | GPL |

**채택 근거:** 동급 정확도(CER 0.11) 대비 3배 빠름 + 경량 + 허용적 라이선스. CER 0.11의 오류는 LLM이 문맥으로 보간 가능.

**구현 방향:**
- **페이지별 분류 (text / scanned / mixed)** — 문서 단위가 아닌 페이지 단위 판단
- 복수 신호 조합으로 분류 (PyMuPDF 활용):
  - 이미지 커버리지: 페이지 면적 대비 이미지 90%+ → scanned (가장 신뢰도 높음)
  - GlyphLessFont: 이전 OCR 텍스트 레이어 감지 → 재OCR 필요 여부 판단
  - 텍스트 블록 수: text block 0개 + image block 존재 → scanned
- scanned/mixed 페이지만 PaddleOCR 실행, text 페이지는 기존 추출 유지
- Docling의 OCR 백엔드 설정에 PaddleOCR 연결
- nexus.config.yaml에 OCR 설정 추가

##### 깨진 Excel → LLM 구조 추론

| 항목 | 현재 | 개선 후 |
|------|------|---------|
| 병합 셀 | 무시 (빈 셀로 처리) | 병합 감지 → LLM에 구조 추론 요청 |
| 컬럼명 위치 | 첫 행 고정 | 상위 N행 스캔 → 헤더 자동 탐지 |
| 결측/비정형 | 그대로 마크다운 변환 | LLM이 데이터 구조 해석 후 정규화 |

**구현 방향:**
- `excel_parser.py`에 비정형 감지 단계 추가 — 다음 신호 중 하나라도 감지되면 비정형:
  - `ws.merged_cells.ranges`가 비어있지 않음 (병합 셀)
  - 1행이 비어있거나 상위 N행에 데이터가 아닌 제목/메모 존재 (헤더 위치 불명)
  - 데이터 중간에 빈 행 존재 (하나의 시트에 여러 테이블)
  - 같은 열에 숫자/텍스트 타입 혼재
- 비정형 감지 시 LLM에 시트 샘플(상위 20행) 전달 → 구조 해석 결과 수신
- 정형이면 기존 파서 로직 유지 (불필요한 LLM 호출 방지)
- SpreadsheetLLM 논문의 핵심 아이디어 차용 (전체 구현이 아닌 개념 활용)

#### 4.6.3 Tier 1: 가공 품질 (청킹 개선)

**문제:** 현재 고정 1536토큰 슬라이딩 윈도우로 모든 문서를 동일하게 자른다. 문맥이 잘리고, 검색 정밀도가 떨어진다.

##### Parent-Child Chunking

```
현재:  문서 → [1536토큰 청크] [1536토큰 청크] [1536토큰 청크] ...
             (검색 단위 = 반환 단위)

개선 후:
  문서 → [Parent: 큰 청크 (문맥 보존)]
           ├── [Child: 작은 청크 (검색용)]
           ├── [Child: 작은 청크 (검색용)]
           └── [Child: 작은 청크 (검색용)]
         검색은 Child로, 반환은 Parent로
```

| 항목 | 설계 |
|------|------|
| Parent 크기 | 2048~3072 토큰 (문맥 충분히 보존) |
| Child 크기 | 256~512 토큰 (검색 정밀도 향상) |
| 매핑 | Child → Parent ID 참조 (Qdrant payload에 parent_id 저장) |
| 검색 흐름 | Child로 검색 → parent_id로 Parent 조회 → Parent 텍스트 반환 |

**구현 방향:**
- `semantic_chunker.py` 확장 → Parent/Child 이중 청크 생성
- Qdrant 스키마: child 포인트에 `parent_id` 페이로드 추가
- `doc-search/server.py`: 검색 결과에서 parent_id 역참조 로직
- nexus.config.yaml에 Parent/Child 크기 설정 추가

##### Contextual Chunking (LLM 메타데이터 주입)

```
현재:  청크: "Step 3: 센서 교체 후 캘리브레이션 실행"
       → 검색 시 "캘리브레이션"만 매칭

개선 후:
  청크: "Step 3: 센서 교체 후 캘리브레이션 실행"
  + 컨텍스트: "X-Ray 검사장비 E2001 에러 조치 절차 중 3단계.
              센서 교체 작업 후 수행하는 보정 과정."
       → 검색 시 "E2001", "센서", "보정" 모두 매칭
```

| 항목 | 설계 |
|------|------|
| 방식 | 각 청크에 LLM으로 컨텍스트 설명 생성 → 메타데이터로 저장 |
| 임베딩 | 원본 텍스트 + 컨텍스트를 합쳐서 임베딩 |
| LLM 비용 | 인덱싱 시 1회만 (검색 시에는 추가 호출 없음) |
| 출처 | Anthropic "Contextual Retrieval" 제안 (2024) |

**구현 방향:**
- `worker.py` 인덱싱 파이프라인에 컨텍스트 생성 단계 추가 (청킹 후, 임베딩 전)
- 배치 처리: 청크 N개를 묶어 LLM 호출 (비용/속도 최적화)
- nexus.config.yaml에 contextual_chunking 설정 (on/off, LLM 모델, 배치 크기)

#### 4.6.4 Tier 2: 검색 품질

##### HyDE (Hypothetical Document Embeddings)

```
현재:
  사용자 질문 "E2001 해결 방법" → 질문 임베딩 → 문서 검색
  (질문과 문서의 어휘가 다르면 검색 품질 저하)

개선 후:
  사용자 질문 "E2001 해결 방법"
    → LLM이 가상 답변 생성: "E2001 에러는 X-Ray 센서 캘리브레이션 오류로..."
    → 가상 답변 임베딩 → 문서 검색
  (답변 형태의 임베딩이 문서와 더 유사 → 검색 품질 향상)
```

| 항목 | 설계 |
|------|------|
| 방식 | 쿼리 → LLM 가상 답변 생성 → 가상 답변 임베딩으로 검색 |
| 효과 | 쿼리-문서 어휘 갭 해소 (질문 형태 ≠ 문서 형태 문제 해결) |
| 비용 | 검색 시마다 LLM 1회 호출 (지연 +1~2초) |
| 폴백 | LLM 장애 시 기존 쿼리 임베딩으로 폴백 |

**구현 방향:**
- `doc-search/server.py` 검색 단계 1 전에 HyDE 단계 추가
- nexus.config.yaml에 HyDE 설정 (on/off, LLM 모델)
- 온라인(GPT) / 오프라인(Ollama) LLM 자동 라우팅 적용

##### Reranker 업그레이드

| 항목 | 현재 | 후보 |
|------|------|------|
| 모델 | Qwen3-Reranker-0.6B ONNX | bge-reranker-v2-m3 또는 mxbai-rerank-v2 |
| 크기 | 0.6B | ~560M (bge-v2-m3) |
| 성능 | 기본 수준 | 오픈소스 최상위 (다국어 리랭킹 SOTA) |
| 조건 | ONNX 필수, CPU 실행 가능 | ONNX 변환 가능 여부 확인 필요 |

**채택 시점:** Tier 0~1 구현 후 리랭커 교체 효과 측정. ONNX 변환이 가능한 모델 중 선택.

**구현 방향:**
- `embedding/server.py`의 리랭커 모듈만 교체 (인터페이스 동일)
- 기존 Qwen3 리랭커 대비 A/B 테스트
- nexus.config.yaml에 리랭커 모델 설정 추가

#### 4.6.5 Tier 3: 고급 기능 (보류)

현 단계에서는 채택하지 않으나, Tier 0~2 완료 후 검토한다.

| 기술 | 설명 | 보류 이유 |
|------|------|----------|
| GraphRAG (Microsoft) | 엔티티 그래프 기반 멀티홉 추론 | Phase 2 Knowledge Graph와 통합 검토 |
| LightRAG | 경량 그래프 RAG, CPU 동작 가능 | Phase 2에서 Neo4j 대안으로 비교 |
| ColPali | 페이지 이미지 → 패치 임베딩, OCR 불필요 | GPU 8GB+ 필요 (하드웨어 제약) |

#### 4.6.6 Agentic RAG 설계 결정

**선택지:**

| 옵션 | 방식 | 장점 | 단점 |
|------|------|------|------|
| A | 엔진 레벨에 Self-RAG 통합 | 모든 도메인 자동 적용 | 도메인마다 판단 기준이 다름 |
| **B** ✓ | skill.md(에이전트 레이어)에서 처리 | 도메인별 맞춤 판단 | 도메인마다 설정 필요 |

**Option B 채택 근거:**
- 의료 도메인: "검색 결과 신뢰도 90% 미만이면 무조건 에스컬레이션" (엄격)
- FAQ 도메인: "비슷한 결과라도 일단 제공, 부족하면 추가 질문" (유연)
- → 검색 판단 기준이 도메인마다 본질적으로 다르다
- → 엔진은 능력만 제공, 판단은 skill.md가 — NEXUS 설계 원칙과 일치

**Phase 1~5 파이프라인 수정:** 불필요 (현재 skill.md에 이미 부분 구현됨)

**소폭 보강 계획:**

scar_guide.md에 **"Retrieval Decision"** 섹션 추가:

| 단계 | 설명 |
|------|------|
| Pre-retrieval | 검색이 필요한 질문인가? (인사/잡담 vs 지식 필요 질문 구분) |
| Post-retrieval | 검색 결과가 충분한가? (결과 수, 관련성 판단 기준) |
| Retry | 결과 부족 시 키워드 변경/범위 확대/축소 전략 |
| Fallback | 재시도 후에도 부족하면 에스컬레이션 or 웹 검색 제안 |

frameworks.md에 **프레임워크별 검색 패턴** 추가:

| 프레임워크 | 검색 전략 |
|-----------|----------|
| Diagnostic-Branching | 고유 식별자 → 정확 매칭 우선, 없으면 증상 키워드 조합 |
| Exploration-Discovery | 넓은 키워드 → 점진적 좁히기 (탐색적 검색) |
| Sequential-Procedural | 절차/단계명으로 검색, 순서 맥락 유지 |
| Analytical-Decision | 다중 소스 비교 검색, 수치/기준 중심 |
| Compliance-Audit | 규정/기준 정확 매칭, 조항 번호 검색 |
| Knowledge-Transfer | 용어/개념 검색, 관련 사례 확장 |
| Creative-Advisory | 유사 사례 광범위 검색, 영감 중심 |

#### 4.6.7 구현 로드맵

```
Tier 0 ──→ Tier 1 ──→ Tier 2
(파싱)     (청킹)     (검색)
  |           |          |
  └── 독립 ──┘          │
                         └── Tier 0~1 효과 확인 후
```

| 순서 | 작업 | 의존 | 변경 파일 |
|------|------|------|----------|
| 1 | PaddleOCR 연동 | 없음 | pdf_parser.py, nexus.config.yaml, Dockerfile |
| 2 | Excel LLM 구조 추론 | 없음 | excel_parser.py, nexus.config.yaml |
| 3 | Parent-Child Chunking | 없음 | semantic_chunker.py, worker.py, doc-search/server.py, init_qdrant.sh |
| 4 | Contextual Chunking | 3번 완료 | worker.py, nexus.config.yaml |
| 5 | HyDE | 없음 | doc-search/server.py, nexus.config.yaml |
| 6 | Reranker 업그레이드 | Tier 0~1 효과 측정 후 | embedding/server.py, nexus.config.yaml |
| 7 | scar_guide.md 보강 | 없음 | scar_guide.md |
| 8 | frameworks.md 보강 | 없음 | frameworks.md |

**작업 1~2 (Tier 0)과 3 (Tier 1)은 병렬 가능. 4는 3 완료 후. Tier 2는 0~1 효과 확인 후 진행.**
**작업 7~8 (Agentic 보강)은 Tier와 무관하게 즉시 가능.**

---

## Part 5: Phase 2 -- Knowledge Graph (미래)

### 5.1 개요

Layer 2를 구현하여 벡터 검색에 그래프 탐색을 결합한다.

| 항목 | 기술 |
|------|------|
| 그래프 DB | Neo4j (docker-compose.yml에 이미 정의, profile: phase2) |
| 엔티티 추출 | GLiNER-ko (사람, 조직, 제품, 개념) |
| 관계 매핑 | 엔티티 간 관계 자동 추출 |
| 검색 방식 | 하이브리드: 벡터 검색 + 그래프 순회 |
| 웹 UI | Open WebUI (docker-compose.yml에 정의, profile: webui, 포트 8081) |

### 5.2 준비 상태

| 준비 항목 | 상태 | 위치 |
|----------|------|------|
| Neo4j 서비스 정의 | 완료 (profile: phase2) | docker-compose.yml |
| 포트 예약 | 7474 (HTTP), 7687 (Bolt) | docker-compose.yml |
| KG 엔티티 후크 | 주석 처리 상태 | worker.py |
| entities 페이로드 슬롯 | 빈 리스트로 확보 | worker.py |
| NEO4J_PASSWORD 환경변수 | 정의 완료 | .env.example |

### 5.3 검토 사항: OpenViking 통합

**OpenViking** (github.com/volcengine/OpenViking) — ByteDance의 오픈소스 컨텍스트 DB. 2026년 3월 출시.

**현재 판단:** Phase 2에서 검토. Phase 1에서는 현재 Qdrant 기반 검색 유지.

**검토 시점 조건 (하나 이상 충족 시):**
- 인덱싱 문서 5,000개 이상 → L0/L1/L2 계층 로딩 필요
- 토큰 비용 월 $200 초과 → 온디맨드 로딩으로 절약 필요
- "반영해줘" 사용률 저조 → 자동 메모리 capture 필요
- OpenViking v1.0 안정화 + 커뮤니티 형성

**전환 시 변경 범위:**
- 교체: doc-search MCP, worker.py, 임베딩 서버, Qdrant → OpenViking
- 유지: Domain Builder, Crystallization, domain-search/add/export, skill.md/soul.md, 전체 도메인 구조

**참고:** OpenViking은 검색 엔진 교체이지 NEXUS 아키텍처 변경이 아님. 도입 시 git clone(submodule)으로 소스 확보 권장 (프로젝트 중단 리스크 대비).

---

## Part 6: Phase 3 -- Proactive Intelligence (미래)

### 6.1 개요

Layer 3를 구현하여 AI가 능동적으로 정보를 제공한다.

| 기능 | 설명 |
|------|------|
| 자동 알림 | 새 문서 분석 결과, 트렌드 변화 감지 시 알림 |
| 주간 다이제스트 | 지식 변화 요약 자동 생성 |
| 고아 문서 감지 | 인덱싱되었으나 한 번도 검색되지 않은 문서 식별 |
| 배포 | K8s 기반 운영 배포 |

---

## Part 7: 의사결정 기록

왜 이 기술을 선택했는지, 코드 감사 + 설계서 감사 기반.

### 7.1 BGE-M3 선택 이유

- 한국어+영어 다국어 임베딩에서 최고 수준 성능
- Dense (1024d) + Sparse 동시 출력으로 하이브리드 검색 단일 모델로 가능
- ONNX 변환 지원 -> CPU에서 실행 가능 (GPU 불필요)

### 7.2 Qwen3-Reranker-0.6B (BGE ONNX 미제공 -> Qwen3)

- 원래 설계: BGE-reranker-v2-m3
- **문제:** BGE 리랭커가 ONNX 변환을 공식 지원하지 않음
- **대안:** Qwen3-Reranker-0.6B ONNX 선택
  - zhiqing/Qwen3-Reranker-0.6B-ONNX로 사전 변환 제공
  - 0.6B 파라미터로 CPU에서도 실행 가능
  - yes/no logits + softmax 방식으로 리랭킹 점수 계산

### 7.3 OpenClaw + MCP 연동 (mcp-bridge)

- OpenClaw은 Telegram/WebChat 연동이 편리한 에이전트 프레임워크
- **문제:** MCP를 네이티브로 지원하지 않음
- **v1.0~v1.1 시도:** mcporter CLI 사용 → Windows 한글 인코딩 깨짐, PowerShell 정책 차단, 에이전트 도구 미인식 등 근본적 한계
- **v1.2 해결:** openclaw-mcp-bridge (MIT) vendoring → 에이전트가 MCP 도구를 네이티브로 인식/호출
- **포크 안 한 이유:** OpenClaw 하루 수십 커밋, upstream 추적 비현실적. NEXUS 핵심 가치는 Domain Builder + Crystallization이지 에이전트 프레임워크가 아님
- **mcp-bridge 직접 npm 의존 안 한 이유:** Stars 5, 생성 11일 — vendoring하여 우리가 유지보수
- **커스텀 수정:** transport-stdio.js의 startup deadlock 해결 (FastMCP 호환)

### 7.4 GPT-5.4 via Codex (로컬 LLM 타임아웃)

- 온라인 LLM: GPT-5.4 via Codex (원래 GPT-4o에서 업그레이드)
- 오프라인 LLM: Qwen3:4b via Ollama (원래 Qwen3:8b -> 하드웨어 제약으로 축소)
- LLM 라우팅: auto 모드 -- 기밀 문서는 강제 오프라인, API 장애 시 폴백

### 7.5 Docker + Windows 네이티브 혼합 (Ollama GPU)

- Docker: Qdrant, Redis, 임베딩 서버, 인덱싱 워커
- Windows 네이티브: Ollama (GPU 직접 접근 필요), OpenClaw (Telegram 연동)
- 이유: Docker 내에서 GPU 접근이 복잡하므로, Ollama는 Windows에서 직접 실행

### 7.6 subprocess로 data-analysis (async 블로킹)

- data-analysis MCP에서 openpyxl로 Excel을 읽을 때 동기 I/O 발생
- MCP 서버는 async 기반이므로 동기 I/O가 이벤트 루프를 블로킹
- **해결:** subprocess로 파일 읽기를 분리하여 블로킹 방지

### 7.7 리랭커 OOM 해결 (단건 처리 + gc)

- Qwen3 리랭커를 배치로 처리하면 CPU 메모리 부족 (OOM)
- **해결:**
  1. 문서 1개씩 개별 추론 (배치 사용 안 함)
  2. 매 추론 후 `gc.collect()` 실행
  3. `max_doc_chars=1500`으로 문서 길이 제한

### 7.8 NFD 채택 이유

- 기존 RAG의 한계: 문서를 넣으면 검색만 가능. 경험이 축적되지 않음.
- NFD 논문(arxiv 2603.10808)이 제안한 Knowledge Crystallization으로:
  - 대화 경험이 자동으로 구조화된 지식이 됨
  - 사용 통계 기반으로 신뢰도 검증 가능
  - 검증된 지식이 자동으로 Skill에 승격
- Domain Builder와 결합하여 "입력만 바꾸면 어떤 도메인이든 전문가 AI 생성" 달성

### 7.9 Sparse 벡터 구현 방식

- 설계 원안: BGE-M3 lexical_weights (BM25 유사)
- 실제 구현: hidden state L2 norm 근사 (token weight 기반)
- 이유: FlagEmbedding 라이브러리 대신 ONNX Runtime 직접 사용으로, lexical_weights API 미지원
- 영향: 정확도 차이 가능 (향후 개선 대상)

### 7.10 mcporter → mcp-bridge 전환

- v1.0~v1.1에서 mcporter CLI 사용하여 MCP 서버 호출
- **문제:** Windows 한글 인코딩 깨짐, PowerShell 실행 정책 차단, SOUL.md에 CLI 명령어 하드코딩 필수, 에이전트가 도구를 네이티브로 인식 불가
- **검토한 옵션:**
  - OpenClaw 포크 → 하루 수십 커밋, upstream 추적 비현실적 → 기각
  - openclaw-mcp-bridge 직접 사용 → Stars 5, 생성 11일, 안정성 미검증 → 기각
  - openclaw-mcp-bridge vendoring → 핵심 ~350줄, MIT 라이선스, 우리가 유지보수 → **채택**
- **효과:** 에이전트가 MCP 도구를 네이티브로 인식, 한글 인코딩 문제 해결, SOUL.md에서 CLI 명령어 제거 가능

### 7.11 PaddleOCR 채택 (Docling OCR 백엔드)

- 스캔 PDF 문서(이미지 기반)의 텍스트 추출 필요
- **비교:** PaddleOCR vs EasyOCR vs Tesseract vs Surya (한국어 CER, CPU 속도, VRAM, 라이선스)
- **선택:** PaddleOCR
  - 한국어 CER 0.11 (EasyOCR과 동급, Tesseract 0.31보다 3배 우수)
  - CPU 12.7 FPS (EasyOCR 대비 3배 빠름)
  - 모델 ~15MB (경량)
  - Apache 2.0 라이선스
- CER 0.11의 오류는 LLM이 문맥으로 보간 가능 → 충분한 정확도

### 7.12 Agentic RAG — Option B (skill.md 레이어)

- 검색 판단 지능(Self-RAG, CRAG 등)을 어디에 배치할지 결정 필요
- **Option A:** 엔진 레벨에 통합 → 모든 도메인 동일 기준 적용
- **Option B:** skill.md(에이전트 레이어)에서 처리 → 도메인별 맞춤 판단
- **선택:** Option B
  - 의료=엄격, FAQ=유연 등 도메인마다 판단 기준이 본질적으로 다름
  - "엔진은 능력 제공, skill.md가 사용 방법 결정" — NEXUS 설계 원칙과 일치
  - Phase 1~5 파이프라인 대규모 수정 불필요
  - scar_guide.md + frameworks.md 소폭 보강으로 충분

---

## Part 8: 현재 상태 + 다음 할 일

> **이 섹션은 다음 AI 세션이 작업을 이어받을 때 반드시 읽어야 한다.**

### 8.1 현재 상태 스냅샷

**v1.0 구현 완료:**

| 항목 | 상태 |
|------|------|
| 임베딩 서버 (BGE-M3 + Qwen3 리랭커) | 완료, Docker 운영 중 |
| 인덱싱 파이프라인 (파서 3종 + 청커 + 워커 + 와치독) | 완료, Docker 운영 중 |
| Qdrant 벡터 DB ("documents" 컬렉션) | 완료, Docker 운영 중 |
| Redis 작업 큐 | 완료, Docker 운영 중 |
| MCP 서버 4종 (doc-search, doc-summary, data-analysis, indexing-admin) | 완료 |
| OpenClaw + Telegram 연동 | 완료, Windows 네이티브 |
| 평가 프레임워크 (15개 질의, Recall/MRR/Hit Rate) | 완료 |
| 설치/백업 스크립트 | 완료 |

**v1.1 구현 완료:**

| 항목 | 상태 |
|------|------|
| Core-Domain 분리 구조 (nexus/ + domains/) | 완료 |
| domain-search MCP (JSON 지식 검색, DOMAINS_BASE 패턴) | 완료 |
| domain-add MCP (JSON 지식 추가 + 대화 로그 저장) | 완료 |
| domain-export MCP (JSON → Excel 내보내기) | 완료 |
| domain-builder MCP (6 Phase 도구) | 완료 (Phase 1, 3 재설계 완료) |
| Domain Builder 엔진 (process_refiner, analyzer, converter, skill_generator, soul_generator, config_generator) | 완료 (Phase 1, 3 재설계 완료) |
| Knowledge Crystallization 엔진 (crystallizer, promoter, reporter, log_manager, scheduler) | 완료 |
| soul.md 파일 기반 답변 전달 (한글 파라미터 우회) | 완료 |
| NSE CS 도메인 빌드 테스트 (Phase 1~6 완주) | 완료 |
| 하드코딩 도메인 MCP (nse-cs, food-manufacturing, engineering-cs) 삭제 | 완료 |

**v1.2 설계 완료, 구현 필요:**

| 항목 | 설계 상태 | 구현 상태 |
|------|---------|----------|
| Phase 1: 7개 프레임워크 카탈로그 기반 정교화 | 설계 완료 (이 문서 4.1.4) | **코드 완료**, 테스트 필요 |
| Phase 3: SCAR Framework 기반 skill.md 변환 | 설계 완료 (이 문서 4.1.4) | **코드 완료**, 테스트 필요 |
| process_refiner.py 재설계 (프레임워크 선택 + 동적 질문) | 설계 완료 | **완료** |
| skill_generator.py 재설계 (LLM 변환 + SCAR 원칙) | 설계 완료 | **완료** |
| frameworks.md 생성 (7개 프레임워크 LLM 레퍼런스) | 설계 완료 (이 문서 부록) | **완료** |
| scar_guide.md 생성 (SCAR 작성 원칙 LLM 레퍼런스) | 설계 완료 (이 문서 부록) | **완료** |
| openclaw-mcp-bridge vendoring (mcporter 대체) | 설계 완료 (이 문서 7.10) | **완료** |

**v1.3 설계 완료, 구현 전:**

| 항목 | 설계 상태 | 구현 상태 |
|------|---------|----------|
| Tier 0: Docling + PaddleOCR (스캔 PDF OCR) | 설계 완료 (이 문서 4.6.2) | ✅ 구현+검증+리팩토링 완료 — 4신호 분류 + PaddleOCR + config 연동 (DPI/lang/임계값 전부 nexus.config.yaml에서 로드, 하드코딩 제거) |
| Tier 0: Excel LLM 구조 추론 (깨진 Excel) | 설계 완료 (이 문서 4.6.2) | ✅ 구현+검증+리팩토링 완료 — LLM 구조추론 + config 연동 (sample_rows/scan_depth/sanity_threshold/LLM params) + 프롬프트 보강 + 인코딩 리스트 단일 출처화 |
| Tier 1: Parent-Child Chunking | 설계 완료 (이 문서 4.6.3) | ✅ 구현+검증 완료 — ParentChildChunker, worker 분리 저장, doc-search Parent 역참조. config 연동 (parent_size/child_size/overlap) |
| Tier 1: Contextual Chunking | 설계 완료 (이 문서 4.6.3) | ✅ 구현+검증 완료 — Parent 텍스트 기반 LLM 컨텍스트 생성, 임베딩에 context 합산. config 연동 (enabled/max_tokens) |
| Tier 2: HyDE | 설계 완료 (이 문서 4.6.4) | ✅ 구현 완료 — Agent-driven 방식 채택. scar_guide.md 4.2 Query Enhancement 섹션 추가 (MUST 규칙). 시스템 레벨 HyDE 불채택 (qwen2.5:3b 품질 부족, GPT-5.4 에이전트가 더 우수) |
| Tier 2: Reranker 업그레이드 | 설계 완료 (이 문서 4.6.4) | 미구현 (Tier 0~1 후) |
| Agentic RAG: scar_guide.md 보강 | 설계 완료 (이 문서 4.6.6) | ✅ 구현 완료 |
| Agentic RAG: frameworks.md 보강 | 설계 완료 (이 문서 4.6.6) | ✅ 구현 완료 |

**알려진 이슈:**

| # | 항목 | 심각도 | 이슈 |
|---|------|--------|------|
| 1 | path_utils.py | 낮음 | workspace 매칭이 substring 기반 (의도치 않은 매칭) |
| 2 | semantic_chunker.py | 정보 | 이름은 "semantic"이나 실제는 고정 크기 슬라이딩 윈도우 → **v1.3 Tier 1에서 해결 예정** |
| 3 | doc-search/server.py | 중간 | RBAC 기밀 접근 제어 미구현 (include_confidential) |
| 4 | Sparse 벡터 구현 | 중간 | BGE-M3 lexical_weights 대신 hidden state norm 근사 |

**Git 정보:**
- 리포: aihwangso/NEXUS (private)
- 브랜치: main
- 사용자: aihwangso / aihwangso@gmail.com

### 8.2 다음 할 일

**1단계: v1.2 잔여 — Domain Builder Phase 6 오류 해결**

| 순서 | 작업 | 상태 |
|------|------|------|
| 1 | process_refiner.py 재설계 (7개 프레임워크) | **완료** |
| 2 | skill_generator.py 재설계 (SCAR) | **완료** |
| 3 | domain-builder/server.py 업데이트 | **완료** |
| 4 | Core SOUL.md 업데이트 | **완료** |
| 5 | openclaw-mcp-bridge vendoring + 설정 | **완료** |
| 6 | SOUL.md에서 mcporter CLI 제거 + mcp-bridge 방식 반영 | **완료** |
| 7 | NSE CS 재빌드 테스트 — Phase 1~5 검증 | **완료** |
| 8 | Phase 6 오류 분석 + 개발 (인덱싱 트리거 + 빌드 로그) | **완료** — trigger_indexing() Redis enqueue 방식으로 수정 |

**2단계: v1.3 구현 — RAG 엔진 품질 개선 (설계서 4.6 참조)**

| 순서 | 작업 | 의존 | 상태 |
|------|------|------|------|
| 1 | PaddleOCR 연동 (Tier 0) | 없음 | **완료+검증+리팩토링** — classify_page 4신호, PaddleOCR, Docling 수정. test.pdf + nse_cs 469p 검증. config 연동 완료 (하드코딩 제거) |
| 2 | Excel LLM 구조 추론 (Tier 0) | 없음 | **완료+검증+리팩토링** — LLM 구조추론, sanity check. Troubleshooting Guide 7시트 검증. config 연동 + 프롬프트 보강 + 인코딩 중복 제거 완료 |
| 3 | Parent-Child Chunking (Tier 1) | 없음 | **완료+검증** — ParentChildChunker 구현, worker Parent/Child 분리 저장, doc-search Parent 역참조, init_qdrant 인덱스 추가. test.pdf + Troubleshooting Guide 7시트 검증 (Parent=4, Child=16, Other=10) |
| 4 | Contextual Chunking (Tier 1) | 3번 | **완료+검증** — worker.py에 LLM 컨텍스트 생성 단계 추가 (Parent 텍스트 기반), 임베딩 시 context+원본 합산, payload에 context 저장. config 연동 (enabled/max_tokens). Ollama 로컬 검증 |
| 5 | scar_guide.md 보강 (Agentic) | 없음 | **완료** |
| 6 | frameworks.md 보강 (Agentic) | 없음 | **완료** |
| 7 | HyDE (Tier 2) | 없음 | **완료** — Agent-driven 방식. scar_guide.md 4.2 Query Enhancement MUST 규칙 추가 |
| 8 | Reranker 업그레이드 (Tier 2) | Tier 0~1 효과 측정 후 | 미착수 |

**3단계: 통합 테스트 + 실서비스 배포**

| 작업 | 설명 | 상태 |
|------|------|------|
| NSE CS 도메인 빌드 | 텔레그램에서 Phase 1~6 실행 | **완료** — skill.md(Diagnostic-Branching), soul.md, config.yaml 생성 |
| NSE CS 문서 인덱싱 | 1,246건 파일 인덱싱 | **완료** — 10,706 포인트, Parent-Child Chunking 적용 |
| 실사용 테스트 | 텔레그램에서 실제 CS 문의 대응 | **완료** — 답변 정상 확인 |
| 라이프사이클 검증 | backup_domain + reset_to_core | **완료** — 백업(126MB) + Core 복귀 정상 |
| Crystallization 검증 | 대화 → 지식 축적 → 자동 승격 흐름 확인 | 미착수 |
| RAG 품질 평가 | Recall/MRR 측정 | 미착수 |

### 8.2.1 도메인 라이프사이클 관리 (설계+구현+검증 완료)

**문제:** Domain Builder로 도메인을 빌드하면 soul.md가 워크스페이스에 덮어쓰여 Core 모드(Domain Builder)로 복귀 불가. 연속으로 여러 도메인을 빌드할 수 없음.

**빌더 워크플로우:**

```
Core 모드 → 도메인 A 빌드(Phase 1~6) → 테스트 → 백업 → 초기화 → Core 모드 → 도메인 B 빌드 → ...
```

**구현 도구 3개 (domain-builder MCP에 추가, ✅ 구현 완료):**

#### switch_domain

| 항목 | 대상 | 위치 | 방법 |
|------|------|------|------|
| 워크스페이스 SOUL.md | 도메인 soul.md 또는 Core 템플릿으로 교체 | Windows 로컬 | domain_name="core"이면 Core 복원, 아니면 도메인 soul.md 복사 |

**추가 변경 (✅ 구현 완료):**

| 파일 | 변경 |
|------|------|
| soul_generator.py | `sync_to_runtime` 기본값 `True` → `False`. Phase 4에서 워크스페이스 자동 덮어쓰기 제거 |
| Core soul.md | Phase 6 완료 후 switch_domain/backup_domain/reset_to_core 안내 + 라이프사이클 관리 섹션 추가 |

#### backup_domain

| 항목 | 대상 | 위치 | 방법 |
|------|------|------|------|
| 도메인 파일 | domains/{도메인}/ 전체 | Windows 로컬 | 파일 복사 → backups/{도메인}_{날짜}/ |
| 워크스페이스 SOUL.md | ~/.openclaw/workspace/SOUL.md | Windows 로컬 | 파일 복사 |
| Qdrant 데이터 | documents 컬렉션 | Docker 컨테이너 | Qdrant 스냅샷 API (POST /collections/documents/snapshots → 다운로드) |
| .env 설정 | nexus/.env | Windows 로컬 | 파일 복사 |

#### reset_to_core

| 항목 | 대상 | 위치 | 방법 |
|------|------|------|------|
| 워크스페이스 SOUL.md | Core 템플릿으로 복원 | Windows 로컬 | nexus/config/openclaw/soul.md → ~/.openclaw/workspace/SOUL.md 복사 |
| Qdrant | 포인트 전체 삭제 | Docker 컨테이너 | Qdrant API (POST /collections/documents/points/delete, filter={}) |
| Redis 큐 | 큐 전체 삭제 | Docker 컨테이너 | Redis DEL 명령 (queue, retry, dead_letter) |
| .env DOCS_PATH | 기본값으로 리셋 | Windows 로컬 | DOCS_PATH를 기본값으로 변경 |
| Worker 컨테이너 | 재시작 | Docker | "docker compose up -d indexing-worker 실행 필요" 안내 |

**추가 변경:**

| 파일 | 변경 |
|------|------|
| soul_generator.py | `sync_to_runtime` 기본값 `True` → `False`. 워크스페이스 자동 덮어쓰기 제거 |
| Core soul.md | Phase 6 완료 후 안내 문구 추가: "테스트하려면 switch_domain, 백업하려면 backup_domain, 초기화하려면 reset_to_core" |
| domain-builder/server.py | backup_domain, reset_to_core 도구 추가 |

**접근 방식:** domain-builder MCP 서버에서 실행. Windows 파일은 직접 접근, Docker 서비스는 API(Qdrant HTTP, Redis 클라이언트)로 접근. localhost 기본값 사용 (trigger_indexing과 동일 패턴).

**미래 확장:** 현재는 빌더 워크플로우(한 번에 하나의 도메인)만 지원. 멀티도메인 동시 운영은 Qdrant payload에 domain 필드 추가 + doc-search domain 필터링이 필요하며, 별도 설계 후 구현.

### 8.3 사용자 선호/규칙

다음 AI 세션이 반드시 지켜야 할 규칙:

| 규칙 | 설명 |
|------|------|
| **커밋/푸시** | 사용자가 명시적으로 요청할 때만 수행. 자의적으로 커밋하지 않는다. |
| **작업 방식** | 단계별 보고 → 사용자 검토 → 승인 후 다음 단계. 한꺼번에 진행하지 않는다. |
| **설계서 우선** | 설계서에 없거나 변경되는 사항은 반드시 설계서 먼저 업데이트 → 코드 작업 순서. |
| **설계 오류 시** | 설계서대로 개발하려 할 때 설계 오류로 보이면 사용자에게 확인받는다. 임의로 변경하지 않는다. |
| **domains/ 파일** | domains/{도메인}/ 아래 파일은 Domain Builder의 OUTPUT이다. 직접 수정하지 않고, 생성기(generator)를 수정한다. |
| **비즈니스 모델** | Domain Builder는 고객에게 비공개. 도메인 구축은 서비스로 수익화한다. |
| **언어** | 한국어로 작업한다. 코드 주석, 커밋 메시지, 문서 모두 한국어. |
| **설계 문서** | 이 문서(`NEXUS-설계서.md`)가 유일한 설계서. 다른 설계 문서를 만들지 않는다. |

---

## 부록

### 부록 A: 참고 출처

| 출처 | URL | 활용 |
|------|-----|------|
| NFD 논문 | https://arxiv.org/html/2603.10808 | 이론적 기반 (Knowledge Crystallization, Three-Layer Architecture) |
| Superpowers brainstorming | https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md | 소크라테스식 질문 패턴 참고 |
| OpenClaw skill-creator | https://github.com/openclaw/openclaw/blob/main/skills/skill-creator/SKILL.md | Skill md 생성 베스트 프랙티스 참고 |
| OpenClaw Creating Skills | https://docs.openclaw.ai/tools/creating-skills | Skill 작성 가이드 참고 |

**참고 활용 방식:** 이들을 그대로 쓰는 것이 아니라, 패턴만 차용하여 Domain Builder 전용으로 구현.

### 부록 B: 환경변수 목록 (.env.example 기준)

| 변수 | 필수 | 설명 | 기본값/예시 |
|------|------|------|-----------|
| `DOCS_PATH` | 필수 | 문서 폴더 경로 | /mnt/shared-docs |
| `QDRANT_API_KEY` | 필수 | Qdrant 인증 키 | nexus-qdrant-change-me |
| `OPENAI_API_KEY` | 선택 | OpenAI/Codex API 키 | sk-... |
| `ANTHROPIC_API_KEY` | 선택 | Anthropic API 키 | sk-ant-... |
| `GOOGLE_API_KEY` | 선택 | Google API 키 | AIza... |
| `DASHSCOPE_API_KEY` | 선택 | DashScope API 키 | sk-... |
| `DEEPSEEK_API_KEY` | 선택 | DeepSeek API 키 | sk-... |
| `TAVILY_API_KEY` | 선택 | Tavily 웹검색 API 키 | tvly-... |
| `TEAMS_APP_ID` | 선택 | Teams 앱 ID | - |
| `TEAMS_APP_PASSWORD` | 선택 | Teams 앱 비밀번호 | - |
| `TEAMS_TENANT_ID` | 선택 | Teams 테넌트 ID | - |
| `NEO4J_PASSWORD` | Phase 2 | Neo4j 비밀번호 | nexus-neo4j-change-me |
| `GATEWAY_PORT` | 선택 | OpenClaw Gateway 포트 | 18789 |
| `WEBCHAT_PORT` | 선택 | WebChat 포트 | 3000 |
| `WEBUI_PORT` | 선택 | Open WebUI 포트 | 8081 |
| `GRAFANA_PORT` | 선택 | Grafana 포트 | 3001 |

### 부록 C: 전체 파일 목록 + 한 줄 설명

총 53개 소스 파일 (models, __pycache__, test-docs 제외).

**인프라/설정 (7개):**

| 파일 | 설명 |
|------|------|
| `nexus/.env` | 환경변수 (실제 값, git 미추적) |
| `nexus/.env.example` | 환경변수 템플릿 |
| `nexus/.gitignore` | Git 제외 규칙 |
| `nexus/docker-compose.yml` | Docker 서비스 오케스트레이션 |
| `nexus/nexus.config.yaml` | 전체 시스템 설정 (LLM, 검색, 인덱싱, RBAC) |
| `nexus/config/openclaw/openclaw.yaml` | OpenClaw 에이전트 설정 |
| `nexus/config/openclaw/soul.md` | AI 에이전트 시스템 프롬프트 |

**임베딩 서비스 (3개):**

| 파일 | 설명 |
|------|------|
| `nexus/services/embedding/server.py` | FastAPI 임베딩+리랭커 서버 |
| `nexus/services/embedding/Dockerfile` | Docker 이미지 빌드 |
| `nexus/services/embedding/requirements.txt` | Python 의존성 |

**인덱싱 서비스 (14개):**

| 파일 | 설명 |
|------|------|
| `nexus/services/indexing/worker.py` | 인덱싱 워커 (파싱->청킹->임베딩->저장) |
| `nexus/services/indexing/watchdog_service.py` | 파일시스템 변경 감지 |
| `nexus/services/indexing/Dockerfile` | Docker 이미지 빌드 |
| `nexus/services/indexing/requirements.txt` | Python 의존성 |
| `nexus/services/indexing/supervisord.conf` | supervisord 설정 (worker + watchdog) |
| `nexus/services/indexing/parsers/__init__.py` | 파서 패키지 |
| `nexus/services/indexing/parsers/base.py` | 파서 인터페이스 (ParsedPage, ParsedDocument) |
| `nexus/services/indexing/parsers/factory.py` | 파서 팩토리 (get_parser) |
| `nexus/services/indexing/parsers/pdf_parser.py` | DoclingParser (PDF/DOCX/PPTX/HTML) |
| `nexus/services/indexing/parsers/excel_parser.py` | ExcelParser (XLSX/XLS/CSV) |
| `nexus/services/indexing/parsers/text_parser.py` | TextParser (TXT/MD/LOG/JSON/XML/YAML) |
| `nexus/services/indexing/chunkers/__init__.py` | 청커 패키지 |
| `nexus/services/indexing/chunkers/base.py` | 청커 인터페이스 (Chunk, BaseChunker) |
| `nexus/services/indexing/chunkers/factory.py` | 청커 팩토리 (get_chunker) |
| `nexus/services/indexing/chunkers/semantic_chunker.py` | 슬라이딩 윈도우 + 테이블 분리 청커 |
| `nexus/services/indexing/utils/__init__.py` | 유틸 패키지 |
| `nexus/services/indexing/utils/config_loader.py` | YAML 설정 로더 (싱글턴) |
| `nexus/services/indexing/utils/path_utils.py` | 워크스페이스 매핑, 기밀 판별 |

**MCP 서버 (8개):**

| 파일 | 설명 |
|------|------|
| `nexus/services/mcp-servers/doc-search/server.py` | 7단계 하이브리드 검색 |
| `nexus/services/mcp-servers/doc-search/requirements.txt` | 의존성 |
| `nexus/services/mcp-servers/doc-summary/server.py` | 문서 요약 |
| `nexus/services/mcp-servers/data-analysis/server.py` | Excel/CSV 분석 |
| `nexus/services/mcp-servers/indexing-admin/server.py` | 인덱싱 관리 |
| `nexus/services/mcp-servers/domain-search/server.py` | [v1.1] JSON 지식 검색 |
| `nexus/services/mcp-servers/domain-add/server.py` | [v1.1] JSON 지식 추가 |
| `nexus/services/mcp-servers/domain-export/server.py` | [v1.1] JSON → Excel 내보내기 |
| `nexus/services/mcp-servers/domain-builder/server.py` | [v1.1] Domain Builder |

**스크립트 (4개):**

| 파일 | 설명 |
|------|------|
| `nexus/scripts/setup.sh` | 원클릭 설치 |
| `nexus/scripts/download_models.sh` | ONNX 모델 다운로드 |
| `nexus/scripts/init_qdrant.sh` | Qdrant 컬렉션 초기화 |
| `nexus/scripts/backup_qdrant.sh` | Qdrant 스냅샷 백업 |

**테스트 (2개):**

| 파일 | 설명 |
|------|------|
| `nexus/tests/eval/run_eval.py` | 검색 품질 평가 프레임워크 |
| `nexus/tests/eval/eval_dataset.json` | 평가 데이터셋 (15개 질의) |

**모니터링 (1개):**

| 파일 | 설명 |
|------|------|
| `nexus/config/prometheus/prometheus.yml` | Prometheus 설정 |

### 부록 D: 7개 프레임워크 카탈로그 상세

> **상세 내용은 `nexus/core/domain-builder/frameworks.md`에 있다.**
> 이 파일은 LLM이 Phase 1(process.md 정교화)과 Phase 3(skill.md 생성) 시 직접 읽는 레퍼런스이다.
> 설계서와 frameworks.md의 내용이 다를 경우 frameworks.md가 우선한다.

포함 내용:
- 7개 프레임워크별: 적용 대상, 밸류체인, 방법론 기반, 질문 방향(8개), 프로세스 구조 가이드
- 프레임워크 선택 방법

이전 버전에서는 이 부록에 상세 내용이 인라인으로 포함되어 있었으나, v1.2부터 LLM이 직접 읽는 파일로 분리하여 설계서 수정과 코드 동작이 독립적으로 유지된다.

### 부록 E: SCAR 작성 원칙 참조

> **상세 내용은 `nexus/core/domain-builder/scar_guide.md`에 있다.**
> 이 파일은 LLM이 Phase 3(skill.md 생성) 시 직접 읽는 레퍼런스이다.
> 설계서와 scar_guide.md의 내용이 다를 경우 scar_guide.md가 우선한다.

포함 내용:
- SCAR 4원칙 (S: SOP, C: Constraint, A: Agent Principles, R: Runbook)
- skill.md 범용 골격 (역할, 도구, 프로세스, 지식 추출, 결과 판단, 규칙, 완료 시)
- 작성 가이드라인 (Progressive Disclosure, 500줄 이하, 검증 조건 필수 등)

SCAR는 **작성 원칙**이지 고정된 구조 템플릿이 아니다. 프로세스 섹션의 내부 구조는 frameworks.md의 선택된 프레임워크가 결정한다.

---

---

> **이 문서는 NEXUS 프로젝트의 유일한 설계서이다.**
> 모든 설계 변경은 이 문서를 업데이트하여 반영한다.
> 기존 설계 문서(10건)는 `docs/archive/`에 보관한다.
