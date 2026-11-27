"""LE ZONAGE — résolution de la zone d'une parcelle en règles chiffrées (nouveau système, unique).

Depuis PLU-CALIBRAGE-4, ce module est la SOURCE UNIQUE des règles de zone. Il remplace l'ancien
moteur de constructibilité (supprimé) et ne lit plus aucun `config/plu_<slug>.yaml` :

  · les VALEURS chiffrées viennent des `regles` servies par le module `plu.destinations`
    (PLU-CALIBRAGE-1/2/3, qui les ont extraites, sourcées article/page, puis préservées — 0-diff) ;
  · la MÉTADONNÉE de zonage (mode strict/progressif, zones AU*st, renvois AU→U, habitat, prospect,
    hypothèses moteur, notes de provenance) vient de `config/plu_zonage.yaml` (migrée en lot 4).

Le contrôle de flux reproduit à l'identique l'ancien `_resolve_zone_base` : correspondance directe,
zones AU*st non constructibles, renvoi AU→U, repli générique, modes strict/progressif. La
superposition des feuilles VALIDÉES (`_calibrage_overlay`) impose valeur + source ; un `propose`
ne branche jamais le calcul (l'étape reste ESTIMÉE). `resolve_zone` = base + overlay.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace as _replace
from functools import lru_cache
from pathlib import Path

import yaml

log = logging.getLogger("labuse.faisabilite.zonage")

_CONFIG = Path(__file__).resolve().parents[3] / "config"
_ZONAGE = _CONFIG / "plu_zonage.yaml"

# ── marqueurs de valeur (mêmes sémantiques que l'ancien moteur de constructibilité) ─────────────
A_VERIFIER = "a_verifier"          # présent au règlement mais ambigu : à signaler, ne pas combler
EXEMPT = "exempt"                  # stationnement explicitement non réglementé
NON_MODELISABLE = "non_modelisable"  # norme présente mais pas exprimée en places/logement


@dataclass
class ZoneRules:
    """Règles chiffrées d'une (sous-)zone, avec leurs sources. Un champ peut valoir
    None (non réglementé) ou A_VERIFIER (ambigu : à signaler, ne pas combler)."""

    code: str
    bassin: str | None = None
    he_m: float | str | None = None          # hauteur égout/acrotère (niveaux habitables)
    hf_m: float | str | None = None          # hauteur faîtage
    emprise_sol_pct: float | str | None = None
    recul_voirie_m: float | str | None = None
    recul_limites_sep_m: float | str | None = None
    # CHASSE-DONNEES-FIX-1 (Lot 6, D-50) — la FORMULE du recul (« H/2, minimum 3 m ») quand le YAML
    # la porte : la fiche affichait le seul plancher (3 m) comme LA valeur, alors que pour une façade
    # de 15 m le retrait réel exigé est 7,5 m. Servie À CÔTÉ du plancher, jamais à sa place.
    recul_limites_formule: str | None = None
    stat_logement: str | None = None         # ex. "1,5 place / logement"
    pleine_terre_pct: float | str | None = None
    # provenance / contexte
    via_renvoi: str | None = None            # ex. "AU1a → règles U1a"
    constructible_neuf: bool = True          # False pour les zones AU*st
    habitat: str | None = None               # "interdit" = vocation non résidentielle au règlement
    calibree: bool = True                    # True = règles d'une commune ; False = estimation générique
    hauteur_estimee: bool = False            # RECETTE-PROD-1 (A7) : enveloppe calibrée mais HAUTEUR non
    #  réductible à une valeur unique (table graphique par secteur) → hauteur de repli, à présenter
    #  comme ESTIMÉE (jamais comme la valeur validée du règlement)
    hauteur_mode: str | None = None          # 'prospect' = hf_m calculé PAR PARCELLE (L≥H, largeur voirie)
    niveaux_max: int | None = None           # R+n LU au règlement (validé) → niveaux imposés
    hauteur_plage: dict | None = None         # hauteur variant par secteur (base) → plage
    emprise_plage: dict | None = None         # idem emprise au sol
    regle_non_validee: str | None = None      # PLU-CALIBRAGE-6 : liste des feuilles SDP `propose`
    #  (règle PLU non validée) qui BRANCHERAIENT la SDP → capacité non calculable, jamais un défaut
    ces_perimetres: list | None = None        # MOTEUR-VERITE-FIX-4 LOT 2 : CES réduit dans des
    #  périmètres REPÉRÉS (prescriptions GPU mesurées par parcelle — ex. Le Port Uc, OAP
    #  Mascareignes 60 %) ; [{libelle_regex, subtypes, pct, source}]
    recul_fond_m: float | None = None         # MOTEUR-VERITE-FIX-4 LOT 3 : retrait FIXE propre au
    #  FOND (ex. Trois-Bassins Ue 7.3 « 4 m ») — la formule H/2 ne s'applique alors qu'aux
    #  latérales, jamais re-calculée sur le fond
    capacite_a_verifier: str | None = None    # MOTEUR-VERITE-FIX-3 LOT 2 : la zone a une RÈGLE
    #  PROPRE validée mais non réductible à un nombre (ex. Saint-Denis Udo, hauteur par rue) —
    #  le repli ne sert JAMAIS une valeur générique à sa place : verdict constructible, SDP ∅
    recul_voirie_alignement: bool = False     # PLU-CALIBRAGE-7 forme 1 : recul 0 = « à l'alignement »
    recul_limites_alignement: bool = False    #  (idem « en limite séparative ») — 0 EXPLICITE, ≠ absent
    # MOTEUR-VERITE-FIX-1 (LOT 2) — mode d'IMPLANTATION par rapport aux limites séparatives, lu au
    # règlement et calibré SÉPARÉMENT pour les limites latérales et le fond de parcelle :
    #   {mode: retrait_obligatoire | limite_ou_retrait | limite_sous_conditions | limite_imposee,
    #    condition_texte?, condition_modelable? («largeur_terrain_max:X» | «une_seule_limite» |
    #    «deux_limites_max» | «hauteur_bande:…» | «non»), citation?, article?, page_pdf?}.
    # None = non calibré → le retrait (min_m / formule) s'applique comme aujourd'hui.
    implantation_laterales: dict | None = None
    implantation_fond: dict | None = None
    # MOTEUR-VERITE-FIX-3 LOT 1 — référence de hauteur du retrait relatif, LUE À L'ARTICLE :
    # 'egout' (seul cas où le scénario niveau-par-niveau à l'égout s'applique),
    # 'hauteur_totale_facade', 'altitude_point_a_point'. None/au-delà → référence PRUDENTE
    # (faîtage de la zone).
    h_reference: str | None = None
    pleine_terre_compose: dict | None = None  # PLU-CALIBRAGE-7 forme 2 : {espaces_verts_pct, part_pct}
    #  pleine_terre_pct = espaces_verts_pct × part_pct / 100 (calculé, JAMAIS stocké — les 2 chiffres sourcés)
    permeabilite_pct: float | None = None     # CHIRURGICAL-FIX-1 (LOT I 3c) — 2e obligation de sol : la
    #  SURFACE PERMÉABLE (enveloppe), DISTINCTE de la pleine terre (le noyau). Ex. Le Tampon Ud : « 40 %
    #  perméable, dont 30 % pleine terre » → permeabilite_pct=40 ET pleine_terre_pct=30 (les deux servies).
    pleine_terre_nature: str | None = None    # CHIRURGICAL-FIX-1 (LOT H pt8) — vraie nature de la règle
    #  « 2.6 » selon sa CITATION : 'permeable' | 'pleine_terre' | 'biotope' | 'espace_vert'. Le champ
    #  pleine_terre_pct agrège des règles DISTINCTES ; le document nomme celle qui est citée (jamais
    #  « pleine terre » pour une règle de perméabilité — AM0838/UE L'Étang-Salé : « 25 % … perméable »).
    # FICHE-FIX-2 P4 / PLU-CALIBRAGE-9 — clause de mixité sociale de la zone (LLS), lue des `regles`
    #  calibrées : {seuil_m2|seuil_logements, quota_pct, quota_base?, produits?, portee, article,
    #  page_pdf, citation, statut}. None si la zone n'en porte pas. `statut` = 'valide' → branchée
    #  (11e étape sourcée : seuil en m² de SDP ou en logements) ; 'propose'/None → non modélisée.
    mixite: dict | None = None
    # PLU-EXCEPTIONS-1 — exceptions au règlement portées par les feuilles `regles` (verbatim + article +
    #  page + `porte`). Servies AVEC leur règle (id `<cle_regle>.exception`), jamais recomposées. Une
    #  liste par clé de règle ('hauteur','emprise','recul_voirie','recul_limites','pleine_terre',
    #  'stationnement','mixite') ; {} si la zone n'en porte aucune. AUCUNE n'entre dans un calcul.
    exceptions: dict[str, list[dict]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def places_par_logement(self) -> float | str | None:
        """Ratio places/logement. Quatre issues DISTINCTES, jamais une valeur inventée :
          · nombre · None (absente) · A_VERIFIER (ambiguë) · EXEMPT · NON_MODELISABLE."""
        s = self.stat_logement
        if not s:
            return None
        if s == A_VERIFIER:
            return A_VERIFIER
        if re.search(r"exempt|aucune place|sauf en zone", s, re.I):
            return EXEMPT
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*places?\s*/?\s*(?:par\s*)?logement", s, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        # ETUDE-STATIONNEMENT (merge moteur-verite) — barème PAR TYPOLOGIE (Le Tampon : 0,5 ≤T1 · 1 T2 · 1,5 T3+)
        # : le ratio de BASE (logement standard = T2 collectif) n'est pas lisible dans le texte détaillé. On le
        # lit sur le barème lui-même (`places_pour`), comme la capacité. Sans base lisible → NON_MODELISABLE.
        try:
            from ..implantation.regles import charger as _charger_b
            _b = _charger_b(_insee(self.bassin), self.code).stationnement
            _r = _b.places_pour(pieces=2, sdp_m2=50.0, destination="collectif")
            if isinstance(_r, (int, float)):
                return float(_r)
        except Exception:  # noqa: BLE001 — lecture annexe, jamais bloquante
            pass
        return NON_MODELISABLE          # texte présent mais aucune forme « X place/logement » lisible


# ── métadonnée de zonage (config/plu_zonage.yaml, migrée hors des plu_<slug>.yaml) ──────────────
@lru_cache(maxsize=None)
def _zonage_doc() -> dict:
    return yaml.safe_load(_ZONAGE.read_text(encoding="utf-8")) if _ZONAGE.is_file() else {}


def _insee(commune: str | None) -> str | None:
    """Commune → INSEE. `commune=None` ⇒ Saint-Paul (back-compat, comme l'ancien _YAML)."""
    from ..plu.destinations import _fichier_commune, _slug
    if commune is None:
        return "97415"                    # Saint-Paul (gold, défaut historique)
    if re.fullmatch(r"974\d\d", str(commune).strip()):
        return commune.strip()
    p = _fichier_commune(commune)          # 974xx_slug.yaml
    if p is not None:
        return p.name[:5]
    slug = _slug(commune)
    for ins, e in _zonage_doc().items():   # repli : slug → insee via plu_zonage
        if e.get("slug") == slug:
            return ins
    return None


def _zonage_commune(commune: str | None) -> dict | None:
    ins = _insee(commune)
    return _zonage_doc().get(ins) if ins else None


# ── valeurs chiffrées reconstruites depuis les regles (TOUTES les feuilles, quel que soit le
#    statut : la conversion PLU-CALIBRAGE-3 a préservé les valeurs de l'ancien système) ──────────
def _val(reg: dict, rub: str, feuille: str, cle: str):
    """Valeur d'une feuille VALIDÉE seulement.

    PLU-CALIBRAGE-6 (garde) : la base est désormais VALIDÉES-ONLY, comme l'overlay
    (`_calibrage_overlay`). Avant, `_val` lisait la valeur numérique quel que soit le statut —
    c'est le trou de SCORING-5-RETOUR §2 : les 95 feuilles `propose` numériques branchaient la
    SDP (« un résiduel calculé sur du non-validé casse la règle "chaque chiffre est sourcé" »).
    Désormais un `propose` renvoie `a_verifier` (non numérique → n'entre PAS dans la SDP) ; la
    présence d'une telle feuille rend la zone non calculable (cf. `_regles_sdp_non_validees` /
    `_zone_regle_non_validee`), jamais une valeur par défaut."""
    leaf = (reg.get(rub) or {}).get(feuille) if rub in reg else None
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    if leaf.get("statut") != "valide":
        return A_VERIFIER if leaf.get("statut") == "propose" else None
    v = leaf.get(cle)
    if v is None:
        return None
    return float(v) if isinstance(v, (int, float)) else v


# ── garde PLU-CALIBRAGE-6 : les feuilles SDP-déterminantes NON validées rendent la capacité non
#    calculable (jamais une valeur par défaut). Le stationnement en est EXCLU : il ne détermine pas
#    la SDP (il borne le scénario « logements au sol », pas `surface_plancher_m2`). ────────────────
_FEUILLES_SDP_CAPACITE = (
    ("hauteur", "faitage", "m"), ("hauteur", "egout", "m"), ("hauteur", "niveaux", "r_plus"),
    ("emprise_sol", "ces", "pct"),
    ("retraits", "voie", "min_m"), ("retraits", "limites_separatives", "min_m"),
    ("pleine_terre", "pct", "pct"),
)


def _feuille_sdp_porte_valeur(rub: str, cle: str, leaf: dict) -> bool:
    """La feuille porterait-elle une valeur dans la SDP ? (numérique standard, ou PLU-CALIBRAGE-7 :
    recul « forme: alignement » = 0 explicite, ou pleine terre composée `espaces_verts_pct`)."""
    if isinstance(leaf.get(cle), (int, float)):
        return True
    if rub == "retraits" and leaf.get("forme") == "alignement":
        return True                                      # forme 1 : recul 0 explicite
    if rub == "pleine_terre" and isinstance(leaf.get("espaces_verts_pct"), (int, float)):
        return True                                      # forme 2 : composée
    return False


def _regles_sdp_non_validees(reg: dict) -> list[str]:
    """Feuilles SDP-déterminantes en statut `propose` PORTANT une valeur (elles brancheraient la
    SDP). Leur présence = capacité non calculable (« règle PLU non validée »). Vide = la zone se
    calcule sur ses seules feuilles validées."""
    out: list[str] = []
    for rub, feuille, cle in _FEUILLES_SDP_CAPACITE:
        sous = reg.get(rub)
        leaf = sous.get(feuille) if isinstance(sous, dict) else None
        if not isinstance(leaf, dict):
            continue
        if (leaf.get("statut") == "propose" and not leaf.get("absent") and not leaf.get("plage")
                and _feuille_sdp_porte_valeur(rub, cle, leaf)):
            out.append(f"{rub}.{feuille}")
    return out


# ── PLU-CALIBRAGE-7 — lecture des deux formes de règle ajoutées au schéma ─────────────────────────
def _implantation_leaf(reg: dict, cle: str) -> dict | None:
    """MOTEUR-VERITE-FIX-1 (LOT 2) — mode d'implantation par côté, VALIDÉ seulement.
    Feuille `retraits.limites_separatives.<implantation_laterales|implantation_fond>` :
    {mode, condition_texte?, condition_modelable?, citation?, article?, page_pdf?, statut}.
    `statut` ≠ valide ou mode inconnu → None (le retrait min_m/formule s'applique seul)."""
    leaf = ((reg.get("retraits") or {}).get("limites_separatives") or {}).get(cle)
    if not isinstance(leaf, dict) or leaf.get("statut") != "valide":
        return None
    if leaf.get("mode") not in ("retrait_obligatoire", "limite_ou_retrait",
                                "limite_sous_conditions", "limite_imposee"):
        return None
    return dict(leaf)


def _recul_alignement(reg: dict, feuille: str) -> bool:
    """Forme 1 : la feuille recul (`retraits.<feuille>`) est-elle VALIDÉE en « forme: alignement »
    (recul 0 explicite — « à l'alignement » / « en limite séparative ») ? ≠ absent."""
    leaf = (reg.get("retraits") or {}).get(feuille)
    return (isinstance(leaf, dict) and leaf.get("statut") == "valide"
            and leaf.get("forme") == "alignement")


def _pleine_terre_val(reg: dict):
    """Valeur de pleine terre d'une feuille VALIDÉE — directe (`pct`) ou COMPOSÉE (forme 2 :
    `espaces_verts_pct` × `pleine_terre_part` / 100). `propose` → a_verifier (ne branche pas)."""
    leaf = (reg.get("pleine_terre") or {}).get("pct")
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    if leaf.get("statut") != "valide":
        return A_VERIFIER if leaf.get("statut") == "propose" else None
    if isinstance(leaf.get("pct"), (int, float)):
        return float(leaf["pct"])
    ev, part = leaf.get("espaces_verts_pct"), leaf.get("pleine_terre_part")
    if isinstance(ev, (int, float)) and isinstance(part, (int, float)):
        return round(float(ev) * float(part) / 100.0, 2)      # forme 2 : le moteur calcule
    return None


_LIBELLE_ESPACES_LIBRES = {
    "permeable": "Surface perméable",
    "biotope": "Coefficient de biotope",
    "espace_vert": "Espaces verts",
    "pleine_terre": "Pleine terre",
}


def libelle_espaces_libres(nature: str | None, defaut: str = "Pleine terre") -> str:
    """CHIRURGICAL-FIX-1 (LOT H pt8) — nom de base de la règle d'espaces libres (art. 2.6) selon sa
    nature citée : surface perméable ≠ pleine terre ≠ biotope ≠ espaces verts. Le suffixe (« min » /
    « minimale ») est ajouté par l'appelant. Défaut « Pleine terre » (rétro-compatibilité)."""
    return _LIBELLE_ESPACES_LIBRES.get(nature or "", defaut)


def _pleine_terre_nature(reg: dict) -> str | None:
    """CHIRURGICAL-FIX-1 (LOT H pt8) — nature RÉELLE de la règle d'« espaces libres / art. 2.6 » lue de
    sa CITATION sourcée : surface perméable, pleine terre, coefficient de biotope ou espace vert. Le
    champ `pleine_terre_pct` agrège ces règles distinctes ; le libellé du document doit nommer celle
    qui est citée (« pleine terre » prioritaire si la citation la nomme explicitement)."""
    leaf = (reg.get("pleine_terre") or {}).get("pct")
    if not isinstance(leaf, dict):
        return None
    cit = (leaf.get("citation") or "").lower()
    if not cit:
        return None
    if "pleine terre" in cit:
        return "pleine_terre"
    if "biotope" in cit:
        return "biotope"
    if "perméab" in cit or "permeab" in cit:
        return "permeable"
    if "espace" in cit and "vert" in cit:
        return "espace_vert"
    return None


def _permeabilite_pct(reg: dict):
    """CHIRURGICAL-FIX-1 (LOT I 3c) — 2e obligation de sol : la SURFACE PERMÉABLE (enveloppe), quand la
    citation en porte DEUX (« X % perméable, dont Y % pleine terre » — Le Tampon Ud 40/30, Ua 20/15…),
    ou un renvoi « respectivement X % et Y % » (Uav 30/20). `pleine_terre_pct` garde le NOYAU (Y) ; on
    sert ici l'ENVELOPPE (X), seulement si elle est DISTINCTE (sinon une seule obligation, déjà nommée)."""
    import re as _re
    leaf = (reg.get("pleine_terre") or {}).get("pct")
    if not isinstance(leaf, dict):
        return None
    cit = leaf.get("citation") or ""
    noyau = leaf.get("pct") if isinstance(leaf.get("pct"), (int, float)) else None
    # forme 1 : « X % … perméable » (enveloppe explicite ; `[^%]*?` s'arrête au 1er « perméable »,
    # AVANT le « dont Y % … pleine terre » — on capte bien l'enveloppe X, pas le noyau Y).
    m = _re.search(r"(\d+(?:[.,]\d+)?)\s*%[^%]*?perm[ée]able", cit)
    perm = None
    if m:
        perm = float(m.group(1).replace(",", "."))
    else:  # forme 2 : renvoi « respectivement X % et Y % » (X = perméable, Y = pleine terre)
        m = _re.search(r"respectivement.*?(\d+(?:[.,]\d+)?)\s*%\s*et\s*(\d+(?:[.,]\d+)?)\s*%", cit)
        if m:
            perm = float(m.group(1).replace(",", "."))
    if perm is None or (noyau is not None and abs(perm - float(noyau)) < 1e-6):
        return None            # pas de 2e obligation distincte (une seule règle, déjà nommée)
    return perm


def _pleine_terre_compose(reg: dict) -> dict | None:
    """Forme 2 : les deux chiffres sourcés {espaces_verts_pct, part_pct} d'une feuille pleine terre
    composée VALIDÉE (pour l'affichage de l'étape). None si feuille directe / non validée."""
    leaf = (reg.get("pleine_terre") or {}).get("pct")
    if (isinstance(leaf, dict) and leaf.get("statut") == "valide"
            and isinstance(leaf.get("espaces_verts_pct"), (int, float))
            and isinstance(leaf.get("pleine_terre_part"), (int, float))):
        return {"espaces_verts_pct": float(leaf["espaces_verts_pct"]),
                "part_pct": float(leaf["pleine_terre_part"])}
    return None


def _zone_regle_non_validee(code: str, feuilles: list[str]) -> ZoneRules:
    """ZoneRules « non calculable — règle PLU non validée » : la zone est calibrée mais une (ou
    plusieurs) de ses feuilles SDP restent `propose`. On NE retombe PAS sur l'estimation générique
    (ce serait une valeur par défaut) : la capacité est déclarée non calculable, motif porté."""
    liste = ", ".join(sorted(set(feuilles)))
    return ZoneRules(
        code=code, calibree=True, regle_non_validee=liste,
        notes=[f"Capacité non calculable — règle(s) PLU non validée(s) : {liste} "
               "(feuille `propose`, sans citation retenue). Aucune valeur par défaut appliquée."],
        sources={"zone": "règle PLU non validée (feuille propose)"})


def _stat_from_regles(reg: dict, insee: str | None = None, code: str | None = None):
    # ETUDE-STATIONNEMENT-FIX-4 (LOT 2) — SOURCE UNIQUE de la règle de stationnement : le barème que l'Étude
    # APPLIQUE (`BaremeStationnement`), rendu par la MÊME fonction `_regle_stationnement_courte`. Le Dossier
    # cessait de dire « non réglementé » dès que la règle n'était pas « N places / logement » (BW2635 Uav :
    # barème par typologie Ua12.2 ; HT0538 Ud6 : par m² de SDP) alors que l'Étude, elle, l'appliquait. On
    # affiche donc la règle ENTIÈRE ; repli sur l'ancienne lecture `par_logement` si le barème n'est pas validé.
    if insee and code:
        try:
            from ..implantation.regles import charger as _charger_b
            from ..implantation.service import _regle_stationnement_courte
            _b = _charger_b(insee, code).stationnement
            _rc = _regle_stationnement_courte(_b)
            if _rc:
                return _rc
        except Exception:  # noqa: BLE001 — lecture annexe, jamais bloquante pour le Dossier
            pass
    leaf = (reg.get("stationnement") or {}).get("par_logement")
    if not isinstance(leaf, dict) or leaf.get("absent"):
        return None
    # CHASSE-DONNEES-FIX-1 (Lot 6, D-52) — un BARÈME chiffré par type de logement (ex. L'Étang-Salé
    # UC 2.7.3 : individuel 2 / collectif 1-2 p. 1, 3-4 p. 1,5, ≥5 p. 2) n'est PAS un nombre unique
    # mais EST chiffré au règlement : servi comme texte au lieu de « à vérifier » (feuille `bareme`).
    bareme = leaf.get("bareme")
    if isinstance(bareme, str) and bareme.strip():
        return bareme.strip()
    p = leaf.get("places")
    # PLU-CALIBRAGE-6 : la VALEUR numérique ne branche que si la feuille est validée (validées-only,
    # comme l'overlay). L'exemption (non numérique, cf. ci-dessous) reste reconnue quel que soit le
    # statut : c'est un silence de règle, pas un chiffre injecté dans le calcul.
    if isinstance(p, (int, float)) and leaf.get("statut") == "valide":
        p = int(p) if float(p).is_integer() else p
        return f"{p} place / logement" if p == 1 else f"{p} places / logement"
    # exemption explicite (ex. Saint-Paul U1pru, Art. 12 « sauf en zone… ») : la RAISON de la
    # feuille la porte (« exempté : aucune place imposée ») — on la préserve pour que
    # places_par_logement() la reconnaisse EXEMPT (l'ancien YAML portait la même mention). On lit
    # la raison (curée par zone), pas la citation (qui cite la règle générale « sauf en zone U1pru »
    # pour BEAUCOUP de zones → aurait faussement exempté les autres).
    if re.search(r"exempt|aucune place", leaf.get("raison") or "", re.I):
        return "exempté : aucune place imposée"
    return A_VERIFIER if leaf.get("statut") == "propose" else None


def _mixite_leaf(reg: dict) -> dict | None:
    """FICHE-FIX-2 P4 / PLU-CALIBRAGE-9 — clause de mixité sociale (LLS) de la zone, lue TELLE
    QUELLE des regles calibrées. None si absente.

    Deux formes de SEUIL de déclenchement, lues toutes deux (le moteur choisit celle présente) :
      · `seuil_m2`        — surface de plancher en m² (forme PLU-CALIBRAGE-9, majoritaire à La
                            Réunion : « programme > N m² de SDP → X % de logement aidé ») ;
      · `seuil_logements` — nombre de logements (forme FICHE-FIX-2, Saint-Denis).
    `quota_pct` = part aidée au-delà du seuil ; `quota_base` = assiette du quota (`surface_plancher`
    ou `logements`, informatif) ; `produits` = liste des produits visés (LLS/LLTS/PLS/LLI…) si cités.
    Rien n'est fabriqué : chaque champ relaie le YAML."""
    m = reg.get("mixite") if isinstance(reg, dict) else None
    if not isinstance(m, dict):
        return None
    return {"seuil_logements": m.get("seuil_logements"), "seuil_m2": m.get("seuil_m2"),
            "quota_pct": m.get("quota_pct"), "quota_base": m.get("quota_base"),
            "produits": m.get("produits"), "portee": m.get("portee"),
            "article": m.get("article"), "page_pdf": m.get("page_pdf"),
            "citation": m.get("citation"), "statut": m.get("statut")}


# PLU-EXCEPTIONS-1 — clé de règle servie (reglement_block / regles_valeurs) pour un chemin de feuille.
_CLE_REGLE = {"hauteur": "hauteur", "emprise_sol": "emprise", "pleine_terre": "pleine_terre",
              "stationnement": "stationnement", "mixite": "mixite"}


def _cle_regle(chemin: tuple) -> str:
    rub = chemin[0]
    if rub == "retraits":
        return "recul_voirie" if (len(chemin) > 1 and chemin[1] == "voie") else "recul_limites"
    return _CLE_REGLE.get(rub, rub)


def _exceptions_from_regles(commune: str | None, code: str) -> dict[str, list[dict]]:
    """Exceptions au règlement portées par les feuilles `regles` de la zone → {cle_regle: [exc…]}.
    Relaie le bloc `exception` TEL QUEL (texte verbatim, article, page, porte) ; dédoublonne par
    (cle, texte) : une même clause portée par faîtage ET égout n'apparaît qu'une fois. Ne fabrique
    rien, n'entre dans aucun calcul (PLU-EXCEPTIONS-1 Lot C)."""
    from ..plu import destinations as D
    reg = D.regles_zone(_insee(commune) or "", code)
    if not isinstance(reg, dict):
        return {}
    out: dict[str, list[dict]] = {}
    vus: set[tuple] = set()
    for chemin, feuille in D.iter_regles_feuilles(reg):
        if not isinstance(feuille, dict):
            continue
        excs = feuille.get("exceptions") or ([feuille["exception"]] if feuille.get("exception") else [])
        cle = _cle_regle(chemin)
        for exc in excs:
            if not isinstance(exc, dict) or not (exc.get("texte") or "").strip():
                continue
            clef = (cle, (exc.get("texte") or "").strip())
            if clef in vus:            # même clause portée par faîtage ET égout → une fois
                continue
            vus.add(clef)
            out.setdefault(cle, []).append({
                "texte": exc.get("texte"), "article": exc.get("article"),
                "page_pdf": exc.get("page_pdf"), "porte": exc.get("porte"),
                "modifie_calcul": bool(exc.get("modifie_calcul"))})
    return out


def _hauteur_regle_sans_valeur(reg: dict | None) -> dict | None:
    """MOTEUR-VERITE-FIX-4 LOT 3 — feuille hauteur VALIDÉE avec citation mais SANS valeur
    numérique ni plage ni R+n (ex. Saint-Denis Udo : plafonds par rue nommée, Ud.10 p.44) :
    la zone a une règle propre non chiffrable — AUCUNE hauteur générique à sa place."""
    if not reg:
        return None
    h = reg.get("hauteur") or {}
    for feuille, cle in (("egout", "m"), ("faitage", "m")):
        leaf = h.get(feuille)
        if (isinstance(leaf, dict) and leaf.get("statut") == "valide" and not leaf.get("absent")
                and not leaf.get("plage") and leaf.get(cle) is None
                and (leaf.get("citation") or "").strip()):
            return leaf
    return None


def _zone_rules_from_regles(commune: str | None, code: str, zmeta: dict) -> ZoneRules:
    """ZoneRules d'une zone CALIBRÉE : valeurs des regles + métadonnée de zone (plu_zonage)."""
    from ..plu import destinations as D
    reg = D.regles_zone(_insee(commune) or "", code)
    zm = (zmeta.get("zones") or {}).get(code, {})
    # MOTEUR-VERITE-FIX-4 LOT 3 — une zone CALIBRÉE dont la hauteur est une règle propre SANS
    # valeur (Udo : plafonds par rue) ne reçoit AUCUNE hauteur par défaut : capacité à vérifier
    # (le repli générique le faisait déjà — la voie calibrée servait 9 m, AO0742 865 m²).
    _cav = None
    _he0, _hf0 = _val(reg, "hauteur", "egout", "m"), _val(reg, "hauteur", "faitage", "m")
    _niv0 = _val(reg, "hauteur", "niveaux", "r_plus")
    if (not isinstance(_he0, (int, float)) and not isinstance(_hf0, (int, float))
            and not isinstance(_niv0, (int, float)) and zm.get("hauteur_mode") != "prospect"):
        _lh = _hauteur_regle_sans_valeur(reg)
        if _lh is not None:
            _cav = (f"hauteur en zone {code} réglée en propre ({_lh.get('article') or '?'}, "
                    f"p. {_lh.get('page_pdf') or '?'}) mais non réductible à un nombre par "
                    "parcelle — aucune hauteur générique appliquée à sa place.")
    _fond = _val(reg, "retraits", "limites_separatives", "fond_min_m")
    _ces_leaf = ((reg.get("emprise_sol") or {}).get("ces")) if reg else None
    _ces_per = (_ces_leaf or {}).get("perimetres_mesures") if isinstance(_ces_leaf, dict) else None
    return ZoneRules(
        capacite_a_verifier=_cav,
        ces_perimetres=_ces_per if isinstance(_ces_per, list) and _ces_per else None,
        recul_fond_m=_fond if isinstance(_fond, (int, float)) else None,
        code=code, bassin=zm.get("bassin"), mixite=_mixite_leaf(reg),
        exceptions=_exceptions_from_regles(commune, code),
        he_m=_val(reg, "hauteur", "egout", "m"),
        hf_m=_val(reg, "hauteur", "faitage", "m"),
        emprise_sol_pct=_val(reg, "emprise_sol", "ces", "pct"),
        recul_voirie_m=_val(reg, "retraits", "voie", "min_m"),
        recul_limites_sep_m=_val(reg, "retraits", "limites_separatives", "min_m"),
        recul_limites_formule=_val(reg, "retraits", "limites_separatives", "formule"),
        recul_voirie_alignement=_recul_alignement(reg, "voie"),
        recul_limites_alignement=_recul_alignement(reg, "limites_separatives"),
        # MOTEUR-VERITE-FIX-1 (LOT 2) — mode d'implantation par côté, calibré sous la MÊME feuille
        # VALIDÉE que le retrait (les dicts passent tels quels ; None = non calibré → retrait).
        implantation_laterales=_implantation_leaf(reg, "implantation_laterales"),
        implantation_fond=_implantation_leaf(reg, "implantation_fond"),
        h_reference=(((reg.get("retraits") or {}).get("limites_separatives") or {})
                     .get("h_reference") or None),
        # ETUDE-STATIONNEMENT (FIX-6) — barème lu par insee+zone (régimes par commune) : on garde insee/code.
        stat_logement=_stat_from_regles(reg, _insee(commune), code),
        pleine_terre_pct=_pleine_terre_val(reg),
        pleine_terre_compose=_pleine_terre_compose(reg),
        pleine_terre_nature=_pleine_terre_nature(reg),
        permeabilite_pct=_permeabilite_pct(reg),
        hauteur_mode=zm.get("hauteur_mode"),
        habitat=zm.get("habitat"),
        constructible_neuf=zm.get("constructible_neuf", True),
        notes=list(zm.get("notes") or []),   # provenance/ouverture — lues par classify_au_statut
        calibree=True, sources={}, raw={"_regles": True, "notes": zm.get("notes") or []},
    )


def _resolve_zone_base(code: str, commune: str | None = None) -> ZoneRules | None:
    """Résout le code de zone en ZoneRules (depuis regles + plu_zonage), AVANT l'overlay validé.

    Deux modes (`mode:` de plu_zonage, défaut « progressif ») :
      - `strict` (Saint-Paul, « gold ou rien ») : code hors calibrage → None ;
      - `progressif` (défaut) : code hors calibrage, ou zone sans hauteur exploitable, → estimation
        générique (`calibree=False`). `commune=None` ⇒ Saint-Paul (back-compat) ; None si code vide.
    """
    from .zone_norm import normalize_key
    from ..plu import destinations as D
    if not code:
        return None
    code = code.strip()
    zc = _zonage_commune(commune)
    ins = _insee(commune)
    # « commune outillée » = elle a une métadonnée de zonage OU des regles (les communes extraites
    # par l'agent interne n'ont pas d'entrée plu_zonage mais ont des regles).
    # « calibrée » = la zone porte une feuille d'ENVELOPPE (hauteur/emprise/reculs/stationnement/…).
    # Une zone qui ne porte qu'une feuille descriptive (entre_constructions, PLU-CALIBRAGE-10) n'est
    # PAS reconnue ici en correspondance directe : elle se résout par sa branche dédiée (gelée, renvoi,
    # estimation), comme avant l'injection de ces feuilles.
    reg_zones = D.zones_calibrees(ins) if ins else set()
    # PLU-CALIBRAGE-8 (oct.) Lot B — les zones qui tirent leurs règles d'un `renvoi` (sans `regles`
    # propre) sont RÉSOLVABLES et CALIBRÉES : `_zone_regles_brut` suit déjà le renvoi pour les valeurs,
    # il ne manquait que de les reconnaître ici (sinon repli générique → gabarit bloqué « non calibré »).
    renvois = D.renvois_commune(ins) if ins else {}
    outillee = (zc is not None) or bool(reg_zones) or bool(renvois)
    if outillee:
        zc = zc or {}
        strict = (zc.get("mode") == "strict")
        zones = set(reg_zones) | set(renvois) | set((zc.get("zones") or {}).keys())
        norm = {normalize_key(c): c for c in zones}

        def _resolu_direct(hit: str, lib: str, prefixe_phase: str | None = None):
            """Construit le ZoneRules d'une zone calibrée (ou renvoi), avec garde `propose` et via_renvoi."""
            nv = _regles_sdp_non_validees(D.regles_zone(ins, hit)) if ins else []
            if nv:
                return _zone_regle_non_validee(lib, nv)    # règle PLU non validée → non calculable
            r = _zone_rules_from_regles(commune, hit, zc)
            r.code = lib
            if hit in renvois:
                r.via_renvoi = f"{lib} → règles de {renvois[hit]} (renvoi du règlement)"
            elif prefixe_phase:
                r.via_renvoi = f"{lib} → règles de {hit} (zone AU phasée « {prefixe_phase} »)"
            if strict or _has_usable_height(r):
                return r
            # RECETTE-PROD-1 (A7) — zone calibrée pour l'enveloppe mais sans hauteur unique exploitable :
            # on GARDE ses valeurs calibrées (calibree=True → plus de faux « PLU non calibré ») et on
            # complète la SEULE hauteur par le repli générique, en le DISANT (note + source). On ne jette
            # plus l'emprise/les reculs calibrés au profit d'une estimation entièrement générique.
            from .zone_norm import est_famille
            if _a_enveloppe_calibree(r) and est_famille(lib, _positive_prefixes()):
                from .engine import HE_DEFAUT_GENERIQUE_M
                return _replace(
                    r, he_m=float(HE_DEFAUT_GENERIQUE_M), hauteur_estimee=True,
                    notes=[*(r.notes or []), _NOTE_HAUTEUR_GRAPHIQUE],
                    sources={**(r.sources or {}), "hauteur": "hauteur estimée (table graphique par secteur, non chiffrable en valeur unique)"})
            return _zone_generique(lib, commune)

        # 1) correspondance directe (normalisée)
        hit = norm.get(normalize_key(code))
        if hit is not None:
            return _resolu_direct(hit, code)

        # 1bis) zone AU PHASÉE « <n>AU<indice> » (1AU/2AU = phasage, mêmes règles par indice) : si
        #   « AU<indice> » existe (clé directe ou renvoi), on l'utilise. Additif — ces codes ne
        #   trouvaient aucun hit auparavant (le renvoi pattern étape 3 exige « AU<chiffre> »).
        mph = re.fullmatch(r"(\d+)(AU\w+)", code, re.I)
        if mph is not None:
            hit_ph = norm.get(normalize_key(mph.group(2)))
            if hit_ph is not None:
                return _resolu_direct(hit_ph, code, prefixe_phase=mph.group(1) + "AU")

        # 2) zones AU*st — pas de construction neuve
        st = zc.get("zones_au_st") or {}
        st_norm = {normalize_key(x) for x in (st.get("liste") or [])}
        if normalize_key(code) in st_norm or re.fullmatch(r"AU\w*st", code, re.I):
            _hmax = st.get("hauteur_max_m")
            return ZoneRules(
                code=code, constructible_neuf=False,
                hf_m=float(_hmax) if _hmax is not None else None,
                notes=[st.get("portee", "Travaux mineurs uniquement")],
                sources=({"hauteur": st["source"]} if (_hmax is not None and st.get("source")) else {}))

        # 3) renvoi AU<n><indice> → U<n><indice>
        m = re.fullmatch(r"AU(\d[a-zA-Z0-9]*)", code, re.I)
        if m:
            u_code = "U" + m.group(1)
            hit_u = norm.get(normalize_key(u_code))
            if hit_u is not None:
                nv = _regles_sdp_non_validees(D.regles_zone(ins, hit_u)) if ins else []
                if nv:
                    return _zone_regle_non_validee(code, nv)   # renvoi vers zone U à règle non validée
                r = _zone_rules_from_regles(commune, hit_u, zc)
                r.code = code
                r.via_renvoi = (f"{code} → règles de {hit_u} (renvoi du règlement, "
                                f"{(zc.get('zones_au_renvoi') or {}).get('AU' + m.group(1)[0], 'caractère de zone')})")
                return r

        # 4) code hors zonage : strict → None ; progressif → estimation
        return None if strict else _zone_generique(code, commune)

    return _zone_generique(code, commune)           # commune SANS calibrage → capacité ESTIMÉE générique


def resolve_zone(code: str, commune: str | None = None) -> ZoneRules | None:
    """Résout le code de zone, PUIS superpose les règles chiffrées validées (PLU-CALIBRAGE-2), PUIS
    complète le renvoi AU → U (ORACLE-FIX-1 Lot A : règles SDP reprises de la zone U de renvoi)."""
    rules = _appliquer_calibrage(_resolve_zone_base(code, commune), code, commune)
    return _completer_renvoi(rules, code, commune)


# rétro-compat : le harnais d'équivalence et d'anciens scripts nomment resolve_zone_v2.
resolve_zone_v2 = resolve_zone


# ── DONNEES-FIX-1 point 4 — les exceptions PLU `modifie_calcul=true` entrent au moteur ────────────
# Constat : 81 exceptions (bandes depuis limite, sous-secteurs, majorations conditionnelles) étaient
# AFFICHÉES sous le « i » mais jamais déduites. Elles entrent maintenant par le MÊME système unique
# que le reste des règles (ce module). Calibrage figé, sourcé article/page, dans
# `config/plu_exceptions_effet.json` (index = ligne de PLU-EXCEPTIONS-1/A_CALIBRER.csv). Quatre
# décisions, une seule source :
#   · applique       — la valeur de l'exception entre dans ZoneRules SI sa condition est vérifiée
#                      (ex. majoration de hauteur si terrain ≥ seuil), jamais approximée ;
#   · deja_couvert   — le sous-secteur cité se résout DÉJÀ comme sa propre zone calibrée (resolve_zone
#                      lui sert la bonne valeur) → aucune action sur la zone parente ;
#   · hors_sdp       — n'affecte pas l'enveloppe SDP (stationnement) → aucune action ;
#   · non_modelisee  — on NE l'approxime PAS : la règle reste affichée et la parcelle la PORTE
#                      (« règle non modélisée », avec article/page), jamais une valeur inventée.
_EXC_EFFET = _CONFIG / "plu_exceptions_effet.json"


@lru_cache(maxsize=1)
def _exceptions_effet() -> dict[tuple[str, str], list[dict]]:
    """Calibrage des 81 exceptions `modifie_calcul=true`, indexé par (insee, zone). SOURCE UNIQUE.

    ORF-19 (FIX-ORFEVRE-1) — un JSON CORROMPU **lève** (avant : `except ValueError: return {}` faisait
    disparaître EN SILENCE les 81 exceptions PLU `modifie_calcul=true` → capacités recalculées sans
    elles, zéro signal). Seul le fichier ABSENT reste un repli assumé (base de test nue)."""
    import json
    try:
        raw = json.loads(_EXC_EFFET.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.debug("plu_exceptions_effet.json absent — aucune exception PLU appliquée (base nue)")
        return {}
    except ValueError as exc:
        log.error("plu_exceptions_effet.json CORROMPU : %s — les 81 exceptions PLU seraient perdues "
                  "en silence, on refuse de calculer sans elles", exc)
        raise ValueError(f"config/plu_exceptions_effet.json illisible (JSON corrompu) : {exc}") from exc
    out: dict[tuple[str, str], list[dict]] = {}
    for e in (raw.get("entries") or {}).values():
        out.setdefault((e["insee"], e["zone"]), []).append(e)
    return out


def appliquer_exceptions_calcul(rules: "ZoneRules | None", commune: str | None,
                                zone_lib: str | None, surface_m2: float | None
                                ) -> tuple["ZoneRules | None", list[dict]]:
    """Applique au moteur les exceptions PLU `modifie_calcul=true` de (commune, zone_lib) et renvoie
    (rules ajustées, règles non modélisées). Copie la ZoneRules (dataclasses.replace) — la règle de
    zone partagée n'est JAMAIS mutée. Une majoration ne fait que RELÂCHER (valeur plus haute) : elle
    n'abaisse jamais une contrainte de zone (garde de sens)."""
    if rules is None or not zone_lib:
        return rules, []
    ins = _insee(commune)
    if not ins:
        return rules, []
    non_modelisees: list[dict] = []
    for e in _exceptions_effet().get((ins, zone_lib), []):
        dec = e.get("decision")
        if dec == "non_modelisee":
            # PLU-CALIBRAGE-5 — on PORTE aussi le verbatim (`texte`, source A_CALIBRER.csv) : la fiche
            # affiche sous la capacité « une exception du règlement n'est pas modélisée » AVEC son texte.
            non_modelisees.append({"regle": e.get("regle"), "porte": e.get("porte"),
                                   "article": e.get("article"), "page_pdf": e.get("page_pdf"),
                                   "texte": e.get("texte")})
        elif dec == "applique":
            eff = e.get("effet") or {}
            if eff.get("type") == "majoration_surface":
                seuil, champ, val = eff.get("seuil_m2"), eff.get("champ"), eff.get("valeur")
                if (surface_m2 is not None and seuil is not None and champ and val is not None
                        and float(surface_m2) >= float(seuil)):
                    cur = getattr(rules, champ, None)
                    if not isinstance(cur, (int, float)) or float(val) > float(cur):
                        rules = _replace(rules, **{champ: float(val)})
        # deja_couvert / hors_sdp : aucune action (documenté au calibrage)
    return rules, non_modelisees


def load_rules(commune: str | None = None) -> dict[str, ZoneRules]:
    """(Sous-)zones d'une commune → ZoneRules (regles + overlay validé), sans repli générique
    (chaque zone garde ses valeurs calibrées, ex. l'emprise, même sans hauteur exploitable)."""
    from ..plu import destinations as D
    zc = _zonage_commune(commune) or {}
    ins = _insee(commune)
    codes = set((zc.get("zones") or {}).keys())
    if ins:
        codes |= {r["zone"] for r in D.regles_commune(ins)}
    out: dict[str, ZoneRules] = {}
    for code in codes:
        out[code] = _appliquer_calibrage(_zone_rules_from_regles(commune, code, zc), code, commune)
    return out


def est_outillee(commune: str | None) -> bool:
    """La commune a-t-elle un calibrage (métadonnée de zonage OU regles) ? Remplace l'ancien
    `_calibrated_yaml(commune) is not None`."""
    from ..plu import destinations as D
    if _zonage_commune(commune) is not None:
        return True
    ins = _insee(commune)
    return bool(ins and D.regles_commune(ins))


def reglement_source(commune: str | None, zone: str | None = None) -> dict | None:
    """Métadonnée du document règlement de la commune (URL, document, édition, millésime), lue de
    module `plu.destinations` (meta). Remplace l'ancien `_doc(commune)['source']`. `offset` = 0 : regles
    portent `page_pdf` (page PDF réelle), plus de conversion page imprimée → page PDF."""
    from ..plu import destinations as D
    meta = D.reglement_meta(commune, zone) if commune else D.reglement_meta(_insee(commune) or "", zone)
    if meta is None:
        return None
    return {"url": meta.get("url"), "document": meta.get("document"),
            "edition": meta.get("edition"), "approbation": meta.get("edition"),
            "millesime": meta.get("millesime"), "note_locale": meta.get("note_locale"), "offset": 0}


# ── superposition des feuilles VALIDÉES (branchement PLU-CALIBRAGE-2, lu de destinations) ────────
_ABSENT_SENTINELLE = "pas de règle dans le PLU"


def _art(leaf: dict) -> str:
    """« Article Ud.7 » ou « Ud 10 » → « Art. Ud.7 » (jamais « Art. Article … »)."""
    a = str(leaf.get("article") or "").strip()
    a = re.sub(r"^\s*articles?\s+", "", a, flags=re.I)
    return f"Art. {a}"


def _src_validee(leaf: dict) -> str:
    return f"{_art(leaf)} · p.{leaf.get('page_pdf')} (PLU, calibrage validé)"


def _src_absente(leaf: dict) -> str:
    return f"{_ABSENT_SENTINELLE} (silence prouvé — {_art(leaf)} · p.{leaf.get('page_pdf')})"


@lru_cache(maxsize=4096)
def _calibrage_overlay(code: str, commune: str | None):
    """Overrides (valeurs + sources) tirés des règles chiffrées VALIDÉES de la (commune, zone),
    ou None si rien à appliquer. Ne considère QUE les feuilles `valide` / `absent` — jamais
    `propose`. Mis en cache (les regles ne changent pas en cours de process)."""
    from ..plu import destinations as _D
    ins = _insee(commune)
    if not ins:
        return None
    reg = _D.regles_zone(ins, code)
    if not reg:
        return None
    champs: dict = {}
    src: dict[str, str] = {}

    def _feuille(*chemin):
        """La feuille (valeur OU silence prouvé) SEULEMENT si son statut est `valide` ; sinon
        None (un `propose` ne branche jamais le calcul)."""
        n = reg
        for k in chemin:
            n = n.get(k) if isinstance(n, dict) else None
            if n is None:
                return None
        return n if (isinstance(n, dict) and n.get("statut") == "valide") else None

    # hauteur : faîtage (hf), égout (he), niveaux (R+n imposé)
    fait = _feuille("hauteur", "faitage")
    ego = _feuille("hauteur", "egout")
    niv = _feuille("hauteur", "niveaux")
    if fait and fait.get("plage"):
        champs["hauteur_plage"] = {**fait, "source": _src_validee(fait)}
        src["hauteur"] = _src_validee(fait)
    elif fait and not fait.get("absent") and isinstance(fait.get("m"), (int, float)):
        champs["hf_m"] = float(fait["m"]); src["hauteur"] = _src_validee(fait)
        champs["hauteur_mode"] = None      # une hauteur ABSOLUE validée prime sur le mode prospect
    if ego and not ego.get("absent") and isinstance(ego.get("m"), (int, float)):
        champs["he_m"] = float(ego["m"]); src.setdefault("hauteur", _src_validee(ego))
    if niv and not niv.get("absent") and isinstance(niv.get("r_plus"), int):
        champs["niveaux_max"] = int(niv["r_plus"]); src.setdefault("hauteur", _src_validee(niv))
    for leaf in (fait, ego, niv):
        if leaf and leaf.get("absent"):
            src.setdefault("hauteur", _src_absente(leaf))

    # emprise au sol (CES)
    ces = _feuille("emprise_sol", "ces")
    if ces and ces.get("plage"):
        champs["emprise_plage"] = {**ces, "source": _src_validee(ces)}
        src["emprise"] = _src_validee(ces)
    elif ces and not ces.get("absent") and isinstance(ces.get("pct"), (int, float)):
        champs["emprise_sol_pct"] = float(ces["pct"]); src["emprise"] = _src_validee(ces)
    elif ces and ces.get("absent"):
        src["emprise"] = _src_absente(ces)         # l'étape « % réglementé » le dira

    # retraits : voie, limites séparatives (min_m — la formule est évaluée telle quelle par le moteur ;
    # PLU-CALIBRAGE-7 forme 1 : « forme: alignement » = recul 0 EXPLICITE, ≠ absent)
    voie = _feuille("retraits", "voie")
    lim = _feuille("retraits", "limites_separatives")
    if voie and voie.get("forme") == "alignement":
        champs["recul_voirie_m"] = 0.0; champs["recul_voirie_alignement"] = True
        src["recul_voirie"] = _src_validee(voie)
    elif voie and not voie.get("absent") and isinstance(voie.get("min_m"), (int, float)):
        champs["recul_voirie_m"] = float(voie["min_m"]); src["recul_voirie"] = _src_validee(voie)
    elif voie and voie.get("absent"):
        src["recul_voirie"] = _src_absente(voie)
    if lim and lim.get("forme") == "alignement":
        champs["recul_limites_sep_m"] = 0.0; champs["recul_limites_alignement"] = True
        src["recul_limites"] = _src_validee(lim)
    elif lim and not lim.get("absent") and isinstance(lim.get("min_m"), (int, float)):
        champs["recul_limites_sep_m"] = float(lim["min_m"]); src["recul_limites"] = _src_validee(lim)
    elif lim and lim.get("absent"):
        src["recul_limites"] = _src_absente(lim)

    # pleine terre (PLU-CALIBRAGE-7 forme 2 : composée `espaces_verts_pct × pleine_terre_part`) —
    # sourcée ici (l'ancienne lecture base-only ne portait pas d'article) ; valeur = _pleine_terre_val.
    pt = _feuille("pleine_terre", "pct")
    if pt and not pt.get("absent"):
        _ptv = _pleine_terre_val(reg)
        if isinstance(_ptv, (int, float)):
            champs["pleine_terre_pct"] = float(_ptv); src["pleine_terre"] = _src_validee(pt)
            _cmp = _pleine_terre_compose(reg)
            if _cmp:
                champs["pleine_terre_compose"] = _cmp
            _nat = _pleine_terre_nature(reg)       # CHIRURGICAL-FIX-1 (LOT H pt8) — nom de la règle citée
            if _nat:
                champs["pleine_terre_nature"] = _nat
            _perm = _permeabilite_pct(reg)         # CHIRURGICAL-FIX-1 (LOT I 3c) — 2e obligation de sol
            if _perm is not None:
                champs["permeabilite_pct"] = _perm
    elif pt and pt.get("absent"):
        src["pleine_terre"] = _src_absente(pt)

    # stationnement (par logement)
    st = _feuille("stationnement", "par_logement")
    # CHIRURGICAL-FIX-1 (LOT I 3c) — un BARÈME chiffré (feuille `bareme`) DIT SA PORTÉE (Le Tampon :
    # « 1 place / logement ; 1,5 au-delà de 5 lots/logements ») : on le sert tel quel, comme la lecture
    # de base `_stat_from_regles`, au lieu de réduire au seul « 1 place / logement ».
    if st and not st.get("absent") and isinstance(st.get("bareme"), str) and st["bareme"].strip():
        champs["stat_logement"] = st["bareme"].strip()
        src["stationnement"] = _src_validee(st)
    elif st and not st.get("absent") and isinstance(st.get("places"), (int, float)):
        p = st["places"]; p = int(p) if float(p).is_integer() else p
        champs["stat_logement"] = f"{p} place / logement" if p == 1 else f"{p} places / logement"
        src["stationnement"] = _src_validee(st)
    elif st and st.get("absent"):
        src["stationnement"] = _src_absente(st)
    # ETUDE-STATIONNEMENT (merge moteur-verite) — barème PAR TYPOLOGIE (Le Tampon Ua/Ud 12.2, et secteurs qui le
    # renvoient) : pas de feuille `par_logement`, l'article/source vient de `par_typologie`. Sans quoi la ligne
    # du Dossier renverrait « au règlement de la zone » au lieu de l'article précis (Ud 12.2).
    if "stationnement" not in src:
        stt = _feuille("stationnement", "par_typologie")
        if stt and not stt.get("absent") and stt.get("article"):
            src["stationnement"] = _src_validee(stt)

    if not champs and not src:
        return None
    return champs, src


def _appliquer_calibrage(rules: ZoneRules | None, code: str, commune: str | None) -> ZoneRules | None:
    """Superpose les règles chiffrées validées à un ZoneRules (identité si rien à appliquer)."""
    if rules is None:
        return None
    ov = _calibrage_overlay(code, commune)
    if ov is None:
        return rules
    champs, src = ov
    return _replace(rules, sources={**(rules.sources or {}), **src}, **champs)


# ── ORACLE-FIX-1 (Lot A) — complétion du renvoi AU → U ────────────────────────────────────────────
# Constat ORACLE-1 (défaut systémique n°1) : des zones AU<indice> servent recul/pleine terre/stationnement
# « non réglementé » alors que le règlement les fixe — parce que leur bloc `regles` n'a calibré QU'UNE
# partie (souvent la seule hauteur), et que le renvoi « se reporter au règlement de la zone U<indice> »
# (art. AUindicée) n'était appliqué qu'aux codes SANS hit direct (étape 3 de _resolve_zone_base) et
# seulement pour la forme « AU<chiffre> ». Résultat : le moteur calculait la SDP comme si recul/pleine
# terre étaient LIBRES (capacité gonflée — témoin S07 2AUd Le Tampon → Ud). On complète ici : toute règle
# SDP laissée None par la zone AU est reprise de sa zone U de renvoi (valeur + source « via renvoi »),
# SANS jamais écraser une règle déjà posée par la zone AU. Corrige l'affichage (regles_valeurs) ET la
# capacité (même ZoneRules), sur toute l'île, en un seul point.
_RENVOI_AU = re.compile(r"^(\d*)AU(\w+)$", re.I)   # 2AUd→Ud · 1AUe→Ue · AU1a→U1a

# champ ZoneRules SDP → (clé de source, champs auxiliaires solidaires à reprendre ensemble)
_SDP_RENVOI = {
    "he_m": ("hauteur", ()),
    "hf_m": ("hauteur", ("hauteur_plage", "hauteur_mode")),
    "emprise_sol_pct": ("emprise", ("emprise_plage",)),
    "recul_voirie_m": ("recul_voirie", ("recul_voirie_alignement",)),
    "recul_limites_sep_m": ("recul_limites", ("recul_limites_alignement",)),
    "pleine_terre_pct": ("pleine_terre", ("pleine_terre_compose",)),
    "stat_logement": ("stationnement", ()),
}


def _ref_u_code(code: str | None) -> str | None:
    """Code de la zone U de renvoi d'une zone AU<indice> (2AUd→Ud, 1AUe→Ue, AU1a→U1a). None sinon."""
    m = _RENVOI_AU.match((code or "").strip())
    return ("U" + m.group(2)) if m else None


def _completer_renvoi(rules: "ZoneRules | None", code: str, commune: str | None) -> "ZoneRules | None":
    """Reprend de la zone U de renvoi les règles SDP que la zone AU laisse None (voir note ci-dessus)."""
    from .zone_norm import normalize_key
    from ..plu import destinations as D
    if rules is None or not getattr(rules, "calibree", False):
        return rules
    u = _ref_u_code(code)
    ins = _insee(commune)
    if not u or not ins or normalize_key(u) == normalize_key(code):
        return rules
    u_hit = {normalize_key(r["zone"]): r["zone"] for r in D.regles_commune(ins)}.get(normalize_key(u))
    if u_hit is None:
        return rules
    ov = _calibrage_overlay(u_hit, commune)
    if ov is None:
        return rules
    champs, src = ov
    # PLU-CALIBRAGE-8 (oct.) Lot D — ne JAMAIS emprunter à la zone U un champ que le règlement de la
    # zone AU prouve ABSENT (silence prouvé = affirmation « pas de règle ici », pas un trou). Sans quoi
    # la complétion par motif AU→U inventerait une valeur contre le texte (ex. Saint-Leu AUe : l'Art.
    # AU 10 ne fixe QUE l'égout → le faîtage ne doit pas être emprunté à UE, aucun renvoi écrit).
    au_reg = D.regles_zone(ins, code) or {}

    def _prouve_absent(rub: str, feu: str) -> bool:
        leaf = (au_reg.get(rub) or {}).get(feu)
        return isinstance(leaf, dict) and leaf.get("absent") is True and leaf.get("statut") == "valide"

    _ABSENT_FEUILLE = {
        "he_m": ("hauteur", "egout"), "hf_m": ("hauteur", "faitage"),
        "emprise_sol_pct": ("emprise_sol", "ces"), "recul_voirie_m": ("retraits", "voie"),
        "recul_limites_sep_m": ("retraits", "limites_separatives"),
        "pleine_terre_pct": ("pleine_terre", "pct"), "stat_logement": ("stationnement", "par_logement"),
    }
    fill: dict = {}
    new_src = dict(rules.sources or {})
    for champ, (cle_src, aux) in _SDP_RENVOI.items():
        if getattr(rules, champ, None) is None and champ in champs:
            rc = _ABSENT_FEUILLE.get(champ)
            if rc and _prouve_absent(*rc):
                continue                       # silence prouvé par le règlement de la zone AU
            fill[champ] = champs[champ]
            for a in aux:
                if a in champs:
                    fill[a] = champs[a]
            if cle_src in src and cle_src not in new_src:
                new_src[cle_src] = f"{src[cle_src]} — via renvoi {code} → {u_hit}"
    if not fill:
        return rules
    return _replace(rules, via_renvoi=f"{code} → règles de {u_hit} (renvoi du règlement)",
                    sources=new_src, **fill)


# ── repli générique + hypothèses moteur ─────────────────────────────────────────────────────────
def _has_usable_height(r: ZoneRules) -> bool:
    """Le moteur ne calcule des niveaux que si he_m OU hf_m est chiffré (sinon « non constructible »).
    EXCEPTION : zone 'prospect' → hf_m calculé PAR PARCELLE, donc considérée exploitable."""
    return r.hauteur_mode == 'prospect' or isinstance(r.he_m, (int, float)) or isinstance(r.hf_m, (int, float))


# RECETTE-PROD-1 (A7) — une zone peut être CALIBRÉE pour l'enveloppe (emprise, reculs, niveaux) alors
# que sa HAUTEUR n'est pas réductible à une valeur unique (ex. table graphique par secteur, Art. U-4 à
# La Réunion). Sans cette distinction, `_resolu_direct` la jetait en `_zone_generique` (calibree=False)
# → le gabarit affichait « PLU non calibré pour la zone Ub », FAUX (l'emprise CES 80 % est calibrée).
_NOTE_HAUTEUR_GRAPHIQUE = ("Hauteur réglementaire non réductible à une valeur unique (table graphique "
                           "par secteur) — hauteur estimée ; emprise et reculs restent calibrés.")


def _a_enveloppe_calibree(r: ZoneRules) -> bool:
    """La zone porte au moins une feuille d'enveloppe chiffrée (emprise / reculs / niveaux), même si la
    hauteur manque. Sert à NE PAS la déclasser en « PLU non calibré » quand seule la hauteur est absente."""
    return (isinstance(r.emprise_sol_pct, (int, float)) or r.emprise_plage is not None
            or isinstance(r.recul_voirie_m, (int, float)) or r.recul_voirie_alignement
            or isinstance(r.recul_limites_sep_m, (int, float)) or r.recul_limites_alignement
            or r.recul_limites_formule is not None or isinstance(r.niveaux_max, int))


def _positive_prefixes() -> tuple[str, ...]:
    """Préfixes constructibles — SOURCE UNIQUE : cascade_rules.yaml › zonage_plu_gpu."""
    from .. import config
    for lc in config.cascade_rules().get("layers", []):
        if lc.get("name") == "zonage_plu_gpu":
            return tuple(lc.get("params", {}).get("positive_prefixes", ["U", "AU"]))
    return ("U", "AU")


def _zone_generique(code: str, commune: str | None = None) -> ZoneRules:
    """Règles ESTIMÉES pour une zone hors calibrage (calibree=False) : préfixe U/AU →
    constructible (hé générique prudent) ; N/A → non constructible."""
    from .zone_norm import est_famille
    constructible = est_famille(code, _positive_prefixes())
    note = ("Capacité ESTIMÉE — PLU de la commune non calibré. Valeurs génériques prudentes ; "
            "calibrage = extraction des regles de la commune.")
    if not constructible:
        return ZoneRules(code=code, calibree=False, constructible_neuf=False,
                         notes=[note], sources={"zone": "estimation générique"})
    from .engine import HE_DEFAUT_GENERIQUE_M
    he = float(HE_DEFAUT_GENERIQUE_M)
    # MOTEUR-VERITE-FIX-2 LOT C puis FIX-3 LOT 2 — le REPLI générique lit TOUTES les valeurs
    # calibrées de la zone quand elles existent (feuilles validées des destinations), au lieu
    # des défauts : Saint-Denis Uicm porte « 5 m minimum » ET un CES de 40 % (Ui.9) en propre,
    # le repli servait 3 m et le CES générique ; même chose pour la hauteur (Udo a sa propre
    # règle). La zone n'est pas « calibrée » pour autant (calibree=False, avertissement servi).
    _reg = None
    if commune:
        from ..plu import destinations as _D
        _reg = _D.regles_zone(_insee(commune) or "", code) or None

    def _num(rub: str, feuille: str, cle: str):
        v = _val(_reg, rub, feuille, cle) if _reg else None
        return float(v) if isinstance(v, (int, float)) else None

    _he = _num("hauteur", "egout", "m")
    _hf = _num("hauteur", "faitage", "m")

    def _regle_sans_valeur(rub: str, feuille: str, cle: str) -> dict | None:
        """Feuille VALIDÉE avec citation mais SANS valeur numérique : la zone a une règle propre
        non réductible à un nombre — le générique ne doit pas la remplacer."""
        leaf = ((_reg.get(rub) or {}).get(feuille)) if _reg else None
        if (isinstance(leaf, dict) and leaf.get("statut") == "valide" and not leaf.get("absent")
                and not leaf.get("plage") and leaf.get(cle) is None
                and (leaf.get("citation") or "").strip()):
            return leaf
        return None

    _cav = None
    if _he is None and _hf is None:
        _lh = _regle_sans_valeur("hauteur", "egout", "m") or _regle_sans_valeur("hauteur", "faitage", "m")
        if _lh is not None:
            _cav = (f"hauteur en zone {code} réglée en propre ({_lh.get('article') or '?'}, "
                    f"p. {_lh.get('page_pdf') or '?'}) mais non réductible à un nombre par "
                    "parcelle — aucune hauteur générique appliquée à sa place.")
    src_h = ("règle propre de la zone (feuille validée lue par le repli)"
             if (_he is not None or _hf is not None)
             else "estimation générique (PLU non outillé)")
    return ZoneRules(code=code, calibree=False, notes=[note],
                     he_m=_he if _he is not None else he, hf_m=_hf,
                     emprise_sol_pct=_num("emprise_sol", "ces", "pct"),
                     recul_voirie_m=_num("retraits", "voie", "min_m"),
                     recul_limites_sep_m=_num("retraits", "limites_separatives", "min_m"),
                     capacite_a_verifier=_cav,
                     sources={"hauteur": src_h, "zone": "estimation générique"})


def hypotheses_faisabilite(commune: str | None = None) -> dict:
    """Section `hypotheses_faisabilite` migrée dans plu_zonage.yaml (remplace l'ancien point de
    lecture des plu_<slug>.yaml). Commune non outillée → {} (l'appelant retombe sur les défauts)."""
    zc = _zonage_commune(commune)
    return (zc or {}).get("hypotheses_faisabilite") or {}


# rétro-compat de nom pour le harnais d'équivalence.
hypotheses_faisabilite_v2 = hypotheses_faisabilite


def _hypotheses_ile() -> dict:
    """Hypothèses ÎLE-GÉNÉRIQUES (source NEUTRE `config/hypotheses_ile.yaml`), base AVANT tout
    override commune. Valeurs identiques aux anciens défauts → golden = baseline.

    ORF-19 (FIX-ORFEVRE-1) — seul le fichier ABSENT est un repli assumé (défauts dataclass, base de
    test nue). Un YAML CASSÉ **lève** (avant : `except Exception: return {}` → chiffres qui bougent
    sans trace)."""
    from .. import config
    try:
        return (config.load_yaml_config("hypotheses_ile") or {}).get("hypotheses_ile") or {}
    except FileNotFoundError:
        log.debug("hypotheses_ile.yaml absent — défauts dataclass (base nue)")
        return {}
    except Exception as exc:  # noqa: BLE001 — YAML corrompu : on refuse le repli silencieux
        log.error("hypotheses_ile.yaml ILLISIBLE : %s — repli silencieux refusé (les hypothèses de "
                  "calcul bougeraient sans trace)", exc)
        raise ValueError(f"config/hypotheses_ile.yaml illisible : {exc}") from exc
