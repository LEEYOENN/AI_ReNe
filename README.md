# ReNe Project (Next Recruit) - AI Career Platform

## 1. Project Overview
**ReNe(Next Recruit)**는 언리얼 엔진 5(UE5) 기반의 메타버스 환경과 LLM/RAG 기반의 AI 에이전트를 결합한 차세대 채용 플랫폼입니다.

기존의 텍스트 중심 채용 방식에서 벗어나, **3D 가상 면접(AI Interview)**과 **P2P 실전 면접**을 통해 구직자의 역량을 '데이터(Avatar Stats)'로 증명하고, 기업에게는 검증된 인재를 매칭합니다.

### Key Features
* **AI Profile Generation (시작의 레네)**
    * 사용자와의 대화를 통해 핵심 역량 키워드와 요약 프로필을 자동 생성합니다.
    * 문서 업로드 과정을 거쳤다면, 프로필을 검증 & 갱신하는 역할을 수행합니다.
* **Training Simulation (성장의 레네)**
    * 직무별 모의 면접을 통해, 구직자의 구체적인 기술적 Depth 를 검증합니다.
* **Company Simulation (시련의 레네)**
    * 특정 기업의 RAG 데이터(인재상, JD)를 기반으로 한 고난도 압박 면접을 연습합니다.
* **Real Interview (실전/P2P)**
    * **Company AI:** 실제 채용 공고에 지원하는 AI 면접입니다.
    * **P2P:** 기업 담당자와 구직자 간의 1:1 화상/음성 면접 (녹음 후 AI 분석 리포트 제공).
* **Dashboard (UMG)**
    * AI가 분석한 정량적 데이터(스탯, 리포트)를 시각화하여 제공합니다.

---

## 2. Directory Structure & Naming Convention
본 프로젝트는 **FastAPI**를 기반으로 하며, AI Agent 로직과 API 서버가 통합된 구조입니다.

### Naming Convention
* **Directory:** `snake_case` (e.g., `src`, `tech_npc_agent`)
* **File:** `snake_case` (e.g., `my_agent_logic.py`)

### Folder Structure
```plaintext
/ai_agent_project
├── .env                  # 환경 변수 (API Key, DB Credential) - 절대 Commit 금지
├── .gitignore            # Git 무시 목록 (.env, .venv, data/logs 등)
├── README.md             # 프로젝트 명세 및 실행 가이드
├── requirements.txt      # Python 의존성 패키지 목록
├── .venv/                # 가상 환경
├── data/                 # [External Data] 소스 코드 외 리소스
│   ├── models/           # 학습된 AI 모델 (.pth, .onnx)
│   ├── datasets/         # RAG용 기업 데이터, 학습 데이터셋
│   └── logs/             # 서버 실행 로그
├── notebooks/            # (Optional) 데이터 탐색 및 실험용 Jupyter Notebook
├── scripts/              # (Optional) 전처리, 마이그레이션 스크립트
├── tests/                # 테스트 코드 (Pytest)
└── src/                  # [Application Source Code]
    ├── main.py           # FastAPI Entry Point (App 실행)
    ├── api/              # API Router Definitions
    │   ├── endpoints/    # 개별 도메인별 라우터
    │   │   └── session_api.py
    │   ├── deps.py       # 의존성 주입 (Auth, DB Session)
    │   └── static/       # 정적 파일 (HTML/JS 등 필요 시)
    ├── prompts/          # LLM System Prompts & Templates 관리
    ├── agents/           # [Core AI Logic] 에이전트 로직
    │   ├── base_agent.py # 에이전트 추상 클래스
    │   ├── tools/        # RAG 검색, 외부 API 호출 도구
    │   └── main_agent.py # LLM 호출 및 응답 생성 오케스트레이터
    ├── services/         # 비즈니스 로직 (DB 트랜잭션, 복잡한 연산)
    ├── models/           # DB Entity (SQLAlchemy/Tortoise Model)
    ├── repositories/     # DB CRUD 접근 계층
    ├── core/             # 전역 설정
    │   ├── config.py     # .env 로드 및 App Config
    │   └── database.py   # DB 연결 설정
    ├── schemas/          # Pydantic Schemas (Request/Response DTO)
    └── utils/            # 공통 유틸리티 (Logger, File I/O)
```
