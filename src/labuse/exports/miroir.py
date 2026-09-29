"""EXPORTS-REBRANCHEMENT-1 lot 1 — LE MIROIR : le Dossier EST la fiche parcelle.

Le Dossier ne compose plus ses propres sections : il rend les DÉCLARATIONS de la fiche
(`declarations/fiche/` — sections.yaml pour l'ordre et les noms, chaque surface pour ses
lignes). Mêmes 11 sections, mêmes noms, même ordre, mêmes lignes que l'écran ; chaque valeur
vient du robinet unique (`robinet_fiche`, le payload `/parcels/{idu}`) et porte sa nature du
registre. Une ligne qui n'est pas déclarée n'existe pas au PDF (verrou V5d étendu) ; chaque
ligne rendue porte `data-quoi="<id>"` — c'est la preuve mécanique que le verrou lit.

Les lignes déclarées SANS valeur sur la parcelle sont dites sous « Vérifié, sans objet »
(en petit — le PDF n'a pas de clic pour déplier) avec leur phrase d'absence DÉCLARÉE.
Les lignes déclarées sans extracteur câblé sont OMISES et listées par `non_cables()` —
jamais un silence : le test de couverture les compte.

Cas particuliers assumés :
  · `simulation` (§11) = un encart de renvoi au document Financier, rien d'autre (lot 2) ;
  · la clôture « Sources, limites et mentions » suit les 11 sections (noms de sources seuls,
    aucun millésime — doctrine PAGE-SOURCES-1 du 18/09, lot 2).
"""
from __future__ import annotations

from typing import Any

from ..registre import declarations as DEC
from ..registre.valeur import Valeur
from .nature import chip
from .pieds import sources_lues
from .registre_fmt import fmt_eur, fmt_eur_m2, fmt_m, fmt_m2, fmt_pct, groupe
from .rendu import aside, esc, esc_noms, note, section, tuiles, verdict
from .verdicts import rendu_verdict, verdict_potentiel, verdict_reseaux, verdict_zonage

# ── EXPORTS-FIX-1 : normalisations d'affichage (lot A) ───────────────────────────────────────
import re as _re

#: EXPORTS-FIX-1 A7 — toute date ISO servie (AAAA-MM-JJ) s'imprime JJ/MM/AAAA. On ne touche PAS la
#: valeur du registre : on la met en forme au rendu (les codes type « 97408_PLU_20251217 » n'ont
#: pas de tiret et ne sont donc jamais capturés).
def _fr_dates(s: str) -> str:
    return _re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", lambda m: f"{m.group(3)}/{m.group(2)}/{m.group(1)}", str(s))


#: EXPORTS-FIX-1-BIS point 1 — nomenclature d'USAGE du sol OCS GE (dimension US, IGN v2.0), reprise
#: CODE PAR CODE de la nomenclature officielle (portail de l'artificialisation / IGN ; cf.
#: src/labuse/ingestion/ocsge.py). L'ancienne table inversait US1.1 (agriculture, pas résidentiel) et
#: US5 (résidentiel, pas « sans usage »). Repli : le code seul si la classe n'est pas au catalogue.
_OCS_GE_US = {
    "US1.1": "Agriculture",
    "US1.2": "Sylviculture",
    "US1.3": "Activités d'extraction",
    "US1.4": "Pêche et aquaculture",
    "US1.5": "Production de sel",
    "US2": "Production secondaire (industrie)",
    "US3": "Production tertiaire",
    "US235": "Production et usage résidentiel (secondaire, tertiaire, résidentiel)",
    "US4.1.1": "Réseau routier",
    "US4.1.2": "Réseau ferré",
    "US4.1.3": "Transport aérien",
    "US4.2": "Réseaux d'utilité publique (eau, énergie, télécom)",
    "US4.3": "Logistique et stockage",
    "US5": "Usage résidentiel",
    "US6.1": "Zones en transition",
    "US6.2": "Zones abandonnées",
}


def _ocs_ge_libelle(code: str) -> str:
    return _OCS_GE_US.get(str(code).strip(), str(code))


#: EXPORTS-FIX-1 A5 — libellés des catégories de servitudes d'utilité publique (code CNIG → clair).
_SUP_CAT = {
    "PM1": "plan de prévention des risques naturels (PPR)",
    "PM2": "plan de prévention des risques technologiques (PPRT)",
    "PM3": "plan de prévention des risques miniers",
    "AC1": "abords de monuments historiques", "AC2": "sites classés ou inscrits",
    "AC4": "aire de mise en valeur de l'architecture et du patrimoine",
    "AS1": "protection des eaux (captage)", "EL3": "halage et marchepied",
    "EL7": "alignement des voies", "I4": "lignes électriques", "T1": "voies ferrées",
    "PT1": "protection des centres de réception radioélectriques",
    "PT2": "protection contre les obstacles (radioélectrique)", "PT3": "communications téléphoniques",
    "A1": "forêts de protection", "A4": "cours d'eau non domaniaux",
}


def _sup_libelle(cat: str) -> str:
    lib = _SUP_CAT.get(str(cat).strip().upper())
    return f"{cat} — {lib}" if lib else str(cat)


def _frr_libelle(frr: dict) -> str:
    """EXPORTS-FIX-1 C2 — FRR à La Réunion, dit juste. La FAQ FRR de la DGCL (MAJ juillet 2025) est
    explicite : seules les communes de la ZONE SPÉCIALE D'ACTION RURALE (les Hauts, décret n° 78-690
    du 23/06/1978) sont classées FRR, et elles n'ouvrent QUE les mesures NON FISCALES — l'exonération
    de l'art. 44 quindecies A CGI ne s'applique PAS dans les DOM. Sans test géométrique à la parcelle
    (classement « partie » = commune classée en partie), on ne dit pas « Parcelle DANS »."""
    partie = frr.get("classement") == "partie"
    tete = ("Commune classée FRR en partie — zone spéciale d'action rurale des Hauts (décret 1978) ; "
            "position de cette parcelle dans le périmètre non vérifiée géométriquement"
            if partie else "Parcelle en zone FRR — zone spéciale d'action rurale des Hauts")
    return (tete + ". À La Réunion, ce classement n'ouvre que les mesures NON FISCALES "
            "(FAQ FRR DGCL, juillet 2025) : l'exonération d'impôt de l'art. 44 quindecies A CGI "
            "ne s'y applique pas — à confirmer par un fiscaliste.")


def _norm_ebc(lib: str) -> str:
    """EXPORTS-FIX-1 A1 — « EBC Espace Boisé Classé » → « Espace boisé classé »."""
    l = str(lib).strip()
    if l.upper().startswith("EBC "):
        l = l[4:].strip()
    if l.lower().startswith("espace bois"):
        return "Espace boisé classé"
    return l


#: EXPORTS-FIX-1 A4 — natures d'aléa servies avec un code technique (« mouvement_terrain »).
def _nature_alea(nat: str) -> str:
    return _re.sub(r"mouvement_terrain", "mouvement de terrain", str(nat)).replace("_", " ")


#: EXPORTS-FIX-1 A8 — phrases d'absence servies en jargon interne, dites en clair au rendu (le
#: fait est conservé ; seul le vocabulaire client change — la valeur du registre n'est pas modifiée).
_ABSENCE_CLAIR = {
    "cosia_detecte_m2": "Bâti détecté par IA (CoSIA) : cohérent avec la cartographie IGN, rien à signaler.",
    # EXPORTS-FIX-1 B5 — `dispositifs_parcelle` = les SERVITUDES d'utilité publique (SUP) seules ;
    # ER/EBC/DPU/PEB sont des lignes distinctes avec leur propre absence. La phrase ne doit donc
    # PAS revendiquer « aucune prescription (ER/EBC/DPU/PEB) » quand un DPU, lui, est présent.
    "dispositifs_parcelle": "Aucune servitude d'utilité publique (SUP) intersectant la parcelle.",
    # EXPORTS-FIX-1 C4 — la RTAA DOM s'applique à TOUT logement neuf : jamais « aucune exigence ».
    "rtaa_exigences": ("RTAA DOM : conception réglementée pour tout logement neuf (aération "
                       "traversante, protection solaire, eau chaude solaire) — à intégrer au projet."),
    # EXPORTS-FIX-1-BIS point 3 — la ligne « insuffisant » du terrain nu nomme SON périmètre (rayon
    # 500 m, le même que l'ancien bâti secteur), pas un « secteur » ambigu avec le « secteur cadastral »
    # des médianes par type.
    "prix_terrain_secteur_eur_m2": ("Terrain nu — à moins de 500 m : échantillon DVF insuffisant "
                                    "pour une médiane fiable."),
}

#: EXPORTS-FIX-1 C3 — le SAR n'est pas en base : la ligne « Aucune divergence SAR indiquée » ne
#: doit pas s'imprimer (elle affirme un contrôle qui n'a pas eu lieu). Absence purement masquée.
_ABSENCE_MASQUEE = {"sar_divergence"}

#: EXPORTS-FIX-1 C6 — marqueurs d'une donnée NON DISPONIBLE (non calculée/déterminée), à distinguer
#: d'un « vérifié : rien » (contrôle fait, rien trouvé). Deux encadrés distincts au rendu.
_MARQUEURS_NON_DISPO = ("non calcul", "non détermin", "non estim", "non relev", "non renseign",
                        "non évalu", "non dispon", "rien d'évalu", "non chiffr")


def _est_non_dispo(phrase: str) -> bool:
    p = str(phrase).lower()
    return any(m in p for m in _MARQUEURS_NON_DISPO)


def _absence_une_raison(phrase: str, zone, *, gabarit_bloque: bool = False) -> str:
    # EXPORTS-FIX-1 C6 / BIS point 11 — jamais « A ou B » : on tranche selon le contexte réel.
    #  · « (zone non constructible ou X) » → selon la zone (A/N → non constructible) ;
    #  · « (hauteur de règle ou bâti non déterminés) » → si le gabarit est bloqué, c'est la hauteur
    #    de règle (pas le bâti) ; sinon on garde le bâti.
    non_constructible = str(zone or "").upper() in ("A", "N")
    p = _re.sub(r"\(zone non constructible ou ([^)]+)\)",
                lambda m: "(zone non constructible)" if non_constructible else f"({m.group(1)})",
                str(phrase))
    p = _re.sub(r"\(hauteur de règle ou bâti non déterminés\)",
                "(hauteur de règle non déterminée)" if gabarit_bloque else "(bâti non déterminé)", p)
    return p


#: EXPORTS-FIX-1-BIS point 8 — sources citées au §5 (ABF, ICPE, cavités) qui n'avaient AUCUNE ligne :
#: quand la cascade les a LUES (result PASS), on imprime leur « vérifié : rien » ; sinon elles sortent
#: des listes (elles n'apparaissent alors ni au pied ni au §12, faute d'avoir été servies).
_SOURCES_VERIFIE_RIEN = {
    "abf": "ABF / Monuments historiques : hors périmètre de protection.",
    "icpe": "ICPE : aucune installation classée relevée à proximité.",
    "cavite": "Cavités souterraines : aucune recensée à proximité.",
    "cavites": "Cavités souterraines : aucune recensée à proximité.",
}


def _lignes_verifie_rien(fiche: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    vus: set[str] = set()
    for l in (fiche.get("lines") or []):
        if not isinstance(l, dict):
            continue
        lay = l.get("layer")
        if lay in _SOURCES_VERIFIE_RIEN and l.get("result") == "PASS" and lay not in vus:
            vus.add(lay)
            out.append((lay, _SOURCES_VERIFIE_RIEN[lay]))
    return out


def _n_aleas(valeurs: dict) -> int | None:
    """EXPORTS-FIX-1-BIS point 6 — le nombre d'aléas IMPRIMÉS au §5 (aleas_parcelle_liste), qui doit
    valoir le chiffre de la garde et du §5 (au lieu de n_vigilances, un compteur de couches interne)."""
    v = valeurs.get("aleas_parcelle_liste")
    aleas = v.valeur if v is not None else None
    return len(aleas) if isinstance(aleas, list) else None


def _absence_clair(quoi: str, phrase: str) -> str:
    return _ABSENCE_CLAIR.get(quoi, phrase)


#: EXPORTS-FIX-1 B2 — une piscine détectée (FLAIR ∪ CoSIA) n'est ni un dispositif fiscal ni un
#: périmètre : elle est un élément du terrain (§2), jamais compté au §7. On la repère et la retire.
def _is_piscine(per: dict) -> bool:
    return isinstance(per, dict) and "piscine" in (per.get("libelle") or "").lower()


def _perimetres_hors_piscine(v: dict) -> list:
    return [p for p in (v.get("perimetres") or []) if not _is_piscine(p)]


def _piscine_dispositif(v: dict) -> dict | None:
    for p in (v.get("perimetres") or []):
        if _is_piscine(p):
            return p
    return None


# ── la structure : sections + lignes, depuis les déclarations ────────────────────────────────


def structure() -> list[dict]:
    """Les sections de la fiche (ordre de sections.yaml), chacune avec ses lignes déclarées.
    Ordre des lignes dans une section : en_tete avant replie, puis (surface, rang)."""
    surfaces = [s for s in DEC.charger()[0] if s.categorie == "fiche"]
    par_section: dict[str, list] = {}
    for s in surfaces:
        for l in s.donnees:
            cle = l.fiche_section or s.fiche_section
            if cle:
                par_section.setdefault(cle, []).append((s, l))
    out = []
    for sec in DEC.sections_fiche():
        lignes = sorted(par_section.get(sec["id"], []),
                        key=lambda t: (t[1].etat != "en_tete", t[0].surface, t[1].rang))
        out.append({**sec, "lignes": lignes})
    return out


def ids_declares() -> set[str]:
    return {l.quoi for s in DEC.charger()[0] if s.categorie == "fiche" for l in s.donnees}


def non_cables() -> list[str]:
    """Les ids déclarés sur la fiche SANS extracteur au robinet — omis du rendu, comptés ici."""
    from .robinet_fiche import EXTRACTEURS
    return sorted(cid for cid in ids_declares() if cid not in EXTRACTEURS)


# ── formats scalaires (comment.format du FORMAT.md) ──────────────────────────────────────────

def _fmt_scalaire(fmt: str | None, v: Any) -> str:
    try:
        if fmt == "entier_m2":
            return fmt_m2(v)
        if fmt == "euro":
            return fmt_eur(v)
        if fmt == "euro_m2":
            return fmt_eur_m2(v)
        if fmt == "pourcent":
            return fmt_pct(v)
        if fmt == "metre":
            return fmt_m(v)
        if fmt == "degre":
            return f"{str(v).replace('.', ',')}°"
        if fmt == "entier":
            return groupe(round(float(v)))
    except (TypeError, ValueError):
        pass
    return esc(v)


# ── rendeurs par id (valeurs structurées) — la phrase de l'écran, jamais un dump ─────────────

def _r_prix_achat(v):
    d = f"{fmt_eur(v['valeur'])}" if v.get("valeur") else ""
    quand = (v.get("date_mutation") or "")[:4]
    nat = v.get("nature") or ""
    bits = [b for b in (d, nat.lower() if nat else "", quand) if b]
    return " — ".join(bits[:1] + [", ".join(bits[1:])] if len(bits) > 1 else bits)


def _r_copros(v):
    n = len(v) if isinstance(v, list) else 1
    return f"{n} copropriété{'s' if n > 1 else ''} enregistrée{'s' if n > 1 else ''} (RNIC)"


def _r_timeline(v):
    if not isinstance(v, list) or not v:
        return ""
    d = v[0].get("denomination") or ""
    ans = [str(x.get("millesime")) for x in v if x.get("millesime")]
    per = f"{ans[0]}–{ans[-1]}" if len(ans) > 1 else (ans[0] if ans else "")
    return esc(f"{d} ({per})" if d else per)


def permis_incoherence_note(dep, aut) -> str:
    """DONNEES-6/7 — dépôt enregistré APRÈS l'autorisation (incohérence du producteur SDES/Dido).
    On ne réordonne JAMAIS les dates ; on qualifie l'écart : au-delà d'1 MOIS, c'est le plus souvent
    un permis modificatif ou transféré (nouveau dépôt postérieur sur l'autorisation d'origine — le
    flux open data ne porte pas le n° de modificatif, on le DIT comme tendance) ; sous 1 mois, on ne
    présume rien (« dates incohérentes chez le producteur »). Rend "" si les dates sont cohérentes."""
    from datetime import date as _date
    if not (dep and aut) or str(aut) >= str(dep):
        return ""
    try:
        gap = (_date.fromisoformat(str(dep)[:10]) - _date.fromisoformat(str(aut)[:10])).days
    except (ValueError, TypeError):
        gap = 0          # dates non parsables mais aut<dep : on reste sur la mention prudente
    if gap > 31:
        return "Dépôt enregistré après l'autorisation — souvent un permis modificatif ou transféré"
    return "dates incohérentes chez le producteur"


def _r_permis_liste(v):
    # DONNEES-5 — la MÊME liste que l'écran (HistoriqueSiteBlock) : chaque permis daté (type,
    # dépôt, autorisation), 6 max comme la fiche, plus le reste compté. Même source (historique_site).
    if not isinstance(v, list) or not v:
        return ""
    lignes = []
    for pm in v[:6]:
        t = esc(pm.get("type") or "permis")
        dep = pm.get("date_depot")
        aut = pm.get("date_autorisation")
        dep_txt = esc(dep or aut or "?")
        auto = f", autorisé {esc(aut)}" if aut else ""
        note = permis_incoherence_note(dep, aut)   # littéral de confiance (2 valeurs fixes) — pas d'esc
        lignes.append(f"{t} — déposé {dep_txt}{auto}" + (f" · {note}" if note else ""))
    reste = f" (+{len(v) - 6} autres)" if len(v) > 6 else ""
    return f"{len(v)} permis sur la parcelle (Sitadel) — " + " ; ".join(lignes) + reste


def _r_er_ebc(v):
    # EXPORTS-FIX-1 A1 — la valeur servie peut être un dict OU une liste de dicts : dans les deux
    # cas on rend une phrase (« Espace boisé classé — 89,6 % de la parcelle »), jamais le dict brut.
    item = v[0] if isinstance(v, list) and v else v
    if isinstance(item, dict):
        lib = _norm_ebc(item.get("libelle") or item.get("detail") or "parcelle concernée")
        part = item.get("part_pct")
        return esc(f"{lib} — {groupe(part, 1)} % de la parcelle" if part else lib)
    return esc(item)


def _r_dpu(v):
    # EXPORTS-FIX-1 A6 — la valeur dit le FAIT, jamais le sigle nu (« DPU : DPU »).
    return esc("Parcelle dans le périmètre du droit de préemption urbain (DPU) : "
               "la commune peut préempter à la vente")


def _r_peb(v):
    z = v.get("zone")
    return esc(f"Zone {z} du plan d'exposition au bruit" + (f" — {v['detail']}" if v.get("detail") else ""))


def _r_sup(v):
    # EXPORTS-FIX-1 A5 — dédoublonnage par catégorie CNIG (deux assiettes PM1 = UNE servitude PM1)
    # et libellé clair de chaque catégorie, jamais le code d'assiette technique répété.
    if isinstance(v, list):
        cats: list[str] = []
        mills: list[str] = []      # RETOUCHES-1 point 7 — millésime(s) des SUP intersectées
        for x in v:
            if not x:
                continue
            cat = str((x.get("categorie") if isinstance(x, dict) else None) or x)
            if cat not in cats:
                cats.append(cat)
            m = x.get("millesime") if isinstance(x, dict) else None
            if m and m not in mills:
                mills.append(m)
        libs = [_sup_libelle(c) for c in cats[:6]]
        s = f"{len(cats)} servitude{'s' if len(cats) > 1 else ''} — " + " · ".join(libs)
        if mills:   # millésime de la source (data_sources.source_millesime), comme les autres sources
            s += " · millésime " + " · ".join(mills[:3])
        return esc(s)
    return esc(v)


def _r_statut_plu(v):
    # EXPORTS-FIX-1 C1 — date d'APPROBATION du PLU (Sudocuh) + dernière évolution ; la date GPU
    # (« horizon », 2025-12-17) est dite comme une PUBLICATION, jamais comme une approbation.
    #  · La Possession : approuvé le 12/06/2019 ; Saint-Paul : le 27/09/2012 (recette).
    appro = v.get("approbation_sudocuh")
    evol = v.get("evolution_sudocuh")
    gpu = v.get("horizon")
    if appro:
        s = f"PLU approuvé le {_fr_dates(appro)}"
        if evol and evol != appro:
            s += f" — dernière évolution engagée le {_fr_dates(evol)}"
        if gpu:
            s += f" — version publiée au Géoportail de l'urbanisme le {_fr_dates(gpu)} (document opposable)"
        return esc(s + ".")
    if gpu:   # à défaut : dire que la date GPU est une publication, pas une approbation
        return esc(f"PLU — version publiée au Géoportail de l'urbanisme le {_fr_dates(gpu)} "
                   "(document opposable).")
    # EXPORTS-FIX-1 A7 — repli : dates ISO servies → JJ/MM/AAAA.
    return esc(_fr_dates(v.get("libelle") or ""))


def _r_scot(v):
    # EXPORTS-FIX-1 A6/A7 — la valeur ne répète pas le libellé « SCOT » de la ligne (« SCOT SCOT
    # TCO »), et sa date d'approbation s'imprime JJ/MM/AAAA.
    s = _fr_dates(v if isinstance(v, str) else (v.get("libelle") if isinstance(v, dict) else str(v)))
    s = _re.sub(r"^\s*SCOT\s+", "", s)
    return esc(s)


def _r_usage_sol(v):
    # EXPORTS-FIX-1 A4 — code d'usage OCS GE → libellé français (nomenclature IGN).
    return esc(_ocs_ge_libelle(v))


def _r_gabarit_motif(v):
    # EXPORTS-FIX-1 A8 — motif interne « PLU non calibré pour la zone A (estimation générique) »
    # dit en clair, sans jargon de calibration.
    s = str(v or "")
    m = _re.match(r"PLU non calibré pour la zone (\S+)", s)
    if m:
        return esc(f"Règles de la zone {m.group(1)} non détaillées dans LABUSE — gabarit non chiffré ici.")
    return esc(s)


def _r_aleas(v, val: Valeur):
    rows = []
    for a in v:
        nat = esc(_nature_alea(a.get("nature") or "Aléa"))   # EXPORTS-FIX-1 A4 — jamais « mouvement_terrain »
        lib = esc(a.get("libelle") or "")
        niv = a.get("niveau")
        if niv:
            lib += esc(f" — aléa de niveau {niv}") if "niveau" not in (a.get("libelle") or "") else ""
        # RETOUCHES-1 point 7 — le MILLÉSIME de la source (data_sources.source_millesime, déjà composé
        # par servitudes.aleas_parcelle) s'imprime sur la ligne, comme le veut la relecture du Dossier.
        mill = a.get("millesime")
        if mill:
            lib += esc(f" · millésime {mill}")
        rows.append(f'<tr data-quoi="aleas_parcelle_liste"><td class="k">{nat}</td>'
                    f'<td>{lib}</td><td class="n">{chip(val)}</td></tr>')
    return '<table class="kv">' + "".join(rows) + "</table>"


def _r_sols(v):
    bits = []
    if v.get("sis") or v.get("sis_classe"):
        bits.append(f"SIS : {v.get('sis') or v.get('sis_classe')}")
    if v.get("casias") or v.get("casias_statut"):
        bits.append(f"CASIAS : {v.get('casias') or v.get('casias_statut')}")
    return esc(" · ".join(bits))


def _r_viab(v):
    # EXPORTS-FIX-1 A8 / BIS point 11 — la viabilisation est un score (étiqueté « estimé ») : le mot
    # suit l'étiquette → « probable », jamais « confirmée ».
    lib = ((v.get("libelle") or v.get("verdict") or "")
           .replace(" confirmée par les faits", " probable").replace(" confirmée", " probable"))
    ind = v.get("indices") or []
    if ind:
        lib += " — indices : " + " · ".join(str(i) for i in ind[:4])
    return esc(lib)


def _r_proximites(v):
    bits = []
    a = v.get("arret")
    if isinstance(a, dict) and a.get("distance_m") is not None:
        res = f" ({a['reseau']})" if a.get("reseau") else ""
        bits.append(f"Arrêt {a.get('nom', '')}{res} à {groupe(a['distance_m'])} m")
    p = v.get("pole")
    if isinstance(p, dict) and p.get("distance_m") is not None:
        bits.append(f"{p.get('nom', 'Pôle')} à {groupe(p['distance_m'])} m")
    ax = v.get("axe")
    if isinstance(ax, dict) and ax.get("distance_m") is not None:
        bits.append(f"{ax.get('nom', 'Axe')} à {groupe(ax['distance_m'])} m")
    return esc(" · ".join(bits))


def _r_tcsp(v):
    d = v.get("distance_m")
    lib = "Station de transport en site propre"
    if d is not None:
        lib += f" à {groupe(d)} m"
    # EXPORTS-FIX-1 B8 — le seuil L151-36 est 800 m : au-delà, on le DIT (« hors rayon »), jamais
    # « stationnement allégé » ; la distance imprimée est bien celle du test (à vol d'oiseau).
    if v.get("sous_800m"):
        lib += " — stationnement allégé possible (L151-36, < 800 m)"
    elif d is not None:
        lib += " — hors rayon de 800 m (pas d'allègement L151-36)"
    return esc(lib)


def _r_anc(v):
    return esc(v.get("phrase") or v.get("libelle") or "")


def _r_fibre(v):
    e = v.get("etat")
    return esc({"servi": "Immeuble raccordable (Arcep)"}.get(e, v.get("libelle") or str(e)))


def _r_prix_ancien(v):
    lib = fmt_eur_m2(v["median"])
    n = v.get("n")
    typ = v.get("type_bien") or "ancien"
    if n:
        lib += f" — {typ}, {groupe(n)} ventes à moins de 500 m"
    return esc(lib)


def _r_vefa_prix(v):
    # EXPORTS-FIX-1 C5 — la médiane VEFA (neuf déclaré à l'acte) avec son effectif et sa fenêtre.
    if not isinstance(v, dict) or v.get("prix_m2") is None:
        return esc(v)
    det = fmt_eur_m2(v["prix_m2"]) + " — VEFA déclaré à l'acte"
    if v.get("n"):
        det += f", {groupe(v['n'])} ventes"
    det += f" (commune{', ' + str(v['fenetre_ans']) + ' ans' if v.get('fenetre_ans') else ''})"
    return esc(det)


def _r_terrain_nu(v):
    lib = fmt_eur_m2(v["prix_m2"])
    if v.get("n"):
        lib += f" — terrain nu, {groupe(v['n'])} ventes"
    return esc(lib)


def _r_n(v):
    return esc(groupe(v["n"])) if isinstance(v, dict) and v.get("n") is not None else esc(v)


def _r_permis_proximite(v):
    # EXPORTS-FIX-1 B7 — le compte de permis « à proximité » dit son rayon ET sa fenêtre (définition
    # client 500 m · 24 mois, arbitrage Q7 du 05/09), jamais un « 15 » nu.
    if not isinstance(v, dict) or v.get("n") is None:
        return _r_n(v)
    n, r, fen = v.get("n"), v.get("rayon_m"), v.get("fenetre_mois")
    suff = f" (< {groupe(r)} m, {fen} mois)" if r and fen else ""
    return esc(f"{groupe(n)} permis{suff}")


def _r_dvf_liste(v, val: Valeur, zone=None):
    from ..dvf_mediane import SEUIL_N     # EXPORTS-FIX-1 B6 — LE seuil d'échantillon déjà en place (5)
    agricole = str(zone or "").upper() in ("A", "N")
    rows = []
    for r in v[:6]:
        n = r.get("n_ventes")
        # EXPORTS-FIX-1 B6 — MÊME seuil pour tous les types (terrain, maison, appartement…) : sous 5
        # ventes, pas de médiane servie (l'appartement à 2 ventes est omis, comme le terrain nu l'était).
        if n is not None and n < SEUIL_N:
            continue
        typ = str(r.get("type_bien") or "")
        # RETOUCHES-1 point 4 — « autre » est le fourre-tout DVF (dépendances, locaux, biens mixtes) :
        # une médiane en PRIX TOTAL (pas de €/m², `mediane_prix_m2` absente), sans surface comparable
        # aux lignes maison/appartement/terrain. La fiche ne l'affiche jamais (marche.tsx ne rend que
        # terrain/maison/appartement) ; on le retire du Dossier pour la même raison — cohérence fiche == Dossier.
        if typ.lower() == "autre":
            continue
        tb = esc(typ.capitalize())
        px = fmt_eur_m2(r["mediane_prix_m2"]) if r.get("mediane_prix_m2") else \
            (fmt_eur(r["mediane_valeur"]) if r.get("mediane_valeur") else "")
        # EXPORTS-FIX-1 B6 — chaque prix dit son PÉRIMÈTRE (secteur cadastral) ET sa fenêtre.
        det = f"{px} — {groupe(n)} ventes" if n else px
        det += " · secteur cadastral" + (f", {r['fenetre']}" if r.get("fenetre") else "")
        # EXPORTS-FIX-1 C8 — en zone A/N, la médiane « Terrain » est un prix de terrain À BÂTIR :
        # on le DIT, elle ne vaut pas pour une parcelle agricole ou naturelle.
        if agricole and typ.lower() == "terrain":
            det += " — terrain à bâtir, ne vaut pas pour une parcelle agricole ou naturelle"
        rows.append(f'<tr data-quoi="dvf_parcelle_liste"><td class="k">{tb}</td>'
                    f'<td>{esc(det)}</td><td class="n">{chip(val)}</td></tr>')
    return ('<table class="kv">' + "".join(rows) + "</table>") if rows else ""


def _r_radar(v):
    n = len(v) if isinstance(v, list) else 0
    return f"{n} annonce{'s' if n > 1 else ''} active{'s' if n > 1 else ''} repérée{'s' if n > 1 else ''}" if n else ""


def _r_voisinage(v):
    bits = []
    if v.get("ventes_dvf") is not None:
        bits.append(f"{groupe(v['ventes_dvf'])} vente{'s' if v['ventes_dvf'] > 1 else ''} DVF")
    # EXPORTS-FIX-1 B6 — la médiane « à 100 m » mélange TOUS les types (terrain, maison, appart) sur
    # un très petit échantillon (« 15 000 € ») : trompeuse. On la retire (une médiane par type vit
    # déjà au §8, avec sa fenêtre) ; la ligne à 100 m ne garde que le compte de ventes et de permis.
    if v.get("permis") is not None:
        bits.append(f"{groupe(v['permis'])} permis")
    r, fen = v.get("rayon_m"), v.get("fenetre_mois")
    suff = f" (< {r} m, {fen} mois)" if r and fen else ""
    return esc(" · ".join(bits) + suff)


def _r_iris(v, val: Valeur):
    # COHERENCE-FIX-1 (lot D) — ménages absents → la mention SAUTE (jamais « 0 ménages »).
    t = tuiles([(groupe(v["habitants"]),
                 "habitants" + (f", {groupe(v['menages'])} ménages" if v.get("menages") is not None else "")),
                (fmt_pct(v["part_60_plus_pct"]), "de 60 ans et plus")
                if v.get("part_60_plus_pct") is not None else ("", ""),
                (fmt_pct(v["part_locataires_pct"]), "de locataires")
                if v.get("part_locataires_pct") is not None else ("", "")])
    lignes = ""
    if v.get("logements") is not None:
        det = f"{groupe(v['logements'])} logements"
        if v.get("vacance_pct") is not None:
            det += f", {fmt_pct(v['vacance_pct'])} de vacance"
        lignes = (f'<table class="kv"><tr data-quoi="iris_quartier">'
                  f'<td class="k">Parc de logements du quartier</td><td>{esc(det)}</td>'
                  f'<td class="n">{chip(val)}</td></tr></table>')
    return f'<div data-quoi="iris_quartier">{t}</div>' + lignes


#: EXPORTS-FIX-1 D4/E7 — libellé client de la famille d'équipement (« Bus » → « Arrêt de bus »).
_CAT_EQUIP = {"Bus": "Arrêt de bus"}


def _r_equipements(v):
    # EXPORTS-FIX-1 D4 — MÊMES données que la fiche (Étude de zone) : le plus proche de chaque famille
    # avec son NOM et sa distance, jamais un compte « 1 école, 1 commerce » identique d'une parcelle à
    # l'autre (P1 et P2 avaient le même « 1 … » alors que les équipements diffèrent).
    bits = []
    for it in (v or []):
        if not isinstance(it, dict):
            continue
        cat = _CAT_EQUIP.get(it.get("cat") or "", it.get("cat") or "")
        nom = it.get("nom")
        d = it.get("distance_m")
        s = cat + (f" : {nom}" if nom else "") + (f" ({groupe(d)} m)" if d is not None else "")
        if s:
            bits.append(s)
    return esc(" · ".join(bits))


def _r_potentiel(v):
    # ZONE-1 — sous une CAUSE (zone non constructible…), le libellé brut de sous-densité ne
    # s'imprime JAMAIS (faux constructible) : le bandeau verdict_potentiel dit déjà la cause.
    if v.get("cause"):
        return ""
    niv = v.get("libelle") or v.get("niveau") or ""
    return esc(niv)


def _r_dpe(v):
    et, an = v.get("etiquette"), v.get("annee")
    return esc(f"DPE {et}" + (f" ({an})" if an else "")) if et else esc(v.get("libelle") or "")


def _r_rnb(v):
    n = len(v) if isinstance(v, list) else 0
    return f"{n} identifiant{'s' if n > 1 else ''} RNB" if n else ""


def _r_tfpb(v):
    # RETOUCHES-1 point 2 — MÊME ligne que la fiche et le Copilote : « part communale X % · hors part
    # départementale, TEOM et taxes spéciales ». Producteur unique (fiscalite_libelle). On n'énumère
    # plus « EPCI 0,00 % · TEOM 16,00 % » (le lecteur croyait lire la taxe entière). L'intitulé de la
    # ligne devient « Taxe foncière (bâti) » (sections_restantes.yaml).
    from ..fiscalite_libelle import lignes_taxe_fonciere
    lignes = lignes_taxe_fonciere(v)
    return esc(lignes[0]["detail"]) if lignes else ""


def _r_taxe(v):
    taux = v.get("taux_communal_pct")
    if taux is None:
        return ""
    lib = f"Taux communal {fmt_pct(taux)}"
    if v.get("taux_communal_millesime"):
        lib += f" — {v['taux_communal_millesime']}"
    lib += (". Se calcule sur la surface de plancher créée par le projet — "
            "montant chiffré dans le document Financier.")   # EXPORTS-FIX-1 A8
    return esc(lib)


def _r_territoire(v, val: Valeur):
    rows = []

    def _row(cle, lib):
        # EXPORTS-FIX-1 A7 — les dates de ces libellés (ORT « signée le … ») s'impriment JJ/MM/AAAA.
        rows.append(f'<tr data-quoi="perimetres_dispositifs_liste"><td class="k">{esc(cle)}</td>'
                    f'<td>{esc(_fr_dates(lib))}</td><td class="n">{chip(val)}</td></tr>')

    def _cle_dom(dom: dict, i: int) -> str:
        # EXPORTS-FIX-1 A9 — chaque dispositif de commune est NOMMÉ (jamais « Dispositif de commune »).
        lib = (dom.get("libelle") or "").lower()
        if i == 0:
            return "Zonage du logement"
        if "tva" in lib:
            return "TVA outre-mer"
        if "revitalisation" in lib or "ort" in lib:
            return "Opération de revitalisation (ORT)"
        if "action cœur de ville" in lib or "acv" in lib:
            return "Action Cœur de Ville (ACV)"
        if "petites villes" in lib:
            return "Petites Villes de Demain (PVD)"
        return "Dispositif de commune"
    # KELFONCIER-FIX-1 (Lot F) — le Dossier miroir rend TOUS les dispositifs de commune (zonage A/B/C,
    # TVA DOM, et Petites Villes de Demain/ACV/ORT), plus seulement le premier.
    for i, dom in enumerate(v.get("dispositifs_dom") or []):
        if dom.get("libelle"):
            _row(_cle_dom(dom, i), dom["libelle"])
    if (v.get("zfang") or {}).get("libelle"):
        _row("ZFANG", v["zfang"]["libelle"])
    if (v.get("frr") or {}).get("libelle"):
        _row("FRR (ex-ZRR)", _frr_libelle(v["frr"]))
    for per in _perimetres_hors_piscine(v):   # EXPORTS-FIX-1 B2 — la piscine sort du §7 (elle est au §2)
        if per.get("libelle"):
            # EXPORTS-FIX-1 A9 — la bande QPV est nommée, jamais « Périmètre » nu.
            lib = (per.get("libelle") or "").lower()
            cle = per.get("cle") or per.get("type")
            if not cle:
                if "quartier prioritaire" in lib or "qpv" in lib:
                    cle = "Quartier prioritaire (QPV)"
                elif "npnru" in lib or "renouvellement urbain" in lib:
                    cle = "Renouvellement urbain (NPNRU)"
                else:
                    cle = "Périmètre"
            _row(cle, per["libelle"])
    return '<table class="kv">' + "".join(rows) + "</table>" if rows else ""


def _r_rang(v):
    if v.get("total"):
        return esc(f"{groupe(v['rang'])} sur {groupe(v['total'])}")
    return esc(groupe(v["rang"]))


def _r_filiation(v):
    # RETOUCHES-1 point 5 — on rend la filiation ELLE-MÊME (parcelles mères « Issue de » / filles
    # « A donné », avec date et nature), comme la fiche (FiliationBlock, FICHE-FIX-4), au lieu de
    # l'annonce vide « Filiation cadastrale disponible ». `v` = passe-plat de dfi.filiation_parcelle().
    if isinstance(v, list):   # compat d'un ancien format (liste d'événements)
        return esc(f"{len(v)} événement{'s' if len(v) > 1 else ''} cadastral(aux) (DFI)")
    if not isinstance(v, dict):
        return ""

    def _un(r):
        det = r.get("code_amont") or r.get("nature")
        qual = ", ".join(x for x in (det, r.get("date")) if x)
        return (r.get("idu") or "") + (f" ({qual})" if qual else "")

    bits = []
    if v.get("meres"):
        bits.append("Issue de " + " · ".join(_un(m) for m in v["meres"][:6]))
    if v.get("filles"):
        bits.append("A donné " + " · ".join(_un(x) for x in v["filles"][:6]))
    # aucune mère ni fille exploitable → "" : la ligne bascule en « Non disponible ici » (absence déclarée).
    return esc(_fr_dates(" — ".join(bits)))


#: id → rendeur. `bloc` = fragment pleine largeur (tableau propre) ; sinon cellule valeur.
_RENDEURS: dict[str, Any] = {
    "prix_achat_historique_eur": _r_prix_achat, "coproprietes_liste": _r_copros,
    "proprietaire_timeline_liste": _r_timeline, "historique_permis_liste": _r_permis_liste,
    "er_emplacement_reserve": _r_er_ebc, "ebc_classe": _r_er_ebc, "dpu_perimetre": _r_dpu,
    "peb_zone": _r_peb, "dispositifs_parcelle": _r_sup, "statut_plu": _r_statut_plu,
    "sols_parcelle": _r_sols, "viabilisation_verdict": _r_viab, "distance_arret_m": _r_proximites,
    "tcsp_stationnement_allege": _r_tcsp, "part_logements_egout_pct": _r_anc,
    "fibre_parcelle": _r_fibre, "prix_sortie_bati_eur_m2": _r_prix_ancien,
    "prix_neuf_vefa_acte_eur_m2": _r_vefa_prix,   # EXPORTS-FIX-1 C5
    "prix_terrain_secteur_eur_m2": _r_terrain_nu, "ventes_retenues_n": _r_n,
    "ventes_ecartees_n": _r_n, "n_permis_proximite": _r_permis_proximite, "radar_annonces_liste": _r_radar,
    "ventes_100m_n": _r_voisinage, "voisinage_100m_liste": _r_voisinage,
    "equipements_proximite_liste": _r_equipements, "potentiel_verdict": _r_potentiel,
    "dpe_connu": _r_dpe, "rnb_batiments_liste": _r_rnb, "tfpb_taux_pct": _r_tfpb,
    "taxe_amenagement_estimee_eur": _r_taxe, "rang_tier": _r_rang,
    "filiation_parcelle": _r_filiation,
    # EXPORTS-FIX-1 A4/A6/A7/A8/B3
    "scot_parcelle": _r_scot, "usage_sol_dominant": _r_usage_sol,
    "gabarit_motif_blocage": _r_gabarit_motif,
    # EXPORTS-FIX-1-BIS point 6 — n_vigilances est rendu spécialement (nombre d'aléas imprimés),
    # plus de rendeur « couches … cascade ».
}
def _r_gabarit_plan(brute, val=None):
    """Le plan 2D du gabarit (SVG) — fragment pleine largeur, figure de la ligne « zone
    d'implantation ». `brute` est le SVG déjà sûr (généré serveur, mêmes couleurs que l'écran)."""
    svg = brute if isinstance(brute, str) else ""
    return (f'<div class="gabarit-plan" data-quoi="gabarit_plan_2d" '
            f'style="margin:6px 0;text-align:center">{svg}</div>')


_RENDEURS_BLOC: dict[str, Any] = {
    "aleas_parcelle_liste": _r_aleas, "dvf_parcelle_liste": _r_dvf_liste,
    "iris_quartier": _r_iris, "perimetres_dispositifs_liste": _r_territoire,
    "gabarit_plan_2d": _r_gabarit_plan,
}
#: EXPORTS-FIX-1 A8 — intitulés de groupe internes, masqués au rendu (lignes conservées).
_GROUPES_MASQUES = {"Bilan indicatif"}

#: le règlement PLU (extraits) garde son rendu de bloc historique (blocs/zonage._regles) — réutilisé.
#: `simulation` : lignes remplacées par l'encart de renvoi (lot 2) — dit dans le rendu.
_IGNORES_SIMULATION = True


def _valeur_html(cid: str, l, brute, val: Valeur) -> str:
    r = _RENDEURS.get(cid)
    if r is not None:
        return r(brute)
    return _fmt_scalaire((l.comment or {}).get("format"), brute)


# ── le rendu ─────────────────────────────────────────────────────────────────────────────────

def _pied_noms(vals: list[Valeur]) -> str:
    """Le pied de section : les NOMS des sources lues — aucun millésime, aucune date
    (doctrine PAGE-SOURCES-1 du 18/09)."""
    noms = [nom for nom, _mill in sources_lues(vals)]
    return note("Sources : " + " · ".join(noms)) if noms else ""


#: EXPORTS-FIX-1 B9 — l'étiquette de nature d'un fait, corrigée au rendu (présentation, jamais la
#: valeur du registre) : un même fait porte la MÊME étiquette partout.
#:  · sol libre = une soustraction (parcelle − bâti − …) → dérivé (et non sourcé) ;
#:  · viabilisation = un faisceau d'indices (un score) → jamais sourcé → estimé ;
#:  · taxe d'aménagement (taux) = lue au barème public DELTA → sourcé (la ligne n'existe que si lu).
_IDS_DERIVE = {"surface_libre_sol_m2"}
_IDS_ESTIME = {"viabilisation_verdict"}
_IDS_SOURCE = {"taxe_amenagement_estimee_eur"}


def _chip_fixe(nat: str) -> str:
    from .nature import CLASSE, LIBELLE
    return f'<span class="chip {CLASSE[nat]}">{LIBELLE[nat]}</span>'


def _chip_de(quoi: str, v: Valeur) -> str:
    if quoi in _IDS_DERIVE:
        return chip(v, derive=True)
    if quoi in _IDS_ESTIME:
        return _chip_fixe("estime")
    if quoi in _IDS_SOURCE:
        return _chip_fixe("source")
    # EXPORTS-FIX-1 B9 — « emprise non réglementé » : MÊME étiquette qu'au §4 (blocs/zonage._chip_regle
    # rend « estimé » pour une absence de règle non référencée). Un plafond chiffré reste sourcé.
    if quoi == "gabarit_emprise_plafond_m2" and str(v.valeur).strip().lower().startswith("non"):
        return _chip_fixe("estime")
    return chip(v)


def _ligne_tr(cid: str, cle: str, valeur_html: str, chip_html: str) -> str:
    return (f'<tr data-quoi="{esc(cid)}"><td class="k">{esc(cle)}</td><td>{valeur_html}</td>'
            f'<td class="n">{chip_html}</td></tr>')


#: valeur COURTE d'une tuile pour les ids structurés de l'en-tête (jamais un dict imprimé).
_TUILE_FMT = {
    "tfpb_taux_pct": lambda v: fmt_pct(v["tfpb_commune_pct"], 2) if isinstance(v, dict) else fmt_pct(v, 2),
    "rang_tier": lambda v: f"{groupe(v['rang'])} / {groupe(v['total'])}" if v.get("total") else groupe(v["rang"]),
}


def _entete_tuiles(sec: dict, valeurs: dict[str, Valeur]) -> str:
    items, quois = [], []
    for s, l in sec["lignes"]:
        v = valeurs.get(l.quoi)
        if v is None:
            continue
        f = _TUILE_FMT.get(l.quoi)
        if f is not None:
            try:
                court = f(v.valeur)
            except (KeyError, TypeError, ValueError):
                continue
        elif isinstance(v.valeur, (dict, list)):
            continue                                # pas de forme courte : la tuile n'invente pas
        else:
            court = _fmt_scalaire((l.comment or {}).get("format"), v.valeur)
        items.append((court, (l.comment or {}).get("libelle") or l.quoi))
        quois.append(l.quoi)
    if not items:
        return ""
    cells = "".join(f'<div class="tile" data-quoi="{esc(q)}"><div class="v">{v}</div>'
                    f'<div class="l">{esc(lb)}</div></div>' for q, (v, lb) in zip(quois, items))
    return f'<div class="tiles">{cells}</div>'


def _v(valeurs, cid):
    x = valeurs.get(cid)
    return x.valeur if x else None


def _verdict_factuel(sec_id: str, valeurs: dict[str, Valeur]) -> tuple[str, str, str] | None:
    """EXPORTS-REBRANCHEMENT-2 lot 1 — le verdict-phrase FACTUEL des sections « gris » (le maquette
    v4 en veut un en tête de CHAQUE section). Assemblé DÉTERMINISTIQUEMENT de valeurs servies —
    jamais une prose inventée : chaque nombre est ancré au registre (crible de provenance). Rend
    (texte, ton, chiffre_id_tampon) ou None si rien de servi (pas de bandeau vide)."""
    if sec_id == "identite":
        pm = _v(valeurs, "type_proprietaire")
        tl = _v(valeurs, "proprietaire_timeline_liste")
        if not pm:
            return None
        bout = ""
        if isinstance(tl, list) and tl:
            ans = [str(x.get("millesime")) for x in tl if x.get("millesime")]
            if ans:
                # EXPORTS-FIX-1 A8 — « au fichier 2019–2025 » (interne) → « propriétaire depuis au moins … ».
                bout = f" — propriétaire depuis au moins {ans[0]}"
        return (esc(str(pm).split(" (SIREN")[0]) + esc(bout) + ".", "neutral", "type_proprietaire")
    if sec_id == "terrain":
        p = _v(valeurs, "pente_deg")
        libre = _v(valeurs, "surface_libre_sol_m2")
        bits = []
        if p is not None:
            bits.append(f"pente {str(p).replace('.', ',')}°")
        if libre is not None:
            bits.append(f"{fmt_m2(libre)} de sol libre")
        return (esc(" · ".join(bits).capitalize()) + ".", "neutral", "pente_deg") if bits else None
    if sec_id == "bati":
        n = _v(valeurs, "n_batiments")
        emp = _v(valeurs, "emprise_batie_m2")
        if not n:
            return ("Parcelle non bâtie (aucun bâtiment cartographié).", "neutral", "n_batiments")
        t = f"{groupe(n)} bâtiment{'s' if n > 1 else ''}"
        if emp is not None:
            t += f", {fmt_m2(emp)} au sol"
        return (esc(t) + ".", "neutral", "n_batiments")
    if sec_id == "fiscalite":
        tf = _v(valeurs, "perimetres_dispositifs_liste")
        if isinstance(tf, dict):
            _doms = tf.get("dispositifs_dom") or [{}]
            dom = _doms[0]
            z = dom.get("libelle") or ""
            # KELFONCIER-FIX-1 (Lot F) — le résumé compte AUSSI les dispositifs de commune au-delà du
            # zonage (TVA DOM, Petites Villes de Demain/ACV/ORT), plus seulement zfang/frr/périmètres.
            # EXPORTS-FIX-1 B2 — la piscine n'est pas un dispositif : hors du compte des dispositifs.
            n_disp = sum(1 for k in ("zfang", "frr") if (tf.get(k) or {}).get("libelle")) \
                + len(_perimetres_hors_piscine(tf)) + max(0, len(_doms) - 1)
            t = esc(z) if z else "Régime fiscal de droit commun"
            if n_disp:
                t += f" · {n_disp} dispositif{'s' if n_disp > 1 else ''} territ{'oriaux' if n_disp > 1 else 'orial'}"
            return (t + ".", "neutral", "perimetres_dispositifs_liste")
        return None
    if sec_id == "marche":
        pa = _v(valeurs, "prix_sortie_bati_eur_m2")
        if isinstance(pa, dict) and pa.get("median") is not None:
            t = f"Prix ancien médian {fmt_eur_m2(pa['median'])}"
            if pa.get("n"):
                t += f" ({groupe(pa['n'])} ventes à moins de 500 m)"
            return (esc(t) + ".", "neutral", "prix_sortie_bati_eur_m2")
        return None
    if sec_id == "quartier":
        iq = _v(valeurs, "iris_quartier")
        if isinstance(iq, dict) and iq.get("habitants") is not None:
            nom = iq.get("nom") or "le quartier IRIS"
            # COHERENCE-FIX-1 (lot E) — le millésime du recensement accompagne le chiffre (« vrai
            # hier, faux aujourd'hui, sans date pour le dire » — plus jamais).
            mil = f" ({iq['millesime']})" if iq.get("millesime") else ""
            return (esc(f"{nom} — {groupe(iq['habitants'])} habitants{mil}") + ".", "neutral", "iris_quartier")
        return None
    return None


def _bandeau(sec_id: str, valeurs: dict[str, Valeur]) -> str:
    """Le verdict-phrase de tête de section. Moteurs réels quand ils existent (urbanisme, potentiel,
    réseaux, risques) ; sinon une synthèse FACTUELLE déterministe (identité, terrain, bâti, fiscalité,
    marché, quartier). Rien pour §10 si la fiche ne sert pas de potentiel (pas de bandeau vide)."""
    if sec_id == "urbanisme":
        v = verdict_zonage(valeurs)
        return f'<div data-quoi="zone_plu_famille">{rendu_verdict(v)}</div>' if v else ""
    if sec_id == "potentiel":
        v = verdict_potentiel(valeurs)
        return f'<div data-quoi="potentiel_verdict">{rendu_verdict(v)}</div>' if v else ""
    if sec_id == "reseaux":
        v = verdict_reseaux(valeurs)
        return f'<div data-quoi="viabilisation_verdict">{rendu_verdict(v)}</div>' if v else ""
    if sec_id == "risques":
        av = valeurs.get("aleas_parcelle_liste")
        rouges = [a for a in ((av.valeur if av else None) or [])
                  if isinstance(a, dict) and a.get("redhibitoire")]
        if rouges:
            return (f'<div data-quoi="aleas_parcelle_liste">'
                    f'{verdict(esc(rouges[0].get("libelle") or ""), ton="warn")}</div>')
        if av is not None:
            return f'<div data-quoi="aleas_parcelle_liste">{verdict("Aléas relevés — aucun rédhibitoire.", ton="neutral")}</div>'
        return ""
    fx = _verdict_factuel(sec_id, valeurs)
    if fx:
        texte, ton, cid = fx
        return f'<div data-quoi="{esc(cid)}">{verdict(texte, ton=ton)}</div>'
    return ""


def _renvoi_financier() -> str:
    return aside(
        '<div class="t">Renseignez votre opération pour obtenir le bilan</div>'
        "<p>Le bilan dépend de chiffres que vous seul connaissez : prix demandé par le vendeur, "
        "coût de construction, marge visée. LABUSE ne les suppose pas à votre place. "
        "Le document <strong>Financier</strong> les recueille et imprime le chiffre d'affaires, "
        "la charge foncière supportable, l'écart au prix demandé et la sensibilité au coût de "
        "construction.</p>", variante="projet")


def _bloc_reglement(valeurs: dict[str, Valeur]) -> str:
    """Les extraits du règlement (règles calibrées + destinations + drapeau Q12 + renvoi GPU) —
    le rendu historique du bloc zonage, réutilisé tel quel (mêmes gardes de mots interdits)."""
    from .blocs.zonage import _destinations, _regles
    v = valeurs.get("reglement_plu_bloc")
    z = (v.valeur if v else None) or {}
    corps = _regles(z) + _destinations(z)
    if isinstance(z, dict) and z.get("_prescriptions_verifiables") is False:
        motif = z.get("_prescriptions_motif") or "aucun document de prescriptions publié pour cette commune"
        corps += aside(f"<strong>Prescriptions non vérifiables sur cette commune</strong> — {esc(motif)}. "
                       "Un emplacement réservé ou une servitude peut exister sans être publié : "
                       "à vérifier en mairie.", "rose")
    if z.get("idurba"):
        corps += note(f"Règlement complet : {z['idurba']} sur le Géoportail de l'urbanisme. "
                      "Les valeurs ci-dessus sont une aide à la lecture ; le règlement fait foi.")
    return corps


#: EXPORTS-REBRANCHEMENT-2 lot 1 — les SIX chiffres du bandeau de garde (maquette v4), dans
#: l'ordre : Surface · Zone · Pente · Exposition · Risques · SDP restante. Le SCORE n'y est pas.
_COVER_TUILES = [
    ("surface_parcelle_m2", "Surface", lambda v: fmt_m2(v)),
    ("zone_plu_famille", "Zone", lambda v: esc(v)),
    ("pente_deg", "Pente", lambda v: esc(f"{str(v).replace('.', ',')}°")),
    ("exposition_versant", "Exposition", lambda v: esc(v)),
    ("n_vigilances", "Risques", lambda v: esc(f"{groupe(v)} relevé{'s' if v and v > 1 else ''}")),
    ("sdp_residuelle_m2", "SDP restante", lambda v: fmt_m2(v)),
]


def cover_dossier(idu: str, fiche: dict, numero: str, jour, valeurs: dict[str, Valeur],
                  modele: str) -> str:
    """La page de garde du Dossier (maquette v4) : cartouche 4 champs + bandeau des SIX chiffres
    de la fiche en 3 colonnes + sommaire des sections + légende. Chaque tuile porte data-quoi
    (verrou V5d) ; une valeur absente s'affiche « — » (jamais un zéro inventé)."""
    adresse = fiche.get("adresse") or ""
    commune = fiche.get("commune") or ""
    tuiles_html = []
    _zone = valeurs.get("zone_plu_famille")
    _zone_v = str(_zone.valeur).upper() if _zone is not None and _zone.valeur is not None else ""
    # EXPORTS-FIX-1 F2 — le CODE COMPLET de zone (« U5b »), comme au §4, jamais la famille tronquée « U ».
    _reg = valeurs.get("reglement_plu_bloc")
    _zone_code = (_reg.valeur.get("zone") if _reg is not None and isinstance(_reg.valeur, dict) else None)
    for cid, lib, fmt in _COVER_TUILES:
        v = valeurs.get(cid)
        try:
            aff = fmt(v.valeur) if v is not None and v.valeur is not None else None
        except (TypeError, ValueError, KeyError):
            aff = None
        if cid == "zone_plu_famille" and _zone_code:
            aff = esc(_zone_code)
        # EXPORTS-FIX-1-BIS point 6 — la tuile « Risques » compte les aléas IMPRIMÉS au §5 (le même
        # chiffre que le §5), pas n_vigilances (couches internes).
        if cid == "n_vigilances":
            _na = _n_aleas(valeurs)
            aff = esc(f"{groupe(_na)} relevé{'s' if _na and _na > 1 else ''}") if _na is not None else None
        # EXPORTS-FIX-1 C7 — SDP en zone A/N : « 0 m² — zone A » (arbitrage Q6), jamais « — ».
        if aff is None and cid == "sdp_residuelle_m2" and _zone_v in ("A", "N"):
            aff = f'0 m² — zone {esc(_zone_v)}'
        # EXPORTS-FIX-1 C7 — aucun champ vide imprimé : une tuile sans valeur est OMISE (pas de « — »).
        if aff is None:
            continue
        tuiles_html.append(f'<div class="tile" data-quoi="{esc(cid)}"><div class="v">{aff}</div>'
                           f'<div class="l">{esc(lib)}</div></div>')
    toc = []
    n = 0
    for sec in structure():
        if sec["id"] == "entete":
            continue
        n += 1
        # EXPORTS-FIX-1 A3 — plus de clé technique (« fiche identite ») en colonne droite du sommaire.
        toc.append(f'<li>{n}. {esc(sec["titre"])}</li>')
    toc.append(f'<li>{n + 1}. Limites et sources</li>')
    legende = (
        '<div class="legend">'
        '<span class="chip s">sourcé</span> lu dans la source · '
        '<span class="chip d">dérivé</span> calculé · '
        '<span class="chip e">estimé</span> hypothèse dite · '
        '<span class="chip p">projet</span> saisi par vous</div>')
    return (
        '<div class="cover">'
        '<div class="kicker">Dossier parcelle</div>'
        # EXPORTS-FIX-1 F4 — l'IDU en police MONO (chiffre 0 pointé, distinct du O), jamais en
        # SpaceGrotesk où « EO0796 » se lit « E00796 ».
        f'<h1 class="idu-code">{esc(idu)}</h1>'
        + (f'<p class="address">{esc_noms(adresse)}</p>' if adresse else "")
        + f'<p class="idu">{esc(commune)}</p>'
        '<div class="gm-meta">'
        f'<div><b>{esc(numero)}</b>n° de rapport</div>'
        f'<div><b>{jour:%d/%m/%Y}</b>généré le</div>'
        f'<div><b>{fmt_m2(valeurs["surface_parcelle_m2"].valeur) if valeurs.get("surface_parcelle_m2") else "—"}</b>contenance</div>'
        # EXPORTS-FIX-1 A2 — plus de « Modèle 3.0 · miroir de la fiche » en page de garde.
        '</div>'
        f'<div class="cover-tiles">{"".join(tuiles_html)}</div>'
        # EXPORTS-FIX-1 A2 — plus de « Le bandeau des six chiffres de la fiche. »
        f'<ul class="toc">{"".join(toc)}</ul>'
        + legende +
        '</div>')


def rendu_sections(valeurs: dict[str, Valeur], fiche: dict, *, plan_html: str = "") -> str:
    """Le corps du Dossier : les 11 sections de la fiche, depuis les déclarations. L'en-tête de
    tuiles vit désormais dans la page de garde (cover_dossier) ; la clôture §12 (limites + sources)
    est ajoutée ici. `plan_html` : le plan de situation injecté en §1 (même composant que l'Apporteur)."""
    corps = []
    numero = 0
    for sec in structure():
        if sec["id"] == "entete":
            continue                                   # rendu dans la page de garde (cover_dossier)
        numero += 1
        titre = f"{numero}. {sec['titre']}" if sec.get("numerote", True) else sec["titre"]
        if sec["id"] == "simulation":
            corps.append(section(titre, _renvoi_financier()))
            continue
        frags: list[str] = []
        frags.append(_bandeau(sec["id"], valeurs))
        blocs_pleins: list[str] = []
        groupes: dict[str, list[str]] = {}           # libellé de groupe → lignes kv (ordre 1re vue)
        absents: list[tuple[str, str]] = []          # (quoi, phrase d'absence déclarée)
        vals_lus: list[Valeur] = []
        from .robinet_fiche import EXTRACTEURS
        # EXPORTS-FIX-1 B2 — la piscine détectée (FLAIR ∪ CoSIA, confirmée sur l'orthophoto) est
        # servie côté fiche dans les périmètres ; au Dossier elle est UN ÉLÉMENT DU TERRAIN (§2),
        # jamais un dispositif fiscal. On la présente ici quand la mesure BD ORTHO (piscine_m2) manque.
        _pdl = valeurs.get("perimetres_dispositifs_liste")
        _pisc = _piscine_dispositif((_pdl.valeur if _pdl else {}) or {}) if _pdl else None
        for s, l in sec["lignes"]:
            # EXPORTS-FIX-1 B6 — la ligne « à 100 m » ne s'imprime qu'UNE fois, au §8 (ventes_100m_n) ;
            # le doublon du §9 (voisinage_100m_liste) est omis.
            if l.quoi == "voisinage_100m_liste":
                continue
            v = valeurs.get(l.quoi)
            if v is None:
                if l.quoi == "rtaa_exigences":
                    # EXPORTS-FIX-1-BIS point 4 — la RTAA DOM est une RÈGLE APPLICABLE (tout logement
                    # neuf), pas une absence : ligne normale du §4, hors de l'encadré « Vérifié : rien ».
                    _grp = l.section if (l.section and l.section != sec["titre"]) else ""
                    groupes.setdefault(_grp, []).append(_ligne_tr(
                        "rtaa_exigences", (l.comment or {}).get("libelle") or "Rappel RTAA DOM",
                        esc("Conception réglementée pour tout logement neuf (aération traversante, "
                            "protection solaire, eau chaude solaire) — à intégrer au projet."),
                        _chip_fixe("source")))
                    continue
                if l.quoi == "piscine_m2" and _pisc:
                    # la valeur ne répète pas le libellé « Piscine détectée » de la ligne (cf. A6).
                    _pv = _re.sub(r"^\s*Piscine détectée\s*[—-]\s*", "",
                                  _pisc.get("libelle") or "1 bassin")
                    val_txt = (esc(_pv) + " — détection FLAIR ∪ CoSIA (orthophoto 20 cm), "
                               "à confirmer sur place")
                    groupes.setdefault("", []).append(
                        _ligne_tr("piscine_m2", "Piscine détectée", val_txt, chip(_pdl, derive=True)))
                    continue
                # DONNEES-1 lot 2 — `masquer_si_absent` : la ligne disparaît, aucune phrase d'absence.
                # EXPORTS-FIX-1 C3 — `_ABSENCE_MASQUEE` : idem pour une absence qui affirmerait un
                # contrôle non tenu (SAR hors base).
                if (l.quoi in EXTRACTEURS and l.absence and not l.masquer_si_absent
                        and l.quoi not in _ABSENCE_MASQUEE):
                    absents.append((l.quoi, l.absence))
                continue                              # sans extracteur : omis (non_cables le compte)
            # EXPORTS-FIX-1-BIS point 11 — un gabarit NON CHIFFRÉ (motif de blocage servi) est un
            # non-calcul : il va dans « Non disponible ici » SANS étiquette, jamais une ligne « sourcé ».
            if l.quoi == "gabarit_motif_blocage":
                _s = str(v.valeur or "")
                _m = _re.match(r"PLU non calibré pour la zone (\S+)", _s)
                _ph = (f"Gabarit réglementaire : règles de la zone {_m.group(1)} non détaillées dans "
                       "LABUSE — non chiffré ici.") if _m else f"Gabarit réglementaire : {_s} — non chiffré ici."
                absents.append(("gabarit_motif_blocage", _ph))
                continue
            vals_lus.append(v)
            if l.quoi == "reglement_plu_bloc":
                blocs_pleins.append(f'<div data-quoi="reglement_plu_bloc">{_bloc_reglement(valeurs)}</div>')
                continue
            if l.quoi in _RENDEURS_BLOC:
                if l.quoi == "dvf_parcelle_liste":   # EXPORTS-FIX-1 C8 — caveat Terrain en zone A/N
                    blocs_pleins.append(_r_dvf_liste(v.valeur, v, zone=_v(valeurs, "zone_plu_famille")))
                else:
                    blocs_pleins.append(_RENDEURS_BLOC[l.quoi](v.valeur, v))
                continue
            if l.quoi == "n_vigilances":
                # EXPORTS-FIX-1-BIS point 6 — le compteur affiche le nombre d'aléas IMPRIMÉS au §5,
                # pas n_vigilances (couches internes) ; le mot « cascade » n'apparaît plus.
                na = _n_aleas(valeurs)
                html = esc(groupe(na)) if na is not None else ""
            else:
                html = _valeur_html(l.quoi, l, v.valeur, v)
            if not html:
                continue
            lib = (l.comment or {}).get("libelle") or l.quoi
            grp = l.section if (l.section and l.section != sec["titre"]) else ""
            groupes.setdefault(grp, []).append(_ligne_tr(l.quoi, lib, html, _chip_de(l.quoi, v)))  # B9
        # EXPORTS-FIX-1-BIS point 8 — §5 : ABF / ICPE / cavités, citées en source mais sans ligne,
        # impriment leur « vérifié : rien » quand la cascade les a lues (sinon elles ne sont pas
        # servies et ne figurent ni au pied ni au §12).
        if sec["id"] == "risques":
            absents += _lignes_verifie_rien(fiche)
        rows: list[str] = []
        for grp, lignes_grp in groupes.items():      # un en-tête de groupe UNE fois, jamais vide
            # EXPORTS-FIX-1 A8 — « Bilan indicatif » est un intitulé interne : ses lignes se rangent
            # dans la section sans cet en-tête (retiré, pas renommé — le libellé fiche fait foi).
            if grp and grp not in _GROUPES_MASQUES:
                rows.append(f'<tr class="grp"><td colspan="3"><strong>{esc(grp)}</strong></td></tr>')
            rows += lignes_grp
        if rows:
            frags.append('<table class="kv">' + "".join(rows) + "</table>")
        frags += blocs_pleins
        # §1 — le plan de situation (ortho IGN, contour, voisines du même propriétaire), le MÊME
        # composant que l'Apporteur, injecté par le builder (qui a la base).
        if sec["id"] == "identite" and plan_html:
            frags.append(plan_html)
        if absents:
            # EXPORTS-FIX-1 C6 — deux encadrés distincts : « Vérifié : rien » (contrôle tenu, rien
            # trouvé) et « Non disponible ici » (donnée non calculée/déterminée), avec LA raison —
            # jamais « A ou B » (résolu selon la zone).
            _zone = _v(valeurs, "zone_plu_famille")
            _gab_bloque = valeurs.get("gabarit_motif_blocage") is not None
            # EXPORTS-FIX-1-BIS point 2 — quand une SDP RÉSIDUELLE est servie (droits à bâtir non
            # consommés), aucune ligne ne doit la contredire : on retire « surface de plancher non
            # calculable (capacité nulle) » et on dit la vraie raison de la capacité (pas « capacité nulle »).
            _sdp = _v(valeurs, "sdp_residuelle_m2")
            _has_sdp = isinstance(_sdp, (int, float)) and not isinstance(_sdp, bool) and _sdp > 0
            verifie: list[str] = []
            nondispo: list[str] = []
            for q, ph in absents:
                if _has_sdp and q == "surface_plancher_m2":
                    continue
                if _has_sdp and q == "capacite_logements":
                    ph = ("Capacité en logements : non chiffrée ici — le potentiel relève des droits "
                          "à bâtir résiduels (la SDP ci-dessus), pas un programme de logements.")
                phc = _absence_une_raison(_absence_clair(q, ph), _zone, gabarit_bloque=_gab_bloque)
                li = f'<li data-quoi="{esc(q)}">{esc(phc)}</li>'
                (nondispo if _est_non_dispo(phc) else verifie).append(li)
            if verifie:
                frags.append('<div class="sansobjet"><div class="t">Vérifié : rien</div>'
                             f'<ul>{"".join(verifie)}</ul></div>')
            if nondispo:
                frags.append('<div class="sansobjet"><div class="t">Non disponible ici</div>'
                             f'<ul>{"".join(nondispo)}</ul></div>')
        if vals_lus:
            frags.append(_pied_noms(vals_lus))
        corps.append(section(titre, "".join(x for x in frags if x)))
    # §12 — ce que ce document ne peut pas dire + les NOMS des sources (bloc dédié, sans millésime).
    from .blocs import sources as bloc_sources
    corps.append(section(f"{numero + 1}. Limites et sources", bloc_sources.corps_sources(valeurs)))
    return "".join(corps)
