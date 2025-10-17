# Dsearch API

Korean Enterprise Document Search Platform - 한국어 기업 문서 검색 플랫폼

## 📋 프로젝트 소개

Dsearch API는 FastAPI 기반의 고성능 한국어 문서 검색 플랫폼입니다. Elasticsearch를 활용한 텍스트 검색, 벡터 검색, 그리고 OpenAI GPT 통합을 통해 기업 환경에서 효율적인 문서 관리를 제공합니다.

## ✨ 주요 기능

- **텍스트 검색**: Elasticsearch를 활용한 고속 텍스트 검색
- **벡터 검색**: Sentence Transformers를 이용한 의미 기반 검색
- **AI 통합**: OpenAI GPT를 활용한 텍스트 생성 및 분석
- **배치 처리**: APScheduler를 통한 자동화된 문서 처리
- **캐싱**: Redis를 활용한 고성능 캐싱 시스템
- **다양한 파일 지원**: PDF, Word, Excel 등 다양한 문서 형식 지원
- **RESTful API**: 표준화된 REST API 인터페이스

## 🛠 기술 스택

- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL (선택), SQLite (기본)
- **Search Engine**: Elasticsearch 8.x
- **Cache**: Redis 7.x
- **AI/ML**: OpenAI GPT, Sentence Transformers
- **Container**: Docker, Docker Compose
- **Testing**: Pytest, Locust (부하 테스트)

## 🚀 설치 및 실행

### 전제 조건

- Python 3.11+
- Docker & Docker Compose (권장)
- Elasticsearch, Redis (또는 Docker 사용)

### 1. 로컬 개발 환경

```bash
# 1. 저장소 클론
git clone <repository-url>
cd project-code

# 2. 가상 환경 생성 및 활성화
python3 -m venv venv3.11
source venv3.11/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 설정

# 5. 데이터베이스 마이그레이션 (필요 시)
# alembic upgrade head

# 6. 서버 실행
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 2. Docker를 사용한 실행

```bash
# 전체 스택 실행 (PostgreSQL, Elasticsearch, Redis 포함)
docker-compose up -d

# 또는 로컬 Elasticsearch 연결 시
docker-compose -f docker-compose.local-es.yml up -d

# 오프라인 환경용
docker-compose -f docker-compose.offline.yml up -d
```

## ⚙ 환경 설정

.env 파일을 통해 환경 변수를 설정하세요:

```env
# 애플리케이션 설정
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 데이터베이스
DATABASE_URL=sqlite:///./dsearch.db

# Elasticsearch
ELASTICSEARCH_URLS=["http://localhost:9200"]
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=elastic

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your-api-key
```

## 📚 API 사용

### API 문서

서버 실행 후 다음 URL에서 API 문서를 확인하세요:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 주요 엔드포인트

- `GET /api/v1/health` - 헬스 체크
- `POST /api/v1/search` - 문서 검색
- `POST /api/v1/batch/process` - 배치 문서 처리
- `POST /api/v1/ml/generate` - AI 텍스트 생성

### 예시 요청

```bash
# 검색 API
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "문서 검색"}'

# 파일 업로드
curl -X POST "http://localhost:8000/api/v1/batch/process" \
  -F "files=@document.pdf"
```

## 🧪 테스트

### 단위 테스트

```bash
# 기본 테스트 실행
pytest tests/

# 커버리지 확인
pytest --cov=app --cov-report=html
```

### 부하 테스트

```bash
# Locust 설치
pip install locust

# 부하 테스트 실행
locust -f tests/locustfile.py --host=http://localhost:8000
```

### API 테스트

```bash
# FastAPI TestClient 사용
python -m pytest tests/test_api.py
```

## 🚢 배포

### Docker Compose 배포

```bash
# 프로덕션 환경
docker-compose up -d

# 로그 확인
docker-compose logs -f app

# 스케일링
docker-compose up -d --scale app=3
```

### 수동 배포

```bash
# 빌드
docker build -t dsearch-api .

# 실행
docker run -d -p 8000:8000 --env-file .env dsearch-api
```

## 📁 프로젝트 구조

```
project-code/
├── app/
│   ├── api/v1/          # API 엔드포인트
│   ├── core/            # 설정 및 로깅
│   ├── models/          # 데이터 모델
│   ├── services/        # 비즈니스 로직
│   └── utils/           # 유틸리티 함수
├── tests/               # 테스트 코드
├── logs/                # 로그 파일
├── media/               # 업로드 파일
├── static/              # 정적 파일
├── Dockerfile           # Docker 이미지
├── docker-compose.yml   # Docker Compose 설정
├── requirements.txt     # Python 의존성
├── main.py             # 애플리케이션 진입점
└── .env                # 환경 변수
```

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 LICENSE 파일을 참조하세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면 [이슈](https://github.com/your-repo/issues)를 통해 문의해 주세요.

---

**개발자**: Dsearch Team
**버전**: 2.0.0
**마지막 업데이트**: 2024년 10월 16일
