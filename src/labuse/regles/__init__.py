"""CIRCUIT-4 — LE REGISTRE DES RÈGLES : chaque calcul adossé à sa référence.

Une FICHE DE RÈGLE par CALCUL (un module `regles/<donnee_id>.py`, nommé d'après sa donnée
représentative ; une fiche couvre TOUTES les données produites par ce calcul via `donnees`).
La fiche porte :
  · `formule_codee` — la formule EN FRANÇAIS + notation mathématique, écrite DEPUIS LE CODE
    (jamais depuis la doc) ; le champ `fonction` pointe le producteur (fichier:fonction) ;
  · `entrees` — les entrées brutes (tables/champs) ;
  · `classe` — regle_externe · methode_standard · choix_labuse · modele ;
  · `reference` — la référence externe (titre, article, url, version datée, EXTRAIT réellement lu)
    ou None (alors le verdict ne peut pas être « conforme » — règle 2 du mandat, verrouillée ici) ;
  · `verdict` — conforme · ecart · reference_introuvable · partiel (règles externes/méthodes)
    · choix_assume (choix LABUSE) · modele_valide (scoring : backtest+golden font foi) ;
  · `exemple_temoin` — le calcul refait À LA MAIN (hors moteur) sur une clé connue, épinglé
    dans tests/regles/ (le champ pointe le test) ;
  · `valide_par` — cc · vic · stephanie · en_attente ; `verifie_le` — date du dernier passage.

INVARIANTS (garde lot 1.3, tests/test_circuit4_lot1.py) :
  · toute donnée du registre avec calcul == "moteur" est couverte par EXACTEMENT une fiche ;
  · toute fonction publique de `registre/moteurs/` est référencée par ≥ 1 fiche
    (COUVERTURE_MOTEURS_PKG liste les deux côtés) ;
  · un verdict « conforme » sans extrait daté est REFUSÉ à la construction (jamais silencieux).
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field

CLASSES = ("regle_externe", "methode_standard", "choix_labuse", "modele")
VERDICTS = ("conforme", "ecart", "reference_introuvable", "partiel", "choix_assume", "modele_valide")
VALIDEURS = ("cc", "vic", "stephanie", "en_attente")


@dataclass(frozen=True)
class Reference:
    titre: str                     # « Code de l'urbanisme », « Arrêté du 31/03/2021 »…
    article: str                   # article / section précis (« art. R111-22 », « annexe I »)
    url: str                       # la page lue
    version: str                   # date de version / vigueur du texte lu (« en vigueur au JJ/MM/AAAA »)
    extrait: str                   # le PASSAGE réellement lu, cité tel quel (jamais paraphrasé)
    lu_le: str = ""                # date de la lecture (AAAA-MM-JJ)


@dataclass(frozen=True)
class FicheRegle:
    donnees: tuple[str, ...]       # ids du registre couverts par CE calcul (≥ 1)
    formule_codee: str             # français + notation mathématique, DEPUIS le code
    entrees: tuple[str, ...]       # tables/champs bruts lus
    classe: str                    # ∈ CLASSES
    fonction: str                  # producteur (fichier:fonction) — d'où la formule est lue
    verdict: str                   # ∈ VERDICTS
    reference: Reference | None = None
    choix: str | None = None       # choix_labuse : la définition + le pourquoi + depuis quand
    exemple_temoin: str | None = None   # tests/regles/test_<...>.py::<test> (implémentation indépendante)
    ecart: str | None = None       # verdict ecart/partiel : la différence, en français
    valide_par: str = "en_attente"
    verifie_le: str = ""           # AAAA-MM-JJ du dernier passage (agent règle / CC)
    moteur_fonctions: tuple[str, ...] = field(default_factory=tuple)
    # ^ fonctions de registre/moteurs/ couvertes par cette fiche (garde 1.3) — vide si le calcul
    #   vit ailleurs (faisabilite/, marche_service, …).

    def __post_init__(self):
        if self.classe not in CLASSES:
            raise ValueError(f"classe inconnue : {self.classe!r}")
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict inconnu : {self.verdict!r}")
        if self.valide_par not in VALIDEURS:
            raise ValueError(f"valide_par inconnu : {self.valide_par!r}")
        # Règle 2 du mandat — VERROU : « conforme » (et « partiel », qui affirme une lecture)
        # EXIGENT une référence avec un extrait daté réellement lu. Sans passage cité → le
        # constructeur refuse ; le verdict honnête est « reference_introuvable ».
        if self.verdict in ("conforme", "partiel"):
            r = self.reference
            if r is None or not (r.extrait or "").strip() or not (r.version or "").strip():
                raise ValueError(
                    f"fiche {self.donnees[0]} : verdict {self.verdict!r} sans extrait daté "
                    "(règle 2 du mandat — jamais « conforme » sans passage cité)")
        if self.verdict == "ecart" and not (self.ecart or "").strip():
            raise ValueError(f"fiche {self.donnees[0]} : verdict 'ecart' sans écart décrit")
        if self.classe == "choix_labuse" and not (self.choix or "").strip():
            raise ValueError(f"fiche {self.donnees[0]} : choix_labuse sans définition du choix")


#: rempli à l'import des modules de fiches — donnee_id → FicheRegle (une fiche par calcul,
#: plusieurs données peuvent pointer la même fiche).
FICHES: dict[str, FicheRegle] = {}
#: les fiches uniques, dans l'ordre de déclaration (pour les docs générées).
TOUTES: list[FicheRegle] = []


def declarer(fiche: FicheRegle) -> FicheRegle:
    """Appelé par chaque module de fiche. Refuse une donnée couverte deux fois (un calcul = une
    fiche — deux fiches sur la même donnée seraient deux vérités)."""
    for d in fiche.donnees:
        if d in FICHES:
            raise ValueError(f"donnée {d!r} couverte par deux fiches")
        FICHES[d] = fiche
    TOUTES.append(fiche)
    return fiche


_CHARGE = False


def charger() -> dict[str, FicheRegle]:
    """Importe tous les modules de fiches (une fois) et rend FICHES."""
    global _CHARGE
    if not _CHARGE:
        import labuse.regles as pkg
        for m in pkgutil.iter_modules(pkg.__path__):
            if not m.name.startswith("_"):
                importlib.import_module(f"labuse.regles.{m.name}")
        _CHARGE = True
    return FICHES


def couverture_moteurs_pkg() -> dict[str, list[str]]:
    """fonction publique de registre/moteurs/ → fiches qui la couvrent (garde 1.3 : aucune vide)."""
    charger()
    import inspect

    from labuse.registre import moteurs as pkg
    fonctions: list[str] = []
    for m in pkgutil.iter_modules(pkg.__path__):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"labuse.registre.moteurs.{m.name}")
        for nom, obj in vars(mod).items():
            if inspect.isfunction(obj) and not nom.startswith("_") and obj.__module__ == mod.__name__:
                fonctions.append(f"{m.name}.{nom}")
    couverture = {f: [] for f in fonctions}
    for fiche in TOUTES:
        for f in fiche.moteur_fonctions:
            couverture.setdefault(f, []).append(fiche.donnees[0])
    return couverture


def pour_api(cid: str) -> dict | None:
    """CIRCUIT-4 lot 5 — la règle d'une donnée, au format servi (page Circuit, tiroir de trace,
    miroir base). None si la donnée n'a pas de fiche (passe-plat/constante)."""
    charger()
    f = FICHES.get(cid)
    if f is None:
        return None
    r = f.reference
    return {
        "classe": f.classe, "verdict": f.verdict, "valide_par": f.valide_par,
        "verifie_le": f.verifie_le, "choix": f.choix, "ecart": f.ecart,
        "reference": ({"titre": r.titre, "article": r.article, "url": r.url,
                       "version": r.version, "extrait": r.extrait, "lu_le": r.lu_le}
                      if r else None),
    }


def robinets_par_verdict(robinets_chiffres: dict) -> dict:
    """CIRCUIT-4 lot 5.3 — {ecart: {ids robinets}, choix: {ids robinets}} : un robinet est en
    « écart à la règle » s'il SERT une donnée d'une fiche verdict == ecart ; « choix à
    confirmer » s'il sert une donnée choix_labuse encore valide_par == en_attente.
    `robinets_chiffres` = {id_robinet: [chiffres servis]}."""
    charger()
    ecart_donnees = {d for f in TOUTES if f.verdict == "ecart" for d in f.donnees}
    choix_donnees = {d for f in TOUTES
                     if f.classe == "choix_labuse" and f.valide_par == "en_attente"
                     for d in f.donnees}
    out = {"ecart": set(), "choix": set()}
    for rid, chiffres in robinets_chiffres.items():
        cs = set(chiffres or [])
        if cs & ecart_donnees:
            out["ecart"].add(rid)
        if cs & choix_donnees:
            out["choix"].add(rid)
    return out
