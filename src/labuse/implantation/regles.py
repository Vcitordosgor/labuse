"""Règles PLU de la zone, avec le VERROU de validation.

Une règle n'est utilisable pour un contrôle « Réussi » que si elle est `validee` (statut
« valide » au règlement) ET porte une citation. Toute règle absente ou `propose` reste non
validée → le contrôle correspondant sera « Non effectué », jamais « Réussi ».

Généralisé (IMPLANTATION-1BIS) pour servir plusieurs communes sans réglage par terrain :
barème stationnement scalaire (par_logement validé) ou par typologie (pièces OU surface de
plancher) ; mixité à seuil en m² OU en logements ; emprise / pleine terre optionnelles ;
hauteur à l'égout sinon au faîtage.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Regle:
    nom: str
    valeur: Optional[float]
    unite: str
    validee: bool
    article: Optional[str] = None
    page_pdf: Optional[int] = None
    citation: Optional[str] = None
    absent: bool = False   # ETUDE-STATIONNEMENT-FIX-1 (LOT 5) — silence PROUVÉ : le PLU ne réglemente pas (cité)

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        bout = []
        if self.article:
            bout.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            bout.append(f"p. {self.page_pdf}")
        tete = " · ".join(bout)
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


# ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — projet dessiné → destination lue dans le barème. Le moteur
# dessine du collectif ; le TYPE DE PROJET choisi (collectif/social/senior/étudiant) sélectionne la
# ligne du règlement. Le lotissement reste traité à part (division).
DESTINATION_PAR_PROJET: dict[str, str] = {
    "collectif": "collectif",
    "social": "social",
    "senior": "senior",
    "etudiante": "etudiant",
    "lotissement": "individuel",
}


@dataclass(frozen=True)
class LigneBareme:
    # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — une ligne porte SOIT un ratio par logement (`places`), SOIT une
    # formule « une place par tranche de N m² de surface de plancher » (`par_m2`). `role` distingue la règle
    # de base (par logement/typologie), une règle d'OPÉRATION (déclenchée au-delà de `logements_min`), et une
    # formule ALTERNATIVE dont on retient la PLUS EXIGEANTE (`retenue=max`). `arrondi` facultatif par ligne.
    places: Optional[float] = None
    par_m2: Optional[float] = None
    pieces_min: Optional[int] = None
    pieces_max: Optional[int] = None
    sdp_min: Optional[float] = None
    sdp_max: Optional[float] = None
    logements_min: Optional[int] = None
    destination: str = "collectif"
    role: str = "base"                  # 'base' | 'operation' | 'alt'
    arrondi: Optional[str] = None
    libelle: str = ""


@dataclass(frozen=True)
class Visiteurs:
    """Places visiteurs : `places` par tranche de `par_logements` logements OU de `par_m2_sdp` m² de SDP
    (tranche complète)."""
    places: float
    par_logements: Optional[int] = None
    par_m2_sdp: Optional[float] = None
    logements_min: Optional[int] = None    # part visiteur due seulement AU-DELÀ de N logements (ex. Saint-Benoît)
    publique: bool = False                 # places PUBLIQUES (hors parcelle) — comptées À PART, pas dans le total à dessiner
    arrondi: str = "superieur"
    article: Optional[str] = None
    page_pdf: Optional[int] = None
    citation: Optional[str] = None


@dataclass(frozen=True)
class ExigenceStationnement:
    """ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — résultat du barème pour le PROGRAMME dessiné : nb de places
    exigé (résident + visiteur), la formule RETENUE, les candidats écartés, et les conditions NON
    MODÉLISABLES (ex. « ≥ 0,5 place à l'extérieur ») à afficher « à vérifier » — jamais comptées comme
    satisfaites. `couvert` = tous les logements ont trouvé une ligne (sinon la règle ne couvre pas le
    programme → le contrôle reste « Non vérifié »)."""
    places: int
    places_residents: int
    places_visiteurs: int
    base: str
    formule: str
    formules_ecartees: tuple[str, ...]
    conditions: tuple[str, ...]
    couvert: bool
    details: dict
    places_publiques: int = 0   # places PUBLIQUES (hors parcelle) — exigées mais NON dessinées sur le terrain


@dataclass(frozen=True)
class BaremeStationnement:
    validee: bool
    mode: str                 # 'par_logement' | 'par_typologie' | 'par_m2_sdp' | 'absent'
    base: Optional[str]       # 'pieces' | 'surface_plancher' | None
    arrondi: str              # 'inferieur' | 'superieur'
    flat_places: Optional[float]
    lignes: tuple[LigneBareme, ...]
    article: Optional[str]
    page_pdf: Optional[int]
    citation: Optional[str]
    # ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — formes enrichies (toutes facultatives, rétro-compatibles).
    m2_par_place: Optional[float] = None          # mode 'par_m2_sdp' : 1 place / N m² de SDP (tranche complète)
    retenue: str = "max"                          # entre formules concurrentes : 'max' (la plus exigeante)
    visiteurs: Optional[Visiteurs] = None
    # ETUDE-STATIONNEMENT-FIX-2 (LOT 1, banc 212) — visiteur PROPRE au logement aidé (souvent 1/10, distinct
    # du visiteur ordinaire 1/5). Appliqué à la destination « social » à la place du visiteur général.
    visiteurs_social: Optional[Visiteurs] = None
    conditions: tuple[str, ...] = ()              # exigences non modélisables, à afficher « à vérifier »
    # ETUDE-STATIONNEMENT-FIX-1 (LOT 3, règle permanente #2) — colonne « places intégrées à la construction » :
    # au-delà d'un seuil de SDP, une part des places doit être BÂTIE (plein air exclu). Le moteur ne force pas
    # le sous-sol : il l'affiche en CONDITION bloquante à vérifier dès que l'opération dépasse le seuil.
    integ_pct: Optional[float] = None
    integ_seuil_m2: Optional[float] = None
    integ_citation: Optional[str] = None
    # ETUDE-STATIONNEMENT-FIX-2 (LOT 2) — plafond NATIONAL du Code de l'urbanisme (L151-35/36). C'est un
    # PLAFOND : il ne peut que FAIRE BAISSER l'exigence locale, jamais la relever, et il s'applique MÊME
    # quand le PLU sert une ligne dédiée. {ratio, article, citation}. ratio = places/logement au plus.
    plafond_national: Optional[dict] = None

    def places_pour(self, *, pieces: int, sdp_m2: float, destination: str = "collectif") -> Optional[float]:
        """Ratio par logement pour un logement (aperçu/jauge). Ne renvoie que la part RÉSIDENT par logement
        (les parts d'opération/visiteur se lisent au niveau du programme via `exiger`)."""
        if not self.validee:
            return None
        if self.mode == "par_logement":
            return self.flat_places
        if self.mode == "par_m2_sdp" and self.m2_par_place:
            return sdp_m2 / self.m2_par_place
        for l in self.lignes:
            if l.role != "base" or l.places is None:
                continue
            if l.destination != destination:
                continue
            if l.pieces_min is not None and pieces < l.pieces_min:
                continue
            if l.pieces_max is not None and pieces > l.pieces_max:
                continue
            if l.sdp_min is not None and sdp_m2 < l.sdp_min:
                continue
            if l.sdp_max is not None and sdp_m2 >= l.sdp_max:
                continue
            return l.places
        return None

    def arrondir(self, total: float, sens: Optional[str] = None) -> int:
        s = sens or self.arrondi
        return int(math.floor(total + 1e-9)) if s == "inferieur" else int(math.ceil(total - 1e-9))

    def has_destination(self, destination: str) -> bool:
        """Vrai si le barème sert une ligne DÉDIÉE à cette destination (social/senior/étudiant)."""
        return self.validee and any(l.destination == destination and l.role == "base" and
                                    (l.places is not None or l.par_m2 is not None) for l in self.lignes)

    def _parts_visiteurs(self, destination: str, n: int, sdp_tot: float) -> tuple[int, int]:
        """(visiteurs privés, places publiques) pour le programme. Les places PUBLIQUES (hors parcelle,
        `publique=True`) sont UNIVERSELLES : exigées pour toute destination, y compris le logement aidé
        (ex. Saint-Louis « opération > 10 logts : +0,5 place publique/logt »). Le visiteur PRIVÉ est propre
        à la destination : `visiteurs_social` pour l'aidé, `visiteurs` (s'il n'est pas public) sinon."""
        vis = pub = 0
        if self.visiteurs is not None:
            gv, gp = self._visiteurs_de(self.visiteurs, n, sdp_tot)
            pub += gp                                       # public : universel
            if destination != "social" and not self.visiteurs.publique:
                vis += gv                                   # visiteur privé ordinaire (logement non-aidé)
        if destination == "social" and self.visiteurs_social is not None:
            sv, sp = self._visiteurs_de(self.visiteurs_social, n, sdp_tot)
            vis += sv
            pub += sp
        return vis, pub

    @staticmethod
    def _visiteurs_de(vz: "Optional[Visiteurs]", n: int, sdp_tot: float) -> tuple[int, int]:
        """Compte (visiteurs privés, places publiques) pour une config de visiteurs. 0,0 si None/seuil non
        atteint. `par_logements` : 1 tranche par N logements ; `par_m2_sdp` : 1 tranche par N m²."""
        if vz is None or (vz.logements_min is not None and n < vz.logements_min):
            return 0, 0
        v = 0.0
        if vz.par_logements:
            v = math.ceil(n / vz.par_logements - 1e-9) * vz.places
        elif vz.par_m2_sdp:
            v = math.ceil(sdp_tot / vz.par_m2_sdp - 1e-9) * vz.places
        v = int(math.floor(v + 1e-9) if vz.arrondi == "inferieur" else math.ceil(v - 1e-9))
        return (0, v) if vz.publique else (v, 0)

    def _cap_plafond(self, residents: int, n: int, formule: str, ecartees: tuple) -> tuple[int, str, tuple]:
        """ETUDE-STATIONNEMENT-FIX-2 (LOT 2) — borne l'exigence RÉSIDENT par le plafond national (ne la
        relève jamais, s'applique même sur une ligne dédiée). Renvoie (residents, formule, écartées)."""
        if not (self.plafond_national and n > 0):
            return residents, formule, ecartees
        ratio = float(self.plafond_national.get("ratio", 0.0))
        cap = int(math.floor(n * ratio + 1e-9))
        if cap >= residents:
            return residents, formule, ecartees
        art = self.plafond_national.get("article", "L151-35")
        return cap, (f"plafond national {art} : au plus {ratio:g} place/logt × {n} → {cap} "
                     f"(borne l'exigence locale {residents})"), ecartees + (f"barème local = {residents}",)

    # ------------------------------------------------------------------ exigence au niveau du PROGRAMME
    def _ligne_base(self, pieces: int, sdp_m2: float, destination: str) -> Optional[LigneBareme]:
        for l in self.lignes:
            if l.role != "base" or l.places is None or l.destination != destination:
                continue
            if l.pieces_min is not None and pieces < l.pieces_min:
                continue
            if l.pieces_max is not None and pieces > l.pieces_max:
                continue
            if l.sdp_min is not None and sdp_m2 < l.sdp_min:
                continue
            if l.sdp_max is not None and sdp_m2 >= l.sdp_max:
                continue
            return l
        return None

    def exiger(self, modules, *, destination: str = "collectif",
               sdp_total: Optional[float] = None) -> Optional[ExigenceStationnement]:
        """Places exigées par le barème pour le PROGRAMME `modules` (chacun porte `.pieces` et
        `.surface_m2`). Applique la règle du type de projet (`destination`), retient la formule la PLUS
        EXIGEANTE entre lectures concurrentes, ajoute les visiteurs, et remonte les conditions non
        modélisables. None si le barème n'est pas validé.

        `sdp_total` (facultatif) = SURFACE DE PLANCHER réelle du programme (modules + noyaux) pour les
        formules « par tranche de m² » ; sans lui, on somme les surfaces des logements (approximation)."""
        if not self.validee:
            return None
        n = len(modules)
        sdp_tot = (float(sdp_total) if sdp_total is not None
                   else sum(float(getattr(m, "surface_m2", 0.0)) for m in modules))
        conditions = list(self.conditions)
        # Règle permanente #2 — colonne « places intégrées à la construction » : au-delà du seuil de SDP, une
        # part des places doit être BÂTIE (plein air exclu). Affichée en CONDITION (bloquante) à vérifier.
        if self.integ_pct and self.integ_seuil_m2 is not None and sdp_tot > self.integ_seuil_m2 + 1e-6:
            conditions.append(
                f"{self.integ_pct:g} % des places doivent être intégrées à la construction (opération > "
                f"{self.integ_seuil_m2:g} m² de surface de plancher) : stationnement en plein air exclu "
                f"au-delà du seuil — à vérifier" + (f" ({self.integ_citation})" if self.integ_citation else ""))
        conditions = tuple(conditions)
        if n == 0:
            return ExigenceStationnement(0, 0, 0, self.mode, "aucun logement", (), conditions, True, {})

        # Règle permanente #4 — destination SPÉCIALE (social/senior/étudiant) : une ligne dédiée, si elle
        # existe, GOUVERNE (remplace la règle générale). Sans ligne → la règle générale s'applique (collectif).
        if destination != "collectif":
            sp = next((l for l in self.lignes if l.role == "base" and l.destination == destination
                       and (l.places is not None or l.par_m2 is not None)), None)
            if sp is not None:
                # ligne dédiée : arrondi de la LIGNE, sinon celui du barème (qui reflète l'en-tête du tableau,
                # ex. Trois-Bassins « arrondi à l'entier inférieur ») — jamais « supérieur » par défaut.
                if sp.par_m2 is not None:
                    tot = self.arrondir(sdp_tot / sp.par_m2, sp.arrondi)
                    formule = f"{destination} : 1 place / {sp.par_m2:g} m² SDP · {sdp_tot:.0f} m²"
                else:
                    tot = self.arrondir(n * sp.places, sp.arrondi)
                    formule = f"{destination} : {sp.places:g} place/logt × {n} logts"
                tot, formule, ecartees = self._cap_plafond(int(tot), n, formule, ())
                svis, spub = self._parts_visiteurs(destination, n, sdp_tot)
                det = {"destination": destination}
                if svis: det["visiteurs"] = svis
                if spub: det["publiques"] = spub
                return ExigenceStationnement(int(tot) + svis, int(tot), svis, self.mode, formule, ecartees,
                                             conditions, True, det, places_publiques=spub)

        candidats: list[tuple[float, str]] = []      # (places résident, libellé de formule)
        couvert = True
        details: dict = {}

        if self.mode == "par_logement" and self.flat_places is not None:
            tot = n * self.flat_places
            candidats.append((self.arrondir(tot), f"{self.flat_places:g} place/logt × {n} logts"))
        elif self.mode == "par_m2_sdp" and self.m2_par_place:
            # Sens d'arrondi LU dans la règle. « tranche complète » (Saint-Pierre) = seules les tranches
            # ENTIÈRES comptent → arrondi INFÉRIEUR. Texte muet → supérieur (plus exigeant), fixé à l'ingestion.
            tot = self.arrondir(sdp_tot / self.m2_par_place)
            arr = "inférieur" if self.arrondi == "inferieur" else "supérieur"
            candidats.append((tot, f"1 place / {self.m2_par_place:g} m² · SDP {sdp_tot:.0f} m² (arrondi {arr})"))
        elif self.mode == "par_typologie":
            # (a) règle de BASE, logement par logement (par pièces ou surface). N'est une LECTURE valable que
            # si TOUS les logements trouvent une ligne de base pour la destination (sinon elle ne couvre pas
            # le programme). Une zone qui n'exprime le collectif QUE par des formules d'opération (ex. Les
            # Avirons : max(1,25/logt, 1/35 m²)) n'a pas de ligne de base : la couverture vient alors des alt.
            # FIX-2 — une maison seule (destination « individuel ») dans une zone SANS ligne individuelle
            # dédiée relève de la norme résidentielle GÉNÉRALE (les tranches « collectif » s'appliquent à tout
            # logement). On retombe alors sur « collectif » pour l'appariement des lignes de base.
            dest_match = destination
            if destination != "collectif" and not any(l.role == "base" and l.destination == destination
                                                       for l in self.lignes):
                dest_match = "collectif"
            lignes_base_dest = [l for l in self.lignes if l.role == "base" and l.destination == dest_match]
            base_tot = 0.0
            base_matched = 0
            par_ligne: dict[str, int] = {}
            for m in modules:
                l = self._ligne_base(int(getattr(m, "pieces", 0)), float(getattr(m, "surface_m2", 0.0)), dest_match)
                if l is None:
                    continue
                base_tot += l.places
                base_matched += 1
                par_ligne[l.libelle or f"{l.places:g}/logt"] = par_ligne.get(l.libelle or f"{l.places:g}/logt", 0) + 1
            if lignes_base_dest and base_matched == n and base_tot > 0:
                candidats.append((self.arrondir(base_tot), "barème par typologie : "
                                  + " + ".join(f"{v}×{k}" for k, v in par_ligne.items())))
                details["par_typologie"] = par_ligne
            elif lignes_base_dest and 0 < base_matched < n:
                # certains logements n'ont pas de ligne de base → la règle ne couvre pas TOUT le programme.
                couvert = False
            # (b) formules d'OPÉRATION et ALTERNATIVES (déclenchées selon logements_min), retenue = la plus exigeante
            for l in self.lignes:
                if l.role not in ("operation", "alt"):
                    continue
                if l.destination != dest_match:
                    continue
                if l.logements_min is not None and n < l.logements_min:
                    continue
                if l.par_m2 is not None:
                    # formule alternative « 1 place / N m² » : arrondi de la ligne sinon SUPÉRIEUR (plus exigeant).
                    v = self.arrondir(sdp_tot / l.par_m2, l.arrondi or "superieur")
                    arr = "inférieur" if (l.arrondi or "superieur") == "inferieur" else "supérieur"
                    candidats.append((v, f"1 place / {l.par_m2:g} m² SDP · {sdp_tot:.0f} m² (arrondi {arr})"))
                elif l.places is not None:
                    v = self.arrondir(n * l.places, l.arrondi)
                    seuil = f" (opération > {l.logements_min - 1} logts)" if l.logements_min else ""
                    candidats.append((v, f"{l.places:g} place/logt × {n} logts{seuil}, arrondi {l.arrondi or self.arrondi}"))

        if not candidats:
            # barème validé mais aucune ligne ne couvre le programme dessiné → on ne force pas « Réussi ».
            return ExigenceStationnement(0, 0, 0, self.mode, "règle ne couvrant pas le programme",
                                         (), conditions, False, details)

        # la PLUS EXIGEANTE des lectures concurrentes (mandat : « on applique la plus exigeante et on l'écrit »)
        if self.retenue == "max":
            residents, formule = max(candidats, key=lambda c: c[0])
        else:
            residents, formule = candidats[0]
        ecartees = tuple(f"{lib} = {int(v)}" for v, lib in candidats if (v, lib) != (residents, formule))

        # visiteurs / places publiques (parts additionnelles). Les places PUBLIQUES (hors parcelle) sont
        # exigées mais NON dessinées sur le terrain → comptées à part (reviewer : Saint-Louis).
        # visiteurs privés (par destination) + places publiques (universelles).
        vis, pub = self._parts_visiteurs(destination, n, sdp_tot)
        if vis:
            details["visiteurs"] = vis
        if pub:
            details["publiques"] = pub

        residents = int(residents)
        residents, formule, ecartees = self._cap_plafond(residents, n, formule, ecartees)
        return ExigenceStationnement(
            places=residents + vis, places_residents=residents, places_visiteurs=vis,
            base=self.mode, formule=formule, formules_ecartees=ecartees,
            conditions=conditions, couvert=couvert, details=details, places_publiques=pub)

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        tete = []
        if self.article:
            tete.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            tete.append(f"p. {self.page_pdf}")
        t = " · ".join(tete)
        return f"{t} — « {self.citation} »" if self.citation else (t or None)


@dataclass(frozen=True)
class Mixite:
    validee: bool
    seuil_m2: Optional[float]
    seuil_logements: Optional[int]
    quota_pct: Optional[float]
    article: Optional[str]
    page_pdf: Optional[int]
    citation: Optional[str]

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        t = []
        if self.article:
            t.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            t.append(f"p. {self.page_pdf}")
        tete = " · ".join(t)
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


@dataclass(frozen=True)
class DistanceConstructions:
    """PLU-CALIBRAGE-10 — implantation des constructions les unes par rapport aux autres sur une
    même propriété (ex-article 8). Quatre FORMES servables, et elles seules :
      · fixe          : distance absolue en m (`min_m`) ;
      · relative      : fraction de la hauteur (`fraction_hauteur`, base `cumulee`=H+h ou
                        `plus_haut`=H) avec un `min_m` plancher éventuel ;
      · conditionnelle: deux valeurs selon que les façades portent (`avec_ouvertures_m`) ou non
                        (`sans_ouvertures_m`) des ouvertures — le moteur applique la plus stricte ;
      · contiguite    : contiguïté autorisée (`contiguite_autorisee: true`) ou non.
    `silence` = le règlement ne réglemente pas (prouvé, cité). Toute autre forme = non servie
    (STOP — on ne devine pas). Servable (`validee`) seulement avec statut `valide` ET citation."""
    validee: bool
    forme: str                          # fixe|relative|conditionnelle|contiguite|silence|absente
    min_m: Optional[float] = None
    fraction_hauteur: Optional[float] = None
    base_hauteur: Optional[str] = None  # 'cumulee' (H+h) | 'plus_haut' (H du plus haut)
    avec_ouvertures_m: Optional[float] = None
    sans_ouvertures_m: Optional[float] = None
    contiguite_autorisee: Optional[bool] = None
    article: Optional[str] = None
    page_pdf: Optional[int] = None
    citation: Optional[str] = None

    @property
    def est_silence(self) -> bool:
        return self.validee and self.forme == "silence"

    @property
    def est_chiffrable(self) -> bool:
        """Règle servie que le moteur sait transformer en distance requise (fixe/relative/
        conditionnelle/contiguité) — par opposition au silence et au non-servi."""
        return self.validee and self.forme in ("fixe", "relative", "conditionnelle", "contiguite")

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        t = []
        if self.article:
            t.append(f"PLU art. {self.article}")
        if self.page_pdf is not None:
            t.append(f"p. {self.page_pdf}")
        tete = " · ".join(t)
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


@dataclass(frozen=True)
class EspacesVerts:
    """ETUDE-V6-2 (Lot 3, correction §2) — quota d'espaces verts (part de la parcelle à végétaliser),
    éventuellement « hors stationnement »."""
    validee: bool
    pct: Optional[float] = None
    hors_stationnement: bool = True
    article: Optional[str] = None
    page_pdf: Optional[int] = None
    citation: Optional[str] = None

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        t = [x for x in (f"PLU art. {self.article}" if self.article else None,
                         f"p. {self.page_pdf}" if self.page_pdf is not None else None) if x]
        tete = " · ".join(t)
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


@dataclass(frozen=True)
class MargePlantee:
    """ETUDE-V6-2 (Lot 3, correction §2) — bande plantée en périphérie : largeur mini sur une fraction du
    linéaire des limites, hors limites mitoyennes."""
    validee: bool
    largeur_m: Optional[float] = None
    pct_lineaire: Optional[float] = None
    hors_mitoyennete: bool = True
    article: Optional[str] = None
    page_pdf: Optional[int] = None
    citation: Optional[str] = None

    @property
    def citation_complete(self) -> Optional[str]:
        if not self.validee:
            return None
        t = [x for x in (f"PLU art. {self.article}" if self.article else None,
                         f"p. {self.page_pdf}" if self.page_pdf is not None else None) if x]
        tete = " · ".join(t)
        return f"{tete} — « {self.citation} »" if self.citation else (tete or None)


@dataclass(frozen=True)
class ReglesZone:
    insee: str
    zone: str
    hauteur_egout: Regle
    hauteur_faitage: Regle
    emprise_ces: Regle
    recul_voie: Regle
    recul_separatives: Regle
    pleine_terre: Regle
    mixite: Mixite
    stationnement: BaremeStationnement
    distance_constructions: DistanceConstructions
    prospect: Optional[Regle] = None   # règle de hauteur RELATIVE non chiffrable (ex. L ≥ h/2)
    espaces_verts: "EspacesVerts" = field(default_factory=lambda: EspacesVerts(validee=False))
    marge_plantee: "MargePlantee" = field(default_factory=lambda: MargePlantee(validee=False))
    # ETUDE-STATIONNEMENT-FIX-1 — règle de hauteur PRÈS DES LIMITES (ex. Le Tampon Ua10.3, bande de 3,60 m)
    # que le moteur ne sait pas chiffrer : existe → contrôle « Non vérifié », jamais absente.
    hauteur_bande_limite: Optional[dict] = None

    @property
    def hauteur_plafond(self) -> Regle:
        """La hauteur qui borne les niveaux : l'égout si validé, sinon le faîtage."""
        if self.hauteur_egout.validee:
            return self.hauteur_egout
        return self.hauteur_faitage

    @property
    def hauteur_non_chiffrable(self) -> bool:
        """Vrai s'il existe une règle de hauteur que le moteur ne sait pas chiffrer (prospect L>H).
        Règle générale : une telle règle ne laisse jamais l'étude exploitable."""
        return self.prospect is not None


def _leaf_val(leaf: Optional[dict], key: str, nom: str, unite: str) -> Regle:
    if not isinstance(leaf, dict):
        return Regle(nom=nom, valeur=None, unite=unite, validee=False)
    valide = leaf.get("statut") == "valide" and not leaf.get("absent")
    # silence PROUVÉ : statut valide + absent:true + citation → la règle est « Non réglementée » (pas « Non effectué »)
    absent = bool(leaf.get("statut") == "valide" and leaf.get("absent") and str(leaf.get("citation") or "").strip())
    v = leaf.get(key)
    return Regle(
        nom=nom, absent=absent,
        valeur=float(v) if (valide and isinstance(v, (int, float))) else None,
        unite=unite,
        validee=bool(valide and isinstance(v, (int, float))),
        article=leaf.get("article"), page_pdf=leaf.get("page_pdf"), citation=leaf.get("citation"),
    )


def _norm_arrondi(v, defaut: str = "superieur") -> str:
    s = str(v or "").strip().lower()
    return s if s in ("inferieur", "superieur") else defaut


def _parse_visiteurs(form: dict, key: str = "visiteurs") -> Optional[Visiteurs]:
    """ETUDE-STATIONNEMENT-FIX-1 (LOT 1) — feuille `visiteurs` : places par tranche de logements OU de m².
    `key` permet de lire aussi `visiteurs_social` (visiteur propre au logement aidé, FIX-2)."""
    v = form.get(key)
    if not isinstance(v, dict) or not isinstance(v.get("places"), (int, float)):
        return None
    return Visiteurs(
        places=float(v["places"]),
        par_logements=v.get("par_logements"), par_m2_sdp=v.get("par_m2_sdp"),
        logements_min=v.get("logements_min"), publique=bool(v.get("publique")),
        arrondi=_norm_arrondi(v.get("arrondi")),
        article=v.get("article"), page_pdf=v.get("page_pdf"), citation=v.get("citation"))


def _parse_conditions(form: dict) -> tuple[str, ...]:
    c = form.get("conditions")
    if isinstance(c, str):
        return (c,)
    if isinstance(c, (list, tuple)):
        return tuple(str(x) for x in c if str(x).strip())
    return ()


_DEST_SPECIALES = {"social": "logement social", "senior": "résidence senior / personnes âgées",
                   "etudiant": "résidence étudiante / universitaire"}


def _lignes_destinations(form: dict) -> list[LigneBareme]:
    """Lignes des destinations spéciales (`social`/`senior`/`etudiant: {places: X}` OU `{par_m2: Y}`),
    lues quand le projet est de ce type (règle permanente #4). Sans ligne → destination « Non vérifié »."""
    out = []
    for cle, lib in _DEST_SPECIALES.items():
        s = form.get(cle)
        if not isinstance(s, dict):
            continue
        if isinstance(s.get("places"), (int, float)):
            out.append(LigneBareme(places=float(s["places"]), destination=cle, role="base",
                                   arrondi=_norm_arrondi(s.get("arrondi"), None) if s.get("arrondi") else None,
                                   libelle=s.get("tranche") or lib))
        elif isinstance(s.get("par_m2"), (int, float)):
            out.append(LigneBareme(par_m2=float(s["par_m2"]), destination=cle, role="base",
                                   arrondi=_norm_arrondi(s.get("arrondi"), None) if s.get("arrondi") else None,
                                   libelle=s.get("tranche") or lib))
    return out


def _integ(form: dict) -> tuple:
    """Colonne « places intégrées à la construction » (règle permanente #2)."""
    pi = form.get("places_integrees")
    if not isinstance(pi, dict) or not isinstance(pi.get("pct"), (int, float)):
        return (None, None, None)
    return (float(pi["pct"]), float(pi["seuil_m2"]) if isinstance(pi.get("seuil_m2"), (int, float)) else 0.0,
            pi.get("citation"))


def _bareme(stat: dict) -> BaremeStationnement:
    pl = stat.get("par_logement") or {}
    pt = stat.get("par_typologie") or {}
    pm = stat.get("par_m2_sdp") or {}
    # 1) par_logement scalaire validé — arrondi désormais LU dans la règle (défaut supérieur)
    if pl.get("statut") == "valide" and isinstance(pl.get("places"), (int, float)):
        ip, isz, ic = _integ(pl)
        return BaremeStationnement(
            validee=True, mode="par_logement", base=None, arrondi=_norm_arrondi(pl.get("arrondi")),
            flat_places=float(pl["places"]), lignes=tuple(_lignes_destinations(pl)),
            article=pl.get("article"), page_pdf=pl.get("page_pdf"), citation=pl.get("citation"),
            visiteurs=_parse_visiteurs(pl), visiteurs_social=_parse_visiteurs(pl, 'visiteurs_social'),
            conditions=_parse_conditions(pl),
            integ_pct=ip, integ_seuil_m2=isz, integ_citation=ic)
    # 2) par_m2_sdp validé — « une place par tranche de N m² de SDP » (ENFIN supporté : tranche complète)
    if pm.get("statut") == "valide" and isinstance(pm.get("m2_par_place"), (int, float)):
        ip, isz, ic = _integ(pm)
        return BaremeStationnement(
            validee=True, mode="par_m2_sdp", base="surface_plancher", arrondi=_norm_arrondi(pm.get("arrondi")),
            flat_places=None, lignes=tuple(_lignes_destinations(pm)), m2_par_place=float(pm["m2_par_place"]),
            article=pm.get("article"), page_pdf=pm.get("page_pdf"), citation=pm.get("citation"),
            visiteurs=_parse_visiteurs(pm), visiteurs_social=_parse_visiteurs(pm, 'visiteurs_social'),
            conditions=_parse_conditions(pm),
            integ_pct=ip, integ_seuil_m2=isz, integ_citation=ic)
    # 3) par_typologie validé (pièces OU surface OU formules d'opération/alternatives)
    if pt.get("statut") == "valide" and pt.get("detail"):
        lignes = []
        for d in pt["detail"]:
            if not isinstance(d, dict):
                continue
            if d.get("places") is None and d.get("par_m2") is None:
                continue
            lignes.append(LigneBareme(
                places=float(d["places"]) if d.get("places") is not None else None,
                par_m2=float(d["par_m2"]) if d.get("par_m2") is not None else None,
                pieces_min=d.get("pieces_min"), pieces_max=d.get("pieces_max"),
                sdp_min=d.get("sdp_min"), sdp_max=d.get("sdp_max"),
                logements_min=d.get("logements_min"),
                destination=d.get("destination") or "collectif",
                role=d.get("role") or "base", arrondi=_norm_arrondi(d.get("arrondi"), None) if d.get("arrondi") else None,
                libelle=d.get("tranche") or d.get("typologie") or ""))
        lignes.extend(_lignes_destinations(pt))
        if lignes:
            ip, isz, ic = _integ(pt)
            return BaremeStationnement(
                validee=True, mode="par_typologie", base=pt.get("base") or "pieces",
                arrondi=_norm_arrondi(pt.get("arrondi")), flat_places=None, lignes=tuple(lignes),
                article=pt.get("article"), page_pdf=pt.get("page_pdf"), citation=pt.get("citation"),
                retenue=(pt.get("retenue") or "max"),
                visiteurs=_parse_visiteurs(pt), visiteurs_social=_parse_visiteurs(pt, 'visiteurs_social'),
                conditions=_parse_conditions(pt),
                integ_pct=ip, integ_seuil_m2=isz, integ_citation=ic)
    return BaremeStationnement(False, "absent", None, "superieur", None, (), None, None, None)


def _distance_constructions(retraits: dict) -> DistanceConstructions:
    """Charge la feuille `retraits.entre_constructions` (PLU-CALIBRAGE-10). Servable seulement si
    statut `valide`, citation présente, et `forme` reconnue. `absent: true` → silence prouvé."""
    leaf = (retraits or {}).get("entre_constructions")
    if not isinstance(leaf, dict):
        return DistanceConstructions(validee=False, forme="absente")
    valide = (leaf.get("statut") == "valide" and str(leaf.get("citation") or "").strip() != "")
    forme = "silence" if leaf.get("absent") else (leaf.get("forme") or "")
    formes_ok = ("fixe", "relative", "conditionnelle", "contiguite", "silence")
    frac = leaf.get("fraction_hauteur")
    return DistanceConstructions(
        validee=bool(valide and forme in formes_ok),
        forme=forme if forme in formes_ok else "absente",
        min_m=float(leaf["min_m"]) if isinstance(leaf.get("min_m"), (int, float)) else None,
        fraction_hauteur=float(frac) if isinstance(frac, (int, float)) else None,
        base_hauteur=leaf.get("base_hauteur"),
        avec_ouvertures_m=float(leaf["avec_ouvertures_m"]) if isinstance(leaf.get("avec_ouvertures_m"), (int, float)) else None,
        sans_ouvertures_m=float(leaf["sans_ouvertures_m"]) if isinstance(leaf.get("sans_ouvertures_m"), (int, float)) else None,
        contiguite_autorisee=leaf.get("contiguite_autorisee"),
        article=leaf.get("article"), page_pdf=leaf.get("page_pdf"), citation=leaf.get("citation"))


def _detect_prospect(reg: dict) -> Optional[Regle]:
    """Prospect / hauteur relative (ex. « L ≥ h/2 ») : règle liant distance et HAUTEUR, que le
    moteur ne sait pas chiffrer. Détectée dans les formules/citations de reculs ou de hauteur.
    PLU-CALIBRAGE-10 : la feuille `entre_constructions` est EXCLUE — sa forme relative (L ≥ h/2
    entre deux bâtiments de la même propriété) est désormais chiffrée par le contrôle dédié."""
    marqueurs = ("h/2", "h / 2", "différence d'altitude", "l ≥ h", "l > h", "l>h", "≥ h/")
    for grp in ("retraits", "hauteur"):
        for cle, leaf in (reg.get(grp) or {}).items():
            if cle == "entre_constructions" or not isinstance(leaf, dict):
                continue
            txt = " ".join(str(leaf.get(f) or "") for f in ("formule", "citation")).lower()
            if any(m in txt for m in marqueurs):
                return Regle(nom="prospect (hauteur relative)", valeur=None, unite="", validee=False,
                             article=leaf.get("article"), page_pdf=leaf.get("page_pdf"),
                             citation=leaf.get("citation") or leaf.get("formule"))
    return None


def charger(insee: str, zone: str) -> ReglesZone:
    from labuse.plu.destinations import regles_zone

    reg = regles_zone(insee, zone) or {}
    hauteur = reg.get("hauteur") or {}
    emprise = reg.get("emprise_sol") or {}
    retraits = reg.get("retraits") or {}
    pleine = reg.get("pleine_terre") or {}
    mix = reg.get("mixite") or {}
    # ETUDE-V6-2 (Lot 3, correction §2) — espaces verts + marge plantée (servables si statut valide).
    ev = ((reg.get("espaces_verts") or {}).get("pct")) or {}
    ev_valide = ev.get("statut") == "valide" and isinstance(ev.get("pct"), (int, float))
    espaces_verts = EspacesVerts(
        validee=bool(ev_valide), pct=float(ev["pct"]) if ev_valide else None,
        hors_stationnement=bool(ev.get("hors_stationnement", True)),
        article=ev.get("article"), page_pdf=ev.get("page_pdf"), citation=ev.get("citation"))
    mp = ((reg.get("marge_plantee") or {}).get("bande")) or {}
    mp_valide = mp.get("statut") == "valide" and isinstance(mp.get("largeur_m"), (int, float))
    marge_plantee = MargePlantee(
        validee=bool(mp_valide), largeur_m=float(mp["largeur_m"]) if mp_valide else None,
        pct_lineaire=float(mp["pct_lineaire"]) if (mp_valide and mp.get("pct_lineaire") is not None) else None,
        hors_mitoyennete=bool(mp.get("hors_mitoyennete", True)),
        article=mp.get("article"), page_pdf=mp.get("page_pdf"), citation=mp.get("citation"))

    mix_valide = mix.get("statut") == "valide"
    mixite = Mixite(
        validee=bool(mix_valide and mix.get("quota_pct") is not None),
        seuil_m2=mix.get("seuil_m2") if mix_valide else None,
        seuil_logements=mix.get("seuil_logements") if mix_valide else None,
        quota_pct=float(mix["quota_pct"]) if (mix_valide and mix.get("quota_pct") is not None) else None,
        article=mix.get("article"), page_pdf=mix.get("page_pdf"), citation=mix.get("citation"))

    # règle de hauteur près des limites (bande_limite) portée en exception d'une feuille de hauteur.
    hauteur_bande = None
    for _leaf in (hauteur.get("faitage"), hauteur.get("egout"), hauteur.get("niveaux")):
        for _e in ((_leaf or {}).get("exceptions") or []):
            if isinstance(_e, dict) and _e.get("porte") == "bande_limite":
                hauteur_bande = {"article": _e.get("article"), "page_pdf": _e.get("page_pdf"),
                                 "citation": _e.get("texte") or _e.get("citation")}
                break
        if hauteur_bande:
            break

    return ReglesZone(
        insee=insee, zone=zone,
        hauteur_bande_limite=hauteur_bande,
        hauteur_egout=_leaf_val(hauteur.get("egout"), "m", "hauteur à l'égout", "m"),
        hauteur_faitage=_leaf_val(hauteur.get("faitage"), "m", "hauteur au faîtage", "m"),
        emprise_ces=_leaf_val(emprise.get("ces"), "pct", "emprise au sol (CES)", "%"),
        recul_voie=_leaf_val(retraits.get("voie"), "min_m", "recul sur voie", "m"),
        recul_separatives=_leaf_val(retraits.get("limites_separatives"), "min_m",
                                    "recul sur limites séparatives", "m"),
        pleine_terre=_leaf_val(pleine.get("pct"), "pct", "pleine terre (perméabilité)", "%"),
        mixite=mixite,
        stationnement=_bareme(reg.get("stationnement") or {}),
        distance_constructions=_distance_constructions(retraits),
        prospect=_detect_prospect(reg),
        espaces_verts=espaces_verts,
        marge_plantee=marge_plantee,
    )
