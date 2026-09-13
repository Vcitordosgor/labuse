"""Bloc « 3. Potentiel constructible ». Verdict déterministe (bloc potentiel), le bâti existant,
les scénarios (au sol / en hauteur à l'ÉGOUT / reconstruction). Surélévation lue à l'égout, jamais
au faîtage (Q6). Étape intermédiaire « 8 à 10 » jamais imprimée (EXPORTS-SOURCES §3)."""
from __future__ import annotations

from ..lignes import a, ligne, pied, val
from ..registre_fmt import fmt_m, fmt_m2, groupe
from ..rendu import chip_span, esc, ligne_kv, note, section, table_kv
from ..verdicts import rendu_verdict, verdict_potentiel

IDS = ("potentiel_verdict", "emprise_batie_m2", "hauteur_bati_m", "n_batiments",
       "surface_libre_sol_m2", "sdp_residuelle_m2", "capacite_logements", "marge_surelevation_m")


def _sur_place(valeurs) -> str:
    # RECETTE-9 T9 — la hauteur du bâti passe d'`estimé` (BD TOPO) à `sourcé` (LiDAR HD) quand la
    # parcelle a été mesurée : on rend alors le faîtage MESURÉ + l'ÉGOUT (que BD TOPO ne donne pas),
    # avec la pastille « sourcé ». Sinon la ligne registre classique (estimé).
    p = val(valeurs, "potentiel_verdict") or {}
    lidar_h = isinstance(p, dict) and p.get("hauteur_nature") == "sourcé" and p.get("hauteur_faitage_lidar_m") is not None
    hauteur_ligne = ligne(valeurs, "Hauteur du bâti", "hauteur_bati_m", fmt_m)
    if lidar_h:
        fait, egout = p.get("hauteur_faitage_lidar_m"), p.get("hauteur_egout_lidar_m")
        # RECETTE-12 D3 — la DATE de survol n'apparaît QU'UNE FOIS dans le §3 (sur la ligne de
        # hauteur/scénario, plus une fois dans les sources §10). Ici, la mesure brute cite juste
        # « mesuré au LiDAR HD » SANS la date (elle était répétée quatre fois).
        mention = "mesuré au LiDAR HD"
        # RECETTE-11 A4 — un permis autorisé après le survol : la mesure peut être dépassée.
        permis = p.get("hauteur_permis_posterieur")
        caveat = (f" — mesure antérieure au permis du {esc(str(permis))}, possiblement dépassée"
                  if permis else "")
        val_h = f"{fmt_m(fait)} au faîtage" + (f" · {fmt_m(egout)} à l'égout" if egout is not None else "")
        hauteur_ligne = ligne_kv("Hauteur du bâti", f"{val_h} <em>({mention}{caveat})</em>",
                                 chip_span("s", "sourcé"))
    lignes = [
        ligne(valeurs, "Emprise bâtie", "emprise_batie_m2", fmt_m2),
        hauteur_ligne,
        ligne(valeurs, "Nombre de bâtiments", "n_batiments", lambda v: str(int(v))),
        ligne(valeurs, "Surface au sol libre", "surface_libre_sol_m2", fmt_m2),
    ]
    lignes = [x for x in lignes if x]
    return ("<h3>Ce qu'il y a dessus</h3>" + table_kv(lignes)) if lignes else ""


def _scenarios(valeurs) -> str:
    p = val(valeurs, "potentiel_verdict") or {}
    if isinstance(p, dict) and p.get("cause"):
        return ""      # terrain non constructible (cause) → aucun scénario (jamais un faux constructible)
    lignes = []
    # au sol
    if a(valeurs, "sdp_residuelle_m2"):
        sdp = val(valeurs, "sdp_residuelle_m2")
        pct = p.get("pct_consomme")
        detail = f"<strong>{fmt_m2(sdp)} de surface de plancher résiduelle</strong>"
        if pct:
            detail += f" — {esc(str(pct))} % de la surface autorisée déjà consommés."
        lignes.append(ligne_kv("Au sol, bâti conservé", detail, ""))
    # en hauteur — RECETTE-7 (E1) : comparé au FAÎTAGE (le bâti BD TOPO est mesuré au faîtage) ;
    # omise si les hauteurs ne sont pas servies (parcelle non bâtie).
    # RECETTE-9 (T9) : quand le LiDAR HD a MESURÉ l'égout (base « égout mesuré (LiDAR HD) »), on
    # compare enfin un ÉGOUT MESURÉ à la règle d'égout — la marge devient une MESURE, pas une
    # soustraction sur un faîtage BD TOPO incertain (la vraie réparation de E1).
    base_h = p.get("hauteur_base") if isinstance(p, dict) else None
    if base_h and "mesuré (LiDAR HD)" in str(base_h):
        # RECETTE-11 A6 — on ne rend PLUS de verdict de faisabilité (« possible »/« non identifiée ») :
        # la phrase s'arrête aux hauteurs mesurées, à la règle, à la marge et à la contrainte qui mord
        # (le lecteur conclut). RECETTE-10 T1 : les deux contraintes, la plus serrée nommée, les deux
        # calculs montrés (règle d'égout vs égout, règle de faîtage vs faîtage — jamais l'une vs l'autre).
        marge = p.get("hauteur_marge_m")
        contrainte = p.get("hauteur_contrainte")                # « égout » | « faîtage »
        contraintes = p.get("hauteur_contraintes") or []
        survol = p.get("hauteur_survol")
        # RECETTE-12 D3 — la phrase de hauteur SUR UNE LIGNE, au format arbitré (Q7) : « Égout X mesuré
        # (règle Y, marge Z) · faîtage … — contrainte qui mord : … ». La date de survol UNE SEULE FOIS,
        # ici (l'autre occurrence est dans les sources §10). Plus de « X sous la hauteur réglementaire ».
        mention = "mesuré au LiDAR HD" + (f", survol de {esc(str(survol))}" if survol else "")
        limite = ("le faîtage" if contrainte == "faîtage"
                  else "l'égout" if contrainte == "égout" else esc(str(contrainte)))
        _cap = lambda s: (s[:1].upper() + s[1:]) if s else s   # « égout » → « Égout »
        detail_c = " · ".join(
            f"{_cap(str(c['base']))} {fmt_m(c['mesure_m'])} mesuré "
            f"(règle {fmt_m(c['regle_m'])}, marge {fmt_m(c['marge_m'])})" for c in contraintes)
        if marge is not None:
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"{esc(detail_c)} — contrainte qui mord : {limite} "
                          f"<em>({mention})</em>.", chip_span("s", "sourcé")))
    elif base_h and str(base_h).startswith("faîtage"):
        # RECETTE-11 A6 — hauteur BD TOPO (pas de LiDAR) : on rend la marge et la règle, sans verdict.
        marge, regle, bati = p.get("hauteur_marge_m"), p.get("hauteur_regle_m"), p.get("hauteur_bati_m")
        ref = "au faîtage" if base_h == "faîtage" else "au faîtage (règle estimée depuis l'égout)"
        if marge is not None and regle is not None and bati is not None:
            estimee = base_h != "faîtage"
            phrase = (f"<strong>{fmt_m(marge)}</strong> {'estimés ' if estimee else ''}sous la hauteur "
                      f"{ref} — {fmt_m(regle)} réglementaires contre {fmt_m(bati)} bâtis (faîtage BD TOPO)")
            if estimee:
                phrase += " ; à vérifier au règlement (la zone ne fixe qu'une hauteur d'égout)"
            lignes.append(ligne_kv("En hauteur, bâti conservé", phrase + ".", ""))
        elif marge is not None:
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"<strong>{fmt_m(marge)}</strong> sous la hauteur {ref}.", ""))
    # reconstruction
    if a(valeurs, "capacite_logements"):
        cap = val(valeurs, "capacite_logements")
        lignes.append(ligne_kv("Reconstruction après démolition",
                               f"<strong>{esc(str(cap))}</strong> — démolition à chiffrer.", ""))
    if not lignes:
        return ""
    entete = '<tr><th>Scénario</th><th>Résultat</th><th></th></tr>'
    return "<h3>Façons de construire ici</h3>" + table_kv(lignes, entete)


def rendu(valeurs) -> str:
    corps = rendu_verdict(verdict_potentiel(valeurs)) + _sur_place(valeurs) + _scenarios(valeurs)
    if not corps.strip():
        return ""      # rien d'évaluable → section omise (aucun bloc creux)
    note_txt = ("Pré-faisabilité sur règlement public. Une étude réglementaire par un "
                "professionnel peut modifier ces valeurs.")
    # RECETTE-12 D3 — la source LiDAR HD (avec sa date de survol) est citée dans les SOURCES (§10) et
    # la date figure déjà sur la ligne de hauteur : plus de répétition ici (elle apparaissait 4 fois).
    corps += note(note_txt)
    corps += pied(valeurs, IDS)
    return section("3. Potentiel constructible", corps)
