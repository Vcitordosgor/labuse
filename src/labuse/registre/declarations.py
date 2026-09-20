"""RACCORDEMENT-1 lot 0 — LE LOADER DES DÉCLARATIONS.

Le registre (`donnees.py`) est LE COMPTEUR. Une *déclaration* est UN CÂBLE : un fichier YAML
par surface spécifique (dossier `declarations/`, hors code, lisible par Vic) qui nomme les
données du registre que la surface affiche, où, comment, sa phrase d'absence et pourquoi.

Ce module lit ces fichiers et en DÉRIVE le graphe de câblage (jamais saisi deux fois) :
  - `charger()`           → toutes les surfaces spécifiques + les génériques ;
  - `verifier()`          → deux listes SÉPARÉES : les *violations de format* (champ obligatoire
                            manquant, état inconnu — doivent être vides) et les *câbles
                            orphelins* (un `quoi` absent du registre — une donnée à créer, un
                            findings du mandat, PAS un crash) ;
  - `cablage()`           → l'onglet Câblage (lot 6) : par donnée qui la consomme, par surface
                            ce qu'elle prend et ce qu'elle pourrait prendre.

Le format est FIGÉ au lot 0 (cf. declarations/FORMAT.md).
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

import yaml

#: racine du dépôt = trois niveaux au-dessus de src/labuse/registre/
_RACINE = pathlib.Path(__file__).resolve().parents[3]
DECLARATIONS = _RACINE / "declarations"

CATEGORIES = ("fiche", "fiche_commune", "outil", "couche", "radar", "document", "score", "cascade")
ETATS = ("en_tete", "replie", "sur_demande")
FORMATS = ("entier", "entier_m2", "metre", "pourcent", "euro", "euro_m2", "degre",
           "classe", "texte", "liste", "date", "verdict")
#: RACCORDEMENT-1 (ajustement Vic) — le CLIENT n'entend pas la même phrase selon la CAUSE de
#: l'absence. Trois causes distinctes (les deux demandées + `non_ingeree`, imposée par des cas
#: réels comme la TFPB « taux non ingéré » : la source publie, LABUSE n'a pas encore ingéré) :
ABSENCE_TYPES = ("absente_ici", "non_publiee", "non_ingeree")
#: RACCORDEMENT-1 lot 2 (Risques, Vic) — le STATUT JURIDIQUE d'une ligne : un promoteur distingue
#: d'un coup d'œil ce qui BLOQUE (opposable) de ce qui INFORME. Optionnel (les sections non
#: réglementaires l'omettent) ; pour une liste hétérogène (aléas), le statut est porté PAR ITEM.
STATUTS_JURIDIQUES = ("opposable", "en_projet", "informatif")
#: RACCORDEMENT-1 lot 3 — la FAMILLE d'une couche (Vic) : le panneau range les 51 couches par
#: catégorie, DEPUIS la déclaration (pas un groupe codé dans Legend.tsx). Un seul panneau à l'écran.
# COUCHES-RECETTE-1 A11 : « reperes » (limites communes/parcelles, en tête, cochées par défaut) et
# « equipements » (BPE + OSM, sortis de « fond_de_plan »). « fond_de_plan » reste déclarée (le bâti 3D
# la garde en YAML) mais disparaît du panneau — il part dans le bouton 3D (exclu côté front).
FAMILLES = ("reperes", "fond_de_plan", "urbanisme", "risques", "environnement", "foncier",
            "reseaux", "transport", "dispositifs", "patrimoine", "marche", "equipements")
#:   · absente_ici  — la source publie, mais la parcelle/le bien n'a pas la donnée (pas de bâti…) ;
#:   · non_publiee  — le producteur ne publie pas (commune/périmètre/échelle non couverts) ;
#:   · non_ingeree  — la source publie, LABUSE ne l'a pas encore ingérée ici (dette interne ;
#:                    la phrase client reste NEUTRE, ne dit jamais « non ingéré »).


@dataclass(frozen=True)
class Ligne:
    quoi: str
    rang: int
    etat: str
    section: str | None
    comment: dict = field(default_factory=dict)
    absence: str = ""
    absence_type: str = ""
    statut_juridique: str | None = None    # opposable · en_projet · informatif (sections réglementaires)
    #: RACCORDEMENT-1 lot 3 — LE STYLE CARTE, porté par la DÉCLARATION (Vic : « une couche nouvelle
    #: s'affiche en ajoutant un fichier, sans toucher au front »). `carte` = {kind, geometrie
    #: (point|ligne|polygone), zoom_min, rang_carte, style {couleur, opacite, trait, rayon},
    #: legende, niveaux[] (pour un rendu multi — piscines : 3 niveaux, chacun couleur+quand+legende)}.
    carte: dict = field(default_factory=dict)
    pourquoi: str = ""
    #: EXPORTS-REBRANCHEMENT-1 lot 1 — surcharge PAR LIGNE de la section fiche (`ou.fiche_section`)
    #: quand une surface chevauche deux sections (le_bien : bâti + terrain). None = celle de la surface.
    fiche_section: str | None = None


@dataclass(frozen=True)
class Surface:
    surface: str
    nom: str
    categorie: str
    parent: str | None
    route: str
    rendu: str
    donnees: tuple[Ligne, ...]
    chemin: str = ""
    #: EXPORTS-REBRANCHEMENT-1 lot 1 — la SECTION de la fiche (sections.yaml) à laquelle cette
    #: surface appartient ; le Dossier PDF (miroir) s'ordonne par elle. None = hors sections (couches…).
    fiche_section: str | None = None


@dataclass(frozen=True)
class Generique:
    surface: str
    nom: str
    route: str
    regle: str


#: RACCORDEMENT-1 lot 1 — `declarations/_exemples/` = les échantillons de FORMAT (validation du
#: lot 0), PAS des câbles de production : l'assembleur et l'onglet Câblage lisent la PRODUCTION
#: seule (arbre vide au lot 1 → fiche vide sous `?raccorde=1`) ; les tests de format les incluent.
EXEMPLES = DECLARATIONS / "_exemples"


def _fichiers(inclure_exemples: bool = False) -> list[pathlib.Path]:
    if not DECLARATIONS.exists():
        return []
    out = []
    for p in DECLARATIONS.rglob("*.yaml"):
        if p.name == "generiques.yaml":
            continue
        # COUCHES-TUYAU-1 §2 — fichier des couches HORS registre (source propre) : lu directement
        # par le tuyau (liste de couches), pas une Surface du format standard.
        if p.name == "tuyau_hors_registre.yaml":
            continue
        # EXPORTS-REBRANCHEMENT-1 lot 1 — les 11 sections de la fiche (ordre + titres), pas une
        # Surface : lues par sections_fiche(), source du miroir Dossier.
        if p.name == "sections.yaml":
            continue
        if not inclure_exemples and EXEMPLES in p.parents:
            continue
        out.append(p)
    return sorted(out)


def charger(inclure_exemples: bool = False) -> tuple[list[Surface], list[Generique]]:
    """Surfaces spécifiques (production) + génériques. `inclure_exemples` ajoute les échantillons
    de `_exemples/` (utilisé par les tests de format ; l'assembleur/Câblage lisent la production)."""
    surfaces: list[Surface] = []
    for p in _fichiers(inclure_exemples):
        # RACCORDEMENT-1 lot 2 — un fichier peut grouper plusieurs surfaces (docs YAML séparés par
        # `---`) pour les petites sections ; chaque document reste UNE surface (règle du format tenue).
        for d in (doc for doc in yaml.safe_load_all(p.read_text(encoding="utf-8")) if doc):
            lignes = tuple(sorted((
                Ligne(quoi=str(x.get("quoi", "")),
                      rang=int((x.get("ou") or {}).get("rang", 0)),
                      etat=str((x.get("ou") or {}).get("etat", "")),
                      section=(x.get("ou") or {}).get("section"),
                      comment=x.get("comment") or {},
                      absence=str(x.get("absence", "")),
                      absence_type=str(x.get("absence_type", "")),
                      statut_juridique=x.get("statut_juridique"),
                      carte=x.get("carte") or {},
                      pourquoi=str(x.get("pourquoi", "")),
                      fiche_section=(x.get("ou") or {}).get("fiche_section"))
                for x in (d.get("donnees") or [])
            ), key=lambda l: l.rang))   # le RANG fait foi de l'ordre (numéroté de 10 en 10)
            surfaces.append(Surface(
                surface=str(d.get("surface", p.stem)), nom=str(d.get("nom", "")),
                categorie=str(d.get("categorie", "")), parent=d.get("parent"),
                route=str(d.get("route", "")), rendu=str(d.get("rendu", "")),
                donnees=lignes, chemin=str(p.relative_to(_RACINE)),
                fiche_section=d.get("fiche_section")))
    gpath = DECLARATIONS / "generiques.yaml"
    generiques: list[Generique] = []
    if gpath.exists():
        g = yaml.safe_load(gpath.read_text(encoding="utf-8")) or {}
        for x in (g.get("generiques") or []):
            generiques.append(Generique(surface=str(x.get("surface", "")), nom=str(x.get("nom", "")),
                                        route=str(x.get("route", "")), regle=str(x.get("regle", ""))))
    return surfaces, generiques


def sections_fiche() -> list[dict]:
    """EXPORTS-REBRANCHEMENT-1 lot 1 — les 11 sections de la fiche parcelle (+ l'en-tête), dans
    l'ORDRE déclaré (declarations/fiche/sections.yaml). Chaque entrée : {id, titre, numerote}.
    C'est LA source de l'ordre et des noms — la fiche écran (SECTION_LABELS) et le Dossier PDF
    (miroir) la reflètent. Vide si le fichier manque (aucun défaut inventé)."""
    p = DECLARATIONS / "fiche" / "sections.yaml"
    if not p.exists():
        return []
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return [{"id": str(s.get("id", "")), "titre": str(s.get("titre", "")),
             "numerote": bool(s.get("numerote", True))}
            for s in (d.get("sections") or []) if s.get("id")]


def verifier(inclure_exemples: bool = True) -> tuple[list[str], list[str]]:
    """(violations_de_format, cables_orphelins). Les violations doivent être vides (le format est
    respecté) ; les orphelins sont un CONSTAT (une donnée affichée hors registre → à créer).
    Par défaut inclut les échantillons `_exemples/` (le format se vérifie dessus au lot 1)."""
    from .donnees import DONNEES
    surfaces, _ = charger(inclure_exemples)
    violations: list[str] = []
    orphelins: list[str] = []
    vus: set[str] = set()
    # EXPORTS-REBRANCHEMENT-1 lot 1 — les surfaces fiche se rattachent aux sections déclarées.
    _sections = {s["id"] for s in sections_fiche()}
    for s in surfaces:
        if s.categorie not in CATEGORIES:
            violations.append(f"{s.chemin} : catégorie inconnue « {s.categorie} »")
        if s.surface in vus:
            violations.append(f"{s.chemin} : surface en double « {s.surface} »")
        vus.add(s.surface)
        rangs = [l.rang for l in s.donnees]
        if not s.donnees:
            violations.append(f"{s.chemin} : surface spécifique sans aucune donnée")
        # lot 1 — une surface FICHE porte un `fiche_section` valide ; les surcharges par ligne aussi.
        if s.categorie == "fiche" and _sections:
            if s.fiche_section not in _sections:
                violations.append(f"{s.chemin} ({s.surface}) : fiche_section "
                                  f"« {s.fiche_section} » ∉ sections.yaml")
            for l in s.donnees:
                if l.fiche_section is not None and l.fiche_section not in _sections:
                    violations.append(f"{s.surface}/{l.quoi} : fiche_section "
                                      f"« {l.fiche_section} » ∉ sections.yaml")
        for l in s.donnees:
            ref = f"{s.surface}/{l.quoi or '?'}"
            if not l.quoi:
                violations.append(f"{ref} : `quoi` manquant")
            if l.etat not in ETATS:
                violations.append(f"{ref} : état inconnu « {l.etat} » (∉ {ETATS})")
            if not l.absence:
                violations.append(f"{ref} : phrase d'absence manquante")
            if l.absence_type not in ABSENCE_TYPES:
                violations.append(f"{ref} : absence_type « {l.absence_type} » inconnu (∉ {ABSENCE_TYPES})")
            if not l.pourquoi:
                violations.append(f"{ref} : `pourquoi` manquant")
            fmt = (l.comment or {}).get("format")
            if fmt is not None and fmt not in FORMATS:
                violations.append(f"{ref} : format inconnu « {fmt} »")
            if l.statut_juridique is not None and l.statut_juridique not in STATUTS_JURIDIQUES:
                violations.append(f"{ref} : statut_juridique « {l.statut_juridique} » inconnu (∉ {STATUTS_JURIDIQUES})")
            # lot 3 — une couche déclare sa FAMILLE (pour le panneau unique) ; famille inconnue = violation
            if s.categorie == "couche":
                fam = (l.carte or {}).get("famille")
                if fam is not None and fam not in FAMILLES:
                    violations.append(f"{ref} : famille « {fam} » inconnue (∉ {FAMILLES})")
            if l.quoi and l.quoi not in DONNEES:
                orphelins.append(f"{ref} : `quoi` absent du registre (câble orphelin — donnée à créer)")
        if len(set(rangs)) != len(rangs):
            violations.append(f"{s.chemin} : rangs en double {sorted(rangs)}")
    return violations, orphelins


def couches_carte() -> list[dict]:
    """RACCORDEMENT-1 lot 3 — LE PLAN DES COUCHES, dérivé des déclarations `couche` (jamais un
    switch dans MapView). Chaque entrée porte tout ce qu'il faut pour rendre la couche GÉNÉRIQUEMENT :
    kind (fetch), géométrie, zoom d'apparition, rang de dessin, style, légende, et `niveaux` pour un
    rendu multi (piscines : 3 rendus). Une couche nouvelle = un fichier de plus → elle apparaît ici."""
    surfaces, _ = charger()
    out = []
    for s in surfaces:
        if s.categorie != "couche":
            continue
        for l in s.donnees:
            c = l.carte or {}
            out.append({
                "surface": s.surface, "nom": s.nom, "donnee": l.quoi,
                "route": s.route,
                "kind": c.get("kind"),
                # étape 37 — filtre subtype pour les kinds VIRTUELS (un kind → plusieurs couches :
                # georisque_alea→inondation/mvt, sol_pollue→sis/casias) : {propriete, valeur|valeurs}.
                "filtre": c.get("filtre") or None,
                "famille": c.get("famille", "urbanisme"),
                "geometrie": c.get("geometrie", "polygone"),
                "zoom_min": c.get("zoom_min", 0),
                "rang_carte": c.get("rang_carte", 500),
                "statut_juridique": l.statut_juridique,
                "style": c.get("style") or {},
                "legende": c.get("legende") or l.comment.get("libelle") or s.nom,
                "niveaux": c.get("niveaux") or None,   # rendu multi (piscines)
                # recette lot 3 — hors panneau carte général (piscines → outil Prospection solaire)
                "panneau_general": c.get("panneau_general", True),
                # recette 2 — pas d'agrégat pastille pour lignes/bandes/couches sans commune (détail dès le zoom île)
                "agregat": c.get("agregat", True),
                # plafond de features (défaut endpoint 6000) — DÉCLARÉ pour les grosses couches île
                # (arrêts 9956, HTA 19480) sinon le générique les tronque en silence (no-silent-cap).
                "limite": c.get("limite"),
                # extrusion 3D : chargée sur la BBOX visible (jamais l'île) + rafraîchie au déplacement ;
                # `hauteur_propriete` porte la hauteur (m). Le bâti 3D LiDAR deviendra une couche majeure.
                "bbox": bool(c.get("bbox", False)),
                "hauteur_propriete": c.get("hauteur_propriete"),
                # popup au clic DÉCLARÉ (strip) : champs + ordre + libellés viennent d'ici, jamais d'un
                # switch par kind côté front. `popup_titre` = titre de la bulle (défaut = libellé couche).
                "popup": c.get("popup"),
                "popup_titre": c.get("popup_titre"),
                # centroïde : remonter les polygones minuscules en POINTS visibles à l'échelle île
                # (pendant PETIT-volume de l'agrégat) — SIS, cimetières, ouvrages, friches.
                "centroide": bool(c.get("centroide", False)),
                "libelle": l.comment.get("libelle") or s.nom,
                "i": l.comment.get("i"),
                # COUCHES-RECETTE-1 : `groupe` (couches fusionnées en un toggle, ex. transport_public) ;
                # `etiquette` (propriété + zoom_min pour un calque symbole d'étiquettes, ex. zonage parcelle).
                "groupe": c.get("groupe"),
                "etiquette": c.get("etiquette"),
                # COUCHES-RECETTE-1 (Lot B) : icône par sous-type (aménités OSM) — {subtype: emoji}.
                "icones": c.get("icones"),
                # COUCHES-RECETTE-2 (retour) : clic précis sur une couche affichée dissoute (SUP) —
                # interroge l'endpoint de détail (table d'origine) au point cliqué.
                "detail_kind": c.get("detail_kind"),
                "popup_detail": c.get("popup_detail"),
                # COUCHES-RECETTE-1 A12 : note de couverture affichée en légende (« pas de donnée
                # publiée pour : … ») — jamais un blanc silencieux.
                "note": c.get("note"),
            })
    return sorted(out, key=lambda e: e["rang_carte"])


def cablage() -> dict[str, Any]:
    """L'onglet Câblage (lot 6), dérivé des fichiers — jamais saisi.
    `par_donnee` : {donnee_id: [surfaces qui la consomment]} ; une donnée servable sans câble
    et non générique-only est ROUGE. `par_surface` : {surface: {prend, pourrait_prendre}}."""
    from .donnees import DONNEES
    surfaces, generiques = charger()
    par_donnee: dict[str, list[str]] = {}
    par_surface: dict[str, dict] = {}
    for s in surfaces:
        prend = [l.quoi for l in s.donnees if l.quoi in DONNEES]
        for q in prend:
            par_donnee.setdefault(q, []).append(s.surface)
        par_surface[s.surface] = {"categorie": s.categorie, "prend": prend}
    # les données de niveau parcelle qu'aucune surface spécifique ne prend (les génériques,
    # elles, consomment tout — donc pas rouges par elles seules)
    servables = {k for k, d in DONNEES.items() if not d.en_attente}
    sans_cable = sorted(servables - set(par_donnee))
    return {"par_donnee": par_donnee, "par_surface": par_surface,
            "generiques": [g.surface for g in generiques],
            "donnees_sans_cable_specifique": sans_cable}
