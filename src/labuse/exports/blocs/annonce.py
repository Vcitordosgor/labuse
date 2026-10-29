"""ANNONCE-5 — bloc « Analyse d'annonce », REFONTE selon la maquette validée. Deux variantes, MIROIR
EXACT de l'outil « Analyser une annonce » : aucun recalcul ici, de la mise en forme. Le builder appelle
les POINTS UNIQUES (`pige.api.rapport_parcelle` / `rapport_lien`) et passe des dicts purs ; l'écran lit
les MÊMES → le PDF et l'outil ne divergent jamais.

 · variante PARCELLE (adresse), 2 pages : en-tête (adresse · IDU · zone · surface · nature) ; deux cartes
   (ortho + cadastre/zonage/aléas) ; 6 tuiles ; « Estimation du prix » (€/m², fourchette, fiabilité,
   source) + « Valeur indicative du bien » (surface × €/m², fourchette, repère terrain nu) ; tableau des
   8 ventes les plus proches. Page 2 : « Le foncier » (règles de la zone face aux mesures de la parcelle)
   + phrase de classement ; « Risques et contraintes » ; « Le marché » (médianes + graphique 5 ans) ;
   « Ce qu'il reste à vérifier ».
 · variante LIEN (commune), 1 page : « Ce que dit l'annonce » (+ extrait si en base) ; « Prix face au
   marché » (lecture bâti + lecture foncière CHIFFRÉE) ; « La commune » (marché + PLU + aléas + permis) ;
   encart « rapport complet ».

Règle « jamais un champ vide imprimé » : une valeur absente ne s'imprime pas (ni « — » ni case vide) ;
une LIGNE sans valeur disparaît. Formats français ; aucun code brut ; aucun texte coupé."""
from __future__ import annotations

from ..registre_fmt import groupe
from ..rendu import esc, esc_noms


# ── formats FR (miroir de frontend/src/lib/format.ts) ────────────────────────────────────────────
def _int(n) -> str | None:
    return groupe(round(n)) if isinstance(n, (int, float)) else None


def _m2(m2) -> str | None:
    if not isinstance(m2, (int, float)):
        return None
    return f"{groupe(m2 / 10_000, 2)} ha" if m2 >= 10_000 else f"{groupe(round(m2))} m²"


def _eur(n) -> str | None:
    return f"{groupe(round(n))} €" if isinstance(n, (int, float)) else None


def _eur_m2(n) -> str | None:
    return f"{groupe(round(n))} €/m²" if isinstance(n, (int, float)) else None


def _pct_signe(n) -> str | None:
    if not isinstance(n, (int, float)):
        return None
    s = f"{n:.1f}".replace(".", ",").rstrip("0").rstrip(",")
    return (f"+{s} %" if n > 0 else f"{s} %")


def _periode(p) -> str | None:
    if p is None or p == [] or p == "":
        return None
    if isinstance(p, (list, tuple)):
        if not p:
            return None
        a, b = p[0], p[-1]
        return str(a) if a == b else f"{a}–{b}"
    return str(p)


def _fiab_niveau(fiabilite, commune_fallback=False) -> tuple[str, str]:
    """(niveau affiché, classe de chip). Trois niveaux : Élevée (menthe) / Moyenne / Limitée (ambre)."""
    if commune_fallback:
        return ("Limitée", "p")
    if fiabilite == "fiable":
        return ("Élevée", "s")
    if fiabilite == "limitee":
        return ("Limitée", "p")
    return ("Moyenne", "p")


def _chip(classe: str, libelle: str) -> str:
    cls = {"s": "chip s", "p": "chip p"}.get(classe, "chip")
    return f'<span class="{cls}">{esc(libelle)}</span>'


def _kv(pairs: list[tuple[str, str | None]], *, titre: str | None = None) -> str:
    """Table clé/valeur : chaque ligne dont la valeur est None DISPARAÎT. `pairs` = [(clé, valeur_html)]."""
    rows = "".join(f'<tr><td class="k">{esc(k)}</td><td class="v">{v}</td></tr>'
                   for k, v in pairs if v is not None and v != "")
    if not rows:
        return ""
    head = f'<div class="kicker">{esc(titre)}</div>' if titre else ""
    return f'{head}<table class="akv">{rows}</table>'


# ═══════════════════════════════════════ EN-TÊTE COMMUN ══════════════════════════════════════════
def entete(titre_html: str, sous_html: str, ref_droite: str, *, sous_bar: str | None = None) -> str:
    """Bandeau haut (LABUSE · Analyse d'annonce … n° · date) + titre + sous-titre, façon maquette."""
    barre = (f'<div class="abar"><span class="abrand">LABUSE</span>'
             f'<span class="akind">Analyse d\'annonce{(" · " + esc(sous_bar)) if sous_bar else ""}</span>'
             f'<span class="aref">{esc(ref_droite)}</span></div>')
    return (barre + f'<h1 class="atitre">{esc_noms(titre_html)}</h1>'
            + (f'<p class="asub">{sous_html}</p>' if sous_html else ""))


# ═══════════════════════════════════════ VARIANTE PARCELLE ═══════════════════════════════════════
def rendu_parcelle(rapport: dict, *, plan_ortho_html: str = "", plan_zonage_html: str = "") -> str:
    r = rapport or {}
    est = r.get("estimation") or {}
    # ── sous-titre : IDU · Zone · Surface · Nature ──
    sous_bits = [b for b in (
        r.get("idu"),
        f"Zone {r['zone']}" if r.get("zone") else None,
        _m2(r.get("surface_m2")),
        r.get("nature_label"),
    ) if b]
    sous = " · ".join(esc(x) for x in sous_bits)
    titre = r.get("adresse") or (f"{r.get('commune')}" if r.get("commune") else r.get("idu") or "Parcelle")
    ref_d = r.get("_ref_droite") or ""
    corps = entete(titre, sous, ref_d)
    # ── deux cartes côte à côte ──
    corps += f'<div class="amaps">{plan_ortho_html}{plan_zonage_html}</div>'
    # ── 6 tuiles ──
    corps += _tuiles(r, est)
    # ── estimation + valeur indicative ──
    corps += _estimation(est)
    # ── tableau des comparables ──
    corps += _comparables(est)
    # ── page 2 ──
    corps += '<div class="apage2">'
    corps += _foncier(r)
    corps += _risques(r.get("risques") or [])
    corps += _marche(r.get("marche") or {}, titre_lieu=r.get("commune"))
    corps += _a_verifier(r.get("a_verifier") or [])
    corps += "</div>"
    return corps


def _tuiles(r: dict, est: dict) -> str:
    cls = r.get("classement") or {}
    bande, lib = cls.get("bande"), cls.get("libelle")
    classement = (f"{bande} · {lib}" if bande and lib and lib != bande else bande) if bande else None
    risq = r.get("risques") or []
    n_al = len(risq)
    expo = r.get("exposition")
    tuiles = [
        (_m2(r.get("surface_m2")), "Surface"),
        (esc(r["zone"]) if r.get("zone") else None, "Zone PLU"),
        (_sdp_tuile(r), "SDP restante"),
        (esc(classement) if classement else None, "Classement"),
        (("aucun aléa" if n_al == 0 else f"{n_al} aléa" + ("s" if n_al > 1 else "")), "Risques"),
        (esc(expo) if expo else None, "Exposition"),
    ]
    cells = "".join(f'<div class="tile"><div class="v">{v}</div><div class="l">{esc(l)}</div></div>'
                    for v, l in tuiles if v)
    return f'<div class="atiles">{cells}</div>'


def _sdp_tuile(r: dict) -> str | None:
    for row in ((r.get("foncier") or {}).get("parcelle") or []):
        if row.get("cle", "").startswith("SDP restante"):
            return esc(row.get("valeur"))
    return None


def _estimation(est: dict) -> str:
    median = est.get("median")
    terrain = est.get("type_comparateur") == "terrain_nu"
    if not isinstance(median, (int, float)):
        motif = est.get("note") or "Estimation indisponible — échantillon de ventes insuffisant."
        return ('<h2>Estimation du prix</h2>'
                f'<p class="anote">{esc(motif)}</p>')
    niv, chip_cls = _fiab_niveau(est.get("fiabilite"), est.get("commune_fallback"))
    q1, q3 = est.get("q1"), est.get("q3")
    fourch = (f"de {_int(q1)} à {_int(q3)} €/m²" if isinstance(q1, (int, float)) and isinstance(q3, (int, float))
              else None)
    # source : N ventes · rayon/secteur · période
    src_bits = []
    n = est.get("n")
    if isinstance(n, (int, float)):
        src_bits.append(f"{_int(n)} vente" + ("s" if n != 1 else ""))
    if terrain:
        if est.get("perimetre"):
            src_bits.append("secteur cadastral" if est["perimetre"] == "secteur" else "commune")
    else:
        if isinstance(est.get("radius_m"), (int, float)):
            src_bits.append(f"rayon {_int(est['radius_m'])} m")
        elif est.get("commune_fallback"):
            src_bits.append("commune")
    per = _periode(est.get("periode"))
    if per:
        src_bits.append(per)
    source = " · ".join(src_bits)
    # note
    if terrain:
        note = "Terrain nu — comparé aux ventes de terrain nu du secteur (repère €/m² de terrain)."
    else:
        pl = est.get("type_label_pluriel") or "biens bâtis anciens"
        note = (f"{(est.get('type_bien') or 'Bâti').capitalize()} — comparé aux ventes de <b>{esc(pl)}</b> "
                "autour de la parcelle. État et prestations du bien non connus du modèle.")
    gauche = (f'<div class="estbig">{_int(median)} €/m²'
              + (f' <span class="estrange">{esc(fourch)}</span>' if fourch else "") + "</div>"
              + f'<div class="estmeta">{_chip(chip_cls, "Fiabilité " + niv)}'
              + (f' <span class="muted">{esc(source)}</span>' if source else "") + "</div>"
              + f'<p class="anote">{note}</p>')
    droite = _valeur_indicative(est)
    return ('<h2>Estimation du prix</h2>'
            f'<div class="estgrid"><div class="estleft">{gauche}</div>'
            f'<div class="estright">{droite}</div></div>')


def _valeur_indicative(est: dict) -> str:
    vi = est.get("valeur_indicative") or {}
    terrain = est.get("type_comparateur") == "terrain_nu"
    rows = []
    surf = vi.get("surface_m2")
    val = vi.get("valeur_eur")
    if isinstance(surf, (int, float)) and isinstance(val, (int, float)):
        label = "Terrain" if terrain else (est.get("type_bien") or "Bâti").capitalize()
        em = est.get("surface_batie") or {}
        note_surf = " estimé" if (not terrain and em.get("niveaux_estimes")) else ""
        libelle = f"{label}{note_surf} {_m2(surf)} × {_eur_m2(vi.get('eur_m2'))}"
        rows.append((libelle, _eur(val)))
    vb, vh = vi.get("valeur_basse"), vi.get("valeur_haute")
    if isinstance(vb, (int, float)) and isinstance(vh, (int, float)):
        rows.append(("Fourchette", f"{_int(vb)} – {_int(vh)} €"))
    # repère terrain nu (ancre foncière), montré aussi pour un bâti
    rtn = est.get("repere_terrain_nu") or {}
    if not terrain and isinstance(rtn.get("eur_m2"), (int, float)):
        suff = f" · {_int(rtn['n'])} ventes" if isinstance(rtn.get("n"), (int, float)) else ""
        rows.append(("Repère terrain nu, secteur", f"{_eur_m2(rtn['eur_m2'])}{esc(suff)}"))
    if not rows:
        return ""
    body = "".join(f'<tr><td class="k">{esc(k)}</td><td class="v">{v}</td></tr>' for k, v in rows)
    return (f'<div class="vibox"><div class="kicker">Valeur indicative du bien</div>'
            f'<table class="akv vikv">{body}</table></div>')


def _comparables(est: dict) -> str:
    comps = est.get("comparables") or []
    if not comps:
        return ""
    head = ('<tr><th>Date</th><th>Type</th><th class="r">Surface</th><th class="r">Prix</th>'
            '<th class="r">€/m²</th><th class="r">Distance</th></tr>')
    rows = ""
    for c in comps:
        rows += ('<tr>'
                 f'<td>{esc(c.get("date") or "")}</td>'
                 f'<td>{esc(c.get("type") or "")}</td>'
                 f'<td class="r">{esc(_m2(c.get("surface_m2")) or "")}</td>'
                 f'<td class="r">{esc(_eur(c.get("prix_eur")) or "")}</td>'
                 f'<td class="r">{esc(_int(c.get("prix_m2")) or "")}</td>'
                 f'<td class="r">{esc((_int(c.get("distance_m")) + " m") if isinstance(c.get("distance_m"), (int, float)) else "")}</td>'
                 '</tr>')
    n_total = est.get("n_total") or len(comps)
    autres = max(0, int(n_total) - len(comps))
    pl = est.get("type_label_pluriel") or "biens"
    per = _periode(est.get("periode"))
    foot = ""
    if autres > 0:
        foot = (f"{_int(autres)} autre" + ("s" if autres > 1 else "") + " vente"
                + ("s" if autres > 1 else "") + " dans le rayon entrent dans le calcul. ")
    foot += f"Source : DVF, ventes de {esc(pl)}" + (f", {esc(per)}" if per else "") + "."
    return ('<h2>Les 8 ventes les plus proches retenues</h2>'
            f'<table class="acomp">{head}{rows}</table>'
            f'<p class="anote">{foot}</p>')


def _foncier(r: dict) -> str:
    f = r.get("foncier") or {}
    regles = f.get("regles") or []
    parcelle = f.get("parcelle") or []
    if not regles and not parcelle:
        return ""
    zone, commune = f.get("zone"), f.get("commune")
    t_reg = "Règles de la zone" + (f" {zone}" if zone else "") + (f" · PLU de {commune}" if commune else "")
    gauche = _kv([(x["cle"], esc(x["valeur"])) for x in regles], titre=t_reg)
    droite = _kv([(x["cle"], esc(x["valeur"])) for x in parcelle], titre="Sur cette parcelle")
    phrase = (r.get("classement") or {}).get("phrase")
    note = f'<p class="anote">{esc(phrase)}</p>' if phrase else ""
    return ('<h2>Le foncier</h2>'
            f'<div class="fongrid"><div>{gauche}</div><div>{droite}</div></div>{note}')


def _risques(rows: list[dict]) -> str:
    if not rows:
        return ""
    head = '<tr><th>Aléa</th><th>Niveau</th><th>Document</th><th>Ce que ça implique</th></tr>'
    body = ""
    for x in rows:
        body += ('<tr>'
                 f'<td>{esc(x.get("alea") or "")}</td>'
                 f'<td>{esc(x.get("niveau") or "")}</td>'
                 f'<td>{esc_noms(x.get("document") or "")}</td>'
                 f'<td>{esc(x.get("implique") or "")}</td>'
                 '</tr>')
    return ('<h2>Risques et contraintes</h2>'
            f'<table class="arisq">{head}{body}</table>')


def _marche(m: dict, *, titre_lieu: str | None = None) -> str:
    if not m:
        return ""
    lignes = [
        ("Ventes de maisons, 12 mois", _int(m.get("ventes_maison_12m"))),
        ("Prix médian maison", _eur_m2(m.get("median_maison_eur_m2"))),
        ("Prix médian appartement", _eur_m2(m.get("median_appartement_eur_m2"))),
        ("Terrain nu, médiane", _eur_m2(m.get("median_terrain_eur_m2"))),
        ("Évolution maisons sur 12 mois", _pct_signe(m.get("evolution_maison_12m_pct"))),
    ]
    gauche = _kv(lignes)
    droite = _bar_chart(m.get("serie_maison_5a") or [])
    if not gauche and not droite:
        return ""
    titre = "Le marché" + (f" · {titre_lieu}" if titre_lieu else "")
    return (f'<h2>{esc(titre)}</h2>'
            f'<div class="mkgrid"><div>{gauche}</div><div>{droite}</div></div>')


def _bar_chart(serie: list[dict]) -> str:
    """Graphique 5 ans (médiane maison) en TABLE (hauteurs en mm) — fiable sous WeasyPrint, contrairement
    à un flex en pourcentage. Dernière barre en menthe foncée. Omis si moins de 2 points."""
    pts = [(s.get("annee"), s.get("median")) for s in serie if isinstance(s.get("median"), (int, float))]
    if len(pts) < 2:
        return ""
    vmax = max(v for _, v in pts)
    vmin = min(v for _, v in pts)
    span = max(1, vmax - vmin)
    vals = "".join(f'<td class="bv">{esc(_int(v))}</td>' for _, v in pts)
    bars = ""
    for i, (an, v) in enumerate(pts):
        h = 6 + round((v - vmin) / span * 20)   # 6 → 26 mm (lisible même valeurs proches)
        last = " last" if i == len(pts) - 1 else ""
        bars += f'<td><div class="bb{last}" style="height:{h}mm"></div></td>'
    years = "".join(f'<td class="bl">{esc(str(an))}</td>' for an, _ in pts)
    return (f'<div class="chart"><div class="kicker">Prix médian maison, €/m²</div>'
            f'<table class="barchart"><tr class="rvals">{vals}</tr>'
            f'<tr class="rbars">{bars}</tr><tr class="ryears">{years}</tr></table></div>')


def _a_verifier(points: list[str]) -> str:
    pts = [p for p in points if p][:3]
    if not pts:
        return ""
    items = "".join(f"<li>{esc(p)}</li>" for p in pts)
    return f'<h2>Ce qu\'il reste à vérifier</h2><ul class="averif">{items}</ul>'


# ═══════════════════════════════════════ VARIANTE LIEN ═══════════════════════════════════════════
_NP = "non précisé dans l'annonce"


def rendu_lien(rapport: dict, *, plan_commune_html: str = "", releve_html: str = "") -> str:
    r = rapport or {}
    a = r.get("annonce") or {}
    typ = a.get("type")
    pieces = a.get("pieces")
    commune = a.get("commune")
    titre = (typ[0].upper() + typ[1:]) if typ else "Annonce"
    if isinstance(pieces, int) and typ in ("maison", "appartement"):
        titre += f" {pieces} pièces"
    if commune:
        titre += f" · {commune}"
    corps = entete(titre, releve_html, r.get("_ref_droite") or "")
    # ── ligne 1 : ce que dit l'annonce (gauche) + carte commune (droite) ──
    corps += (f'<div class="liengrid"><div>{_ce_que_dit(a)}</div>'
              f'<div class="lienmap">{plan_commune_html}</div></div>')
    # ── prix face au marché : deux lectures ──
    corps += _prix_face_marche(r.get("lectures") or {}, a)
    # ── la commune ──
    corps += _la_commune(r.get("commune") or {}, commune)
    # ── encart ──
    corps += _encart()
    return corps


def _ce_que_dit(a: dict) -> str:
    typ = a.get("type")
    prix = a.get("prix")
    prix_m2 = a.get("prix_m2")
    suff = f" · {_eur_m2(prix_m2)}" if isinstance(prix_m2, (int, float)) else ""
    rows = [
        ("Prix demandé", _eur(prix) or _NP),
        ("Type", esc(typ[0].upper() + typ[1:]) if typ else _NP),
    ]
    st, sh, pieces = a.get("surface_terrain"), a.get("surface_hab"), a.get("pieces")
    if typ == "terrain":
        rows.append(("Surface du terrain", (f"{_m2(st)}{suff}") if isinstance(st, (int, float)) else _NP))
    elif typ in ("maison", "appartement"):
        rows.append(("Surface habitable", (f"{_m2(sh)}{suff}") if isinstance(sh, (int, float)) else _NP))
        rows.append(("Pièces", esc(str(pieces)) if isinstance(pieces, int) else _NP))
        if typ == "maison":
            rows.append(("Terrain", _m2(st) if isinstance(st, (int, float)) else _NP))
    else:
        if isinstance(sh, (int, float)):
            rows.append(("Surface habitable", f"{_m2(sh)}{suff}"))
        if isinstance(st, (int, float)):
            rows.append(("Terrain", _m2(st)))
    vendeur = a.get("vendeur")
    if vendeur:
        rows.append(("Vendeur", esc(vendeur)))
    body = "".join(f'<tr><td class="k">{esc(k)}</td><td class="v">{v}</td></tr>' for k, v in rows)
    desc = a.get("description")
    extrait = ""
    if isinstance(desc, str) and desc.strip():
        court = desc.strip().replace("\n", " ")
        if len(court) > 150:
            court = court[:148].rstrip() + "…"
        extrait = (f'<p class="lienextr">« {esc(court)} » '
                   '<span class="muted">— extrait, texte complet sur l\'annonce</span></p>')
    lien = ""
    url = a.get("url")
    return (f'<div class="kicker">Ce que dit l\'annonce</div>'
            f'<table class="akv">{body}</table>{extrait}{lien}')


def _prix_face_marche(lectures: dict, a: dict) -> str:
    bati = lectures.get("bati") or {}
    fonc = lectures.get("fonciere") or {}
    cartes = ""
    if bati.get("calculable") and isinstance(bati.get("ecart_pct"), (int, float)):
        ec = bati["ecart_pct"]
        gros = (f"+{ec} %" if ec > 0 else f"{ec} %")
        ref = bati.get("referentiel_eur_m2")
        sub = (f"face aux {esc(bati.get('type_label_pluriel') or 'biens')} de la commune"
               + (f" : {_eur_m2(ref)}" if isinstance(ref, (int, float)) else ""))
        src = ""
        if isinstance(bati.get("n"), (int, float)):
            src = (f'<p class="anote">{_int(bati["n"])} ventes · {esc(bati.get("type_label_pluriel") or "")}'
                   + '</p>')
        cartes += ('<div class="lcard"><div class="kicker">Lecture bâti · au m² habitable</div>'
                   f'<div class="estbig neg">{esc(gros)}</div><div class="lcsub">{sub}</div>{src}</div>')
    if isinstance(fonc.get("valeur_eur"), (int, float)):
        tm, te = fonc.get("terrain_m2"), fonc.get("terrain_eur_m2")
        sub = (f"{_m2(tm)} × {_eur_m2(te)} de terrain nu" if isinstance(tm, (int, float))
               and isinstance(te, (int, float)) else "")
        concl = fonc.get("conclusion")
        cartes += ('<div class="lcard"><div class="kicker">Lecture foncière · valeur du terrain</div>'
                   f'<div class="estbig">{esc(_eur(fonc["valeur_eur"]))}</div>'
                   f'<div class="lcsub">{esc(sub)}</div>'
                   + (f'<p class="anote">{esc(concl)}</p>' if concl else "") + "</div>")
    if not cartes:
        return ('<h2>Prix face au marché</h2>'
                '<p class="anote">Comparaison au marché indisponible : le prix, la surface ou le repère '
                'communal manquent pour cette annonce.</p>')
    fiab = (f'<div class="estmeta">{_chip("p", "Fiabilité Limitée")} '
            '<span class="muted">repère communal, sans adresse précise · les deux lectures sont '
            'indicatives</span></div>')
    return (f'<h2>Prix face au marché</h2><div class="lgrid">{cartes}</div>{fiab}')


def _la_commune(c: dict, commune: str | None) -> str:
    if not c:
        return ""
    gauche = _kv([
        ("Ventes de maisons, 12 mois", _int(c.get("ventes_maison_12m"))),
        ("Prix médian maison", _eur_m2(c.get("median_maison_eur_m2"))),
        ("Terrain nu, médiane", _eur_m2(c.get("median_terrain_eur_m2"))),
        ("Évolution maisons sur 12 mois", _pct_signe(c.get("evolution_maison_12m_pct"))),
    ])
    aleas = c.get("aleas") or []
    droite = _kv([
        ("PLU", esc(c["plu_statut"]) if c.get("plu_statut") else None),
        ("Aléas principaux", esc(", ".join(aleas)) if aleas else None),
        ("Parc national", "partie du territoire en cœur de parc" if c.get("parc_national") else None),
        ("Permis déposés, 12 mois", _int(c.get("permis_12m"))),
    ])
    if not gauche and not droite:
        return ""
    titre = "La commune" + (f" · {commune}" if commune else "")
    return (f'<h2>{esc(titre)}</h2><div class="mkgrid"><div>{gauche}</div><div>{droite}</div></div>')


def _encart() -> str:
    return ('<div class="encart"><div class="encl">'
            '<div class="enct">Pour le rapport complet sur 2 pages</div>'
            '<div class="encd">Localisez la parcelle dans LABUSE : zonage, SDP restante, ventes '
            'comparables à moins d\'un kilomètre, risques, LiDAR.</div></div>'
            '<div class="encr">Analyser une annonce → C\'est cette parcelle</div></div>')
