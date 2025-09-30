"""
파일 처리 유틸리티

파일 업로드, 다운로드, 메타데이터 추출, 파일 작업 등의
파일 관련 기능들을 제공하는 유틸리티 모듈입니다.
파일 타입 판별, 크기 계산, 보안 검사 등을 포함합니다.
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger("ds")


class FileHandler:
    """\n    파일 작업 및 메타데이터 추출을 위한 유틸리티 클래스.\n\n    파일 업로드, 삭제, 이동, 복사 등의 기본 파일 작업과\n    파일 메타데이터 추출, 타입 판별, 보안 검사 등의\n    고급 기능을 제공합니다.\n    """

    def __init__(self):
        self.media_root = Path(settings.MEDIA_ROOT)
        self.static_root = Path(settings.STATIC_ROOT)

        # Ensure directories exist
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.static_root.mkdir(parents=True, exist_ok=True)

    def file_exists(self, file_path: str) -> bool:
        """\n        파일 존재 여부를 확인합니다.\n\n        Args:\n            file_path: 확인할 파일 경로\n\n        Returns:\n            bool: 파일 존재 여부\n        """
        return Path(file_path).exists()

    def get_full_path(self, relative_path: str) -> str:
        """\n        상대 경로로부터 절대 경로를 가져옵니다.\n\n        Args:\n            relative_path: 상대 경로\n\n        Returns:\n            str: 절대 경로\n        """
        if Path(relative_path).is_absolute():
            return relative_path
        return str(self.media_root / relative_path)

    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """\n        파일 메타데이터와 정보를 추출합니다.\n\n        파일 이름, 확장자, 크기, 타입, MIME 타입, 생성/수정 시간 등\n        파일에 대한 상세한 메타데이터를 추출합니다.\n\n        Args:\n            file_path: 분석할 파일 경로\n\n        Returns:\n            Dict[str, Any]: 파일 메타데이터 딕셔너리\n\n        Raises:\n            FileNotFoundError: 파일을 찾을 수 없는 경우\n            Exception: 메타데이터 추출 중 오류 발생 시\n        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            stat = path.stat()

            # Get file type
            mime_type, _ = mimetypes.guess_type(str(path))
            file_type = self._get_file_category(mime_type, path.suffix)

            # Get file size in human-readable format
            size_bytes = stat.st_size
            size_human = self._format_file_size(size_bytes)

            return {
                "name": path.stem,
                "filename": path.name,
                "extension": path.suffix.lower(),
                "size": size_bytes,
                "size_human": size_human,
                "type": file_type,
                "mime_type": mime_type,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "path": str(path),
                "relative_path": str(path.relative_to(self.media_root)) if self._is_under_media_root(path) else str(path)
            }

        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            raise

    def generate_document_id(self, file_path: str) -> str:
        """\n        파일 경로와 내용을 기반으로 고유 문서 ID를 생성합니다.\n\n        파일 경로와 수정 시간을 결합하여 MD5 해시로\n        고유한 문서 식별자를 생성합니다.\n\n        Args:\n            file_path: 문서 ID를 생성할 파일 경로\n\n        Returns:\n            str: 생성된 문서 ID (해시값)\n        """
        try:
            path = Path(file_path)

            # Create ID based on file path and modification time
            content_for_hash = f"{path.absolute()}:{path.stat().st_mtime}"
            return hashlib.md5(content_for_hash.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error generating document ID for {file_path}: {e}")
            # Fallback to simple path hash
            return hashlib.md5(file_path.encode()).hexdigest()

    def _get_file_category(self, mime_type: Optional[str], extension: str) -> str:
        """Categorize file based on MIME type and extension."""
        if not mime_type:
            mime_type = ""

        # Document types
        if mime_type.startswith("application/pdf"):
            return "pdf"
        elif mime_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return "word"
        elif mime_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return "excel"
        elif mime_type in ["application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
            return "powerpoint"
        elif mime_type.startswith("text/"):
            return "text"
        elif mime_type.startswith("text/html"):
            return "html"

        # Image types
        elif mime_type.startswith("image/"):
            return "image"

        # Archive types
        elif mime_type in ["application/zip", "application/x-rar", "application/x-7z-compressed"]:
            return "archive"

        # Extension-based fallback
        extension_map = {
            ".pdf": "pdf",
            ".doc": "word",
            ".docx": "word",
            ".xls": "excel",
            ".xlsx": "excel",
            ".ppt": "powerpoint",
            ".pptx": "powerpoint",
            ".txt": "text",
            ".html": "html",
            ".htm": "html",
            ".jpg": "image",
            ".jpeg": "image",
            ".png": "image",
            ".gif": "image",
            ".zip": "archive",
            ".rar": "archive",
            ".7z": "archive"
        }

        return extension_map.get(extension.lower(), "unknown")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f} {size_names[i]}"

    def _is_under_media_root(self, path: Path) -> bool:
        """Check if path is under media root."""
        try:
            path.relative_to(self.media_root)
            return True
        except ValueError:
            return False

    async def save_uploaded_file(self, file_content: bytes, filename: str,
                               subdirectory: Optional[str] = None) -> str:
        """Save uploaded file content to media directory."""
        try:
            # Create subdirectory path
            if subdirectory:
                save_dir = self.media_root / subdirectory
            else:
                save_dir = self.media_root

            save_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename if file already exists
            file_path = save_dir / filename
            counter = 1
            original_stem = Path(filename).stem
            original_suffix = Path(filename).suffix

            while file_path.exists():
                new_filename = f"{original_stem}_{counter}{original_suffix}"
                file_path = save_dir / new_filename
                counter += 1

            # Write file content
            with open(file_path, 'wb') as f:
                f.write(file_content)

            logger.info(f"Saved uploaded file: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error saving uploaded file {filename}: {e}")
            raise

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file safely."""
        try:
            path = Path(file_path)

            # Security check: only delete files under media root
            if not self._is_under_media_root(path):
                logger.warning(f"Attempted to delete file outside media root: {file_path}")
                return False

            if path.exists():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """Move file from source to destination."""
        try:
            source = Path(source_path)
            destination = Path(destination_path)

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            source.rename(destination)
            logger.info(f"Moved file from {source_path} to {destination_path}")
            return True

        except Exception as e:
            logger.error(f"Error moving file from {source_path} to {destination_path}: {e}")
            return False

    async def copy_file(self, source_path: str, destination_path: str) -> bool:
        """Copy file from source to destination."""
        try:
            import shutil

            source = Path(source_path)
            destination = Path(destination_path)

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source, destination)
            logger.info(f"Copied file from {source_path} to {destination_path}")
            return True

        except Exception as e:
            logger.error(f"Error copying file from {source_path} to {destination_path}: {e}")
            return False

    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types."""
        return [
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "txt", "html", "htm", "rtf", "odt", "ods", "odp"
        ]

    def is_supported_file_type(self, file_path: str) -> bool:
        """Check if file type is supported for processing."""
        try:
            file_info = Path(file_path)
            extension = file_info.suffix.lower().lstrip('.')

            supported_extensions = {
                "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
                "txt", "html", "htm", "rtf", "odt", "ods", "odp"
            }

            return extension in supported_extensions

        except Exception as e:
            logger.error(f"Error checking file type support for {file_path}: {e}")
            return False

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified hours."""
        try:
            temp_dir = self.media_root / "temp"
            if not temp_dir.exists():
                return 0

            current_time = datetime.now()
            deleted_count = 0

            for file_path in temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.total_seconds() > max_age_hours * 3600:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting temp file {file_path}: {e}")

            logger.info(f"Cleaned up {deleted_count} temporary files")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            return 0

    def get_directory_size(self, directory_path: str) -> Dict[str, Any]:
        """Get directory size and file count statistics."""
        try:
            path = Path(directory_path)
            if not path.exists() or not path.is_dir():
                return {"error": "Directory not found"}

            total_size = 0
            file_count = 0
            dir_count = 0

            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1

            return {
                "total_size_bytes": total_size,
                "total_size_human": self._format_file_size(total_size),
                "file_count": file_count,
                "directory_count": dir_count,
                "path": str(path)
            }

        except Exception as e:
            logger.error(f"Error getting directory size for {directory_path}: {e}")
            return {"error": str(e)}