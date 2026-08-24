"""M87 P0 — définition CANONIQUE des sources AFFICHÉES sur la page Sources & fraîcheur.

UN critère, UN endroit : le compteur d'accueil (`accueil.py`) ET la liste `/sources` lisent d'ici.
Exclusions de l'AFFICHAGE (l'ingestion et les tables restent, seul l'écran change) :
  · les DOUBLON de catalogue (même donnée qu'une ligne canonique — M71) ;
  · les sources MASQUÉES : mortes à l'affichage. M97 : le mécanisme reste, l'ensemble est VIDE —
    Office de l'eau (masquée M87 comme « QA seul ») est SERVIE à la fiche depuis M95
    (anc_office_eau_commune, Sourcé commune) ; une source servie s'affiche (audit M96 G1).
"""
from __future__ import annotations

#: statuts qui rendent une source AFFICHABLE (branchée auto OU alimentée à la main). UN seul jeu,
#: lu par le SQL (WHERE_AFFICHEES) ET par le prédicat Python (est_affichee) — pour qu'ils ne
#: puissent jamais diverger (FIX-SOURCES S1). Comparaison INSENSIBLE À LA CASSE (`lower(status)`) :
#: une casse aberrante (ex. 'CONNECTE' au lieu de 'connecte') ne peut plus effacer une source.
STATUTS_AFFICHES: frozenset[str] = frozenset({"connecte", "manuel"})

#: sources retirées de l'AFFICHAGE (jamais de l'ingestion). Vide depuis M97 (Office de l'eau
#: démasquée — servie via anc_service depuis M95). Le mécanisme reste pour un prochain arbitrage.
SOURCES_MASQUEES: frozenset[str] = frozenset()

#: fragment SQL commun. M123 — CORRECTION du piège des `manuel` : la vitrine ne filtre plus
#: `status='connecte'` STRICT (une source `manuel` CÂBLÉE ET ALIMENTÉE était invisible — cas Fichiers
#: fonciers). Elle affiche désormais `connecte` ∪ `manuel`, et exclut explicitement les DOUBLON, les
#: RETIRÉ (abandon arbitré, raison écrite) et les masquées. Une source retirée/vide porte son tag,
#: elle n'est plus exclue « par son statut » en silence.
#: RÈGLE VIC (M123) : « la vitrine ne montre que ce qui SERT ». Hors vitrine = DOUBLON (canal masqué),
#: RETIRÉ (abandon arbitré), DORMANT (ingéré/déclaré mais servi nulle part) — tous restent en base
#: avec leur note, seul l'écran les écarte.
#: FIX-SOURCES S1 — l'endpoint /sources SÉLECTIONNE désormais via CE fragment (comme le compteur
#: d'accueil), plus via `status=='connecte'` en dur : page rendue == chiffre annoncé, par construction.
WHERE_AFFICHEES = ("lower(status) IN ('connecte', 'manuel') "
                   "AND COALESCE(technical_notes, '') NOT LIKE 'DOUBLON%' "
                   "AND COALESCE(technical_notes, '') NOT LIKE 'RETIRÉ%' "
                   "AND COALESCE(technical_notes, '') NOT LIKE 'DORMANT%' "
                   "AND name <> ALL(:masquees)")


def masquees_param() -> list[str]:
    """Valeur à lier à `:masquees` (liste des noms masqués)."""
    return list(SOURCES_MASQUEES)


def est_affichee(name: str, technical_notes: str | None, status: str | None) -> bool:
    """Une source data_sources est-elle AFFICHÉE ? Prédicat CANONIQUE (même règle que WHERE_AFFICHEES,
    y compris le STATUT) — appliqué en SÉLECTION, pas seulement en masquage post-hoc (FIX-SOURCES S1).
    Casse du statut insensible : une source servie ne disparaît plus pour un 'CONNECTE' mal casé (S2)."""
    tn = technical_notes or ""
    return ((status or "").lower() in STATUTS_AFFICHES
            and not tn.startswith("DOUBLON de") and not tn.startswith("RETIRÉ")
            and not tn.startswith("DORMANT") and name not in SOURCES_MASQUEES)


def normalize_status(raw: str | None) -> str:
    """GARDE d'ingestion (FIX-SOURCES S2) : normalise un statut de source vers la VALEUR d'enum
    canonique (minuscule), et REFUSE tout statut hors enum. Toute écriture de `data_sources.status`
    doit passer par ici — une casse ou une graphie aberrante ne peut plus se retrouver en base et
    effacer silencieusement une source de la vitrine. Renvoie la valeur normalisée ('connecte', …)."""
    from .enums import DataSourceStatus

    val = (raw or "").strip().lower()
    valides = {m.value for m in DataSourceStatus}
    if val not in valides:
        raise ValueError(
            f"statut de source hors enum : {raw!r} (attendus : {sorted(valides)})")
    return val


#: sources CURÉES MANUELLEMENT (arbitrage M86/M87) : la table n'est pas lue directement, mais elle est
#: le SQUELETTE d'un registre curaté à la main qui, lui, est servi. Badge dédié (même visuel que proxy).
SOURCES_CUREES: frozenset[str] = frozenset({
    "Sudocuh (procédures d'urbanisme)",
})
CUREES_NOTE = ("Table non lue directement : le radar PLU servi lit un registre YAML curaté à la main "
               "(config/veille_plu.yaml) dont Sudocuh est le squelette. Source réelle, indirecte.")
