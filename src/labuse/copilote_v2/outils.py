"""M78 · 1b — BOÎTE À OUTILS QUESTION.

Chaque outil APPELLE le point de calcul EXISTANT (jamais un SQL de scoring/marché réécrit) et renvoie
un `ToolResult` avec source + millésime. Import PARESSEUX des symboles d'`api.app`/`api.modules`
(motif `ia.py`) pour éviter le cycle app→router→outils→app. Interdit : `requete_libre(sql)`.

Preuve de non-recréation (RAPPORT_M78 §1b) : les comptages passent par `filtre()` (facette canonique,
égalité validée à l'oracle indépendant) ; le marché par `build_marche_commune` ; la fiche par
`_q_v2_fiche` ; les stats par `commune_contexte` ; les délais par `velocite` (réserve Sitadel citée
mot pour mot) ; le patrimoine par `patrimoine`. Le tier/verdict est LU du run servi, jamais recalculé.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ..scoring.score_v_constants import Q_A_RUN_LABEL as RUN

# M78-quater #4 — la SOURCE affichée au client ne cite JAMAIS un nom de moteur, de table ou de run
# (« run servi », « recherche à facettes »… = interne). Les parcelles viennent du cadastre ; son
# millésime réel est celui de l'ingestion (cf. api.app — « cadastre Etalab 2026-06 »). Le run interne
# (RUN) reste l'argument des points de calcul, il n'apparaît pas dans la source.
CADASTRE_MILLESIME = "Etalab 2026-06"


@dataclass
class ToolResult:
    tool: str
    ok: bool = True
    valeur: Any = None                       # le chiffre principal (pour l'anti-invention)
    data: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    millesime: str | None = None
    partiel: bool = False                     # couverture partielle → la réserve DOIT être dite
    reserve: str | None = None                # texte de réserve (cité mot pour mot depuis le point de calcul)
    refus: str | None = None                  # motif de refus si l'outil ne peut pas répondre
    web: bool = False                         # M78-ter — réponse issue du WEB (marquage distinct, jamais Sourcé/Estimé)
    # M109 — critères de la demande que l'outil choisi NE PEUT PAS appliquer (absents de ses
    # paramètres). Un chiffre servi avec un critère lâché DOIT le dire (jamais le sous-total muet).
    criteres_non_appliques: list[str] = field(default_factory=list)


# ───────────────────────── compter_parcelles ─────────────────────────
_TIER_ALIAS = {"opportunites": "brulante,chaude", "opportunité": "brulante,chaude",
               "brulante": "brulante", "brûlante": "brulante", "chaude": "chaude",
               "reserve": "reserve", "a_creuser": "a_creuser"}


# ───────────────────────── garde toponyme (M103 P4, défaut M100 n°5) ─────────────────────────
# La « normalisation en toponyme réunionnais » ne vivait QUE dans le prompt du routeur — aucune
# garantie code. Filet EN DUR après le prompt : le nom rendu est rapproché du RÉFÉRENTIEL des 24
# communes (labuse.communes, jamais recopié ici) par pliage casse + accents + ponctuation +
# variantes St/Ste → Saint/Sainte. Pas de correspondance → refus HONNÊTE (« je n'ai pas reconnu
# cette commune »), jamais un résultat vide sans raison. Même fonction de pliage des DEUX côtés
# (le référentiel est plié par la même _plier_toponyme — motif M99-B, en Python pur ici).
_TOPO_TRANS = str.maketrans("àâäéèêëïîôöùûüç", "aaaeeeeiioouuuc")


def _plier_toponyme(s: str) -> str:
    import re
    t = s.lower().translate(_TOPO_TRANS)
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    t = re.sub(r"\bst\b", "saint", t)
    t = re.sub(r"\bste\b", "sainte", t)
    return t.replace(" ", "")


def _referentiel_plie() -> dict[str, str]:
    """{forme pliée: nom officiel} — chaque nom est aussi indexé SANS son article de tête
    (« plaine des palmistes » → « La Plaine-des-Palmistes ») ; aucune collision sur les 24."""
    import re
    from ..communes import load_communes
    out: dict[str, str] = {}
    for nom in load_communes():
        out[_plier_toponyme(nom)] = nom
        sans_article = re.sub(r"^(le|la|les|l)\s+", "", re.sub(r"[^a-zàâäéèêëïîôöùûüç0-9]+", " ",
                                                               nom.lower()).strip())
        cle = _plier_toponyme(sans_article)
        out.setdefault(cle, nom)
    return out


def resoudre_commune(nom: str | None) -> str | None:
    """Nom officiel du référentiel, ou None si non reconnu. « st denis », « SAINT-DENIS »,
    « Sainte Marie » → le toponyme officiel exact ; « Sant-Denys » → None (refus honnête)."""
    if not nom or not nom.strip():
        return None
    return _referentiel_plie().get(_plier_toponyme(nom))


def _refus_commune(outil: str, nom: str) -> ToolResult:
    return ToolResult(outil, ok=False,
                      refus=f"Je n'ai pas reconnu la commune « {nom} » — précisez parmi les "
                            "24 communes de La Réunion (ex. Saint-Denis, Le Tampon, L'Étang-Salé).")


#: M110 — signaux de vie interrogeables (facette FiltreCriteres.signaux, mêmes clés qu'à l'écran).
_SIGNAUX_OK = {"procedure", "friche", "cession", "permis_actif", "permis_caduc",
               "defisc", "nu_pm", "assemblage"}
#: libellés client des signaux (le récap nomme le critère appliqué, jamais la clé technique).
_SIGNAUX_FR = {"procedure": "procédure judiciaire (BODACC)", "friche": "friche",
               "cession": "cession de fonds récente", "permis_actif": "permis actif",
               "permis_caduc": "permis caduc", "defisc": "en défiscalisation",
               "nu_pm": "terrain nu détenu par une société", "assemblage": "candidate à l'assemblage"}

# M116 · D1 — la SOURCE de chaque critère (défaut de véracité corrigé : ne plus créditer le cadastre
# pour un critère qui vient d'ailleurs). La source servie est celle des DONNÉES qui fondent le compte,
# pas l'inventaire parcellaire. Quand plusieurs critères concourent, toutes leurs sources sont nommées.
# Provenances établies depuis la facette (api.app) : procédure/cession/événement = BODACC ; permis =
# Sitadel ; adresse absente = BAN ; copropriété = RNIC ; personne morale = DGFiP (SIREN) ; zonage =
# GPU ; friche/assemblage/défisc/renouvellement/tier = analyses dérivées LABUSE (sources multiples,
# pas un référentiel unique — on le DIT plutôt que de fausser). Le cadastre ne reste crédité que pour
# ce qu'il fonde réellement : l'inventaire et la surface des parcelles.
_SOURCE_SIGNAL = {
    "procedure": "BODACC", "cession": "BODACC",
    "permis_actif": "Sitadel (permis de construire)", "permis_caduc": "Sitadel (permis de construire)",
    "defisc": "défiscalisation (analyse LABUSE)", "nu_pm": "DGFiP (SIREN) · cadastre",
    "friche": "signaux de vie (analyse LABUSE)", "assemblage": "signaux de vie (analyse LABUSE)",
}


def compter_parcelles(db: Session, *, commune: str | None = None, surface_min: int | None = None,
                      surface_max: int | None = None, tier: str | None = None,
                      personne_morale: bool = False, evenement: bool = False,
                      signaux: str | None = None, adresse_absente: bool = False,
                      copro: str | None = None, defisc: bool = False,
                      renouvellement: bool = False, zonage: str | None = None) -> ToolResult:
    """Compte via la FACETTE canonique `filtre()` (mêmes chiffres que la recherche à l'écran).

    M110 — la facette est interrogeable au-delà des 5 premiers critères : événement rouge,
    signaux de vie (procédure/friche/…), adresse absente, copropriété, défiscalisation,
    renouvellement, zonage PLU (U/AU/A/N). Le Copilote APPELLE la facette, il ne réimplémente
    rien (un critère = un seul endroit). Chaque critère appliqué est NOMMÉ (récap M109)."""
    from ..api.app import FiltreCriteres, filtre
    if commune is not None:                          # M103 P4 — filet toponyme, refus honnête
        resolue = resoudre_commune(commune)
        if resolue is None:
            return _refus_commune("compter_parcelles", commune)
        commune = resolue
    tiers = _TIER_ALIAS.get((tier or "").lower().strip()) if tier else None
    sig = ",".join(s for s in [x.strip().lower() for x in (signaux or "").split(",")]
                   if s in _SIGNAUX_OK) or None
    cp = (copro or "").strip().lower() if copro and copro.strip().lower() in ("avec", "sans") else None
    zon = ",".join(z for z in [x.strip().upper() for x in (zonage or "").split(",")]
                   if z in ("U", "AU", "A", "N")) or None
    fc = FiltreCriteres(source=RUN, commune=commune,
                        surface_min=int(surface_min) if surface_min is not None else None,
                        surface_max=int(surface_max) if surface_max is not None else None,
                        tiers=tiers, personne_morale=bool(personne_morale),
                        evenement=bool(evenement), signaux=sig, adresse_absente=bool(adresse_absente),
                        copro=cp, defisc_active=bool(defisc), renouvellement=bool(renouvellement),
                        zonage=zon)
    out = filtre(c=fc, limit=0, offset=0, sort=None, idus=0, groupes=0, db=db)
    n = out.get("compte")
    crit = {k: v for k, v in {"commune": commune, "surface_min": surface_min,
            "surface_max": surface_max, "tier": tiers, "personne_morale": personne_morale or None,
            "evenement": evenement or None, "signaux": sig, "adresse_absente": adresse_absente or None,
            "copro": cp, "defisc": defisc or None, "renouvellement": renouvellement or None,
            "zonage": zon}.items() if v is not None}
    # M110 — libellés client des critères de FACETTE appliqués (le récap les nomme, comme aujourd'hui).
    labels: list[str] = []
    if evenement:
        labels.append("à événement rouge")
    for s in (sig or "").split(","):
        if s:
            labels.append(_SIGNAUX_FR.get(s, s))
    if adresse_absente:
        labels.append("sans adresse (BAN)")
    if cp == "avec":
        labels.append("en copropriété")
    elif cp == "sans":
        labels.append("hors copropriété")
    if defisc:
        labels.append("en défiscalisation")
    if renouvellement:
        labels.append("en renouvellement urbain")
    if zon:
        labels.append("zone " + "/".join(zon.split(",")))
    # M116 · D1 — la source servie est celle des critères interrogés, jamais un défaut de cadastre.
    sources: list[str] = []
    def _add(s: str) -> None:
        if s and s not in sources:
            sources.append(s)
    if personne_morale:
        _add("DGFiP (SIREN public)")
    for s in (sig or "").split(","):
        if s:
            _add(_SOURCE_SIGNAL.get(s, "signaux de vie (analyse LABUSE)"))
    if evenement:
        _add("BODACC")
    if adresse_absente:
        _add("Base Adresse Nationale (BAN)")
    if cp:
        _add("RNIC (copropriétés)")
    if defisc:
        _add("défiscalisation (analyse LABUSE)")
    if renouvellement:
        _add("renouvellement urbain (analyse LABUSE)")
    if zon:
        _add("PLU (GPU)")
    if tiers:
        _add("classement LABUSE")
    if surface_min is not None or surface_max is not None:
        _add("cadastre")
    if not sources:                       # commune / base seule → l'inventaire cadastral
        _add("cadastre")
    source = " · ".join(sources)
    # le millésime ne vaut QUE pour un compte purement cadastral ; pour une source externe/dérivée on
    # ne fabrique pas de date (D1 : « si la source ne peut pas être établie, le dire », ici on l'omet).
    millesime = CADASTRE_MILLESIME if sources == ["cadastre"] else None
    return ToolResult("compter_parcelles", valeur=n,
                      data={"compte": n, "criteres": crit, "criteres_labels": labels},
                      source=source, millesime=millesime)


# ───────────────────────── parcelles_par_entreprise ─────────────────────────
_FOLD = ("translate({c}, 'àâäáéèêëíìîïóòôöúùûüçÀÂÄÁÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÇ',"
         "'aaaaeeeeiiiioooouuuucAAAAEEEEIIIIOOOOUUUUC')")
_ACCENTS = str.maketrans("àâäáéèêëíìîïóòôöúùûüçÀÂÄÁÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÇ",
                         "aaaaeeeeiiiioooouuuucAAAAEEEEIIIIOOOOUUUUC")


def _fold_py(s: str) -> str:
    return s.translate(_ACCENTS)


# ───────────────────────── M110 — résolution d'acronyme (référentiel en base) ─────────────────────────
def _repo_root_entites():
    from pathlib import Path
    return Path(__file__).resolve().parents[3]


def _ensure_acronymes(db: Session) -> None:
    """Table `entite_acronyme` (référentiel en base, JAMAIS une table en dur dans le prompt),
    semée depuis le CSV versionné data/entites/acronymes_moraux.csv (SIREN vérifiés). Idempotent :
    créée + semée à la 1re demande si vide (tests / base fraîche), jamais rechargée ensuite."""
    import csv as _csv
    from sqlalchemy import text as _text
    db.execute(_text("CREATE TABLE IF NOT EXISTS entite_acronyme ("
                     "acronyme text PRIMARY KEY, siren varchar(9) NOT NULL, libelle text)"))
    if (db.execute(_text("SELECT count(*) FROM entite_acronyme")).scalar() or 0) == 0:
        seed = _repo_root_entites() / "data" / "entites" / "acronymes_moraux.csv"
        if seed.exists():
            with seed.open(encoding="utf-8") as f:
                for row in _csv.DictReader(f, delimiter=";"):
                    if row.get("acronyme") and row.get("siren"):
                        db.execute(_text("INSERT INTO entite_acronyme (acronyme, siren, libelle) "
                                         "VALUES (:a,:s,:l) ON CONFLICT (acronyme) DO NOTHING"),
                                   {"a": row["acronyme"].strip().upper(), "s": row["siren"].strip(),
                                    "l": (row.get("libelle") or "").strip()})
            db.commit()


def resoudre_acronyme(db: Session, q: str) -> tuple[str, str] | None:
    """(siren, libellé) si un MOT de la demande est un acronyme connu (« la SIDR » → 310863592),
    sinon None. Insensible casse/ponctuation ; le référentiel vit en base (seed vérifié)."""
    import re as _re
    _ensure_acronymes(db)
    from sqlalchemy import text as _text
    for w in [q] + q.split():
        key = _re.sub(r"[^A-Z0-9]", "", w.upper())
        if len(key) < 3:
            continue
        row = db.execute(_text("SELECT siren, libelle FROM entite_acronyme WHERE acronyme = :k"),
                         {"k": key}).first()
        if row:
            return (row[0], row[1])
    return None


def parcelles_par_entreprise(db: Session, *, q: str) -> ToolResult:
    """Patrimoine d'une personne morale (nom ou SIREN) via `patrimoine` (DGFiP open data). Résolution
    nom→SIREN accent-INSENSIBLE (le client tape « Société », la base stocke « SOCIETE »).

    M110 — un ACRONYME connu (SIDR, SHLMR, SAFER…) résout d'abord par le référentiel en base : le
    token-matcher tombait sinon sur un homonyme (« lot SIDR de Terre Sainte »). En cas d'ambiguïté
    réelle du nom (deux entités plausibles de taille comparable), le Copilote DEMANDE."""
    from sqlalchemy import text as _text

    from ..api.modules import patrimoine
    q = (q or "").strip()
    siren = q if q.isdigit() and len(q) >= 9 else None
    libelle_acro = None
    if siren is None:
        acro = resoudre_acronyme(db, q)                  # M110 — l'acronyme prime sur les tokens
        if acro:
            siren, libelle_acro = acro
    if siren is None:
        # matching par TOKENS : chaque mot significatif du nom doit être présent (accent-insensible),
        # robuste aux mots de liaison (« du », « de la ») que la dénomination DGFiP n'a pas.
        _stop = {"de", "du", "la", "le", "les", "des", "et", "au", "aux", "sci", "sarl", "sas"}
        toks = [t for t in q.replace("'", " ").replace("-", " ").lower().split()
                if len(t) >= 3 and t not in _stop]
        if not toks:
            return ToolResult("parcelles_par_entreprise", ok=False, refus=f"nom trop court : « {q} »")
        conds = " AND ".join(f"lower({_FOLD.format(c='denomination')}) LIKE :t{i}" for i in range(len(toks)))
        params = {f"t{i}": f"%{_fold_py(t)}%" for i, t in enumerate(toks)}
        rows = db.execute(_text(
            f"SELECT siren, max(denomination) nom, count(*) n FROM parcelle_personne_morale "
            f"WHERE siren IS NOT NULL AND {conds} GROUP BY siren ORDER BY count(*) DESC LIMIT 3"),
            params).mappings().all()
        if not rows:
            return ToolResult("parcelles_par_entreprise", ok=False,
                              refus=f"aucune personne morale trouvée pour « {q} »")
        # M110 — AMBIGUÏTÉ RÉELLE : deux entités plausibles de taille comparable (2e ≥ 60 % du 1er)
        # ET aucune n'est manifestement dominante → on DEMANDE (clarification, champ M107), on ne
        # tranche pas au hasard.
        if len(rows) >= 2 and rows[1]["n"] >= 0.6 * rows[0]["n"] and rows[0]["n"] < 200:
            noms = " ou ".join(f"« {r['nom']} »" for r in rows[:2])
            return ToolResult("parcelles_par_entreprise", ok=False,
                              refus=f"_ambigu:Plusieurs sociétés correspondent à « {q} » : {noms}. "
                                    "Laquelle ? (vous pouvez répondre par son nom ou son SIREN)")
        siren = rows[0]["siren"]
    res = patrimoine(siren=siren, db=db)
    return ToolResult("parcelles_par_entreprise", valeur=res["n_parcelles"],
                      data={"siren": siren, "nom": res["nom"], "n_parcelles": res["n_parcelles"],
                            "sdp_totale_m2": res["sdp_totale_m2"],
                            "bodacc": res.get("bodacc")},
                      source="DGFiP — parcelles de personnes morales (SIREN public)")


# ───────────────────────── fiche_parcelle ─────────────────────────
def fiche_parcelle(db: Session, *, idu: str) -> ToolResult:
    """Données d'UNE parcelle via `_q_v2_fiche` (verdict/zonage/risques LUS, jamais recalculés)."""
    from ..api.app import _q_v2_fiche
    f = _q_v2_fiche(db, idu, run_label=RUN)
    if not f or f.get("commune") is None:
        return ToolResult("fiche_parcelle", ok=False, refus=f"parcelle {idu} introuvable")
    sv2 = f.get("score_v2") or {}
    reg = (f.get("reglement_plu") or {}).get("zones") or []
    data = {"idu": idu, "commune": f.get("commune"), "surface_m2": f.get("surface_m2"),
            "zone": (reg[0].get("zone") if reg else None),
            "verdict": sv2.get("verdict") or sv2.get("libelle") or sv2.get("tier"),
            "etage0": f.get("etage0")}
    return ToolResult("fiche_parcelle", valeur=f.get("surface_m2"), data=data,
                      source="cadastre", millesime=CADASTRE_MILLESIME)


# ───────────────────────── stats_commune ─────────────────────────
def stats_commune(db: Session, *, commune: str) -> ToolResult:
    """Contexte commune via `commune_contexte` (SRU + INSEE logement — chaque bloc sa source)."""
    from ..api.app import commune_contexte
    resolue = resoudre_commune(commune)              # M103 P4 — filet toponyme
    if resolue is None:
        return _refus_commune("stats_commune", commune)
    commune = resolue
    c = commune_contexte(commune, db=db)
    sru = c.get("sru") or {}
    marche = c.get("marche") or {}
    if not sru and not marche:
        return ToolResult("stats_commune", ok=False, refus=f"commune {commune} inconnue au contexte")
    data = {"commune": commune, "taux_lls": sru.get("taux_lls"), "sru_statut": sru.get("statut"),
            "objectif_pct": sru.get("objectif_pct"), "logements": marche.get("logements"),
            "proprietaires_pct": marche.get("proprietaires_pct")}
    return ToolResult("stats_commune", data=data, source="INSEE (logement) · Inventaire SRU",
                      millesime=sru.get("millesime") or marche.get("millesime"))


# ───────────────────────── delais_instruction ─────────────────────────
def delais_instruction(db: Session, *, commune: str) -> ToolResult:
    """Délai médian d'instruction via `velocite` — la RÉSERVE Sitadel est CITÉE mot pour mot."""
    from ..api.modules import velocite
    resolue = resoudre_commune(commune)              # M103 P4 — filet toponyme
    if resolue is None:
        return _refus_commune("delais_instruction", commune)
    commune = resolue
    v = velocite(fmt="json", nature=None, db=db)
    row = next((r for r in v["communes"] if r["commune"] == commune), None)
    if not row or row.get("delai_median_mois") is None:
        return ToolResult("delais_instruction", ok=False, refus=f"aucun délai mesurable à {commune}")
    n_mur = row.get("n_mur")
    # Réserve = censure (accordés seulement) + disclaimer (historique) + limite type/service, mot pour mot.
    reserve = (v["censure"] + " " + v["disclaimer"]
               + " Je n'ai pas le détail par type de dossier ni par service.")
    if n_mur is not None and n_mur < 30:
        reserve += f" Échantillon faible ({n_mur} permis) — à prendre avec prudence."
    data = {"commune": commune, "delai_median_mois": row["delai_median_mois"], "n_mur": n_mur,
            "n_permis_accordes": row.get("n_valide"), "tendance": row.get("tendance")}
    return ToolResult("delais_instruction", valeur=row["delai_median_mois"], data=data,
                      source="Sitadel — délais d'instruction (dossiers accordés)",
                      millesime=v.get("cohortes"), partiel=True, reserve=reserve)


# ───────────────────────── marche ─────────────────────────
def marche(db: Session, *, commune: str) -> ToolResult:
    """Marché commune via `build_marche_commune` (point de calcul unique, terrain nu M79 inclus)."""
    from ..faisabilite.marche_commune import build_marche_commune
    resolue = resoudre_commune(commune)              # M103 P4 — filet toponyme
    if resolue is None:
        return _refus_commune("marche", commune)
    commune = resolue
    m = build_marche_commune(db, commune)
    lignes = [{"cle": l.get("cle") or l.get("libelle"), "valeur": l.get("valeur"),
               "source": l.get("source"), "millesime": l.get("millesime")}
              for l in (m.get("lignes") or []) if isinstance(l, dict)]
    return ToolResult("marche", data={"commune": commune, "lignes": lignes},
                      source="DVF, Sitadel, DHUP (terrain nu)",
                      millesime="par ligne (fraîcheur = source amont)")


# ───────────────────────── recherche_web (M78-ter) ─────────────────────────
WEB_SYSTEM = """Tu es le copilote foncier de LABUSE (La Réunion). Réponds à la question EN FRANÇAIS en
t'appuyant sur la recherche web. N'invente RIEN : chaque fait vient d'une source web trouvée. Si les
sources DIVERGENT ou sont faibles, dis-le (« Les sources divergent — à vérifier »). Tu ne réponds QUE sur
l'immobilier, le foncier, l'urbanisme, les collectivités et leurs acteurs à La Réunion.
FORMAT (M117 · D5) — STRICT : UNE phrase, le FAIT PRINCIPAL SEUL, ~150 caractères MAXIMUM. INTERDIT :
phrase d'introduction, reformulation de la question, ET tout détail secondaire (pourcentage, score,
date d'élection, prédécesseur, nombre de voix) SAUF s'il EST la question posée. Ne cite pas d'URL (le
serveur ajoute la source). Exemple attendu, à imiter EXACTEMENT : « Le maire de Saint-Denis est Ericka
Bareigts. »"""


def _deux_phrases(texte: str, max_car: int = 180) -> str:
    """M117 · D5 — garde-fou DÉTERMINISTE de la brièveté web : au plus DEUX phrases, ~180 car. Le
    prompt ne suffit pas (le modèle sur-produit) ; on tronque à une frontière de phrase, sinon de
    clause, sinon net avec une ellipse. Jamais couper un mot en deux."""
    import re
    texte = " ".join((texte or "").split())
    phrases = [p for p in re.split(r"(?<=[.!?])\s+", texte) if p.strip()]
    out = ""
    for i, p in enumerate(phrases):
        if i >= 2:
            break
        cand = (out + " " + p).strip() if out else p
        if out and len(cand) > max_car:
            break
        out = cand
    if not out:
        out = (phrases[0] if phrases else texte)[:max_car]
    if len(out) > max_car:                        # une seule phrase déjà trop longue
        # préférer la PREMIÈRE clause (le fait principal « X est Y »), sinon couper net au mot
        prem = out.find(", ", 25)
        out = (out[:prem] if 25 < prem < max_car else out[:max_car].rsplit(" ", 1)[0]).rstrip(" ,;") + "…"
    return out.strip()


def recherche_web(db: Session, *, question: str, history: list[dict] | None = None) -> ToolResult:
    """M78-ter — répondre au-delà de la base pour du PUBLIC hors base (élus, organigrammes, actualité
    réglementaire…) via la recherche web NATIVE de l'API Anthropic (pas de scraping maison). Marqué web,
    jamais Sourcé/Estimé. La hiérarchie (base d'abord) est gérée par l'aiguillage en amont.

    M117 · D9 — `history` (fil du chip web) : les derniers tours sont passés au modèle pour résoudre
    un enchaînement (« et à Saint-Pierre ? »). Le modèle résout la référence ; il ne SOMME pas."""
    import urllib.parse as up
    from datetime import date

    from ..ai import core
    if not core.has_key():
        return ToolResult("recherche_web", ok=False, refus="recherche web indisponible")
    import anthropic
    client = anthropic.Anthropic(timeout=45, max_retries=1)
    msgs = [{"role": str(m.get("role", "user")), "content": str(m.get("content", ""))[:600]}
            for m in (history or [])[-4:] if m.get("content")] + [{"role": "user", "content": question}]
    try:
        msg = client.messages.create(
            model=core.MODEL_REASONING, max_tokens=300, system=WEB_SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=msgs)
    except Exception:
        return ToolResult("recherche_web", ok=False, refus="recherche web échouée")
    texte, domaines = "", []
    for b in msg.content:
        if getattr(b, "type", None) == "text":
            texte += b.text
            for cit in (getattr(b, "citations", None) or []):
                u = getattr(cit, "url", "") or ""
                if u:
                    d = up.urlparse(u).netloc.replace("www.", "")
                    if d and d not in domaines:
                        domaines.append(d)
    try:
        core._log_cost(db, "copilote-web", core.MODEL_REASONING, False,
                       msg.usage.input_tokens, msg.usage.output_tokens)
    except Exception:
        pass
    if not texte.strip() or not domaines:
        return ToolResult("recherche_web", ok=False, refus="rien trouvé sur le web")
    return ToolResult("recherche_web", ok=True, web=True, valeur=None,
                      data={"reponse": _deux_phrases(texte), "domaines": domaines[:3], "date": date.today().isoformat()},
                      source="web")


# FIX-COPILOTE F5 — l'outil `divisibilite` (M82 cas A) est RETIRÉ : injoignable depuis M129-C
# (division_or sort du produit — au chat, la division renvoie au règlement de zone via `_division`
# dans answering.py, jamais un score géométrique). Il n'était plus dans le CATALOGUE montré au
# modèle → jamais sélectionnable → code mort. Ne pas le remettre sans réintroduire la division au
# produit. Le lookup `module_division` en base reste (autres consommateurs, hors Copilote).


# Registre nom → fonction (l'exécuteur du serveur ; le modèle choisit le NOM, jamais le SQL).
OUTILS = {
    "compter_parcelles": compter_parcelles,
    "parcelles_par_entreprise": parcelles_par_entreprise,
    "fiche_parcelle": fiche_parcelle,
    "stats_commune": stats_commune,
    "delais_instruction": delais_instruction,
    "marche": marche,
    "recherche_web": recherche_web,
}
