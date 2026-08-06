"""M41 — RADAR PROCÉDURES PLU : point de calcul UNIQUE (registre + conséquences parcellaires).

Lu par la fiche, les vigilances, l'outil « Vérif procédure » et (plus tard) le preset Veille AU
(M45). Personne ne recalcule : tout le monde lit ICI. Source : `config/veille_plu.yaml` (chair
curatée) + Sudocuh (squelette). Doctrine (arbitrages Vic M41) :

- `confiance` ∈ SOURCE | DEDUIT | ABSENT, OBLIGATOIRE. Le radar ne SERT EN VIGILANCE que SOURCE.
- Vigilance SURSIS : servie UNIQUEMENT si `debat_padd` est une date constatée (sourcée) —
  base légale L.153-11 CU (seuil = débat PADD), L.424-1 (max 2 ans), révision/élaboration seulement.
  Tant que débat PADD = ABSENT : AUCUNE vigilance sursis (pas de conditionnel flou).
- Vigilance VEILLE AU : sur les déclassées zone-fermée/AU des communes en procédure SOURCE —
  « ouverture possible à terme, à suivre ». N'annonce jamais l'issue, ne remonte AUCUN tier.
- Le radar dit le STADE et ses conséquences juridiques ACTUELLES, jamais l'issue.
"""
from __future__ import annotations

from .config import load_yaml_config

REQUIRED = ("commune", "procedure", "stade", "date_acte", "debat_padd", "source",
            "source_url", "date_constat", "confiance")
PROCEDURES = {"revision_plu", "elaboration_plu", "modification_plu", "cloturee", "aucune"}
CONFIANCES = {"SOURCE", "DEDUIT", "ABSENT"}
_ACTIVE_PROC = {"revision_plu", "elaboration_plu"}

#: base légale citée en dépliable (jamais approximée)
BASE_LEGALE_SURSIS = ("Code de l'urbanisme, art. L.153-11 (sursis possible dès le débat sur le PADD) "
                      "et L.424-1 (durée max 2 ans). Applicable aux procédures de révision/élaboration ; "
                      "une modification n'ouvre pas ce sursis. Décision motivée, contrôlée par le juge.")


def _registre() -> dict:
    return (load_yaml_config("veille_plu") or {}).get("communes", {}) or {}


def _meta() -> dict:
    return (load_yaml_config("veille_plu") or {}).get("meta", {}) or {}


def entry(insee: str | None) -> dict | None:
    """L'entrée de registre d'une commune (INSEE = 5 premiers car. de l'IDU), ou None."""
    return _registre().get((insee or "")[:5])


# ─────────────────────────────── LINT (schéma strict) ───────────────────────────────

def lint(registre: dict | None = None) -> list[str]:
    """Vérifie le registre : tous champs obligatoires, `confiance` valide, `raisonnement` si DEDUIT,
    dates ISO ou ABSENT. Retourne la liste des erreurs (vide = OK). Utilisé par le test + le geste
    trimestriel. Un registre qui ne passe pas le lint ne doit jamais être servi."""
    import datetime
    reg = _registre() if registre is None else registre
    errs: list[str] = []

    def _iso_or_absent(v) -> bool:
        if v == "ABSENT" or v is None:
            return True
        try:
            datetime.date.fromisoformat(str(v))
            return True
        except (ValueError, TypeError):
            return False

    for insee, e in (reg or {}).items():
        for k in REQUIRED:
            if k not in e or e[k] in (None, ""):
                errs.append(f"{insee}: champ obligatoire manquant/vide « {k} »")
        if e.get("procedure") not in PROCEDURES:
            errs.append(f"{insee}: procedure invalide « {e.get('procedure')} » (∈ {sorted(PROCEDURES)})")
        if e.get("confiance") not in CONFIANCES:
            errs.append(f"{insee}: confiance invalide « {e.get('confiance')} » (∈ {sorted(CONFIANCES)})")
        if e.get("confiance") == "DEDUIT" and not e.get("raisonnement"):
            errs.append(f"{insee}: confiance=DEDUIT exige un « raisonnement » écrit")
        for dk in ("date_acte", "debat_padd", "date_constat"):
            if dk in e and not _iso_or_absent(e[dk]):
                errs.append(f"{insee}: « {dk} » n'est ni une date ISO ni ABSENT ({e[dk]!r})")
        if e.get("date_constat") in ("ABSENT", None):
            errs.append(f"{insee}: date_constat obligatoire (l'absence est datée, elle aussi)")
    return errs


# ─────────────────────────── conséquences servables (SOURCE only) ───────────────────────────

def procedure_active(e: dict) -> bool:
    """Procédure lourde en cours, SERVABLE (confiance SOURCE, révision/élaboration, non dormante)."""
    return (e.get("confiance") == "SOURCE" and e.get("procedure") in _ACTIVE_PROC
            and e.get("stade") not in ("prescrite_dormante",))


def sursis_arme(e: dict) -> bool:
    """Le sursis L.153-11 est SERVABLE : SOURCE + débat PADD constaté (date réelle). Sinon jamais."""
    return (e.get("confiance") == "SOURCE" and procedure_active(e)
            and e.get("debat_padd") not in ("ABSENT", None, ""))


_TYPE_LABEL = {"revision_plu": "révision générale du PLU", "elaboration_plu": "élaboration du PLU",
               "modification_plu": "modification du PLU"}


def _src_suffixe(e: dict) -> str:
    return f"(Sourcé {e.get('source','?')}, constaté le {e.get('date_constat','?')})"


def fiche_en_cours(insee: str | None) -> str | None:
    """Ligne « EN COURS — non servi » enrichie pour le bloc M40, ou None. SOURCE only ; les entrées
    dormantes/clôturées/DEDUIT ne remontent PAS ici (elles ne sont pas servies)."""
    e = entry(insee)
    if not e or not procedure_active(e):
        return None
    lbl = _TYPE_LABEL.get(e["procedure"], e["procedure"])
    return f"{lbl}, prescrite le {e['date_acte']} {_src_suffixe(e)}"


def vigilance_sursis(insee: str | None) -> dict | None:
    """Vigilance SURSIS À STATUER — servie UNIQUEMENT si le débat PADD est constaté (sourcé).
    Retourne {texte, base_legale} ou None. Jamais de conditionnel flou : pas de PADD → None."""
    e = entry(insee)
    if not e or not sursis_arme(e):
        return None
    lbl = _TYPE_LABEL.get(e["procedure"], e["procedure"])
    return {"texte": (f"{lbl.capitalize()} en cours, débat PADD le {e['debat_padd']} — sursis à statuer "
                      f"possible : sécuriser le calendrier en mairie avant engagement. {_src_suffixe(e)}"),
            "base_legale": BASE_LEGALE_SURSIS}


def vigilance_veille_au(insee: str | None) -> str | None:
    """Vigilance VEILLE AU (opportunité/suivi) pour les déclassées zone-fermée/AU d'une commune en
    procédure SOURCE. Factuelle, ne remonte aucun tier, n'annonce jamais l'ouverture. None sinon."""
    e = entry(insee)
    if not e or not procedure_active(e):
        return None
    lbl = _TYPE_LABEL.get(e["procedure"], e["procedure"])
    return (f"Commune en procédure ({lbl} prescrite le {e['date_acte']}) — les zones AU fermées ne "
            f"s'ouvrent que par cette procédure : ouverture possible à terme, à suivre (aucune "
            f"certitude, ne préjuge pas de l'issue). {_src_suffixe(e)}")


SEUIL_DEFAUT_J = 90   # cadence de re-vérification par défaut (trimestrielle)
SEUIL_ACTIF_J = 30    # commune au radar ACTIF (procédure en cours constatée) : bouge vite → 30 j


def a_reverifier(registre: dict | None = None, today=None) -> list[dict]:
    """Entrées dont `date_constat` dépasse le seuil de fraîcheur (90 j ; 30 j si procédure active).
    Pur/testable (`today` injectable). Retourne la liste triée par âge décroissant, avec l'URL à
    visiter. C'est la matière du geste trimestriel de Vic."""
    import datetime
    reg = _registre() if registre is None else registre
    today = today or datetime.date.today()
    out = []
    for insee, e in (reg or {}).items():
        dc = e.get("date_constat")
        try:
            d = datetime.date.fromisoformat(str(dc))
        except (ValueError, TypeError):
            out.append({"insee": insee, "commune": e.get("commune"), "age_jours": None,
                        "seuil": 0, "source_url": e.get("source_url"), "actif": False,
                        "motif": "date_constat illisible"})
            continue
        actif = procedure_active(e)
        seuil = SEUIL_ACTIF_J if actif else SEUIL_DEFAUT_J
        age = (today - d).days
        if age > seuil:
            out.append({"insee": insee, "commune": e.get("commune"), "age_jours": age,
                        "seuil": seuil, "source_url": e.get("source_url"), "actif": actif,
                        "motif": f"{age} j > seuil {seuil} j" + (" (radar actif)" if actif else "")})
    return sorted(out, key=lambda x: (x["age_jours"] is not None, x["age_jours"] or 0), reverse=True)


def synthese_commune(insee: str | None) -> dict | None:
    """Synthèse radar pour la fiche COMMUNE : stade de la procédure + prochaine étape connue.
    Toujours honnête sur la confiance ; None si commune hors registre."""
    e = entry(insee)
    if not e:
        return None
    active = procedure_active(e)
    if e["procedure"] == "aucune":
        etat = f"Aucune procédure PLU lourde connue au {e['date_constat']} (dernier constat)."
    elif e["procedure"] == "cloturee":
        etat = f"Procédure Sudocuh sans suite connue — clôture probable (confiance {e['confiance']})."
    elif e.get("stade") == "prescrite_dormante":
        etat = f"Élaboration prescrite le {e['date_acte']} — dormante (aucun acte postérieur connu)."
    else:
        lbl = _TYPE_LABEL.get(e["procedure"], e["procedure"])
        etat = f"{lbl.capitalize()} en cours — stade « {e['stade']} », prescrite le {e['date_acte']}."
    padd = (f"Débat PADD constaté le {e['debat_padd']} — sursis à statuer possible."
            if sursis_arme(e) else
            "Débat PADD non constaté à ce jour — pas de sursis servi (donnée à curer).")
    return {"etat": etat, "prochaine_etape": padd if active else None,
            "confiance": e["confiance"], "source": e.get("source"),
            "date_constat": e.get("date_constat"), "servi_en_vigilance": active}
