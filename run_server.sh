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
