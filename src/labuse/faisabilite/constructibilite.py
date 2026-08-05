"""Classification de constructibilité pour le DÉCLASSEMENT en étage 0.

Trois étiquettes distinctes (arbitrage Vic 29/07), JAMAIS confondues :
  A `declasse_zone_fermee`      — le règlement l'interdit AUJOURD'HUI (zone fermée à
                                  l'urbanisation : AU*st, habitat interdit économique).
                                  RÉVERSIBLE : une 2AU peut être ouverte par modification du PLU
                                  (matière du radar M24). On la garde VISIBLE avec son motif.
  B `declasse_non_constructible`— la géométrie l'interdit TOUJOURS (parcelle trop exiguë compte
                                  tenu des reculs, contrainte rédhibitoire). Permanent.
  C `non_verifiable`            — PLU non calibré sur la commune : pas de verdict, on SIGNALE
                                  (on ne déclasse pas sur un verdict absent).

SOURCE AUTORITAIRE : le verdict moteur (`parcel_faisabilite`), qui résout la zone via
`COALESCE(attrs->>'libelle', subtype, name)` (faisabilite/db.py) — le subtype (U/AU) prime, le
`name` descriptif n'est JAMAIS utilisé seul. NE JAMAIS ré-introduire une détection par
`resolve_zone(name)` / `constructible_neuf` isolé : elle faux-exclurait ~21 077 parcelles à
`name` descriptif (subtype U réel) et casserait 13 golden — cf.
`tests/test_declassement_constructibilite.py::test_ne_declasse_pas_name_descriptif` et
`REPLI_NON_OPTIMISTE_PHASE_A_MESURE.md`.
"""
from __future__ import annotations

from .engine import Faisabilite

# familles de cause structurée (engine.py : Faisabilite.cause)
_CAUSE_A = frozenset({"zone_transition", "habitat_interdit"})      # zone fermée au règlement
_CAUSE_B = frozenset({"terrain_exigu", "redhibitoire", "hauteur_indispo"})  # parcelle inconstructible

DECLASSE_ZONE_FERMEE = "declasse_zone_fermee"        # A
DECLASSE_NON_CONSTRUCTIBLE = "declasse_non_constructible"  # B
NON_VERIFIABLE = "non_verifiable"                    # C
# D (mandat AU-OUVERTURE, Vic 30/07) : zone AU dont l'OUVERTURE à l'urbanisation n'a JAMAIS été lue
# (Art. 1/2 non extrait). DISTINCT de zone_fermee : la zone n'est PAS fermée, son statut est INCONNU.
# TEMPORAIRE par construction (parcel_au_statut.computed_at) : dès l'article lu, la parcelle remonte
# ou tombe définitivement. Ne s'applique qu'aux AU « génériques » (non calibrées) ; les AU « dimensions
# seules » (règles de construction extraites) restent SERVIES avec une mention de fiche, pas déclassées.
DECLASSE_AU_STATUT_INCONNU = "declasse_au_statut_inconnu"
# Modèle AU AFFINÉ (GPU-PILOTE, Vic 30/07) — l'ouverture des AU est désormais LUE au règlement, donc
# trois traitements DISTINCTS remplacent l'« au statut inconnu » indifférencié :
#  · DECLASSE_AU_FERMEE  : AU FERMÉE au règlement (AUs/AUst réserve) → déclassement FERME, motif sourcé.
#  · AU_SOUS_PLANCHER    : AU conditionnelle_operation dont la parcelle est TROP PETITE pour
#    l'opération minimale imposée → reste SERVIE (jamais déclassée : c'est une candidate à
#    l'assemblage), avec mention + surface manquante + voisins assemblables. PAS un tier de déclassement.
#  · DECLASSE_AU_STATUT_INCONNU (ci-dessus) : réservé au phasage `conditionnelle_etat_tiers` (2AU→1AU)
#    = vrai inconnu (l'ouverture dépend de l'aménagement d'AUTRES zones, non déductible du règlement).
DECLASSE_AU_FERMEE = "declasse_au_fermee"
AU_SOUS_PLANCHER = "au_sous_plancher"          # SERVI — marqueur de fiche, JAMAIS un tier
# RÈGLE « BÂTIE RÉVÉLÉE » (arbitrage Vic 04/08, dette #4) : couche BD TOPO < 20 m² MAIS
# max(BD TOPO, CoSIA) ≥ 40 m² → une parcelle servie comme nue porte un bâti que l'image voit.
# Déclassement dédié, motif servi daté/sourcé (« bâti détecté CoSIA (PVA 2025), N m² »).
# La bande 20-40 m² n'est JAMAIS auto-déclassée (adjudication humaine sur cartes datées).
# Généralise et REMPLACE les 17 exceptions manuelles du 04/08 (toutes couvertes, CH1893 incluse).
DECLASSE_BATI_REVELE = "declasse_bati_revele"
# FILTRE CLIENT BÂTI (M28, A4) : bâtie SATURÉE (ratio > 40 %, ou 15-40 % récente/année absente
# non divisible, ou SDP saturée par le bâti existant) → tier dédié, badge, motif servi.
# Sort de brûlantes/chaudes, reste trouvable et motivée. Cache : parcel_filtre_bati.
DECLASSE_BATI_SATURE = "declasse_bati_sature"

#: labels de déclassement (retirés du ranking des tiers de tête, mais VISIBLES avec motif).
#: `AU_SOUS_PLANCHER` n'y figure PAS exprès : la parcelle reste SERVIE (candidate à l'assemblage).
DECLASSE_LABELS = frozenset({DECLASSE_ZONE_FERMEE, DECLASSE_NON_CONSTRUCTIBLE, NON_VERIFIABLE,
                             DECLASSE_AU_STATUT_INCONNU, DECLASSE_AU_FERMEE, DECLASSE_BATI_REVELE,
                             DECLASSE_BATI_SATURE})


def classify_constructibilite(faisa: Faisabilite | None) -> tuple[str | None, str]:
    """Retourne (label, motif). `label is None` ⇒ constructible, PAS de déclassement.
    `faisa is None` ⇒ hors PLU outillé ⇒ non vérifiable (signalé, pas déclassé)."""
    if faisa is None:
        return NON_VERIFIABLE, ("Constructibilité non vérifiable — PLU non calibré sur "
                                "cette commune.")
    if faisa.constructible:
        return None, ""
    if faisa.cause in _CAUSE_A:
        ref = f" ({faisa.zone})" if faisa.zone else ""
        return DECLASSE_ZONE_FERMEE, (f"Zone fermée à l'urbanisation — non constructible en "
                                      f"l'état{ref}.")
    # cause B, ou non constructible sans cause structurée → repli prudent en B (physique).
    return DECLASSE_NON_CONSTRUCTIBLE, ("Parcelle non constructible — surface ou reculs "
                                        "insuffisants.")


def build_constructibilite_batch(session, parcel_ids: list[int]) -> int:
    """Calcule et CACHE le verdict de constructibilité (table parcel_constructibilite) pour un
    lot de parcelles, via le moteur (`parcel_faisabilite`). Ne stocke QUE les non-constructibles
    et les non-vérifiables (label non nul) : une parcelle constructible = pas de ligne (le
    pipeline lit un LEFT JOIN → NULL = pas de déclassement). Lecture-moteur, écriture cache."""
    from sqlalchemy import text
    from .db import parcel_faisabilite

    n = 0
    for pid in parcel_ids:
        try:
            res = parcel_faisabilite(session, pid)
        except Exception:  # noqa: BLE001 — une parcelle ne casse pas le lot
            res = None
        faisa = None if res is None else res[1]
        label, motif = classify_constructibilite(faisa)
        if label is None:                       # constructible → pas de ligne
            session.execute(text("DELETE FROM parcel_constructibilite WHERE parcel_id = :p"),
                            {"p": pid})
            continue
        cause = None if faisa is None else faisa.cause
        session.execute(text(
            """INSERT INTO parcel_constructibilite (parcel_id, label, motif, cause, computed_at)
               VALUES (:p, :l, :m, :c, now())
               ON CONFLICT (parcel_id) DO UPDATE SET
                 label=EXCLUDED.label, motif=EXCLUDED.motif, cause=EXCLUDED.cause,
                 computed_at=now()"""),
            {"p": pid, "l": label, "m": motif, "c": cause})
        n += 1
    session.flush()
    return n
