# Dsearch - 한국어 문서 검색 플랫폼

한국어 기업용 문서 검색 플랫폼입니다. FastAPI, Elasticsearch, Redis를 활용한 고성능 검색 시스템을 제공합니다.

## 📋 목차

- [Docker 파일 설명](#docker-파일-설명)
  - [Dockerfile](#dockerfile)
  - [docker-compose.yml](#docker-composeyml)
- [시스템 아키텍처](#시스템-아키텍처)
- [빠른 시작](#빠른-시작)
- [환경 설정](#환경-설정)

## 🐳 Docker 파일 설명

### Dockerfile

`Dockerfile`은 **애플리케이션 컨테이너 이미지를 빌드하기 위한 설정 파일**입니다.

#### 주요 역할:

1. **기본 환경 구성**
   - Python 3.11-slim을 베이스 이미지로 사용
   - 애플리케이션 실행에 필요한 시스템 패키지 설치

2. **시스템 의존성 설치**
   - `gcc`, `g++`: C/C++ 컴파일러 (Python 패키지 빌드용)
   - `libreoffice`: 오피스 문서 처리
   - `poppler-utils`: PDF 처리
   - `tesseract-ocr`, `tesseract-ocr-kor`: OCR(광학 문자 인식) 및 한국어 지원
   - `libmagic1`: 파일 타입 감지

3. **Python 의존성 관리**
   - `uv` 패키지 매니저를 사용하여 빠른 의존성 설치
   - `pyproject.toml`을 기반으로 프로젝트 의존성 설치

4. **애플리케이션 설정**
   - `/app` 디렉토리를 작업 디렉토리로 설정
   - `logs`, `media`, `static` 디렉토리 생성
   - 환경 변수 설정 (PYTHONPATH, PYTHONDONTWRITEBYTECODE 등)

5. **서비스 구성**
   - 포트 8000 노출
   - 헬스체크 설정 (30초 간격으로 `/health` 엔드포인트 확인)
   - Uvicorn 서버로 FastAPI 애플리케이션 실행 (4 워커)

#### Dockerfile 구조:

```dockerfile
FROM python:3.11-slim          # 베이스 이미지
WORKDIR /app                   # 작업 디렉토리
RUN apt-get install ...        # 시스템 패키지 설치
RUN uv pip install ...         # Python 의존성 설치
COPY . .                       # 소스 코드 복사
EXPOSE 8000                    # 포트 노출
CMD ["uvicorn", ...]           # 실행 명령
```

### docker-compose.yml

`docker-compose.yml`은 **여러 서비스를 함께 실행하고 관리하기 위한 오케스트레이션 설정 파일**입니다.

#### 주요 역할:

1. **다중 서비스 관리**
   - 애플리케이션과 의존 서비스들을 하나의 명령으로 관리
   - 서비스 간 네트워크 자동 구성
   - 서비스 시작 순서 제어 (`depends_on`)

2. **구성된 서비스들**

   **📱 app (FastAPI 애플리케이션)**
   - Dockerfile을 사용하여 빌드
   - 포트 8000으로 API 서버 제공
   - 환경 변수로 다른 서비스와 연결

   **🗄️ postgres (PostgreSQL 데이터베이스)**
   - 메타데이터 및 사용자 정보 저장
   - 포트 5432
   - 데이터 영속성을 위한 볼륨 마운트

   **🔍 elasticsearch (검색 엔진)**
   - 문서 인덱싱 및 전문 검색 기능
   - 포트 9200 (HTTP API), 9300 (노드 통신)
   - 단일 노드 모드로 구성
   - 1GB 힙 메모리 할당

   **⚡ redis (캐시 및 세션 저장소)**
   - 검색 결과 캐싱 및 세션 관리
   - 포트 6379
   - AOF(Append Only File) 영속성 활성화

   **📊 kibana (Elasticsearch 관리 UI)**
   - Elasticsearch 데이터 시각화 및 관리
   - 포트 5601
   - Elasticsearch와 자동 연결

   **🔧 redis-commander (Redis 관리 UI)**
   - Redis 데이터 조회 및 관리
   - 포트 8081

   **🌐 nginx (리버스 프록시)**
   - HTTP/HTTPS 트래픽 라우팅
   - 포트 80, 443
   - SSL 인증서 지원

3. **네트워크 구성**
   - `dsearch-network`: 모든 서비스를 연결하는 브리지 네트워크
   - 서비스 이름으로 상호 통신 가능 (예: `elasticsearch:9200`)

4. **데이터 영속성**
   - Named 볼륨을 사용하여 데이터베이스 데이터 보존
   - `postgres_data`: PostgreSQL 데이터
   - `elasticsearch_data`: Elasticsearch 인덱스
   - `redis_data`: Redis 데이터

5. **개발 편의성**
   - 로컬 디렉토리 마운트 (`./media`, `./logs`)
   - 자동 재시작 정책 (`restart: unless-stopped`)
   - 관리 UI 제공 (Kibana, Redis Commander)

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                        Nginx                             │
│                  (Reverse Proxy)                         │
│                    Port 80/443                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   FastAPI App                            │
│              (Dsearch Application)                       │
│                    Port 8000                             │
└─────┬────────────┬──────────────┬───────────────────────┘
      │            │              │
      ▼            ▼              ▼
┌──────────┐ ┌──────────┐  ┌──────────┐
│PostgreSQL│ │Elastic-  │  │  Redis   │
│          │ │ search   │  │          │
│Port 5432 │ │Port 9200 │  │Port 6379 │
└──────────┘ └────┬─────┘  └──────────┘
                  │
            ┌─────▼─────┐
            │  Kibana   │
            │Port 5601  │
            └───────────┘
```

## 🚀 빠른 시작

### 1. 사전 요구사항

- Docker 20.10 이상
- Docker Compose 2.0 이상
- 최소 4GB RAM 권장

### 2. 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다:

```bash
# Security
SECRET_KEY=your-secret-key-here
SUPER_KEY=your-super-key-here

# Database
DATABASE_URL=postgresql+asyncpg://dsearch:dsearch123@postgres:5432/dsearch

# Elasticsearch
ELASTICSEARCH_URLS=http://elasticsearch:9200
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI (선택사항)
OPENAI_API_KEY=your-openai-api-key
```

### 3. 애플리케이션 실행

```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f app

# 서비스 상태 확인
docker-compose ps
```

### 4. 접근 URL

- **API 문서**: http://localhost:8000/docs
- **Kibana**: http://localhost:5601
- **Redis Commander**: http://localhost:8081
- **Nginx**: http://localhost

### 5. 종료

```bash
# 모든 서비스 종료
docker-compose down

# 데이터까지 삭제
docker-compose down -v
```

## ⚙️ 환경 설정

### Dockerfile 빌드 옵션

개발 환경에서 이미지를 직접 빌드하려면:

```bash
# 이미지 빌드
docker build -t dsearch:latest .

# 컨테이너 실행
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./dsearch.db \
  -e ELASTICSEARCH_URLS=http://localhost:9200 \
  dsearch:latest
```

### docker-compose 변형

프로젝트에는 여러 docker-compose 파일이 있습니다:

- `docker-compose.yml`: 프로덕션 환경용 전체 스택
- `docker-compose.local-es.yml`: 로컬 Elasticsearch 사용
- `docker-compose.offline.yml`: 오프라인 환경용

특정 파일을 사용하려면:

```bash
docker-compose -f docker-compose.local-es.yml up -d
```

## 📝 주요 기능

- 🔍 **전문 검색**: Elasticsearch 기반 고성능 한국어 검색
- 📄 **문서 처리**: PDF, Office 문서 자동 파싱
- 🤖 **AI/ML**: OpenAI API 연동, 문서 추천 시스템
- ⚡ **캐싱**: Redis 기반 검색 결과 캐싱
- 📊 **모니터링**: 헬스체크, 로깅, 관리 UI
- 🔐 **보안**: JWT 인증, API 키 관리

## 🛠️ 개발

로컬 개발 환경 설정:

```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -e .

# 개발 서버 실행
uvicorn main:app --reload
```

## 📄 라이센스

이 프로젝트의 라이센스 정보는 LICENSE 파일을 참조하세요.

## 🤝 기여

버그 리포트와 기능 제안은 GitHub Issues를 통해 제출해 주세요.
