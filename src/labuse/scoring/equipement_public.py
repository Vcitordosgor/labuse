"""FONCIER-PUBLIC-1 — classification des ÉQUIPEMENTS PUBLICS (BPE) et du FONCIER PUBLIC.

Décision de Vic (point 7 de ECRANS-NOV-2, cf. `INVESTIGATION-FONCIER-PUBLIC.md`) :

  · un ÉQUIPEMENT PUBLIC EN PLACE (enseignement, santé, administration, sécurité, sport, culture,
    loisirs de plein air) rend la parcelle « Hors de ce projet » dans les DEUX scénarios — ce n'est
    pas un terrain à bâtir pour un promoteur. Les COMMERCES et SERVICES PRIVÉS de la BPE NE comptent
    PAS (restaurants, banques, garages, cabinets libéraux, pharmacies, agences de voyage…) ;
  · un TERRAIN PUBLIC SANS équipement (État, Région, Département, commune, établissement public —
    groupes DGFiP `PUBLIC_DGFIP_GROUPES`) garde sa bande ; il porte seulement un DRAPEAU « foncier
    public » (case « Inclure le foncier public » décochée par défaut, puce sur la carte).

Ce module est la SOURCE UNIQUE de la règle d'équipement : un dictionnaire sous-domaine BPE → catégorie
(mirroir Python pour les tests) ET l'expression SQL équivalente (adaptateur + backfill). La BPE (INSEE,
`spatial_layers kind='amenite_bpe'`) porte le domaine `dom` (A–G), le sous-domaine `sdom` (A1, C3…) et
le type fin `typequ` (A104…). Aucune donnée inventée : on CLASSE ce qui est déjà en base.

Liste RETENUE / EXCLUE (figée ici, reprise telle quelle dans le compte-rendu) :

  RETENUS (équipement public en place) :
    · A1  — Services publics → « administration » (mairie, EPCI, préfecture, tribunaux/justice,
            France services) ; les brigades/commissariats (A104*, A140*) → « sécurité ».
    · C1,C2,C3,C4,C5,C7 — Enseignement (écoles, collèges, lycées, supérieur, université, résidences
            et restaurants universitaires), public OU privé sous contrat : une école en place n'est
            pas un terrain à bâtir.
    · D1  — Établissements de santé (hôpitaux, CHU, centres de santé, HAD…) → « santé ».
    · F1  — Équipements sportifs → « sport » ; F2 — loisirs de plein air (baignade) → « loisirs » ;
            F3 — culture (bibliothèques, archives) → « culture ».

  EXCLUS (commerces / services privés / hors périmètre, la parcelle N'est PAS marquée) :
    · A2 (banque, poste, pompes funèbres), A3 (auto), A4 (artisans du bâtiment),
      A5 (restaurants, coiffure, beauté, vétérinaires) ;
    · B1,B2,B3 — commerces ;
    · C6 — formation continue (organismes majoritairement privés : « A ZOT FORMATION »…) ;
    · D2 (professions de santé libérales), D3 (pharmacies, laboratoires, thermal),
      D4,D5,D6,D7 (action sociale, médico-social, hébergement social — hors « santé publique »
      nommée par Vic ; public/privé non séparable depuis la seule BPE : exclus par prudence) ;
    · E1 — transports (taxis, aéroport) ;
    · G1 — tourisme (agences de voyage, hôtels).

Un même terrain peut porter plusieurs équipements (le campus DO0049 : 2 lycées + un plateau
multisport + un snack). La catégorie SERVIE est la DOMINANTE selon `PRIORITE` (santé avant
enseignement avant administration…), le snack privé (A5) étant ignoré.
"""
from __future__ import annotations

# sous-domaine BPE → catégorie d'équipement public (hors A1, raffiné ci-dessous par `typequ`).
_SDOM_CAT: dict[str, str] = {
    "C1": "enseignement", "C2": "enseignement", "C3": "enseignement", "C4": "enseignement",
    "C5": "enseignement", "C7": "enseignement",
    "D1": "santé",
    "F1": "sport", "F2": "loisirs", "F3": "culture",
}
# sous-domaines retenus (A1 compris) — préfiltre EXISTS côté SQL.
RETENU_SDOM: tuple[str, ...] = ("A1", *_SDOM_CAT.keys())

# A1 (services publics) : sécurité si gendarmerie/commissariat, sinon administration.
_SECURITE_PREFIXES = ("A104", "A140")   # brigade de gendarmerie, commissariat de police

# priorité de la catégorie DOMINANTE quand plusieurs équipements coexistent (1 = gagne).
PRIORITE: dict[str, int] = {
    "santé": 1, "enseignement": 2, "administration": 3, "sécurité": 4,
    "culture": 5, "sport": 6, "loisirs": 7,
}


def categorie(sdom: str | None, typequ: str | None) -> str | None:
    """Catégorie d'équipement public d'un enregistrement BPE, ou None s'il est EXCLU (commerce /
    service privé / hors périmètre). Mirroir EXACT de `categorie_sql`."""
    if not sdom:
        return None
    if sdom == "A1":
        tq = typequ or ""
        return "sécurité" if tq.startswith(_SECURITE_PREFIXES) else "administration"
    return _SDOM_CAT.get(sdom)


def dominante(categories) -> str | None:
    """La catégorie à SERVIR parmi plusieurs (selon `PRIORITE`), ou None si aucune retenue."""
    cats = [c for c in (categories or []) if c in PRIORITE]
    return min(cats, key=lambda c: PRIORITE[c]) if cats else None


def categorie_sql(a: str) -> str:
    """Expression SQL (CASE) donnant la catégorie d'un enregistrement BPE `a` (ou NULL si exclu),
    identique à `categorie`. `a` est l'alias de la ligne `spatial_layers` (lit `a.attrs`)."""
    sdom = f"{a}.attrs->>'sdom'"
    tq = f"{a}.attrs->>'typequ'"
    return f"""CASE
      WHEN {sdom} IN ('C1','C2','C3','C4','C5','C7') THEN 'enseignement'
      WHEN {sdom} = 'D1' THEN 'santé'
      WHEN {sdom} = 'F1' THEN 'sport'
      WHEN {sdom} = 'F2' THEN 'loisirs'
      WHEN {sdom} = 'F3' THEN 'culture'
      WHEN {sdom} = 'A1' AND ({tq} LIKE 'A104%' OR {tq} LIKE 'A140%') THEN 'sécurité'
      WHEN {sdom} = 'A1' THEN 'administration'
      ELSE NULL END"""


def priorite_sql(cat_expr: str) -> str:
    """Rang de priorité SQL (plus petit = dominant) de la catégorie `cat_expr`, pour choisir la
    dominante par parcelle (ORDER BY … LIMIT 1). Les non-retenues (NULL) tombent à 99."""
    whens = " ".join(f"WHEN '{c}' THEN {r}" for c, r in PRIORITE.items())
    return f"CASE ({cat_expr}) {whens} ELSE 99 END"
