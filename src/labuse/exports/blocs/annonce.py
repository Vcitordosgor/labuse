"""ANNONCE-3 — bloc « Analyse d'annonce » : deux variantes, MIROIR EXACT de l'outil « Analyser une
annonce » (frontend/src/components/outils/AnalyserAnnonce.tsx). Aucun recalcul : on rend les MÊMES
sorties d'endpoints que l'écran (fiche / exposition / classement pour la parcelle ; le rapport de
`radar_annonce_analyser` + `commune_contexte` pour la commune). Le builder appelle les endpoints et
passe des dicts purs ; ce module ne fait que de la mise en forme.

 · variante PARCELLE (entrée adresse) : les 6 tuiles (surface, zone PLU, SDP restante, classement
   LABUSE, risques, exposition) + « Estimation du prix » (fourchette, fiabilité, N ventes · rayon ·
   période) + « Le foncier » (zone, hauteur réglementaire, SDP restante). Le plan de situation
   (contour parcelle) est posé AVANT par le builder (_plan_situation_html, même composant que le Dossier).
 · variante COMMUNE (entrée lien) : « Ce que dit l'annonce » (champs PRÉSENTS seulement, pilotés par
   type comme l'écran), « Prix face au marché » (fiabilité LIMITÉE + phrase « localisez la parcelle… »),
   « La commune » (ventes, prix médian DVF, PLU, aléas).

Règle « jamais un champ vide imprimé » : une valeur absente ne s'imprime pas (ni « — » ni case vide) ;
les champs non applicables au type restent masqués, comme à l'écran. Le classement LABUSE est servi
par le builder depuis le run SERVI avec le vocabulaire gravé (radar_annonce_classement)."""
from __future__ import annotations

from ..registre_fmt import groupe
from ..rendu import chip_span, esc, ligne_kv, note, section, table_kv, verdict


# ── formats MIROIR de l'écran (frontend/src/lib/format.ts) pour une parité visuelle stricte. ──
def _fmt_int(n) -> str | None:
    """fmtInt : entier groupé fr (« 431 663 »). None → None (jamais un « — » imprimé)."""
    return groupe(round(n)) if isinstance(n, (int, float)) else None


def _fmt_m2(m2) -> str | None:
    """fmtM2 : « 1 245 m² », « 2,50 ha » au-delà d'un hectare. None → None."""
    if not isinstance(m2, (int, float)):
        return None
    return f"{groupe(m2 / 10_000, 2)} ha" if m2 >= 10_000 else f"{groupe(round(m2))} m²"


def _fiab(fiabilite: str | None, commune_fallback) -> tuple[str, str]:
    """Miroir de `fiab()` (AnalyserAnnonce.tsx) : (mot, classe de chip). L'entrée commune est toujours
    « limitée » ; sinon « élevée » (fiable) ou « indicative »."""
    if commune_fallback:
        return ("limitée", "p")                 # chip ambre
    if fiabilite == "fiable":
        return ("élevée", "s")                   # chip menthe
    return ("indicative", "p")


def _fmt_periode(p) -> str | None:
    """Miroir de `fmtPeriode()` : [a, b] → « a » / « a–b » ; scalaire → str ; vide → None."""
    if p is None or p == [] or p == "":
        return None
    if isinstance(p, (list, tuple)):
        if not p:
            return None
        a = p[0]
        b = p[-1] if len(p) > 1 else p[0]
        return str(a) if a == b else f"{a}–{b}"
    return str(p)


# ═══════════════════════════════════════ VARIANTE PARCELLE ═══════════════════════════════════════
def rendu_parcelle(fiche: dict, expo: dict | None, classement: dict | None) -> str:
    f = fiche or {}
    rp = f.get("reglement_plu") or {}
    zones = rp.get("zones") or []
    zone = (zones[0] or {}).get("zone") if zones and isinstance(zones[0], dict) else None
    pot = f.get("potentiel_transformation") or {}
    sdp = pot.get("sdp_residuelle_m2")
    # classement : bande + libellé gravé (le builder a interrogé radar_annonce_classement sur le run servi).
    cls = classement or {}
    bande, libelle = cls.get("bande"), cls.get("libelle")
    classement_txt = (f"{bande} · {libelle}" if bande and libelle and libelle != bande
                      else bande if bande else None)
    n_aleas = (f.get("aleas") or {}).get("n")
    orientation = (expo or {}).get("orientation")

    # ── les 6 tuiles — une tuile dont la valeur est absente N'EST PAS imprimée (jamais une case vide). ──
    tuiles = [
        ("Surface", _fmt_m2(f.get("surface_m2"))),
        ("Zone PLU", esc(zone) if zone else None),
        ("SDP restante", _fmt_m2(round(sdp)) if isinstance(sdp, (int, float)) else None),
        ("Classement LABUSE", esc(classement_txt) if classement_txt else None),
        # « Risques » : le compte d'aléas est une donnée présente (0 → « aucun aléa »), pas un vide.
        ("Risques", ("aucun aléa" if n_aleas == 0 else f"{n_aleas} aléa{'s' if n_aleas > 1 else ''}")
         if isinstance(n_aleas, int) else None),
        ("Exposition", esc(orientation) if orientation else None),
    ]
    cells = "".join(f'<div class="tile"><div class="v">{v}</div><div class="l">{esc(k)}</div></div>'
                    for k, v in tuiles if v)
    corps = f'<div class="cover-tiles">{cells}</div>'

    corps += _estimation_prix(f.get("prix_ancien"))
    corps += _le_foncier(zone, pot, sdp)
    return section("Analyse d'annonce", corps)


def _estimation_prix(prix_ancien) -> str:
    """« Estimation du prix » = le comparateur DVF de la fiche (lu tel quel, €/m²). MÊME sélection que
    l'écran : median ← median|distribution.apres.median ; fourchette ← q1/q3|p25/p75 ; N · rayon · période."""
    pa = prix_ancien if isinstance(prix_ancien, dict) else {}
    dist = ((pa.get("distribution") or {}).get("apres")) or {}
    median = pa.get("median") if pa.get("median") is not None else dist.get("median")
    p25 = pa.get("q1") if pa.get("q1") is not None else dist.get("p25")
    p75 = pa.get("q3") if pa.get("q3") is not None else dist.get("p75")
    n_ventes = pa.get("n") if pa.get("n") is not None else dist.get("n")
    rayon = pa.get("radius_m")
    periode = _fmt_periode(pa.get("periode"))
    fallback = pa.get("commune_fallback")
    type_prix = pa.get("type_prix")

    if not isinstance(median, (int, float)):
        # absence SOURCÉE (pas un champ vide) : le même constat honnête qu'à l'écran.
        corps = note("Indisponible — pas assez de ventes comparables dans le secteur pour un repère de prix.")
        return section("Estimation du prix", corps)

    mot, chip_cls = _fiab(pa.get("fiabilite"), fallback)
    petit = (f"de {_fmt_int(p25)} à {_fmt_int(p75)} €/m²"
             if isinstance(p25, (int, float)) and isinstance(p75, (int, float)) else "")
    corps = verdict(f"{_fmt_int(median)} €/m²", ton="" if chip_cls == "s" else "neutral", petit_html=petit)
    lignes = [ligne_kv("Fiabilité", chip_span(chip_cls, f"Fiabilité : {mot}"))]
    if isinstance(n_ventes, (int, float)):
        lignes.append(ligne_kv("Ventes comparables", esc(_fmt_int(n_ventes))))
    if isinstance(rayon, (int, float)):
        lignes.append(ligne_kv("Rayon", f"{_fmt_int(rayon)} m"))
    if periode:
        lignes.append(ligne_kv("Période", esc(periode)))
    corps += table_kv(lignes)
    note_txt = (f"Prix observés au m² (bâti ancien{f', {type_prix}' if type_prix else ''}) autour de la "
                "parcelle." + (" Repère élargi à la commune (secteur trop peu fourni)." if fallback else "")
                + " La valeur d'un bien dépend de sa surface et de son état, non connus du modèle.")
    corps += note(note_txt)
    return section("Estimation du prix", corps)


def _le_foncier(zone: str | None, pot: dict, sdp) -> str:
    """« Le foncier » — zone, hauteur réglementaire, SDP restante (mêmes champs que l'écran). Chaque
    ligne absente est omise ; à défaut de SDP, le libellé servi (sinon le repli de l'écran)."""
    lignes = []
    if zone:
        lignes.append(ligne_kv("Zone", f"<b>{esc(zone)}</b>"))
    h = pot.get("hauteur_regle_m")
    if isinstance(h, (int, float)):
        lignes.append(ligne_kv("Hauteur réglementaire", f"{_fmt_int(h)} m"))
    if isinstance(sdp, (int, float)):
        suff = " (estimation simplifiée)" if pot.get("estimation_simplifiee") else ""
        lignes.append(ligne_kv("SDP restante estimée", f"{_fmt_m2(round(sdp))}{esc(suff)}"))
    elif pot.get("libelle"):
        lignes.append(ligne_kv("Potentiel", esc(pot.get("libelle"))))
    if not lignes:
        return ""
    return section("Le foncier", table_kv(lignes))


# ═══════════════════════════════════════ VARIANTE COMMUNE ════════════════════════════════════════
_NP = "non précisé dans l'annonce"


def rendu_commune(annonce: dict, marche: dict | None, contexte: dict | None) -> str:
    a = annonce or {}
    m = marche if isinstance(marche, dict) else None
    c = contexte or {}
    return (_ce_que_dit(a) + _prix_face_marche(m) + _la_commune(a.get("commune"), m, c))


def _cap(s):
    return s[0].upper() + s[1:] if isinstance(s, str) and s else None


def _ce_que_dit(a: dict) -> str:
    """« Ce que dit l'annonce » — champs PILOTÉS PAR TYPE, à l'identique de l'écran : terrain (surface du
    terrain), maison/appart (surface, pièces, + terrain pour la maison), type inconnu (présents seulement).
    « non précisé dans l'annonce » est RÉSERVÉ aux champs ATTENDUS pour le type et absents (jamais un « — »)."""
    typ = a.get("type")
    prix = a.get("prix")
    prix_m2 = a.get("prix_m2")
    suff_m2 = f" · {_fmt_int(prix_m2)} €/m²" if isinstance(prix_m2, (int, float)) else ""
    rows = [
        ligne_kv("Prix demandé", f"{_fmt_int(prix)} €" if isinstance(prix, (int, float)) else _NP),
        ligne_kv("Type", esc(_cap(typ)) if typ else _NP),
    ]
    st, sh, pieces = a.get("surface_terrain"), a.get("surface_hab"), a.get("pieces")
    if typ == "terrain":
        rows.append(ligne_kv("Surface du terrain",
                             f"{_fmt_m2(st)}{suff_m2}" if isinstance(st, (int, float)) else _NP))
    elif typ in ("maison", "appartement"):
        rows.append(ligne_kv("Surface", f"{_fmt_m2(sh)}{suff_m2}" if isinstance(sh, (int, float)) else _NP))
        rows.append(ligne_kv("Pièces", esc(str(pieces)) if isinstance(pieces, int) else _NP))
        if typ == "maison":
            rows.append(ligne_kv("Terrain", _fmt_m2(st) if isinstance(st, (int, float)) else _NP))
    else:
        # type inconnu : on n'affirme aucun attendu → seulement ce qui est réellement présent.
        if isinstance(sh, (int, float)):
            rows.append(ligne_kv("Surface", f"{_fmt_m2(sh)}{suff_m2}"))
        if isinstance(pieces, int):
            rows.append(ligne_kv("Pièces", esc(str(pieces))))
        if isinstance(st, (int, float)):
            rows.append(ligne_kv("Terrain", _fmt_m2(st)))
    corps = table_kv(rows) + note("Seules les informations présentes dans l'annonce sont affichées.")
    return section("Ce que dit l'annonce", corps)


def _prix_face_marche(m: dict | None) -> str:
    """« Prix face au marché » — écart au repère commune du bon type, fiabilité LIMITÉE assumée, puis la
    phrase gravée « localisez la parcelle… ». Repère indisponible → le motif servi (jamais un vide)."""
    phrase = ("L'annonce ne donne pas d'adresse précise : le repère est large. Localisez la parcelle "
              "pour une estimation au micro-marché et l'analyse foncière.")
    if m and m.get("calculable") and m.get("ecart_libelle"):
        repere = m.get("repere_perimetre") or m.get("perimetre") or "du bon type"
        ref = m.get("referentiel_eur_m2")
        sub = f"face au repère commune {esc(repere)}" + (
            f" : {_fmt_int(ref)} €/m²" if isinstance(ref, (int, float)) else "")
        corps = verdict(esc(m["ecart_libelle"]), ton="neutral", petit_html=sub)
        corps += table_kv([ligne_kv("Fiabilité",
                 chip_span("p", "Fiabilité : limitée") + ' <span class="none">repère à l\'échelle de la commune</span>')])
    else:
        motif = (m or {}).get("motif") or ("Comparaison au marché indisponible (prix ou surface absents "
                 "de l'annonce, ou échantillon DVF insuffisant).")
        corps = note(motif)
    corps += note(phrase)
    return section("Prix face au marché", corps)


def _la_commune(commune: str | None, m: dict | None, c: dict) -> str:
    """« La commune » — ventes du repère + prix médian DVF (du rapport d'annonce), PLU et aléas (contexte
    commune). Lignes absentes OMISES (jamais un « — »). Aléas déduits comme à l'écran."""
    m = m or {}
    lignes = []
    n_ref = m.get("n_referentiel")
    if isinstance(n_ref, (int, float)):
        per = _fmt_periode(m.get("periode")) or (m.get("periode") if isinstance(m.get("periode"), str) else None)
        val = _fmt_int(n_ref) + (f" · {esc(per)}" if per else "")
        lignes.append(ligne_kv(f"Ventes {esc(m.get('repere_perimetre') or 'comparables')}", val))
    ref = m.get("referentiel_eur_m2")
    if isinstance(ref, (int, float)):
        lignes.append(ligne_kv("Prix médian (DVF)", f"{_fmt_int(ref)} €/m²"))
    plu = c.get("plu_statut") or {}
    plu_txt = plu.get("statut") or plu.get("libelle")
    if plu_txt:
        lignes.append(ligne_kv("PLU", esc(plu_txt)))
    aleas = _aleas(c.get("risques") or {})
    if aleas:
        lignes.append(ligne_kv("Aléas principaux", esc(", ".join(aleas))))
    if not lignes:
        return ""
    titre = "La commune" + (f" · {commune}" if commune else "")
    return section(titre, table_kv(lignes))


def _aleas(risques: dict) -> list[str]:
    """Miroir du calcul d'aléas de l'écran : inondation (PPR / AZI / TRI), mouvement de terrain, parc national."""
    out = []
    azi_tri = risques.get("azi_tri") or {}
    inond = ((risques.get("ppr_pct") or 0) > 0 or (azi_tri.get("azi") or [])
             or (azi_tri.get("tri") or []))
    if inond:
        out.append("inondation")
    if (risques.get("mouvement_terrain_pct") or 0) > 0:
        out.append("mouvement de terrain")
    if risques.get("parc_national"):
        out.append("parc national")
    return out
