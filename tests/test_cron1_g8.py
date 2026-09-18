"""CRON-1 lot 2 — le verrou G8 : « aucune source vitrine sans contrôle depuis plus de 7 jours ».
Logique PURE (sans DB) : rouge sur un état RÉEL reconstitué (agent à 0 € → les hors-sonde sans contrôle),
vert sur un cas construit où les 94 ont un contrôle récent. La preuve RED sur la vraie base est dans
CRON-1-LOT2.md (15 sources nommées)."""
from datetime import datetime, timezone, timedelta
from labuse.circuit_garanties import classer_sans_controle

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
SEUIL = NOW - timedelta(days=7)
RECENT = NOW - timedelta(days=1)
VIEUX = NOW - timedelta(days=30)


def _row(name, methode, actif=True, passage=None):
    return {"name": name, "methode": methode, "actif": actif, "dernier_passage_at": passage}


def test_g8_rouge_agent_a_zero_les_hors_sonde():
    """État réel reconstitué : 3 sondées récentes (OK), 1 sonde toute neuve sans passage (OK, surveillée),
    et les HORS-SONDE (rappel / aucune) → sans contrôle avec l'agent à 0 €. G8 doit être ROUGE et les nommer."""
    rows = [
        _row("BODACC", "api", passage=RECENT),          # sondée récemment → OK
        _row("Cadastre", "entete", passage=RECENT),     # OK
        _row("Géorisques", "temoin", passage=RECENT),   # OK
        _row("Inventaire SRU (DHUP)", "api", passage=None),   # sonde neuve, 1er passage en attente → OK
        _row("VRD / assainissement (SPANC)", "rappel", passage=None),   # rappel → sans contrôle
        _row("PVGIS (Commission européenne)", "rappel", passage=None),  # rappel → sans contrôle
        _row("OpenStreetMap / Overpass", None, passage=None),           # aucune sonde → sans contrôle
    ]
    sans = classer_sans_controle(rows, SEUIL)
    noms = {s["name"] for s in sans}
    assert noms == {"VRD / assainissement (SPANC)", "PVGIS (Commission européenne)",
                    "OpenStreetMap / Overpass"}, "G8 doit nommer exactement les hors-sonde sans contrôle"
    # SRU (sonde neuve) et les sondées récentes ne sont PAS sans contrôle.
    assert "Inventaire SRU (DHUP)" not in noms and "BODACC" not in noms


def test_g8_rouge_sonde_en_panne():
    """Une sonde CONFIGURÉE mais muette depuis plus de 7 jours (en panne) est sans contrôle → rouge."""
    rows = [_row("Sitadel", "api", passage=VIEUX)]
    sans = classer_sans_controle(rows, SEUIL)
    assert len(sans) == 1 and "muette" in sans[0]["motif"]


def test_g8_vert_quand_les_94_ont_un_controle_recent():
    """Cas CONSTRUIT — les 94 ont toutes un passage de sonde de moins de 7 jours (plafond agent > 0 €,
    l'agent a repris les hors-sonde) : G8 est VERT (aucune sans contrôle)."""
    rows = [_row(f"source_{i}", "api", passage=RECENT) for i in range(94)]
    assert classer_sans_controle(rows, SEUIL) == []
