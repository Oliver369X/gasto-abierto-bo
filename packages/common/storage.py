from __future__ import annotations

import hashlib
import io
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from functools import lru_cache
from typing import Optional

from minio import Minio
from minio.error import S3Error


def _connect_timeout_seconds() -> float:
    return float(os.getenv("MINIO_CONNECT_TIMEOUT_SECONDS", "5"))


class ObjectStore:
    """S3-compatible raw lake (MinIO). Soft-fails if unreachable so offline CI works."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ) -> None:
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9010")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket = bucket or os.getenv("MINIO_BUCKET", "gasto-raw")
        if secure is None:
            secure = os.getenv("MINIO_SECURE", "0") == "1"
        self.secure = secure
        self._client: Minio | None = None
        self.enabled = os.getenv("MINIO_ENABLED", "1") != "0"
        self._disabled_reason: str | None = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def _disable(self, reason: str) -> None:
        self.enabled = False
        self._disabled_reason = reason

    def _ensure_bucket_impl(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def ensure_bucket(self) -> None:
        if not self.enabled:
            return
        timeout = _connect_timeout_seconds()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(self._ensure_bucket_impl).result(timeout=timeout)
        except FuturesTimeout:
            self._disable(f"MinIO no respondió en {timeout}s ({self.endpoint})")
        except Exception as exc:  # noqa: BLE001
            self._disable(f"MinIO no disponible: {exc}")

    def put_bytes(
        self,
        *,
        source_id: str,
        key_suffix: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """Upload raw bytes. Returns object key or None if store disabled/unavailable."""
        if not self.enabled:
            return None
        self.ensure_bucket()
        if not self.enabled:
            return None
        digest = hashlib.sha256(data).hexdigest()[:16]
        key = f"{source_id}/{key_suffix.strip('/')}/{digest}"
        try:
            self.client.put_object(
                self.bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return key
        except S3Error:
            return None
        except Exception as exc:  # noqa: BLE001
            self._disable(str(exc))
            return None

    def sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def get_bytes(self, key: str) -> tuple[Optional[bytes], Optional[str]]:
        if not self.enabled or not key:
            return None, None
        timeout = _connect_timeout_seconds()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(self._get_bytes_impl, key).result(timeout=timeout)
        except FuturesTimeout:
            self._disable(f"lectura MinIO timeout ({timeout}s)")
            return None, None
        except Exception:
            return None, None

    def _get_bytes_impl(self, key: str) -> tuple[Optional[bytes], Optional[str]]:
        resp = self.client.get_object(self.bucket, key)
        try:
            data = resp.read()
            ctype = resp.headers.get("Content-Type")
        finally:
            resp.close()
            resp.release_conn()
        return data, ctype

    def presigned_get(self, key: str, expires_seconds: int = 3600) -> Optional[str]:
        if not self.enabled or not key:
            return None
        timeout = _connect_timeout_seconds()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(self._presigned_get_impl, key, expires_seconds).result(
                    timeout=timeout
                )
        except FuturesTimeout:
            self._disable(f"presign MinIO timeout ({timeout}s)")
            return None
        except Exception:
            return None

    def _presigned_get_impl(self, key: str, expires_seconds: int) -> Optional[str]:
        from datetime import timedelta

        return self.client.presigned_get_object(
            self.bucket, key, expires=timedelta(seconds=expires_seconds)
        )

    def status_message(self) -> str:
        if self.enabled:
            return "ok"
        return self._disabled_reason or "MinIO deshabilitado (MINIO_ENABLED=0)"


@lru_cache(maxsize=1)
def get_store() -> ObjectStore:
    return ObjectStore()
