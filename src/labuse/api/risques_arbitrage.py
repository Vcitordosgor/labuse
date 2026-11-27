"""M73 — arbitrage & libellés client des lignes de RISQUE servies (point de calcul unique).

Les lignes de la cascade servie (`dryrun_cascade_results`) peuvent se RECOUVRIR sur l'emprise :
plusieurs niveaux d'un même aléa (faible + moyen listés côte à côte), un régime PPR réglementaire
(HARD_EXCLUDE « zone rouge inconstructible ») coexistant avec une intersection géométrique marginale
(SOFT_FLAG « < 10 % »). Servi tel quel, chaque document présente une combinaison différente et le
client perd confiance (M73).

Doctrine M73 (arbitrages Vic) :
  - **un seul niveau par aléa** : le plus contraignant, nommé, jamais côte à côte ;
  - **la source réglementaire prime sur la source géométrique** — un régime PPR opposable
    (HARD_EXCLUDE) supprime l'« intersection marginale < 10 % » (une intersection n'est pas un
    régime juridique) ;
  - **aucun libellé technique brut** ni identifiant de table n'atteint le client
    (`PPR INONDATION_MOUVEMENT_DE_TERRAIN`, `mouvement_terrain`, « eleve », `PM1_..._ass`,
    `parcel_residuel`).

Fonction PURE sur la liste de lignes servies — **un seul endroit**, consommée par les 4 documents
(premium, dossier, banquier, fiche écran).
"""
from __future__ import annotations

import re

#: sévérité croissante des niveaux d'aléa — on retient le maximum par type d'aléa.
_NIVEAU_RANK = {
    "negligeable": 0, "négligeable": 0, "faible": 1, "faible_a_modere": 2, "faible à modéré": 2,
    "modere": 3, "modéré": 3, "moyen": 3,
    "eleve": 4, "élevé": 4, "fort": 5, "tres_fort": 6, "très fort": 6,
}
#: forme client d'un niveau technique (accents, espaces).
_NIVEAU_LABEL = {
    "faible": "faible", "faible_a_modere": "faible à modéré", "modere": "modéré",
    "moyen": "moyen", "eleve": "élevé", "tres_fort": "très fort",
}

_ALEA_RE = re.compile(r"^Aléa\s+(?P<type>.+?)\s+—\s+niveau\s+(?P<niveau>[^.\s]+)", re.IGNORECASE)
#: identifiant technique de servitude entre parenthèses : « PM1 (PM1_PPR_i_mvt_..._ass) » → « PM1 ».
_SUP_ID_RE = re.compile(r"\s*\([A-Z0-9]+_[A-Za-z0-9_]+\)")
#: LOT I pt2 — tête d'un libellé de zone rouge marginale (« PPR zone rouge sur N % de la surface »).
_ZONE_ROUGE_MARG_RE = re.compile(r"^(PPR zone rouge sur [\d.,]+ % de la surface)\s*—")


def libelle_client_detail(detail: str | None) -> str | None:
    """Nettoie un détail de ligne servie de tout libellé technique brut (M73 §3)."""
    if not detail:
        return detail
    d = detail
    # libellés PPR bruts en MAJUSCULES_underscore → phrase française.
    d = d.replace("INONDATION_MOUVEMENT_DE_TERRAIN", "inondation et mouvement de terrain")
    d = re.sub(r"PPR ([A-Z][A-Z_]+)", lambda m: "PPR " + m.group(1).lower().replace("_", " "), d)
    # clé de type d'aléa avec underscore.
    d = d.replace("mouvement_terrain", "mouvement de terrain")
    d = d.replace("submersion_marine", "submersion marine")
    # niveaux techniques / sans accent.
    for raw, lab in (("niveau negligeable", "niveau négligeable"), ("niveau tres_eleve", "niveau très élevé"),
                     ("niveau eleve", "niveau élevé"), ("niveau tres_fort", "niveau très fort"),
                     ("niveau faible_a_modere", "niveau faible à modéré"),
                     ("niveau modere", "niveau modéré"),
                     ("Pente modere", "Pente modérée"), ("Pente eleve", "Pente élevée"),
                     ("Pente tres_forte", "Pente très forte"), ("Pente forte", "Pente forte")):
        d = d.replace(raw, lab)
    # identifiant technique de servitude (code d'assiette) retiré côté client.
    d = _SUP_ID_RE.sub("", d)
    # noms de tables internes.
    d = d.replace("hors couverture parcel_residuel", "droits résiduels non couverts")
    d = d.replace("parcel_residuel", "droits résiduels")
    # M81 — « intersection marginale » (terme géométrique) → « recouvrement marginal » côté client.
    # Depuis la graduation PPR (M-I), une part rouge marginale n'est plus une CONTRADICTION (elle ne
    # coexiste plus avec une exclusion) mais un verdict à part entière ; on la NOMME proprement.
    d = d.replace("intersection marginale", "recouvrement marginal")
    # CHIRURGICAL-FIX-1 (LOT I pt2) — zone rouge marginale (< 50 %) : la PARTIE rouge est
    # inconstructible (exclue de l'implantation), les prescriptions relèvent de la zone bleue. On
    # reformule le libellé STOCKÉ « — vigilance forte ; … pas d'exclusion automatique » (que
    # phase1.py n'émet plus ; compat des runs déjà servis) pour dire la même chose que le Dossier.
    _zr = _ZONE_ROUGE_MARG_RE.match(d.strip())
    if _zr and "vigilance forte" in d:
        # CHIRURGICAL-FIX-1 (LOT J pt3b) — on ne renvoie plus « … ne s'appliquent qu'en zone bleue »
        # (qui laissait croire que le rouge est sans règle) : la partie rouge est EXCLUE, le RESTE
        # relève du règlement du plan de prévention.
        d = (f"{_zr.group(1)} — la partie en zone rouge est exclue de l'implantation ; "
             "le reste est soumis au règlement du plan de prévention.")
    return d


def ajuster_clause_affichage(detail: str | None, non_constructible: bool) -> str | None:
    """CAPACITE-1 (B5) — ajustements d'AFFICHAGE communs aux documents texte (Markdown/HTML) ET au
    Comparatif, pour que TOUS servent les MÊMES libellés que les PDF (point unique, jamais deux
    fenêtres ni deux formules pour un même fait). Le run servi n'est PAS recalculé ; on n'ajuste que
    le texte, de façon ciblée :
      1. marché du logement neuf (VEFA) : la fenêtre est « 5 ans » (comme le Dossier §marché), jamais
         « 36 mois » — le texte figé d'anciens runs servait 36 mois pour les MÊMES ventes ;
      2. parcelle NON CONSTRUCTIBLE : on retire la seule clause rassurante « (pas d'exclusion
         automatique) » du PPR partiel (elle rassurerait à tort quand le verdict est non constructible),
         en GARDANT la zone rouge X % et la « vigilance forte ».
    Renvoie le détail ajusté (jamais None pour une entrée non vide)."""
    if not detail:
        return detail
    d = detail
    if "logement neuf (vefa)" in d.lower():
        d = d.replace("36 mois", "5 ans")
    if non_constructible and "exclusion automatique" in d.lower():
        segs = [s.strip() for s in d.split(";") if "exclusion automatique" not in s.lower()]
        d = "; ".join(s for s in segs if s).rstrip(" ;·—-")
        if d and d[-1] not in ".!?":
            d += "."
    return d


def arbitrer_risques(lines: list[dict]) -> list[dict]:
    """Arbitre et nettoie les lignes servies (nouvelle liste, entrée non mutée).

    - ne garde qu'une ligne par type d'aléa (le niveau le plus contraignant) ;
    - ne garde qu'UNE exclusion « PPR zone rouge » (la part maximale) — deux rouges côte à côte
      sans nom de plan se lisent comme une contradiction (EXPORTS-REBRANCHEMENT-1 lot 0) ;
    - retire l'« intersection marginale < 10 % » (PPR géométrique) si un régime PPR réglementaire
      (HARD_EXCLUDE) est présent sur la parcelle ;
    - passe chaque détail conservé par `libelle_client_detail`.
    """
    # 1) un régime PPR réglementaire opposable est-il présent ? (HARD_EXCLUDE mentionnant PPR)
    ppr_reglementaire = any(
        (l.get("result") == "HARD_EXCLUDE") and ("PPR" in (l.get("detail") or ""))
        for l in lines)

    # 1-bis) EXPORTS-REBRANCHEMENT-1 lot 0 — UNE seule exclusion « PPR zone rouge » servie : la plus
    # contraignante (part maximale). Le run peut porter plusieurs intersections rouges (plans PPR
    # distincts ou fragments d'un même plan) dont les verdicts stockés ne NOMMENT pas le plan :
    # servies côte à côte (« 54 % » puis « 100 % »), elles se lisent comme une contradiction sur la
    # même zone. Doctrine M73 (« un seul niveau par aléa, le plus contraignant ») appliquée au rouge.
    _ROUGE_RE = re.compile(r"PPR zone rouge.*?(\d+(?:[.,]\d+)?)\s*%")
    rouges = [(i, float(m.group(1).replace(",", ".")))
              for i, l in enumerate(lines)
              if l.get("result") == "HARD_EXCLUDE"
              and (m := _ROUGE_RE.search(l.get("detail") or ""))]
    rouges_exclus = ({i for i, _ in rouges} - {max(rouges, key=lambda t: t[1])[0]}
                     if len(rouges) > 1 else set())

    # 2) meilleur niveau par type d'aléa (indice de la ligne à conserver).
    alea_best: dict[str, tuple[int, int]] = {}
    for i, l in enumerate(lines):
        m = _ALEA_RE.match(l.get("detail") or "")
        if not m:
            continue
        typ = m.group("type").strip().lower().replace("mouvement_terrain", "mouvement de terrain")
        rank = _NIVEAU_RANK.get(m.group("niveau").strip().lower(), 0)
        if typ not in alea_best or rank > alea_best[typ][0]:
            alea_best[typ] = (rank, i)
    keep_alea = {v[1] for v in alea_best.values()}

    out: list[dict] = []
    for i, l in enumerate(lines):
        d = l.get("detail") or ""
        # rouge PPR : seule l'exclusion à la part MAXIMALE est servie (1-bis).
        if i in rouges_exclus:
            continue
        # aléa : ne conserver que la ligne du niveau le plus contraignant par type.
        if _ALEA_RE.match(d) and i not in keep_alea:
            continue
        # PPR géométrique marginal supprimé quand un régime réglementaire prime.
        if ppr_reglementaire and l.get("result") == "SOFT_FLAG" \
                and "intersection marginale" in d and "PPR" in d:
            continue
        nl = dict(l)
        nl["detail"] = libelle_client_detail(d)
        out.append(nl)
    return out
