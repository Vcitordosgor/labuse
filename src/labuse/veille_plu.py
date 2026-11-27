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

from datetime import date

from .config import load_yaml_config
from .tz import today_reunion   # FIX-ORFEVRE-1 pt 3 (ORF-17) — jour Réunion, jamais le fuseau du process

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
    reg = _registre() if registre is None else registre
    errs: list[str] = []

    def _iso_or_absent(v) -> bool:
        if v == "ABSENT" or v is None:
            return True
        try:
            date.fromisoformat(str(v))
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
        for dk in ("date_acte", "debat_padd", "debat_padd_tenu", "date_arret", "date_constat",
                   "date_enquete_fin", "avis_commission_date", "debat_recherche_le"):
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


def debat_padd_tenu(e: dict) -> str | None:
    """OUTIL-COMMUNES-FIX-12 LOT 2 — DATE du débat sur le PADD TENU EN CONSEIL (fait sourcé), ou None.
    DISTINCT de `debat_padd` qui, lui, ARME le sursis à statuer : on peut consigner qu'un débat a eu
    lieu (fait daté) SANS conclure qu'un sursis s'applique à une parcelle (décision discrétionnaire du
    maire, L.153-11 — jamais servie par LABUSE tant que `debat_padd` reste ABSENT). Sépare « débat
    tenu le » de « sursis applicable »."""
    v = e.get("debat_padd_tenu")
    return v if v not in ("ABSENT", None, "") else None


def _cap(t: str) -> str:
    return (t[:1].upper() + t[1:]) if t else t


def _fr(iso: str | None) -> str | None:
    """Une date ISO (AAAA-MM-JJ) en JJ/MM/AAAA pour l'affichage client ; renvoie l'entrée telle quelle
    si elle n'est pas une date ISO (robustesse : jamais de crash sur une valeur curée inattendue)."""
    if not iso or iso in ("ABSENT",):
        return iso
    try:
        return date.fromisoformat(str(iso)).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso


def sursis_autorise(e: dict) -> dict | None:
    """OUTIL-COMMUNES-FIX-14 LOT 5 — le conseil municipal a-t-il EXPRESSÉMENT autorisé le maire à
    surseoir à statuer (délibération citée, art. visé) ? Fait DISTINCT de `debat_padd` (qui armerait
    une vigilance sursis à l'échelle de la commune) : une autorisation générale donnée au maire ne vaut
    pas décision individuelle de sursis sur une parcelle. Les deux s'affichent ENSEMBLE (« le conseil a
    autorisé… » + « aucune décision de sursis connue pour cette parcelle »). None si le registre n'en
    porte pas. `date` est servie formatée (JJ/MM/AAAA) pour l'écran et le PDF."""
    sa = e.get("sursis_autorise")
    if not isinstance(sa, dict) or not sa.get("date"):
        return None
    return {"date": sa.get("date"), "date_fr": _fr(sa.get("date")),
            "article": sa.get("article"), "base_legale": sa.get("base_legale"),
            "source_url": sa.get("source_url")}


def debat_recherche_le(e: dict) -> str | None:
    """OUTIL-COMMUNES-FIX-14 LOT 6 — DATE à laquelle le débat PADD a été CHERCHÉ sans être retrouvé
    (distincte du `date_constat` général). Permet de DATER la recherche infructueuse sur les trois
    écrans (« non retrouvée lors de la recherche du JJ/MM/AAAA ») au lieu d'un « non constaté » nu."""
    v = e.get("debat_recherche_le")
    return v if v not in ("ABSENT", None, "") else None


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
    return {"texte": (f"{_cap(lbl)} en cours, débat PADD le {e['debat_padd']} — sursis à statuer "
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
    reg = _registre() if registre is None else registre
    today = today or today_reunion()
    out = []
    for insee, e in (reg or {}).items():
        dc = e.get("date_constat")
        try:
            d = date.fromisoformat(str(dc))
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


#: tiers où un permis pourrait être demandé → concernés par le sursis (si armé). Anciens codes
#: + codes politique v2 (PALIERS-1) : un run ne porte qu'un vocabulaire, l'autre ne matche rien.
_TIERS_SURSIS = ("brulante", "chaude", "reserve_fonciere", "a_creuser",
                 "priorite", "a_suivre", "sans_signal")
#: déclassées « zone fermée / AU » → concernées par la veille AU (ouverture à terme)
_TIERS_VEILLE_AU = ("declasse_zone_fermee", "declasse_au_fermee", "declasse_au_statut_inconnu")


def radar_parcelle(insee: str | None, tier: str | None) -> dict | None:
    """Bloc RADAR d'une parcelle : synthèse commune + conséquences parcellaires SERVABLES selon le
    tier. `sursis` seulement si armé (PADD sourcé) ET tier « permis possible ». `veille_au` seulement
    sur les déclassées zone-fermée/AU d'une commune en procédure SOURCE. None si rien à montrer."""
    e = entry(insee)
    if not e:
        return None
    sursis = vigilance_sursis(insee) if tier in _TIERS_SURSIS else None
    veille = vigilance_veille_au(insee) if tier in _TIERS_VEILLE_AU else None
    synth = synthese_commune(insee)
    # ne rien servir si la commune n'a aucune procédure active ET aucune conséquence parcellaire
    if not sursis and not veille and not (synth and synth.get("servi_en_vigilance")):
        return None
    return {"synthese": synth, "sursis": sursis, "veille_au": veille,
            "commune": e.get("commune"), "confiance": e.get("confiance")}


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
        # FIX-4 LOT 2 — une clôture par ACTE D'APPROBATION (stade='approuvée', ex. Sainte-Marie /
        # Sainte-Suzanne) est dite comme telle et datée ; une clôture simplement déduite d'une absence
        # de suite Sudocuh reste prudente (« clôture probable »).
        if e.get("stade") == "approuvée":
            etat = f"PLU révisé APPROUVÉ le {e['date_acte']} (délibération d'approbation) — opposable."
        else:
            etat = f"Procédure Sudocuh sans suite connue — clôture probable (confiance {e['confiance']})."
    elif e.get("stade") == "prescrite_dormante":
        etat = f"Élaboration prescrite le {e['date_acte']} — dormante (aucun acte postérieur connu)."
    else:
        # FIX-13 LOT 1/2 — le STADE réel est dit (la révision ne reste pas éternellement « prescrite »).
        # « arrêté » / « enquête publique » portent la date de l'ARRÊT du projet (date_arret), la
        # prescription restant rappelée comme origine. Les autres stades gardent le libellé générique.
        lbl = _TYPE_LABEL.get(e["procedure"], e["procedure"])
        _arr = e.get("date_arret")
        _stade = e.get("stade")
        if _stade in ("arrêté", "arrete") and _arr:
            etat = f"{_cap(lbl)} — projet ARRÊTÉ le {_fr(_arr)} (prescrite le {_fr(e['date_acte'])})."
        elif _stade in ("avis commission", "avis_commission") and e.get("date_enquete_fin"):
            # FIX-14 LOT 5 — l'enquête publique est CLOSE : on dit le stade RÉEL (enquête terminée + avis
            # de la commission d'enquête), factuel, sans préjuger de la décision municipale. Plus de
            # bandeau « ENQUÊTE PUBLIQUE » (stade dépassé).
            _sens = e.get("avis_commission")
            _dac = e.get("avis_commission_date")
            _avis = (f" — avis {_sens} de la commission d'enquête ({_fr(_dac)})"
                     if _sens and _dac else " — avis de la commission d'enquête")
            etat = f"{_cap(lbl)} — enquête terminée le {_fr(e['date_enquete_fin'])}{_avis}."
        elif _stade in ("enquête publique", "enquete publique", "enquete_publique") and _arr:
            etat = (f"{_cap(lbl)} — enquête publique (projet arrêté le {_fr(_arr)}, prescrite le "
                    f"{_fr(e['date_acte'])}).")
        else:
            etat = f"{_cap(lbl)} en cours — stade « {_stade} », prescrite le {_fr(e['date_acte'])}."
    # FIX-12 LOT 2 — 3 cas, « débat tenu » séparé de « sursis applicable » :
    _tenu = debat_padd_tenu(e)
    _autor = sursis_autorise(e)        # FIX-14 LOT 5 — autorisation expresse de surseoir (conseil)
    _cherche = debat_recherche_le(e)   # FIX-14 LOT 6 — date de la recherche infructueuse du débat
    if sursis_arme(e):
        padd = f"Débat PADD constaté le {_fr(e['debat_padd'])} — sursis à statuer possible."
    elif _tenu and _autor:
        # FIX-14 LOT 5 — débat tenu ET autorisation de surseoir donnée au maire : on sert les DEUX faits
        # ensemble, sans conclure à un sursis sur la parcelle (aucune décision individuelle connue).
        padd = (f"Débat PADD tenu le {_fr(_tenu)}. Le conseil a autorisé le maire à surseoir à statuer "
                f"(délibération du {_autor['date_fr']}, {_autor['article']}) — aucune décision de sursis "
                "connue pour cette parcelle.")
    elif _tenu:
        padd = (f"Débat PADD tenu le {_fr(_tenu)} — sursis à statuer non armé (décision discrétionnaire "
                "du maire, L.153-11, non constatée par LABUSE).")
    elif _cherche:
        # FIX-14 LOT 6 — la recherche infructueuse est DATÉE (distincte du constat général) : le client
        # sait QUAND le débat a été cherché sans être retrouvé, sur les trois écrans.
        padd = (f"Pièce du débat PADD non retrouvée lors de la recherche du {_fr(_cherche)} — "
                "pas de sursis servi.")
    else:
        padd = "Débat PADD non constaté à ce jour — pas de sursis servi (donnée à curer)."
    return {"etat": etat, "prochaine_etape": padd if active else None,
            "debat_padd_tenu": _tenu,   # FIX-12 LOT 2 — fait daté servi au radar (≠ sursis)
            "sursis_autorise": _autor,       # FIX-14 LOT 5 — autorisation de surseoir (conseil), ou None
            "debat_recherche_le": _cherche,  # FIX-14 LOT 6 — date de la recherche infructueuse, ou None
            "confiance": e["confiance"], "source": e.get("source"),
            "date_constat": e.get("date_constat"), "servi_en_vigilance": active}


def communes_en_procedure() -> list[dict]:
    """Liste des communes en procédure PLU ACTIVE servie (SOURCE + révision/élaboration, non
    dormante) — le radar reste le point de calcul UNIQUE, mêmes libellés que la fiche. Type +
    date + synthèse par commune. Le nom servi est celui du registre ; l'API le rapproche du nom
    canonique en base (INSEE) pour un préremplissage exact du périmètre de simulation."""
    out: list[dict] = []
    for insee, e in sorted(_registre().items()):
        if not procedure_active(e):
            continue
        syn = synthese_commune(insee) or {}
        out.append({
            "insee": insee, "commune": e["commune"],
            "type": _TYPE_LABEL.get(e["procedure"], e["procedure"]),
            "stade": e.get("stade"), "date_acte": e.get("date_acte"),
            "etat": syn.get("etat"), "prochaine_etape": syn.get("prochaine_etape"),
            "source": e.get("source"), "source_url": e.get("source_url"),
            "date_constat": e.get("date_constat"), "confiance": e.get("confiance"),
        })
    return out
