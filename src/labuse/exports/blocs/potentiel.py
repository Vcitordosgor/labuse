"""Bloc « 3. Potentiel constructible ». Verdict déterministe (bloc potentiel), le bâti existant,
les scénarios (au sol / en hauteur à l'ÉGOUT / reconstruction). Surélévation lue à l'égout, jamais
au faîtage (Q6). Étape intermédiaire « 8 à 10 » jamais imprimée (EXPORTS-SOURCES §3)."""
from __future__ import annotations

from ..lignes import a, ligne, pied, val
from ..registre_fmt import fmt_m, fmt_m2, groupe
from ..rendu import esc, ligne_kv, note, section, table_kv
from ..verdicts import rendu_verdict, verdict_potentiel

IDS = ("potentiel_verdict", "emprise_batie_m2", "hauteur_bati_m", "n_batiments",
       "surface_libre_sol_m2", "sdp_residuelle_m2", "capacite_logements", "marge_surelevation_m")


def _sur_place(valeurs) -> str:
    lignes = [
        ligne(valeurs, "Emprise bâtie", "emprise_batie_m2", fmt_m2),
        ligne(valeurs, "Hauteur du bâti", "hauteur_bati_m", fmt_m),
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
    base_h = p.get("hauteur_base") if isinstance(p, dict) else None
    if base_h and str(base_h).startswith("faîtage"):
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
