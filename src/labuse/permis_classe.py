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


# ── OUTIL-PERMIS-FIX-8 (LOT 1) — LA fonction UNIQUE « cette date de dépôt est-elle AFFICHABLE ? » ──
# Le contre-audit ASTRA-4 (point 1) : pour 97441626E0304, la fiche écartait correctement le dépôt
# (DR_DEPOT 01/06/2020, dont l'année CONTREDIT l'AN_DEPOT publié = 2026), mais l'historique parcellaire
# et le Dossier lisaient la date BRUTE → six ans d'« instruction » fallacieux. Désormais UNE SEULE règle
# décide, et TOUS les lecteurs l'appellent (fiche, liste, historique parcellaire, fiche parcelle, Dossier).
#
# RÈGLE (décisive = « année de la date = année de dépôt du fichier ») : une date de dépôt n'est affichable
# que si c'est une date PRÉCISE fiable — présente, ANTÉRIEURE à l'autorisation, PAS un 1er janvier (= proxy
# d'année, non un vrai jour), AN_DEPOT exploitable (4 chiffres) ET année de la date == AN_DEPOT. Sinon
# (DR_DEPOT = autorisation / postérieur / proxy 01-01 / année contradictoire / absent) → écartée, et rien
# n'est écrit à sa place. (C'est la validation que la fiche appliquait déjà, extraite ici pour être unique.)
_DEPOT_COND_TMPL = (
    "{a}date_depot IS NOT NULL AND {a}date IS NOT NULL AND {a}date_depot < {a}date"
    " AND NOT (EXTRACT(MONTH FROM {a}date_depot) = 1 AND EXTRACT(DAY FROM {a}date_depot) = 1)"
    " AND {a}raw->>'an_depot' ~ '^[0-9]{{4}}$'"
    " AND EXTRACT(YEAR FROM {a}date_depot)::int = ({a}raw->>'an_depot')::int"
)


def depot_affichable_cond_sql(a: str = "s.") -> str:
    """La CONDITION SQL « cette date de dépôt est affichable » (booléen), `a` = préfixe d'alias de
    `sitadel_permits` (''/'s.'). Les colonnes lues : `date_depot` (DR_DEPOT), `date` (autorisation),
    `raw->>'an_depot'` (AN_DEPOT). Le regex garde le cast `::int` (évalué seulement si 4 chiffres)."""
    return _DEPOT_COND_TMPL.format(a=a)


def depot_affichable_sql(a: str = "s.") -> str:
    """Le CASE SQL qui rend la date de dépôt AFFICHABLE (::date) ou NULL — à utiliser tel quel en SELECT
    (fiche, historique, frise, Dossier). NULL quand le dépôt est écarté (rien écrit à sa place)."""
    return f"CASE WHEN {depot_affichable_cond_sql(a)} THEN {a}date_depot::date END"


# ── OUTIL-PERMIS-FIX-12 (LOT 1) — LA date de l'ÉVÉNEMENT réellement daté, pour la SÉLECTION des veilles ──
# Contre-audit ASTRA-6 (point 2) : la veille de parcelle (events.evaluer_suivis) et l'alerte de zone
# (alertes.compute_alertes) SÉLECTIONNAIENT les permis sur la date de dépôt BRUTE (`date_depot >= since`
# / `date_depot IS NOT NULL`). Résultat faux dans les DEUX sens : un faux dépôt récent fait entrer un
# permis autorisé AVANT le suivi (9744012520010), et un dépôt brut ancien écarte un permis autorisé
# DANS le suivi (97441626E0304) ou sans dépôt du tout (278 permis géolocalisés autorisés inéligibles).
#
# RÈGLE : on sélectionne sur la date de l'ÉVÉNEMENT réellement daté = le dépôt s'il est AFFICHABLE (la
# fonction unique, année = AN_DEPOT…), SINON la date d'autorisation. C'est la même date que celle déjà
# servie en `fait_date` (titre/détail/tri). La date de dépôt brute rejetée ne sert JAMAIS de critère.
def evenement_date_sql(a: str = "s.") -> str:
    """L'expression SQL de la date de l'ÉVÉNEMENT réellement daté d'un permis : `COALESCE(dépôt
    affichable, autorisation)`. `a` = préfixe d'alias de `sitadel_permits` (''/'s.'/'sp.'). NULL
    seulement si le permis n'a NI dépôt affichable NI autorisation (cas marginal) → inéligible."""
    return f"COALESCE({depot_affichable_sql(a)}, {a}date::date)"


# ── OUTIL-PERMIS-FIX-13 (LOT 3) — LA date de DÉPÔT réelle, pour FILTRER/GROUPER « ce qui est déposé » ──
# Contre-audit ASTRA-7 (point 3) : Scan patrimoine (veille_promoteurs) sélectionnait « opérations déposées
# depuis » et groupait les opérations (fenêtre 24 mois « déposés sur une même période ») sur la date
# d'AUTORISATION (`date`) — un PC déposé en 2025 mais autorisé en 2026 (97441625A0405) entrait à tort dans
# « déposées depuis le 01/01/2026 ». La date de dépôt BRUTE (`date_depot`) est, elle, corrompue (= parfois
# l'autorisation). On lit donc la date de dépôt RÉELLE : le dépôt AFFICHABLE (fonction unique) s'il est
# fiable, SINON le 1er janvier de l'ANNÉE DE DÉPÔT officielle `AN_DEPOT` (borne basse, millésime fiable du
# fichier SDES) — JAMAIS la date d'autorisation.
def depot_date_sql(a: str = "s.") -> str:
    """L'expression SQL de la date de DÉPÔT réelle d'un permis, pour la DÉFINITION des périodes (24 mois) :
    `COALESCE(dépôt affichable, 1er janvier de AN_DEPOT)`. `a` = préfixe d'alias de `sitadel_permits`. NULL
    si ni dépôt affichable ni AN_DEPOT exploitable (4 chiffres). Le 1er janvier est un PROXY D'ANNÉE (la
    tolérance de 24 mois l'absorbe) — il ne doit JAMAIS servir un FILTRE au jour (cf. depot_depuis_cond_sql)."""
    return (f"COALESCE({depot_affichable_sql(a)}, CASE WHEN {a}raw->>'an_depot' ~ '^[0-9]{{4}}$' "
            f"THEN make_date(({a}raw->>'an_depot')::int, 1, 1) END)")


# ── OUTIL-PERMIS-FIX-16 (LOT 5) — FILTRE « déposées depuis » SANS jour inventé ──────────────────────
# Contre-audit ASTRA-8 (point 5) : « opérations déposées depuis » tombait de 5 (au 01/01/2026) à 0 (au
# 02/01/2026). Un dépôt connu à la seule ANNÉE (AN_DEPOT, sans jour affichable) était remplacé par le 1er
# janvier, un jour INVENTÉ : il passait « depuis le 01/01 » mais plus « depuis le 02/01 ». On ne compare donc
# un dépôt au JOUR que s'il est connu AU JOUR (dépôt affichable) ; sinon on compare à l'ANNÉE (AN_DEPOT >=
# année du seuil) — jamais un jour fabriqué, et aucune falaise au 2 janvier. Aucun chiffre faussé.
def depot_depuis_cond_sql(a: str = "s.", param: str = ":depuis") -> str:
    """Prédicat SQL « ce permis est déposé le `param` ou après ». Dépôt connu AU JOUR (affichable) →
    comparaison au jour ; connu à la seule ANNÉE (AN_DEPOT) → comparaison à l'ANNÉE du seuil ; inconnu →
    faux. `param` = bind de la date seuil (ISO)."""
    aff = depot_affichable_sql(a)
    seuil = f"CAST({param} AS date)"
    return (f"((({aff}) IS NOT NULL AND ({aff}) >= {seuil}) "
            f"OR (({aff}) IS NULL AND {a}raw->>'an_depot' ~ '^[0-9]{{4}}$' "
            f"AND ({a}raw->>'an_depot')::int >= EXTRACT(YEAR FROM {seuil})::int "
            f"AND ({a}date IS NULL OR {a}date::date >= {seuil})))")


def depot_jour_connu_sql(a: str = "s.") -> str:
    """Booléen SQL « le JOUR de dépôt est connu » (dépôt affichable non nul) — l'écran peut dire « jour de
    dépôt inconnu » sinon, plutôt que d'exhiber un jour fabriqué."""
    return f"({depot_affichable_sql(a)}) IS NOT NULL"


# ── OUTIL-PERMIS-FIX-14 — LA date d'AUTORISATION SOURCE (sitadel_permits.date), pour TOUT AFFICHAGE ──
# Relecture-permis-7 (point 3) : la table dérivée `p_model_permits` est PÉRIMÉE — `date_autorisation`
# porte parfois la date de dépôt BRUTE (ex. 97415000DP0016 : 28/08/2023 au lieu du 26/02/2020 réel) et
# il lui manque des couples PC/parcelle (422 île). Tout écran/route/export qui AFFICHE une date
# d'autorisation de permis doit la lire à la SOURCE `sitadel_permits.date` (comme pc_caducs/veille le
# font déjà), JAMAIS dans `p_model_permits`. La table dérivée reste réservée aux features du modèle P.
def date_autorisation_sql(a: str = "sp.") -> str:
    """L'expression SQL de la date d'AUTORISATION SOURCE d'un permis = `sitadel_permits.date::date`.
    `a` = préfixe d'alias de `sitadel_permits` (''/'s.'/'sp.'). À lire à la source, jamais via la table
    dérivée `p_model_permits.date_autorisation` (périmée, FIX-14)."""
    return f"{a}date::date"


def permis_autorise_apres(db, idu: str, apres):
    """La date d'autorisation la PLUS RÉCENTE d'un permis rattaché à la parcelle `idu` qui soit
    STRICTEMENT postérieure à `apres` (objet `date` ou ISO), ou None. Lit la SOURCE
    `sitadel_permits.date` (explosion de `idu_codes`) — JAMAIS `p_model_permits` (périmée, FIX-14).
    Sert l'avertissement §Bâti « un permis autorisé après le survol a pu changer le bâti ». None aussi
    si la table `sitadel_permits` est absente (dev/test) → l'appelant n'a rien à signaler."""
    from sqlalchemy import text as _text
    d = date_autorisation_sql("sp.")
    try:
        return db.execute(_text(
            f"SELECT max({d}) FROM sitadel_permits sp "
            "JOIN LATERAL jsonb_array_elements_text(sp.idu_codes) j(idu) ON true "
            f"WHERE j.idu = :i AND {d} > :apres"),
            {"i": idu, "apres": apres}).scalar()
    except Exception:          # noqa: BLE001 — table absente (dev/test) → pas de caveat, jamais un faux
        db.rollback()
        return None


def depot_affichable(date_depot, date_autorisation, an_depot):
    """Version Python de `depot_affichable_sql` (même règle, pour les tests et les lecteurs Python) :
    rend la date de dépôt (objet `date`) si elle est affichable, sinon None. Accepte des dates ISO
    (texte) ou des objets `date`/`datetime`."""
    import re
    from datetime import date as _date, datetime as _dt

    def _d(x):
        if x is None:
            return None
        if isinstance(x, _dt):
            return x.date()
        if isinstance(x, _date):
            return x
        return _date.fromisoformat(str(x)[:10])
    dep, aut = _d(date_depot), _d(date_autorisation)
    if dep is None or aut is None or not (dep < aut):
        return None
    if dep.month == 1 and dep.day == 1:   # proxy d'année, pas un vrai jour de dépôt
        return None
    an = str(an_depot or "")
    if not re.fullmatch(r"[0-9]{4}", an) or dep.year != int(an):
        return None
    return dep


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
