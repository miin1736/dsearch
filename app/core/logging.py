"""
로깅 설정 관리 모듈
"""

import logging
import logging.handlers
import os
from pathlib import Path

from .config import settings


def setup_logging():
    """
    애플리케이션 로깅 설정을 초기화합니다.

    서버 로그, 배치 로그, 콘솔 출력을 위한 핸들러들을 설정하고
    각각의 로거에 적절한 핸들러를 연결합니다.
    """

    # Ensure log directory exists
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Define formatters
    basic_formatter = logging.Formatter(
        "%(asctime)s - %(module)s - [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Server log handler
    server_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "server.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    server_handler.setLevel(logging.INFO)
    server_handler.setFormatter(basic_formatter)

    # Batch log handler
    batch_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dir / "batch.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    batch_handler.setLevel(logging.INFO)
    batch_handler.setFormatter(basic_formatter)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(basic_formatter)

    # Configure loggers
    ds_logger = logging.getLogger("ds")
    ds_logger.setLevel(logging.INFO)
    ds_logger.addHandler(server_handler)
    ds_logger.addHandler(console_handler)
    ds_logger.propagate = False

    batch_logger = logging.getLogger("batch")
    batch_logger.setLevel(logging.INFO)
    batch_logger.addHandler(batch_handler)
    batch_logger.addHandler(console_handler)
    batch_logger.propagate = False

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    root_logger.addHandler(console_handler)


def get_logger(name: str = "ds") -> logging.Logger:
    """
    이름으로 로거를 가져옵니다.

    Args:
        name (str): 로거 이름 (기본값: "ds")

    Returns:
        logging.Logger: 요청된 로거 인스턴스
    """
    return logging.getLogger(name)