from pathlib import Path

from worker.adapters.gaceta_scz import GacetaSczAdapter
from worker.adapters.registry import get_adapter


FIXTURE = Path(__file__).parent / "fixtures" / "real" / "gaceta_scz_sample.html"


def test_gaceta_scz_parses_html_and_filters_non_fire_decrees():
    records = GacetaSczAdapter().parse(FIXTURE.read_bytes())

    assert len(records) == 1
    data = records[0].data
    assert data["decree_number"] == "482"
    assert data["event_type"] == "incendio_forestal"
    assert data["promulgated_at"] == "2024-09-07"
    assert "incendios forestales" in data["title"].lower()


def test_gaceta_nacional_is_registered():
    assert get_adapter("gaceta_nacional").source_id == "gaceta_nacional"
