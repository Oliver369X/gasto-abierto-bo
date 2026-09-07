"""Gaceta Oficial del Estado Plurinacional — decretos sobre incendios."""
from __future__ import annotations

from worker.adapters.base import Cursor, RawItem
from worker.adapters.gaceta_scz import GacetaSczAdapter


class GacetaNacionalAdapter(GacetaSczAdapter):
    source_id = "gaceta_nacional"
    base_url = "http://www.gacetaoficialdebolivia.gob.bo"
    default_entity = "Órgano Ejecutivo del Estado Plurinacional"
    default_territory = "Bolivia"
    default_territory_level = "pais"

    def discover(self, cursor: Cursor) -> list[RawItem]:
        if cursor.payload.get("fixture_path"):
            return [RawItem(uri=f"file://{cursor.payload['fixture_path']}", meta={})]
        return [RawItem(
            uri=cursor.payload.get("url", f"{self.base_url}/normas/buscarg/incendios"),
            meta={},
        )]
