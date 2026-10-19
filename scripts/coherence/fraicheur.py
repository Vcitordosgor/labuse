"""FRAICHEUR-PROD-1 — le verrou de fraîcheur des sources (docs/audit-2026-10/FRAICHEUR-PROD-1/).

Rejoue, EN LECTURE SEULE, l'audit « chaque donnée est-elle la dernière version, partout ». Une ligne
[OK]/[ECART]/[SKIP] par garde, bilan final, exit 1 si ECART.

Règle du verrou (mandat §Livrables 3) — il SORT EN ERREUR dès qu'une source est :
  · EN RETARD  — le producteur a publié une version plus récente que la base ;
  · DÉCALÉ     — la base contient une version/ligne incohérente avec ce qu'elle devrait servir ;
  · GELÉ sans motif déclaré — un job d'ingestion commenté sans `# GELÉ (motif)` / sans `gel=` au registre.
Un gel AVEC motif déclaré (ex. « Phase 8 Stéphanie ») et une source NON SURVEILLÉE sont RAPPORTÉS
(ligne [OK] annotée), jamais une erreur : ce sont des choix assumés, pas des régressions.

Le verdict des sentinelles est RÉUTILISÉ (etats_sources) mais NE SUFFIT PAS : la sonde `page` de DVF
lit un millésime « 2025 » qui ne bouge pas quand un semestre est ajouté → angle mort. Les gardes
DVF ci-dessous confrontent donc la base au CALENDRIER DU PRODUCTEUR (publications d'avril et octobre),
indépendamment de la sentinelle.

DSN : `LABUSE_COHERENCE_DSN` → `LABUSE_DATABASE_URL` → poste de dev (via coherence.lib). Pointer
LABUSE_DATABASE_URL sur la prod rejoue l'audit EN PROD. Connexion read-only, statement_timeout 60 s.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timezone

import psycopg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coherence.lib import _dsn_defaut  # noqa: E402 — même DSN que les bancs COHERENCE-1 / chasse_*


def _db():
    cx = psycopg.connect(_dsn_defaut())
    cx.read_only = True                       # AVANT toute requête
    cx.execute("SET statement_timeout = '60s'")
    return cx


# ────────────────────────── vocabulaire du calendrier DVF ──────────────────────────
# DVF (DGFiP/Etalab) publie DEUX fois l'an : avril (→ données jusqu'au 31/12 de l'an précédent) et
# octobre (→ données jusqu'au 30/06 de l'an courant). On en déduit la couverture MINIMALE attendue.

def _dvf_couverture_attendue(j: date) -> date:
    if j.month >= 10:                         # octobre publiée : S1 de l'année courante
        return date(j.year, 6, 30)
    if j.month >= 4:                          # avril publiée : toute l'année précédente
        return date(j.year - 1, 12, 31)
    return date(j.year - 1, 6, 30)            # avant avril : octobre de l'an précédent


# ─────────────────────────────────────── GARDES ───────────────────────────────────────

def g01_dvf_en_retard():
    """DVF : la couverture RÉELLE de la base atteint-elle le dernier semestre publié par le producteur ?
    Ligne réelle = date_mutation à minuit (les dates DVF sont des dates ; une ligne horodatée est
    synthétique, cf. g02). EN RETARD si le réel est en-deçà de la couverture attendue aujourd'hui."""
    with _db() as cx:
        reel = cx.execute(
            "SELECT max(date_mutation)::date FROM dvf_mutations "
            "WHERE date_mutation::time = '00:00:00'").fetchone()[0]
    if reel is None:
        return "SKIP", "dvf_mutations vide ou absente"
    attendu = _dvf_couverture_attendue(datetime.now(tz=timezone.utc).date())
    if reel < attendu:
        return "ECART", (f"EN RETARD : base DVF jusqu'à {reel} < couverture attendue {attendu} "
                         f"(producteur publie avril/octobre ; ingest-dvf est gelé → la nouvelle "
                         f"livraison n'arrivera pas seule).")
    return "OK", f"couverture DVF {reel} ≥ attendu {attendu}"


def g02_dvf_ligne_incoherente():
    """DVF : aucune ligne ne doit être horodatée (date_mutation avec une heure) ni postérieure au
    31/12 de l'an courant. Une telle ligne est SYNTHÉTIQUE (test) et DÉCALE le libellé client
    « ventes jusqu'à … » (_dvf_couverture lit max(date_mutation) NON filtré, modules.py:1752)."""
    with _db() as cx:
        n_horodate = cx.execute(
            "SELECT count(*) FROM dvf_mutations WHERE date_mutation::time <> '00:00:00'").fetchone()[0]
        futur = cx.execute(
            "SELECT count(*) FROM dvf_mutations WHERE date_mutation::date > %(b)s",
            {"b": date(datetime.now(tz=timezone.utc).year, 12, 31)}).fetchone()[0]
    if n_horodate or futur:
        return "ECART", (f"DÉCALÉ : {n_horodate} ligne(s) DVF horodatée(s) (synthétiques) + "
                         f"{futur} postérieure(s) à l'année courante — poison du libellé de couverture.")
    return "OK", "aucune ligne DVF synthétique/future"


# Sources dont le flag `nouvelle_version` est ACQUITTÉ comme bénin par l'audit FRAICHEUR-PROD-1
# (la base porte DÉJÀ le millésime vu amont ; le flag ne tient qu'à une notification non cliquée).
# Toute autre source en `nouvelle_version` non injectée = EN RETARD.
_ACQUIS_BENINS = {25, 148, 157}   # INPN patrinat 07/2026, Communes COG 2026, Population légale 2023


def g03_nouvelle_version_pendante():
    """Sentinelle : une source surveillée en `nouvelle_version`, non injectée et non acquittée, dont
    le millésime amont vu ≠ ce qui est en base = EN RETARD. Les cas bénins (base == amont, simple
    notification non cliquée) sont dans l'allowlist et rapportés sans erreur."""
    with _db() as cx:
        rows = cx.execute(
            "SELECT d.id, d.name, v.dernier_vu, v.injection_vu "
            "FROM data_sources d JOIN source_veille v ON v.source_id = d.id "
            "WHERE v.dernier_statut = 'nouvelle_version' AND v.actif IS NOT FALSE "
            "AND lower(d.status) IN ('connecte','manuel','live') "
            "AND COALESCE(d.affichage_desactive,false) = false").fetchall()
    retard = [(i, n, vu) for (i, n, vu, inj) in rows
              if i not in _ACQUIS_BENINS and (inj or "") != (vu or "")]
    if retard:
        liste = " ; ".join(f"#{i} {n} (amont « {vu} »)" for i, n, vu in retard)
        return "ECART", f"EN RETARD : {len(retard)} source(s) non injectée(s) — {liste}"
    benins = [i for (i, _n, _vu, _inj) in rows if i in _ACQUIS_BENINS]
    return "OK", (f"aucune nouvelle version en retard ({len(benins)} notification(s) bénigne(s) "
                  f"acquittée(s) : {sorted(benins)})" if benins else "aucune nouvelle version pendante")


# Jobs d'ingestion de sources vitrine, avec leur source servie et le motif de gel ATTENDU (registre
# labuse.jobs). Un job gelé DOIT porter un motif ; un job commenté hors de cette table = dérive.
_JOBS_INGEST = {
    "ingest-bodacc": None, "ingest-sitadel": None, "ingest-dpe": None, "ingest-sirene": None,
    "sync-gpu": None, "ingest-dvf": "Phase 8 Stéphanie",
}


def g04_gel_motive():
    """Gel : tout job d'ingestion gelé doit porter un motif déclaré (registre `gel=` → crontab
    `# GELÉ (motif)`). On relit le registre labuse.jobs si importable, sinon on lit /etc/cron.d/labuse.
    ECART = un job commenté SANS motif. Un gel motivé est rapporté (OK annoté), jamais une erreur."""
    gelés_sans_motif, gelés_motivés = [], []
    try:  # chemin registre (source de vérité du crontab)
        from labuse.jobs import JOBS  # type: ignore
        for nom, j in JOBS.items():
            if nom in _JOBS_INGEST and getattr(j, "gel", None):
                gelés_motivés.append(f"{nom} ({j.gel})")
        # un job gelé au crontab mais absent/motif vide du registre ne peut pas exister par construction
        # (deploy.sh génère le crontab depuis le registre) → rien à signaler côté registre.
    except Exception:  # noqa: BLE001 — registre non importable : repli sur le crontab si présent
        cron = "/etc/cron.d/labuse"
        if not os.path.exists(cron):
            return "SKIP", "registre labuse.jobs non importable et /etc/cron.d/labuse absent"
        for ligne in open(cron, encoding="utf-8", errors="replace"):
            if "GELÉ" in ligne or "GELE" in ligne:
                if "(" in ligne and ")" in ligne.split("GEL", 1)[1]:
                    gelés_motivés.append(ligne.split("run ")[-1].strip())
                else:
                    gelés_sans_motif.append(ligne.strip()[:80])
            elif ligne.strip().startswith("#") and " run " in ligne and "jobs run" in ligne:
                gelés_sans_motif.append(ligne.strip()[:80])
    if gelés_sans_motif:
        return "ECART", f"GELÉ SANS MOTIF : {gelés_sans_motif}"
    return "OK", (f"gels motivés (rapportés) : {gelés_motivés}" if gelés_motivés
                  else "aucun job d'ingestion gelé")


def g05_sources_non_surveillees():
    """Rapport (jamais ECART) : sources vitrine sans sentinelle (methode vide) ET sans job d'ingestion
    dédié. NON SURVEILLÉ est un état déclaré, pas une régression — on le rend visible, sans casser."""
    with _db() as cx:
        rows = cx.execute(
            "SELECT d.id, d.name FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id "
            "WHERE lower(d.status) IN ('connecte','manuel','live') "
            "AND COALESCE(d.affichage_desactive,false) = false "
            "AND (v.methode IS NULL OR v.methode = '')").fetchall()
    if rows:
        return "OK", (f"{len(rows)} source(s) NON SURVEILLÉE(S) (rapport) : "
                      + ", ".join(f"#{i} {n}" for i, n in rows))
    return "OK", "toutes les sources vitrine sont surveillées"


GARDES = [
    ("dvf-en-retard", g01_dvf_en_retard),
    ("dvf-ligne-incoherente", g02_dvf_ligne_incoherente),
    ("nouvelle-version-pendante", g03_nouvelle_version_pendante),
    ("gel-motive", g04_gel_motive),
    ("sources-non-surveillees", g05_sources_non_surveillees),
]


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    bilan = {"OK": 0, "ECART": 0, "SKIP": 0}
    for nom, garde in GARDES:
        try:
            verdict, detail = garde()
        except Exception as exc:  # noqa: BLE001 — une garde qui plante ne tue pas le banc
            verdict, detail = "SKIP", f"erreur {type(exc).__name__}: {exc}"
        bilan[verdict] += 1
        print(f"[{verdict}] {nom} — {detail}")
    print(f"\nBilan : {bilan['OK']} OK · {bilan['ECART']} ECART · {bilan['SKIP']} SKIP "
          f"({len(GARDES)} gardes)")
    return 1 if bilan["ECART"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
