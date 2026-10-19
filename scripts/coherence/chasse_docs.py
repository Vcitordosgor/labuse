#!/usr/bin/env python3
"""CHASSE-DOCS-1 — banc rejouable des écarts « Docs & outils parcelle ».

Un test = une garde = un écart trouvé par l'audit CHASSE-DOCS-1 (cf.
docs/audit-2026-10/chasse-docs/RAPPORT.md). Chaque garde tape l'API LIVE (port 8830
par défaut, surchargeable par CHASSE_DOCS_BASE) sur un témoin connu et vérifie que
l'écart a disparu. 0 ECART attendu APRÈS correction (CHASSE-DOCS-FIX-1).

Usage :
    LABUSE_DATABASE_URL=… uvicorn labuse.api.app:app --port 8830 --app-dir src   # API servie
    python scripts/coherence/chasse_docs.py                                       # le banc

Sortie : une ligne par garde (OK / ECART / SKIP) + un récap. Code retour 1 si ≥1 ECART.
Les gardes qui rendent un PDF (Dossier, Étude de zone, Gabarit, Apporteur) nécessitent
`pdftotext` (poppler) dans le PATH ; absent → SKIP (jamais un faux OK).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("CHASSE_DOCS_BASE", "http://127.0.0.1:8830")
HAS_PDFTOTEXT = shutil.which("pdftotext") is not None

# Témoins de l'échantillon CHASSE-DOCS-1 (run servi q_v19 / cascade q_v19_sources / run_seq 16).
T_MIXITE = "97415000BO0852"      # Saint-Paul U1a — clause de mixité VALIDE (seuil 1800 / quota 30 %)
T_SOLS = "97416000DY0106"        # Saint-Pierre — CASIAS « proche_100m » (dict brut)
T_COMMUNE = "97410000AN0347"     # Saint-Benoît — propriétaire COMMUNE (PM connue, SIREN)
T_ACHEVAL = "97416000DY0106"     # à cheval N(54 %)/Ud(46 %)
T_SATURE = "97415000BO0852"      # bâtie saturée
T_EXIGU = "97411000AV0110"       # à cheval Uh/N — gabarit « terrain exigu »
T_AU = "97415000EV0324"          # AU2c « ouverture sous conditions » (+ grande parcelle 41 009 m²)
T_ZONE = "97415000BO0852"        # témoin générique (étude de zone)
T_AD = "97401000AD0554"          # Les Avirons Ud3 — gabarit calculable
T_VOISINES = "97410000AN0347"    # apporteur avec liste de voisines

_PDF_CACHE: dict[str, str] = {}


# ───────────────────────────── transport ─────────────────────────────
def _get_json(path: str, timeout: int = 90):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:  # noqa: BLE001
        return 0, None


def _post_json(path: str, body: dict, timeout: int = 45):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return e.code, None, None
    except Exception as e:  # noqa: BLE001  (timeout inclus)
        return 0, None, repr(e)


def _pdf_text(path: str, body: dict | None = None, timeout: int = 120) -> str | None:
    """Rend un PDF (GET ou POST) et renvoie son pdftotext -layout. None si indisponible."""
    if not HAS_PDFTOTEXT:
        return None
    key = path + (json.dumps(body) if body else "")
    if key in _PDF_CACHE:
        return _PDF_CACHE[key]
    try:
        if body is None:
            req = urllib.request.Request(BASE + path)
        else:
            req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except Exception:  # noqa: BLE001
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw)
        pdf = f.name
    txt = pdf + ".txt"
    try:
        subprocess.run(["pdftotext", "-layout", pdf, txt], check=True, capture_output=True, timeout=60)
        out = Path(txt).read_text(errors="replace")
    except Exception:  # noqa: BLE001
        out = None
    finally:
        for p in (pdf, txt):
            try:
                os.unlink(p)
            except OSError:
                pass
    if out is not None:
        _PDF_CACHE[key] = out
    return out


# ───────────────────────────── gardes ─────────────────────────────
# Chaque garde renvoie (statut, detail) avec statut ∈ {"OK","ECART","SKIP"}.

def g01_mixite_contradiction():
    """E-01 — §Urbanisme affiche le seuil (1 800) ET le quota (30 %) MAIS aussi
    « seuils de la zone non renseignés à ce jour ». Cause : declarations/fiche/reste_a_declarer.yaml
    (absence de `mixite_clause`). FAUX-CLIENT / incohérence."""
    st, fiche = _get_json(f"/parcels/{T_MIXITE}")
    mx = ((fiche or {}).get("reglement_plu") or {}).get("mixite") or {}
    if mx.get("statut") != "valide":
        return "SKIP", "la zone témoin n'a plus de clause de mixité valide"
    txt = _pdf_text(f"/dossier/{T_MIXITE}.pdf?carte=false")
    if txt is None:
        return "SKIP", "Dossier non rendu (pdftotext absent ?)"
    sert_seuil = ("seuil de" in txt and "1 800" in txt) or "1800" in txt
    dit_non_rens = "seuils de la zone non renseignés" in txt
    if sert_seuil and dit_non_rens:
        return "ECART", "seuil/quota servis ET « seuils de la zone non renseignés à ce jour »"
    return "OK", "pas de co-occurrence seuil-servi / non-renseigné"


def g02_sols_dict_brut():
    """E-02 — §Sols imprime un dict Python brut ({'nom':…,'sur_place':False,'fiche_risque':'https://…'}).
    Cause : robinet_fiche.py `_c_sols` renvoie le dict (casias) → rendu via str(dict). FAUX-CLIENT."""
    txt = _pdf_text(f"/dossier/{T_SOLS}.pdf?carte=false")
    if txt is None:
        return "SKIP", "Dossier non rendu"
    if re.search(r"\{'[a-z_]+':", txt) or "'sur_place'" in txt or "'fiche_risque'" in txt:
        return "ECART", "dict Python brut imprimé dans le Dossier (§Sols CASIAS)"
    return "OK", "aucun dict brut dans le Dossier"


def g03_courrier_pm_connue_occupant():
    """E-03 — propriétaire personne morale CONNUE (dénomination + SIREN, ex. COMMUNE DE X) mais le
    Courrier adresse « À l'occupant ». Cause : courrier_adressage.py (PM sans siège enrichi → occupant,
    dénomination jetée). Incohérence (le Dossier nomme la PM). """
    st, fiche = _get_json(f"/parcels/{T_COMMUNE}")
    pm = (fiche or {}).get("proprietaire_moral") or {}
    if not pm.get("denomination"):
        return "SKIP", "le témoin n'est plus une personne morale connue"
    st, c, _ = _post_json("/courrier/composer", {"idu": T_COMMUNE})
    if c is None:
        return "SKIP", "courrier/composer indisponible"
    dest = (c.get("destinataire") or "")
    if dest.strip().lower().startswith("à l'occupant"):
        return "ECART", f"PM connue « {pm['denomination']} » adressée « {dest} »"
    return "OK", f"destinataire = {dest!r}"


def g04_etude_faisabilite_timeout():
    """E-04 — l'Étude de faisabilité (POST /modules/etude) n'aboutit pas sur grande parcelle :
    timeout silencieux (document non livrable). Robustesse / FAUX-CLIENT (échec non dit)."""
    st, payload, err = _post_json("/modules/etude", {"idus": [T_AU]}, timeout=45)
    if err and ("timed out" in err or "timeout" in err.lower()):
        return "ECART", f"POST /modules/etude {T_AU} : timeout (>45 s) — document non livrable"
    if st == 0 and err:
        return "ECART", f"POST /modules/etude {T_AU} : échec {err}"
    return "OK", f"Étude rendue (HTTP {st})"


def g05_dy0106_constructibilite():
    """E-05 — à cheval N/Ud : le Dossier dit « zone non constructible » / « saturée > 300 % » alors que
    Comparer et l'Étude servent une capacité constructible (SDP > 0). Incohérence inter-lecteurs."""
    st, cmp_ = _get_json(f"/compare?idus={T_ACHEVAL}")
    p = ((cmp_ or {}).get("parcels") or [{}])[0]
    constructible = p.get("constructible") and (p.get("sdp_max_m2") or 0) > 0
    txt = _pdf_text(f"/dossier/{T_ACHEVAL}.pdf?carte=false")
    if txt is None or not p:
        return "SKIP", "Comparer/Dossier indisponible"
    dit_non_const = "zone non constructible" in txt
    if constructible and dit_non_const:
        return "ECART", (f"Comparer : constructible {p.get('sdp_max_m2')} m² ; "
                         "Dossier : « zone non constructible »")
    return "OK", "constructibilité cohérente entre Comparer et Dossier"


def g06_bo0852_potentiel_contradictoire():
    """E-06 — §10 Potentiel : « saturée, SDP déjà consommée » + « Marge SDP non calculée » +
    « Marge de surélévation 0,6 m » (trois affirmations incompatibles dans le même bloc). Incohérence."""
    txt = _pdf_text(f"/dossier/{T_SATURE}.pdf?carte=false")
    if txt is None:
        return "SKIP", "Dossier non rendu"
    sature = "saturée" in txt or "déjà consommée" in txt
    non_calc = "Marge SDP non calculée" in txt or "non calculée" in txt
    m = re.search(r"surélévation.{0,60}?(\d+)[,.](\d)\s*m", txt, re.S)
    surelev = bool(m) and (int(m.group(1)) > 0 or int(m.group(2)) > 0)  # marge > 0 (ex. 0,6 m)
    if sature and non_calc and surelev:
        return "ECART", "« saturée » + « marge non calculée » + « surélévation > 0 » coexistent"
    return "OK", "potentiel §10 cohérent"


def g07_av0110_gabarit_sur_terrain_exigu():
    """E-07 — gabarit chiffré (plafond d'emprise > 0, hauteur) imprimé alors que la zone d'implantation
    vaut 0 m² / le terrain est « non retenu — exigu ». Incohérence intra-outil."""
    st, g = _get_json(f"/outils/gabarit/{T_EXIGU}")
    if not g:
        return "SKIP", "gabarit indisponible"
    zi = g.get("zoneImplantationM2")
    pe = g.get("plafondEmpriseM2")
    if (zi in (0, 0.0)) and pe and pe > 0:
        return "ECART", f"zone d'implantation {zi} m² mais plafond d'emprise {pe} m²"
    return "OK", f"gabarit cohérent (zone impl. {zi}, plafond {pe})"


def g08_au_fermee_caveat_manquant():
    """E-08 — zone AU « ouverture sous conditions » (fiche.au_ouverture) mais l'Étude/Comparer servent la
    capacité SANS le caveat (avertissement vide, cause nulle). Incohérence (sur-vente d'une AU fermée)."""
    st, fiche = _get_json(f"/parcels/{T_AU}")
    au = (fiche or {}).get("au_ouverture") or {}
    if not au or au.get("classe") in (None, "ouverte"):
        return "SKIP", "le témoin n'est plus une AU conditionnée"
    st, cmp_ = _get_json(f"/compare?idus={T_AU}")
    p = ((cmp_ or {}).get("parcels") or [{}])[0]
    constructible = p.get("constructible") and (p.get("sdp_max_m2") or 0) > 0
    porte_caveat = bool(p.get("cause_libelle")) or bool(p.get("au_ouverture"))
    if constructible and not porte_caveat:
        return "ECART", (f"Comparer sert {p.get('sdp_max_m2')} m² sans caveat AU "
                         f"(fiche : « {au.get('statut')} »)")
    return "OK", "le caveat AU est porté par Comparer"


def g09_zone_label_acheval():
    """E-09 — à cheval : la faisabilité nomme `capacite.zone` = la zone CONSTRUCTIBLE (Ud) tandis que
    fiche/Comparer nomment la zone DOMINANTE (N). Libellé « zone » divergent. Incohérence (cosmétique)."""
    st, fiche = _get_json(f"/parcels/{T_ACHEVAL}")
    st2, fai = _get_json(f"/modules/faisabilite/{T_ACHEVAL}")
    z_fiche = ((fiche or {}).get("reglement_plu") or {}).get("zones") or []
    dom = z_fiche[0].get("zone") if z_fiche else None
    z_fai = ((fai or {}).get("capacite") or {}).get("zone")
    st3, cmp_ = _get_json(f"/compare?idus={T_ACHEVAL}")
    z_cmp = ((cmp_ or {}).get("parcels") or [{}])[0].get("zone")
    if dom and z_fai and z_fai != dom and z_cmp == dom:
        return "ECART", f"zone : fiche/Comparer={dom} · faisabilité={z_fai}"
    return "OK", f"libellé zone cohérent (dominante {dom}, faisa {z_fai})"


def g10_emplois_salaries_vide():
    """E-10 — l'Étude de zone sert `emplois.postes_min/max` MAIS le PDF n'imprime que le libellé
    « postes salariés déclarés dans la zone » sans le nombre. Cause : etude_zone.py (la branche
    `if libelle` court-circuite `elif postes_min`, le libellé étant TOUJOURS posé par zone.py). Erreur."""
    st, ez, err = _post_json("/outils/etude-zone", {"idu": T_ZONE}, timeout=60)
    emplois = (ez or {}).get("emplois") or {}
    if emplois.get("postes_min") is None:
        return "SKIP", "pas de postes salariés servis pour ce témoin"
    txt = _pdf_text(f"/etude-zone.pdf?idu={T_ZONE}")
    if txt is None:
        return "SKIP", "Étude de zone non rendue"
    m = re.search(r"Emplois salari[eé]s\s+(.+)", txt)
    val = (m.group(1) if m else "").strip()
    a_un_nombre = bool(re.search(r"\d", val))
    if not a_un_nombre:
        return "ECART", f"données : {emplois['postes_min']}–{emplois.get('postes_max')} ; PDF : « {val} »"
    return "OK", f"fourchette imprimée : « {val} »"


def g11_distance_equipement_zero():
    """E-11 — un équipement affiché « (0 m) » = géocodage manquant imprimé en distance nulle. Erreur."""
    txt = _pdf_text(f"/dossier/{T_AU}.pdf?carte=false")
    if txt is None:
        return "SKIP", "Dossier non rendu"
    if re.search(r"\(0\s*m\)", txt):
        return "ECART", "équipement à « (0 m) » (géocodage manquant imprimé en 0)"
    return "OK", "aucune distance équipement à 0 m"


def g12_gabarit_emprise_format():
    """E-12 — gabarit « Emprise maximale : 40.0 » (point décimal, sans unité %) vs « 9,0 m » correct.
    Format non français / unité manquante. Cosmétique."""
    txt = _pdf_text(f"/gabarit/{T_AD}.pdf")
    if txt is None:
        return "SKIP", "Gabarit non rendu (ou non établissable sur ce témoin)"
    m = re.search(r"Emprise maximale\s*:\s*([0-9]+\.[0-9]+)\s*(?!%)", txt)
    if m and "%" not in (txt[m.start():m.start() + 40]):
        return "ECART", f"« Emprise maximale : {m.group(1)} » (point décimal, sans %)"
    return "OK", "emprise gabarit au format FR avec unité"


def g13_dates_iso_permis():
    """E-13 — permis Sitadel affichés en dates ISO brutes (« déposé 2024-01-01 ») + jour placeholder
    01-01 (fausse précision). Format / fausse précision."""
    txt = _pdf_text(f"/dossier/{T_AU}.pdf?carte=false")
    if txt is None:
        return "SKIP", "Dossier non rendu"
    if re.search(r"d[ée]pos[ée]\s+\d{4}-\d{2}-\d{2}", txt):
        return "ECART", "date de permis en ISO brut (déposé AAAA-MM-JJ)"
    return "OK", "dates de permis au format FR"


def g14_etude_zone_double_point():
    """E-14 — coquille « …chiffre d'affaires.. Les mailles… » (double point). Cosmétique."""
    txt = _pdf_text(f"/etude-zone.pdf?idu={T_ZONE}")
    if txt is None:
        return "SKIP", "Étude de zone non rendue"
    if ".." in re.sub(r"\.\.\.+", "", txt):   # ignore les vraies ellipses « … »
        return "ECART", "double point « .. » dans l'Étude de zone"
    return "OK", "pas de double point"


def g15_apporteur_idu_colle():
    """E-15 — apporteur : « référence 97411000AV0110et le numéro » (IDU collé au mot suivant). Cosmétique."""
    txt = _pdf_text(f"/apporteur/{T_EXIGU}.pdf")
    if txt is None:
        return "SKIP", "Apporteur non rendu"
    if re.search(r"[0-9A-Z]{10,}et le num[ée]ro", txt) or re.search(r"\b\w*\d[A-Z]\d+et\b", txt):
        return "ECART", "IDU collé au mot suivant (espace manquant) dans l'Apporteur"
    return "OK", "pas d'IDU collé"


def g16_apporteur_voisines_tronquees():
    """E-16 — apporteur : liste de parcelles voisines annoncée (n) mais tronquée (« … ») dans un champ
    de DONNÉES (pas un exemple de saisie). Troncature."""
    txt = _pdf_text(f"/apporteur/{T_VOISINES}.pdf")
    if txt is None:
        return "SKIP", "Apporteur non rendu"
    m = re.search(r"(\d+)\s+parcelles voisines.{0,200}?\(([^)]*?)…\s*\)", txt, re.S)
    if m:
        annonce = int(m.group(1))
        montrees = len(re.findall(r"[A-Z]{1,2}\s?\d{3,4}", m.group(2)))
        if montrees < annonce:
            return "ECART", f"{annonce} voisines annoncées, {montrees} listées + « … » (troncature)"
    return "OK", "pas de liste de voisines tronquée"


def g17_gabarit_source_dupliquee():
    """E-17 — gabarit : bloc-source (« BD TOPO … ») réimprimé à l'identique sous deux règles + libellé
    « BD TOPO BD TOPO® » redoublé. Doublon intra-document."""
    txt = _pdf_text(f"/gabarit/{T_AD}.pdf")
    if txt is None:
        return "SKIP", "Gabarit non rendu"
    if "BD TOPO BD TOPO" in txt:
        return "ECART", "libellé « BD TOPO BD TOPO® » redoublé dans le Gabarit"
    return "OK", "pas de source dupliquée"


GARDES = [
    ("E-01 mixité : seuil servi ET « non renseigné »", g01_mixite_contradiction),
    ("E-02 §Sols : dict Python brut", g02_sols_dict_brut),
    ("E-03 courrier : PM connue adressée « À l'occupant »", g03_courrier_pm_connue_occupant),
    ("E-04 Étude de faisabilité : timeout silencieux", g04_etude_faisabilite_timeout),
    ("E-05 à cheval : Dossier non constructible vs Comparer constructible", g05_dy0106_constructibilite),
    ("E-06 §10 : saturée + non calculée + surélévation", g06_bo0852_potentiel_contradictoire),
    ("E-07 gabarit chiffré sur terrain exigu (0 m²)", g07_av0110_gabarit_sur_terrain_exigu),
    ("E-08 AU fermée : caveat manquant côté Comparer/Étude", g08_au_fermee_caveat_manquant),
    ("E-09 à cheval : libellé zone divergent", g09_zone_label_acheval),
    ("E-10 Étude de zone : « Emplois salariés » sans nombre", g10_emplois_salaries_vide),
    ("E-11 équipement « (0 m) »", g11_distance_equipement_zero),
    ("E-12 gabarit « Emprise maximale : 40.0 » (format)", g12_gabarit_emprise_format),
    ("E-13 permis : dates ISO brutes", g13_dates_iso_permis),
    ("E-14 Étude de zone : double point « .. »", g14_etude_zone_double_point),
    ("E-15 apporteur : IDU collé", g15_apporteur_idu_colle),
    ("E-16 apporteur : voisines tronquées", g16_apporteur_voisines_tronquees),
    ("E-17 gabarit : source dupliquée", g17_gabarit_source_dupliquee),
]


def main() -> int:
    st, _ = _get_json("/healthz", timeout=10)
    if st == 0:
        print(f"API injoignable sur {BASE} — démarrez l'app (port 8830) avant le banc.")
        return 2
    n_ok = n_ecart = n_skip = 0
    print(f"CHASSE-DOCS — banc ({len(GARDES)} gardes) · base {BASE} · pdftotext={'oui' if HAS_PDFTOTEXT else 'NON'}\n")
    for libelle, fn in GARDES:
        try:
            statut, detail = fn()
        except Exception as e:  # noqa: BLE001 — une garde ne doit jamais casser le banc
            statut, detail = "SKIP", f"exception {e!r}"
        tag = {"OK": "  OK  ", "ECART": " ECART", "SKIP": " SKIP "}[statut]
        print(f"[{tag}] {libelle}\n          → {detail}")
        n_ok += statut == "OK"
        n_ecart += statut == "ECART"
        n_skip += statut == "SKIP"
    print(f"\nRÉCAP : {n_ok} OK · {n_ecart} ECART · {n_skip} SKIP")
    return 1 if n_ecart else 0


if __name__ == "__main__":
    sys.exit(main())
