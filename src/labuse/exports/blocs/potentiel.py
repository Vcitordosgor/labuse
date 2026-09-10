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
        val_h = f"{fmt_m(fait)} au faîtage" + (f" · {fmt_m(egout)} à l'égout" if egout is not None else "")
        hauteur_ligne = ligne_kv("Hauteur du bâti", f"{val_h} <em>(mesuré LiDAR HD)</em>", chip_span("s", "sourcé"))
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
        # RECETTE-10 T1 — le LiDAR mesure égout ET faîtage ; on garde la contrainte la plus serrée et
        # on DIT laquelle mord, en montrant les deux calculs (une règle d'égout comparée à l'égout, une
        # règle de faîtage comparée au faîtage — jamais l'une contre l'autre). Répare l'inversion T9→T1.
        marge = p.get("hauteur_marge_m")
        contrainte = p.get("hauteur_contrainte")                # « égout » | « faîtage »
        possible = p.get("surelevation_possible")
        contraintes = p.get("hauteur_contraintes") or []
        limite = ("le faîtage" if contrainte == "faîtage"
                  else "l'égout" if contrainte == "égout" else esc(str(contrainte)))
        detail_c = " · ".join(
            f"{c['base']} {fmt_m(c['mesure_m'])} mesuré contre {fmt_m(c['regle_m'])} réglementaires "
            f"(marge {fmt_m(c['marge_m'])})" for c in contraintes)
        if possible and marge is not None:
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"<strong>Surélévation possible</strong> — {fmt_m(marge)} disponibles, "
                          f"limité par {limite} (<strong>mesuré au LiDAR HD</strong>). "
                          + esc(detail_c) + ".", chip_span("s", "sourcé")))
        elif possible is False and marge is not None:
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"<strong>Pas de marge de surélévation</strong> — {fmt_m(marge)} au mieux, "
                          f"limité par {limite} (<strong>mesuré au LiDAR HD</strong>). "
                          + esc(detail_c) + ".", chip_span("s", "sourcé")))
    elif base_h and str(base_h).startswith("faîtage"):
        marge, regle, bati = p.get("hauteur_marge_m"), p.get("hauteur_regle_m"), p.get("hauteur_bati_m")
        possible = p.get("surelevation_possible")
        ref = "au faîtage" if base_h == "faîtage" else "au faîtage (règle estimée depuis l'égout)"
        if possible and marge is not None:
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"<strong>Surélévation possible</strong> — {fmt_m(marge)} disponibles "
                          f"sous la hauteur {ref}.", ""))
        elif possible is None and regle is not None and bati is not None:
            # règle de faîtage estimée depuis l'égout : marge incertaine, jamais un « non » ferme.
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"<strong>Surélévation à confirmer</strong> — {fmt_m(regle)} {ref} contre "
                          f"{fmt_m(bati)} bâtis (faîtage BD TOPO) : marge estimée {fmt_m(marge)}, à "
                          "vérifier au règlement (la zone ne fixe qu'une hauteur d'égout).", ""))
        elif possible is False and regle is not None and bati is not None:
            lignes.append(ligne_kv("En hauteur, bâti conservé",
                          f"<strong>Pas de marge de surélévation</strong> — {fmt_m(regle)} {ref} "
                          f"autorisés, {fmt_m(bati)} bâtis (faîtage) : {fmt_m(marge)} restants, "
                          "moins que la hauteur d'un niveau.", ""))
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
    corps += note("Pré-faisabilité sur règlement public. Une étude réglementaire par un "
                  "professionnel peut modifier ces valeurs.")
    corps += pied(valeurs, IDS)
    return section("3. Potentiel constructible", corps)
