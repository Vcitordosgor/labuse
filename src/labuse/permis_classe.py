"""OUTIL-PERMIS-FIX-1 (LOT 1 & 2) — LA définition UNIQUE de l'état d'un permis.

Avant ce module, l'état d'un permis était défini à QUATRE endroits qui ne s'accordaient pas :
`_permis_etat_pred` (compteur/liste, horloge `dmax`), le `perimClasse` du front (mode parcelle,
priorité au code 6), la soustraction du front (chip « Autres »), et `permis_point_mort`
(dormant, horloge `now()` + proxy « absence d'exclusion au run »). D'où les constats du relecteur :
le filtre « Autres » trouvait 4 880 permis de moins que son compteur, un permis achevé changeait
d'état selon l'échelle, et 28 des 30 dormants témoins avaient du bâti sur leurs parcelles.

Ici, UNE SEULE fonction classe un permis, avec un ORDRE DE PRIORITÉ ÉCRIT, servie à l'identique par
le compteur, le filtre, la liste, la carte et le mode parcelle (modules.py) ainsi que par la fiche
commune (commune.py). Le compteur et le filtre dérivent du MÊME prédicat → compteur = lignes du
filtre, par construction (plus aucun état obtenu par soustraction).

ORDRE DE PRIORITÉ (le premier qui s'applique gagne) :

  1. ACHEVÉ   — achèvement déclaré : `daact` présente OU code état 6 (travaux achevés).
               (Avant : l'île regardait `daact`, le mode parcelle regardait le code 6 → divergence.
                Désormais les deux, partout. Un permis achevé a le même état à toutes les échelles.)
  2. DORMANT  — un permis de construire (PC) AUTORISÉ, NON annulé (code ≠ 4), NON « travaux
               commencés » (code ≠ 5), sans achèvement déclaré (pas de `daact`), de plus de 3 ans,
               ET sans bâtiment détecté sur ses parcelles (emprise de bâti MESURÉE < 10 m²,
               `parcel_bati_emprise` = intersection parcelle × empreintes BD TOPO). Le dormant exige
               une parcelle MESURABLE (présente dans `parcel_bati_emprise`) : on ne qualifie jamais
               « terrain nu » un terrain qu'on ne sait pas mesurer.
  3. RÉCENT   — autorisé depuis ≤ 24 mois (fenêtre ancrée sur la FIN DES DONNÉES `dmax`).
  4. AUTRE    — tout le reste (annulés anciens, travaux commencés anciens, bâti détecté, 24–36 mois…).

HORLOGE UNIQUE : toutes les fenêtres (24 mois « récent », 36 mois « dormant ») sont ancrées sur
`dmax` = max(date) de `sitadel_permits` (la fin du flux Sitadel, antérieure à aujourd'hui). Avant,
le dormant était ancré sur `now()` : la borne avançait toute seule (« 50 nouvelles opportunités »
qui n'étaient que l'horloge qui glisse) et finissait par recouper la fenêtre récente figée. Une
seule horloge = un seul état par permis, reproductible.

Le LIBELLÉ dit ce qui est MESURÉ : « sans achèvement déclaré, aucun bâtiment détecté » — jamais
« terrain resté nu » ni « caducité » (la validité juridique d'un PC — 3 ans + prorogations, voire
5 ans pour 2022-2024 — n'est PAS ce qu'on mesure ; on mesure l'absence de DAACT et l'absence de
bâti).
"""
from __future__ import annotations

#: fenêtre « récent » (mois), ancrée sur dmax. 24 mois PARTOUT (compteur, filtre, carte, parcelle).
RECENT_MOIS = 24
#: ancienneté minimale d'un dormant (mois), ancrée sur dmax. « plus de 3 ans ».
DORMANT_MOIS = 36
#: seuil d'emprise bâtie (m²) au-dessus duquel une parcelle est « bâtie » (décision Vic).
BATI_SEUIL_M2 = 10

#: les quatre états de la partition (somme = total). Ordre d'affichage géré par le front.
ETATS = ("recent", "dormant", "acheve", "autre")

#: code ETAT_DAU d'un permis ANNULÉ (= la MÊME règle que ingestion.permits.est_annule et que le CASE
#: d'état ci-dessous, qui exclut '4' du dormant). Un seul littéral, ici.
ANNULE_CODE = "4"


def annule_sql(a: str = "") -> str:
    """Prédicat SQL « ce permis est ANNULÉ » (ETAT_DAU=4) — jumelle SQL de `est_annule` (Python), LA
    règle unique de l'outil (pas une nouvelle). `a` = préfixe d'alias ('' ou 's.'). `etat` NULL/absent
    → NON annulé. Pour « non annulé » qui compte aussi les NULL : `NOT COALESCE((annule_sql), false)`."""
    return f"{a}raw->>'etat' = '{ANNULE_CODE}'"


def _dormant_sql(a: str, dmax: str, bati: bool = True) -> str:
    """Prédicat SQL « ce permis est DORMANT » (hors priorité achevé, traitée avant dans le CASE).

    `a` = préfixe d'alias de la table `sitadel_permits` (''/'s.'). `dmax` = expression SQL de la
    fin des données (paramètre lié `:dmax` ou sous-requête). S'appuie sur `parcel_bati_emprise`
    (idu → emprise de bâti mesurée en m²), précalculée pour les parcelles de permis PC.

    `bati=False` (table `parcel_bati_emprise` ABSENTE : base fraîche, base de test non outillée) →
    le prédicat vaut `false` : AUCUN dormant plutôt qu'un 500 (on ne mesure pas → on ne qualifie pas).
    La couche `parcel_bati_emprise` se construit par `ensure_parcel_bati_emprise` (faisabilite)."""
    if not bati:
        return "false"
    return (
        f"{a}type = 'PC'"
        f" AND ({a}raw->>'etat' IS NULL OR {a}raw->>'etat' NOT IN ('4','5','6'))"
        f" AND {a}raw->>'daact' IS NULL"
        f" AND {a}date < {dmax} - interval '{DORMANT_MOIS} months'"
        # OUTIL-PERMIS-FIX-2 (Défaut C) — « aucun bâtiment détecté sur LEURS parcelles » (toutes) : on
        # exige que CHAQUE parcelle du permis soit RETROUVÉE et MESURÉE sans bâti. Avant, une parcelle
        # absente de `parcels` (donc de `parcel_bati_emprise`) était IGNORÉE : si le bâti du permis était
        # sur elle, il restait invisible et le permis était faussement « dormant » (47/895, relecture-1).
        # Le permis doit avoir au moins une parcelle, et AUCUNE ne doit être non mesurée (_be.idu NULL)
        # ni bâtie (≥ seuil).
        f" AND jsonb_array_length({a}idu_codes) >= 1"
        f" AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements_text({a}idu_codes) _c(idu)"
        f"   LEFT JOIN parcel_bati_emprise _be ON _be.idu = _c.idu"
        f"   WHERE _be.idu IS NULL OR _be.bati_m2 >= {BATI_SEUIL_M2})"
    )


def etat_case_sql(a: str = "", dmax: str = ":dmax", bati: bool = True) -> str:
    """L'EXPRESSION SQL qui classe un permis en recent|dormant|acheve|autre, dans l'ordre de
    priorité écrit en tête de module. À utiliser telle quelle en SELECT (liste, parcelle) ou en
    GROUP BY (compteur). `a` = préfixe d'alias ; `dmax` = expression de la fin des données ;
    `bati` = la couche d'emprise bâtie est disponible (sinon le dormant est inactif, cf. _dormant_sql)."""
    return (
        "CASE"
        f" WHEN {a}raw->>'daact' IS NOT NULL OR {a}raw->>'etat' = '6' THEN 'acheve'"
        f" WHEN {_dormant_sql(a, dmax, bati)} THEN 'dormant'"
        f" WHEN {a}date >= {dmax} - interval '{RECENT_MOIS} months' THEN 'recent'"
        " ELSE 'autre' END"
    )


def etat_pred_sql(etat: str | None, a: str = "", dmax: str = ":dmax", bati: bool = True) -> str:
    """Fragment « AND <ce permis est dans l'état `etat`> » pour FILTRER la liste/la carte sur un
    état. Dérivé du MÊME CASE que le compteur → le filtre et le compteur portent toujours sur les
    mêmes identifiants (preuve LOT 1 : compteur = nombre de lignes du filtre). `etat` hors
    whitelist → aucun filtre (la liste porte alors sur les quatre états)."""
    if etat not in ETATS:
        return ""
    return f" AND ({etat_case_sql(a, dmax, bati)}) = '{etat}'"


def bati_table_existe(db) -> bool:
    """La couche d'emprise bâtie `parcel_bati_emprise` est-elle présente ? (garde des requêtes dormant,
    cf. _dormant_sql). Lecture catalogue, très légère."""
    from sqlalchemy import text as _t
    return bool(db.execute(_t("SELECT to_regclass('parcel_bati_emprise') IS NOT NULL")).scalar())
