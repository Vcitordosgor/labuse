"""FICHE-1 lot 7 → SOURCES-1 lot 1 — les données réglementaires qui ATTENDAIENT une source.

Emplacement réservé, EBC, DPU, PEB, zonage A/B/C étaient déclarées « non calculée — source
absente » et JAMAIS servies. SOURCES-1 lot 1 a ingéré leurs réservoirs : l'en_attente est
LEVÉE, chaque donnée est rattachée à son réservoir réel et servie par un robinet nommé —
le mécanisme du trou visible a fonctionné (déclaré → ingéré → servi)."""
from __future__ import annotations

from labuse.registre import ROBINETS
from labuse.registre.donnees import DONNEES

ARRIVEES = {
    "er_emplacement_reserve": "gpu_prescriptions_er",
    "ebc_classe": "gpu_prescriptions_ebc",
    "dpu_perimetre": "dpu_perimetres",
    "peb_zone": "peb_dgac",
    "zonage_abc_logement": "zonage_abc_dhup",
}


def test_en_attente_levee_et_reservoir_reel():
    for cid, reservoir in ARRIVEES.items():
        d = DONNEES[cid]
        assert d.en_attente is None, cid
        assert reservoir in d.reservoirs, cid
        assert d.domaine_source, cid
        # producteur RÉEL nommé, plus jamais un « réservoir à venir »
        assert "à venir" not in d.fonction, cid


def test_servies_par_un_robinet():
    servies = {c for r in ROBINETS.values() for c in r.chiffres}
    manquantes = set(ARRIVEES) - servies
    assert not manquantes, manquantes
