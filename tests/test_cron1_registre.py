"""CRON-1 lot 1 — le registre unique : une raison par job, l'eau/l'exploitation, un test.
Ces tests ne touchent PAS la base (pur registre) → ils tournent partout."""
from labuse.jobs import JOBS, TOUCHE_EAU


def test_job_a_une_raison():
    """« Un job sans raison n'existe pas » — chaque job porte une RAISON (FR), un TOUCHE (eau|exploitation)
    et un TEST (node-id). Le méta-verrou du registre : impossible d'ajouter un job muet."""
    from pathlib import Path
    for nom, j in JOBS.items():
        assert j.raison and len(j.raison) > 20, f"{nom} : raison manquante ou trop courte"
        assert j.touche in ("eau", "exploitation"), f"{nom} : touche={j.touche!r}"
        assert j.test.startswith("tests/") and "::" in j.test, f"{nom} : test node-id manquant ({j.test!r})"
        fichier = j.test.split("::")[0]
        assert Path(fichier).exists(), f"{nom} : le fichier de test {fichier} n'existe pas"
    # TOUCHE_EAU est DÉRIVÉ du registre (une seule source), jamais tenu à la main.
    assert TOUCHE_EAU == frozenset(n for n, j in JOBS.items() if j.touche == "eau")


def test_backup_sans_trou():
    """Le backup est repris À L'IDENTIQUE du legacy (`30 9 * * *`) : le nouveau tourne au même instant que
    l'ancien ⇒ le remplacement (deploy.sh, lot 3 : pose AVANT retrait) ne laisse jamais une nuit sans dump."""
    b = JOBS["backup-postgres"]
    assert b.cron_utc == "30 9 * * *", "l'horaire doit rester identique au legacy (sans trou)"
    assert b.cadence == "quotidien" and b.touche == "exploitation"
    assert "7" in b.titre and "sans trou" in b.raison.lower()


def test_recoupements_arbitres():
    """Les 4 recoupements tranchés, chacun avec « RECOUPEMENT tranché » écrit dans sa raison."""
    attendu = {
        "backup-postgres": ("30 9 * * *", "quotidien"),   # legacy (le vivant), sans trou
        "ingest-bodacc":   ("40 2 * * *", "quotidien"),   # quotidien, avant les alertes
        "ingest-sitadel":  ("30 0 10 * *", "mensuel (10)"),  # mensuel (producteur mensuel)
        "ingest-dpe":      ("0 0 12 * *", "mensuel (12)"),   # mensuel (producteur mensuel)
    }
    for nom, (cron, cad) in attendu.items():
        j = JOBS[nom]
        assert j.cron_utc == cron and j.cadence == cad, f"{nom} : {j.cron_utc}/{j.cadence} != {cron}/{cad}"
        assert "recoupement tranché" in j.raison.lower(), f"{nom} : la raison ne dit pas l'arbitrage"


def test_sonde_sources_couvre_le_max():
    """La sonde existe (eau, chaque nuit 07:00) et couvre le MAXIMUM des sources à amont interrogeable :
    le SEED de la sentinelle ne fait que grandir (une URL n'y est inscrite qu'appelée pour de vrai)."""
    j = JOBS["sonde-sources"]
    assert j.touche == "eau" and j.cron_utc == "0 3 * * *"   # 07:00 Réunion
    from labuse import sentinelle
    # CRON-1 lot 1 a ajouté SRU (DHUP) au SEED (data.gouv last_update, probé le 18/09).
    noms = {e["name"] for e in sentinelle.SEED}
    assert "Inventaire SRU (DHUP)" in noms
    assert len(sentinelle.SEED) >= 36, f"le SEED a rétréci ({len(sentinelle.SEED)}) — la sonde ne doit que croître"


def test_agents_sources_dimanche():
    """L'agent IA tourne le DIMANCHE nuit, touche l'eau, et son plafond de dépense est nommé dans sa raison."""
    a = JOBS["agents-sources"]
    m, h, dom, mon, dow = a.cron_utc.split()
    assert dow == "0", f"doit tourner le dimanche (dow=0), pas {dow}"
    assert a.touche == "eau" and a.cadence == "hebdo (dim)"
    assert "plafond" in a.raison.lower()


def test_filtres_sources_repris():
    j = JOBS["filtres-sources"]
    assert j.touche == "eau" and j.cron_utc == "5 3 * * *"   # 07:05


def test_coherence_robinets_repris():
    j = JOBS["coherence-robinets"]
    assert j.touche == "eau" and j.cron_utc == "25 3 * * *"  # 07:25


def test_radar_na_pas_de_job():
    """Radar : PAS de job (échéance en base → G8 au lot 2). Aucun radar-cycle/radar-releves au registre."""
    assert "radar-cycle" not in JOBS and "radar-releves" not in JOBS
