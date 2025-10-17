#!/bin/bash

# Dsearch API 프로젝트 초기 환경 설정 스크립트
# Usage: chmod +x setup.sh && ./setup.sh

set -e  # 에러 발생시 스크립트 중단

echo "🚀 Dsearch API 환경 설정을 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$SCRIPT_DIR"

log_info "프로젝트 디렉토리: $PROJECT_DIR"

# Python 버전 확인
check_python() {
    log_info "Python 환경을 확인합니다..."
    
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        log_success "Python 3.11 발견"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        log_info "Python 버전: $PYTHON_VERSION"
        
        if [[ "$PYTHON_VERSION" < "3.8" ]]; then
            log_error "Python 3.8 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
            exit 1
        fi
        log_success "Python 3.x 사용 가능"
    else
        log_error "Python3가 설치되지 않았습니다. Python 3.8+ 설치가 필요합니다."
        echo "macOS: brew install python@3.11"
        echo "Ubuntu: sudo apt-get install python3.11"
        exit 1
    fi
}

# 가상환경 생성 및 활성화
setup_virtualenv() {
    log_info "Python 가상환경을 설정합니다..."
    
    VENV_DIR="$PROJECT_DIR/venv3.11"
    
    if [ -d "$VENV_DIR" ]; then
        log_warning "기존 가상환경 발견. 제거하고 새로 생성하시겠습니까? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
            log_info "기존 가상환경 제거 완료"
        else
            log_info "기존 가상환경 사용"
        fi
    fi
    
    if [ ! -d "$VENV_DIR" ]; then
        log_info "새 가상환경 생성 중..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        log_success "가상환경 생성 완료: $VENV_DIR"
    fi
    
    # 가상환경 활성화
    source "$VENV_DIR/bin/activate"
    log_success "가상환경 활성화 완료"
    
    # pip 업그레이드
    log_info "pip 업그레이드 중..."
    python -m pip install --upgrade pip
}

# 패키지 설치
install_packages() {
    log_info "Python 패키지를 설치합니다..."
    
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        log_error "requirements.txt 파일이 없습니다."
        exit 1
    fi
    
    log_info "의존성 패키지 설치 중... (시간이 걸릴 수 있습니다)"
    pip install -r "$PROJECT_DIR/requirements.txt"
    log_success "패키지 설치 완료"
}

# 환경변수 파일 확인
check_env_file() {
    log_info "환경 설정 파일을 확인합니다..."
    
    ENV_FILE="$PROJECT_DIR/.env"
    ENV_EXAMPLE="$PROJECT_DIR/.env.example"
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            log_info ".env 파일을 .env.example에서 복사합니다..."
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            log_warning ".env 파일을 수정하여 실제 설정값을 입력해주세요"
        else
            log_warning ".env 파일이 없습니다. 기본 .env 파일을 생성합니다..."
            create_default_env
        fi
    else
        log_success ".env 파일 존재 확인"
    fi
}

# 기본 .env 파일 생성
create_default_env() {
    cat > "$PROJECT_DIR/.env" << 'EOF'
# Application Configuration
DEBUG=true
APP_NAME="Dsearch API"
VERSION="2.0.0"
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=your-secret-key-here-change-this-in-production
SUPER_KEY=xlLVg89YUMim03SZ
ALLOWED_HOSTS=["*"]

# Database
DATABASE_URL=sqlite:///./dsearch.db

# Elasticsearch Configuration
ELASTICSEARCH_URLS=["https://cruxdata.co.kr:10323","https://cruxdata.co.kr:10423","https://cruxdata.co.kr:10523"]
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=elastic
ELASTICSEARCH_VERIFY_CERTS=false
ELASTICSEARCH_TIMEOUT=60

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# OpenAI Configuration (Optional)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# File Storage
MEDIA_ROOT=./media
STATIC_ROOT=./static

# Search Configuration
SEARCH_FIELDS=["title^2","text","html_mrc_array^0"]

# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs

# Machine Learning Models
SENTENCE_TRANSFORMER_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Batch Processing
BATCH_SIZE=100
MAX_WORKERS=4

# Localization
LANGUAGE_CODE=ko
TIME_ZONE=Asia/Seoul

# Performance Tuning
ELASTICSEARCH_BULK_SIZE=1000
REDIS_MAX_CONNECTIONS=20
VECTOR_DIMENSION=384

# Monitoring and Health Checks
HEALTH_CHECK_INTERVAL=30
METRICS_ENABLED=true
EOF
    log_success "기본 .env 파일 생성 완료"
}

# 필요한 디렉토리 생성
create_directories() {
    log_info "필요한 디렉토리를 생성합니다..."
    
    dirs=("logs" "media" "static" "media/uploads" "static/assets")
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$PROJECT_DIR/$dir" ]; then
            mkdir -p "$PROJECT_DIR/$dir"
            log_info "디렉토리 생성: $dir"
        fi
    done
    
    log_success "디렉토리 생성 완료"
}

# 애플리케이션 테스트
test_application() {
    log_info "애플리케이션을 테스트합니다..."
    
    if [ ! -f "$PROJECT_DIR/main.py" ]; then
        log_error "main.py 파일이 없습니다."
        exit 1
    fi
    
    # Import 테스트
    log_info "모듈 import 테스트 중..."
    python -c "
try:
    from app.core.config import settings
    from app.api.v1 import api_router
    print('✅ 모든 모듈 import 성공')
except Exception as e:
    print(f'❌ Import 오류: {e}')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "애플리케이션 테스트 통과"
    else
        log_error "애플리케이션 테스트 실패"
        exit 1
    fi
}

# 실행 스크립트 생성
create_run_script() {
    log_info "실행 스크립트를 생성합니다..."
    
    cat > "$PROJECT_DIR/run_server.sh" << 'EOF'
#!/bin/bash

# Dsearch API 서버 실행 스크립트

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv3.11"

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 가상환경 확인
if [ ! -d "$VENV_DIR" ]; then
    log_error "가상환경이 없습니다. setup.sh를 먼저 실행해주세요."
    exit 1
fi

# 가상환경 활성화
source "$VENV_DIR/bin/activate"

# .env 파일 확인
if [ ! -f "$PROJECT_DIR/.env" ]; then
    log_error ".env 파일이 없습니다. setup.sh를 먼저 실행해주세요."
    exit 1
fi

# 로그 디렉토리 생성
mkdir -p "$PROJECT_DIR/logs"

# PID 파일 경로
PID_FILE="$PROJECT_DIR/dsearch_api.pid"

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            log_warning "서버가 이미 실행 중입니다. PID: $(cat $PID_FILE)"
            exit 1
        fi
        
        log_info "Dsearch API 서버를 시작합니다..."
        cd "$PROJECT_DIR"
        
        # 백그라운드에서 서버 실행
        nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 \
            > "$PROJECT_DIR/logs/server.log" 2>&1 &
        
        SERVER_PID=$!
        echo $SERVER_PID > "$PID_FILE"
        
        sleep 2
        
        if kill -0 $SERVER_PID 2>/dev/null; then
            log_success "서버가 성공적으로 시작되었습니다. PID: $SERVER_PID"
            log_info "서버 URL: http://localhost:8000"
            log_info "API 문서: http://localhost:8000/docs"
            log_info "로그 파일: $PROJECT_DIR/logs/server.log"
        else
            log_error "서버 시작에 실패했습니다."
            exit 1
        fi
        ;;
        
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 $PID 2>/dev/null; then
                log_info "서버를 중지합니다. PID: $PID"
                kill $PID
                rm "$PID_FILE"
                log_success "서버가 중지되었습니다."
            else
                log_warning "서버가 실행중이지 않습니다."
                rm "$PID_FILE"
            fi
        else
            log_warning "PID 파일이 없습니다. 서버가 실행중이지 않을 수 있습니다."
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            log_success "서버가 실행 중입니다. PID: $(cat $PID_FILE)"
            log_info "서버 URL: http://localhost:8000"
        else
            log_warning "서버가 실행중이지 않습니다."
        fi
        ;;
        
    logs)
        if [ -f "$PROJECT_DIR/logs/server.log" ]; then
            tail -f "$PROJECT_DIR/logs/server.log"
        else
            log_error "로그 파일이 없습니다."
        fi
        ;;
        
    *)
        echo "사용법: $0 {start|stop|restart|status|logs}"
        echo "  start   - 서버 시작"
        echo "  stop    - 서버 중지"  
        echo "  restart - 서버 재시작"
        echo "  status  - 서버 상태 확인"
        echo "  logs    - 실시간 로그 보기"
        exit 1
        ;;
esac
EOF

    chmod +x "$PROJECT_DIR/run_server.sh"
    log_success "실행 스크립트 생성 완료: run_server.sh"
}

# 메인 실행 함수
main() {
    log_info "=== Dsearch API 환경 설정 시작 ==="
    
    check_python
    setup_virtualenv
    install_packages
    check_env_file
    create_directories
    test_application
    create_run_script
    
    log_success "=== 환경 설정이 완료되었습니다! ==="
    echo ""
    echo "다음 명령어로 서버를 실행할 수 있습니다:"
    echo "  ./run_server.sh start    # 서버 시작"
    echo "  ./run_server.sh stop     # 서버 중지"
    echo "  ./run_server.sh restart  # 서버 재시작"
    echo "  ./run_server.sh status   # 서버 상태"
    echo "  ./run_server.sh logs     # 실시간 로그"
    echo ""
    echo "또는 직접 실행:"
    echo "  source venv3.11/bin/activate"
    echo "  python main.py"
    echo ""
    echo "서버 실행 후 다음 URL에서 확인하세요:"
    echo "  - API 서버: http://localhost:8000"
    echo "  - API 문서: http://localhost:8000/docs"
}

# 스크립트 실행
main "$@"