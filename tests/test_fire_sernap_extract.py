from __future__ import annotations

import json

from worker.fire.phases import f03_corpus


class _Page:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _Pdf:
    def __init__(self, pages: list[_Page]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_extract_sernap_text_pages_uses_manifest_page_types(tmp_path, monkeypatch):
    pdf = tmp_path / "data" / "raw" / "sernap" / "memoria.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"fake")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "path": "data/raw/sernap/memoria.pdf",
                        "sha256": "abc123",
                        "page_types": [
                            {"page": 1, "type": "text"},
                            {"page": 2, "type": "image_or_scan"},
                            {"page": 3, "type": "table"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        f03_corpus.pdfplumber,
        "open",
        lambda _path: _Pdf([_Page("Texto página uno"), _Page(""), _Page("Tabla página tres")]),
    )

    result = f03_corpus.extract_sernap_text_pages(
        manifest_path=manifest,
        root=tmp_path,
        output_root=tmp_path / "out",
    )

    assert result["status"] == "ok"
    assert result["extracted"] == 2
    assert (tmp_path / "out" / "abc123" / "page_1.txt").read_text(encoding="utf-8") == "Texto página uno"
    assert (tmp_path / "out" / "abc123" / "page_3.txt").read_text(encoding="utf-8") == "Tabla página tres"
    assert not (tmp_path / "out" / "abc123" / "page_2.txt").exists()


def test_ocr_sernap_scans_soft_fails_when_ocr_unavailable(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "path": "data/raw/sernap/scan.pdf",
                        "sha256": "scan123",
                        "page_types": [{"page": 1, "type": "image_or_scan"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(f03_corpus, "_load_ocr", lambda: None)

    result = f03_corpus.ocr_sernap_scans(
        manifest_path=manifest,
        root=tmp_path,
        output_root=tmp_path / "out",
    )

    assert result["status"] == "ocr_unavailable"
    assert result["pages"] == [{"sha256": "scan123", "page": 1, "status": "ocr_unavailable"}]
