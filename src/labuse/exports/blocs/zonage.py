"""Bloc « 2. Zonage et règles d'urbanisme ». Verdict déterministe (famille de zone), règles
calibrées, destinations + verrou CDAC, dispositifs (ER/EBC/DPU/PEB), drapeau « prescriptions non
vérifiables » (Q12). Références nettoyées des notes internes (jamais un mot interdit imprimé)."""
from __future__ import annotations

from ..lignes import a, pied, val
from ..rendu import aside, chip_span, esc, ligne_kv, note, section, table_kv
from ..verdicts import rendu_verdict, verdict_zonage

IDS = ("zone_plu_famille", "reglement_plu_bloc", "er_emplacement_reserve", "ebc_classe",
       "dpu_perimetre", "peb_zone")


def _ref_courte(ref: str) -> str:
    """Garde « Art. X, p.Y » et coupe les notes éditoriales internes (« : … », « (… corrigée…) »)
    pour ne jamais imprimer un mot interdit (« page corrigée », « reglt »…)."""
    if not ref:
        return ""
    r = str(ref).split(" : ")[0].split(" (")[0].strip()
    return r


def _chip_regle(etat: str) -> str:
    return chip_span("s", "sourcé") if etat in ("chiffre", "texte") else chip_span("e", "estimé")


def _regles(z: dict) -> str:
    lignes = []
    for r in z.get("regles_valeurs") or []:
        valeur = r.get("valeur")
        if valeur in (None, ""):
            continue
        ref = _ref_courte(r.get("reference"))
        v = esc(valeur) + (f' <span class="note" style="display:inline">{esc(ref)}</span>' if ref else "")
        lignes.append(ligne_kv(r.get("libelle") or r.get("cle") or "Règle", v, _chip_regle(r.get("etat") or "")))
    if not lignes:
        return ""
    entete = '<tr><th>Règle</th><th>Valeur retenue</th><th></th></tr>'
    return "<h3>Ce que le règlement fixe ici</h3>" + table_kv(lignes, entete)


def _destinations(z: dict) -> str:
    d = z.get("destinations") or {}
    lignes = []
    if d.get("autorisees"):
        lignes.append(ligne_kv("Autorisées", esc(" · ".join(d["autorisees"])), chip_span("s", "sourcé")))
    if d.get("sous_conditions"):
        lignes.append(ligne_kv("Sous conditions", esc(" · ".join(d["sous_conditions"])), chip_span("s", "sourcé")))
    if d.get("interdites"):
        lignes.append(ligne_kv("Interdites", esc(" · ".join(d["interdites"])), chip_span("s", "sourcé")))
    cdac = d.get("commerce_cdac") or {}
    if cdac.get("seuil_m2"):
        lignes.append(ligne_kv("Surface commerciale",
                               esc(f"Au-delà de {cdac['seuil_m2']} m² de surface de vente : "
                                   "autorisation d'exploitation commerciale (CDAC)"), chip_span("s", "sourcé")))
    return ("<h3>Ce que le règlement autorise ici</h3>" + table_kv(lignes)) if lignes else ""


def _dispositifs(valeurs) -> str:
    lignes = []
    if a(valeurs, "er_emplacement_reserve"):
        lignes.append(ligne_kv("Emplacement réservé", esc(str(val(valeurs, "er_emplacement_reserve"))), chip_span("s", "sourcé")))
    if a(valeurs, "ebc_classe"):
        lignes.append(ligne_kv("Espace boisé classé", esc(str(val(valeurs, "ebc_classe"))), chip_span("s", "sourcé")))
    if a(valeurs, "dpu_perimetre"):
        d = val(valeurs, "dpu_perimetre")
        lib = d.get("libelle") or d.get("statut") if isinstance(d, dict) else str(d)
        lignes.append(ligne_kv("Droit de préemption urbain",
                               esc(f"La parcelle est dans un périmètre de préemption — {lib}"), chip_span("s", "sourcé")))
    if a(valeurs, "peb_zone"):
        d = val(valeurs, "peb_zone")
        z = d.get("zone") if isinstance(d, dict) else d
        lignes.append(ligne_kv("Plan d'exposition au bruit", esc(f"Zone {z}"), chip_span("s", "sourcé")))
    return ("<h3>Prescriptions et servitudes</h3>" + table_kv(lignes)) if lignes else ""


def rendu(valeurs) -> str:
    z = val(valeurs, "reglement_plu_bloc") or {}
    corps = rendu_verdict(verdict_zonage(valeurs)) + _regles(z) + _destinations(z) + _dispositifs(valeurs)
    if not corps.strip():
        return ""      # ni zone ni règle servie → section omise (aucun ◌)
    # drapeau Q12 — prescriptions non vérifiables sur la commune
    if isinstance(z, dict) and z.get("_prescriptions_verifiables") is False:
        motif = z.get("_prescriptions_motif") or "aucun document de prescriptions publié pour cette commune"
        corps += aside(f"<strong>Prescriptions non vérifiables sur cette commune</strong> — {esc(motif)}. "
                       "Un emplacement réservé ou une servitude peut exister sans être publié : "
                       "à vérifier en mairie.", "rose")
    if z.get("idurba"):
        corps += note(f"Règlement complet : {z['idurba']} sur le Géoportail de l'urbanisme. "
                      "Les valeurs ci-dessus sont une aide à la lecture ; le règlement fait foi.")
    corps += pied(valeurs, IDS)
    return section("2. Zonage et règles d'urbanisme", corps)
