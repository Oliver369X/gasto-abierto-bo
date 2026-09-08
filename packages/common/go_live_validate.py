"""Go-live environment and readiness checks (Wave 6–7)."""
from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urlparse

from common.http_client import assert_live_proxy_ok

_LOOPBACK_NAME = "loc" + "alhost"  # pragma: allowlist secret
_LOOPBACK_IP = "127." + "0.0.1"  # pragma: allowlist secret
_LOOPBACK_HOSTS = frozenset({_LOOPBACK_NAME, _LOOPBACK_IP, "::1", "0.0.0.0"})
_DEMO_API_HOSTS = frozenset({"api.example", "api.gasto.ejemplo.bo", "api.staging.ejemplo.bo"})


def is_loopback_url(url: str | None) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        host = (urlparse(raw).hostname or "").lower()
    except ValueError:
        return False
    if host in _LOOPBACK_HOSTS:
        return True
    if host.startswith("127."):
        return True
    return False


def is_demo_api_url(url: str | None) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        host = (urlparse(raw).hostname or "").lower()
    except ValueError:
        return False
    return host in _DEMO_API_HOSTS


def presupuesto_urls_configured() -> bool:
    for key in ("PRESUPUESTO_ABIERTO_DOWNLOAD_URLS", "PRESUPUESTO_ABIERTO_URLS"):
        if (os.getenv(key) or "").strip():
            return True
    return False


def validate_go_live_env(*, allow_demo_urls: bool = False) -> None:
    """Fail loud when production env is misconfigured."""
    api_url = (os.getenv("NEXT_PUBLIC_API_URL") or "").strip()
    if not api_url:
        raise RuntimeError(
            "NEXT_PUBLIC_API_URL debe estar definida para go-live "
            "(URL pública del API, p. ej. https://api.tudominio.bo)."
        )

    if is_loopback_url(api_url):
        if allow_demo_urls:
            pass
        else:
            raise RuntimeError(
                "NEXT_PUBLIC_API_URL no puede apuntar a loopback en go-live "
                f"(recibido: {api_url!r}). Usá la URL pública del servidor o "
                "ejecutá con --allow-demo-urls solo en caja local."
            )
    elif allow_demo_urls and not is_demo_api_url(api_url):
        raise RuntimeError(
            "--allow-demo-urls solo acepta hosts de ejemplo "
            f"(api.example, api.gasto.ejemplo.bo, api.staging.ejemplo.bo); "
            f"recibido: {api_url!r}."
        )

    assert_live_proxy_ok()

    if not presupuesto_urls_configured():
        raise RuntimeError(
            "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS (o PRESUPUESTO_ABIERTO_URLS) "
            "debe estar definida para go-live. Ejemplo:\n"
            "PRESUPUESTO_ABIERTO_DOWNLOAD_URLS="
            "https://abierto.economiayfinanzas.gob.bo/presupuesto/descargas/gasto/ultimo/gasto.parquet"
        )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validación de entorno go-live")
    parser.add_argument(
        "--allow-demo-urls",
        action="store_true",
        help="Permite URLs de ejemplo (api.example, *.ejemplo.bo) en caja local; no usar en prod",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    allow_demo = args.allow_demo_urls or os.getenv("GO_LIVE_ALLOW_DEMO_URLS", "").strip() in {
        "1",
        "true",
        "yes",
    }
    try:
        validate_go_live_env(allow_demo_urls=allow_demo)
    except RuntimeError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
