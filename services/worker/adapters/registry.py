from __future__ import annotations

from worker.adapters.abt import AbtAdapter
from worker.adapters.agetic import AgeticAdapter
from worker.adapters.cge import CgeAdapter
from worker.adapters.firms import FirmsAdapter
from worker.adapters.gaceta_nacional import GacetaNacionalAdapter
from worker.adapters.gaceta_scz import GacetaSczAdapter
from worker.adapters.mindef import MindefAdapter
from worker.adapters.presupuesto_abierto import PresupuestoAbiertoAdapter
from worker.adapters.scz import GadSczAdapter, GamSczAdapter
from worker.adapters.sernap import SernapAdapter
from worker.adapters.sicoes import SicoesAdapter

ADAPTERS = {
    "agetic": AgeticAdapter,
    "sicoes": SicoesAdapter,
    "presupuesto_abierto": PresupuestoAbiertoAdapter,
    "cge": CgeAdapter,
    "gad_scz": GadSczAdapter,
    "gam_scz": GamSczAdapter,
    "mindef": MindefAdapter,
    "abt": AbtAdapter,
    "gaceta_scz": GacetaSczAdapter,
    "gaceta_nacional": GacetaNacionalAdapter,
    "sernap": SernapAdapter,
    "firms": FirmsAdapter,
}


def get_adapter(source_id: str):
    cls = ADAPTERS.get(source_id)
    if not cls:
        raise KeyError(f"Unknown source_id: {source_id}")
    return cls()
