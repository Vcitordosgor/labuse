"""Bloc « Apporteur » (document « Apporteur », gabarit maquette-apporteur.html). Un brief
confidentiel : la parcelle en un coup d'œil (volontairement pauvre en analyse), puis les questions
à poser sur le terrain — en champs REMPLISSABLES (WeasyPrint pdf_forms=True). Questionnaire
adaptatif (bâti / personne morale / usage industriel proche). Ajouts RELECTURE : mention de
non-mandat (A-a), date d'émission + validité 90 jours (A-b), prix d'achat historique D-a (A-c),
case « propriétaire joignable ». Émetteur = compte de l'utilisateur, non modifiable."""
from __future__ import annotations

from ..lignes import a, val
from ..registre_fmt import fmt_eur, fmt_eur_m2, fmt_m, fmt_m2
from ..rendu import aside, esc, ligne_kv, table_kv

# RECETTE-2 (S7) — un apporteur doit avoir la parcelle EN MAIN : au-delà de surface/zone/bâti, on
# ajoute la SDP résiduelle + capacité, les contraintes (aléas, prescriptions ER/EBC/DPU, PEB) et le
# prix de secteur (terrain nu + ancien). Ces ids existent déjà au catalogue (mêmes que le Résumé).
IDS = ("surface_parcelle_m2", "zone_plu_famille", "statut_plu", "emprise_batie_m2", "hauteur_bati_m",
       "n_batiments", "type_proprietaire", "prix_achat_historique_eur", "distance_arret_m",
       "sdp_residuelle_m2", "capacite_logements", "aleas_parcelle_liste",
       "er_emplacement_reserve", "ebc_classe", "dpu_perimetre", "peb_zone",
       "prix_terrain_secteur_eur_m2", "prix_sortie_bati_eur_m2")

# `appearance:auto` : les <input>/<textarea> deviennent des CHAMPS REMPLISSABLES avec
# render_pdf(forms=True) sur les builds WeasyPrint qui émettent les widgets AcroForm ; sinon ils
# s'impriment comme des lignes/champs à remplir à la main (le style border-bottom reste visible).
_INPUT = ('<input type="text" name="q" style="appearance:auto;width:100%;box-sizing:border-box;'
          'border:none;border-bottom:1px solid #1C2320;height:14pt;font:inherit">')
_AREA = ('<textarea name="q" style="appearance:auto;width:100%;box-sizing:border-box;'
         'border:1px solid #D8DED9;height:28pt;font:inherit"></textarea>')


def _q(label: str, hint: str = "", *, zone: bool = False) -> str:
    petit = f' <small>{esc(hint)}</small>' if hint else ""
    champ = _AREA if zone else _INPUT
    return f'<div class="q"><div class="l">{esc(label)}{petit}</div>{champ}</div>'


def _boxes(label: str, options: list[str]) -> str:
    cases = "".join(f'<label style="margin-right:12pt;font-size:9pt">'
                    f'<input type="checkbox" name="c" style="appearance:auto;vertical-align:-1pt">'
                    f' {esc(o)}</label>' for o in options)
    return f'<div class="q"><div class="l">{esc(label)}</div><div class="boxes">{cases}</div></div>'


def _sur_place(valeurs) -> str:
    bits = []
    if a(valeurs, "n_batiments"):
        bits.append(f"{int(val(valeurs, 'n_batiments'))} bâtiments")
    if a(valeurs, "emprise_batie_m2"):
        bits.append(f"{fmt_m2(val(valeurs, 'emprise_batie_m2'))} au sol")
    if a(valeurs, "hauteur_bati_m"):
        bits.append(f"environ {fmt_m(val(valeurs, 'hauteur_bati_m'))} de haut")
    return " · ".join(bits) or "terrain a priori nu"


def _contraintes(valeurs) -> str:
    """Une ligne « Contraintes » : aléas + prescriptions (ER/EBC/DPU) + zone de bruit (PEB). Vide → ''."""
    bits: list[str] = []
    liste = val(valeurs, "aleas_parcelle_liste") or []
    natures = [x.get("nature") or x.get("libelle") for x in liste
               if isinstance(x, dict) and (x.get("nature") or x.get("libelle"))]
    bits += list(dict.fromkeys(natures))
    if a(valeurs, "dpu_perimetre"):
        bits.append("préemption (DPU)")
    if a(valeurs, "er_emplacement_reserve"):
        bits.append("emplacement réservé")
    if a(valeurs, "ebc_classe"):
        bits.append("espace boisé classé")
    peb = val(valeurs, "peb_zone")
    if peb:
        bits.append(f"bruit d'aéroport (PEB {esc(str(peb))})" if not isinstance(peb, dict)
                    else f"bruit d'aéroport (PEB {esc(str(peb.get('zone') or peb.get('libelle') or ''))})")
    return " · ".join(b for b in bits if b)


def _coup_d_oeil(valeurs, ctx) -> str:
    lignes = []
    if a(valeurs, "surface_parcelle_m2"):
        lignes.append(ligne_kv("Surface", fmt_m2(val(valeurs, "surface_parcelle_m2")), ""))
    if a(valeurs, "zone_plu_famille"):
        plu = val(valeurs, "statut_plu")
        suite = (" — " + esc(plu["libelle"])) if isinstance(plu, dict) and plu.get("libelle") else (
            " — urbaine, constructible" if str(val(valeurs, "zone_plu_famille")).upper() in ("U", "AU") else "")
        lignes.append(ligne_kv("Zone", esc(str(val(valeurs, "zone_plu_famille"))) + suite, ""))
    lignes.append(ligne_kv("Sur place", esc(_sur_place(valeurs)), ""))
    # RECETTE-2 (S7) — SDP résiduelle + capacité : ce que l'apporteur peut annoncer comme potentiel.
    if a(valeurs, "sdp_residuelle_m2"):
        cap = f" · ~{esc(str(val(valeurs, 'capacite_logements')))} logements" if a(valeurs, "capacite_logements") else ""
        lignes.append(ligne_kv("Potentiel", f"{fmt_m2(val(valeurs, 'sdp_residuelle_m2'))} de plancher résiduel{cap}", ""))
    elif a(valeurs, "capacite_logements"):
        lignes.append(ligne_kv("Potentiel", esc(f"~{val(valeurs, 'capacite_logements')} logements"), ""))
    # RECETTE-2 (S7) — contraintes en une ligne (jamais un vide : ligne omise si rien).
    contr = _contraintes(valeurs)
    if contr:
        lignes.append(ligne_kv("Contraintes", contr, ""))
    # RECETTE-2 (S7) — prix de secteur : terrain nu et/ou ancien bâti (repères de négociation).
    prix_bits = []
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("prix_m2"):
        prix_bits.append(f"terrain nu {fmt_eur_m2(tn['prix_m2'])}")
    anc = val(valeurs, "prix_sortie_bati_eur_m2")
    if isinstance(anc, dict) and anc.get("median"):
        prix_bits.append(f"ancien {fmt_eur_m2(anc['median'])}")
    if prix_bits:
        lignes.append(ligne_kv("Prix de secteur", esc(" · ".join(prix_bits)), ""))
    if a(valeurs, "type_proprietaire"):
        lignes.append(ligne_kv("Propriétaire", esc(str(val(valeurs, "type_proprietaire")).split(" (SIREN")[0]), ""))
    prox = val(valeurs, "distance_arret_m")
    if isinstance(prox, dict) and isinstance(prox.get("arret"), dict) and prox["arret"].get("distance_m") is not None:
        lignes.append(ligne_kv("Accès", esc(f"arrêt de bus à {prox['arret']['distance_m']} m"), ""))
    if a(valeurs, "prix_achat_historique_eur"):
        pa = val(valeurs, "prix_achat_historique_eur")
        lignes.append(ligne_kv("Prix d'achat de la parcelle",
                               fmt_eur(pa["valeur"] if isinstance(pa, dict) else pa), ""))
    return table_kv(lignes)


def rendu(valeurs, ctx=None) -> str:
    ctx = ctx or {}
    idu = ctx.get("idu", "")
    adresse = ctx.get("adresse", "")
    is_bati = ctx.get("is_bati", False)
    is_pm = ctx.get("is_pm", False)
    industriel = ctx.get("industriel_proche", False)

    # RECETTE-2 (S7) — la date d'émission / validité (90 j) passe en TÊTE, discrète : c'est une
    # métadonnée du brief, pas de l'identité de l'émetteur.
    emis = ""
    if ctx.get("emission"):
        emis = (f'<p class="idu">Émis le {esc(ctx["emission"])}'
                + (f" — valable 90 jours (jusqu'au {esc(ctx['validite'])})" if ctx.get("validite") else "")
                + '</p>')
    h = ('<div class="confidential">Confidentiel — ne pas transmettre au propriétaire ni à des '
         'tiers.</div>'
         '<div class="brand"><span class="wordmark">LABUSE</span>'
         '<span class="kind">Brief apporteur</span></div>'
         '<h1>Un terrain à sonder</h1>'
         + (f'<p class="address">{esc(adresse)}</p>' if adresse else "")
         + f'<p class="idu">{esc(idu)}</p>'
         + emis)
    # A-a — mention de non-mandat
    h += aside("<strong>Ce document ne vaut pas mandat.</strong> Vous n'êtes pas habilité à "
               "négocier, à faire une offre ni à engager l'émetteur.", "rose")
    h += "<h3>La parcelle en un coup d'œil</h3>" + _coup_d_oeil(valeurs, ctx)
    # RECETTE-2 (S7) — la section « Qui vous envoie ce brief » (émetteur/contact) est RETIRÉE
    # (décision Vic). L'émetteur reste l'auteur du document, il n'a pas à se présenter dedans.
    h += ('<p class="note">Ce brief contient ce qui est public sur la parcelle. Ce qui manque, '
          'vous seul pouvez l\'obtenir : c\'est l\'objet des pages suivantes.</p>')

    # ── PAGE 2 — les questions (remplissables) ──
    q = '<div class="pb"></div><h2>Ce que nous avons besoin de savoir</h2>'
    q += "<h3>Qui décide</h3>"
    if is_pm:
        q += _q("La parcelle est détenue par une société — qui la contrôle, et qui décide de vendre ?",
                "Gérant, associés, nombre de signataires ?", zone=True)
    else:
        q += _q("Qui détient réellement la parcelle, et qui décide de vendre ?",
                "Indivision, succession en cours ? Combien de signataires ?", zone=True)
    q += _boxes("Tous les décideurs sont-ils d'accord pour vendre ?", ["Oui", "Non", "Pas tous", "Ne sait pas"])
    q += _q("Un notaire est-il déjà saisi ? Lequel ?")
    q += "<h3>La vente</h3>"
    q += _q("Le propriétaire est-il vendeur ? Depuis quand, et pourquoi ?",
            "Succession, départ, besoin de liquidités, lassitude…", zone=True)
    q += _q("Quel prix attend-il ? Quel prix a-t-il déjà refusé ?")
    q += _q("Qui est déjà passé ?", "Agence, promoteur, particulier — offres reçues et montants si connus", zone=True)
    q += _boxes("Un mandat de vente est-il en cours ?", ["Non", "Simple", "Exclusif"])
    # A-c question : propriétaire joignable et par quel canal
    q += _q("Le propriétaire est-il joignable, et par quel canal ?", "Téléphone, courrier, sur place, via un tiers ?")

    # bloc adaptatif — bâti et occupation
    if is_bati:
        q += "<h3>Le bâti et son occupation</h3>"
        q += _boxes("Les bâtiments sont-ils occupés ? Par qui ?", ["Vides", "Le propriétaire", "Des locataires", "Une activité"])
        q += _q("Sous quel bail ? Fin de bail, loyers perçus.", "Un bail commercial en cours change tout : notez-le en premier.", zone=True)
        q += _q("État général du bâti ; diagnostics disponibles (amiante, plomb) ?", zone=True)

    # ── PAGE 3 ──
    q += '<div class="pb"></div><h3>Le sol</h3>'
    hint_sol = "Cuves enterrées, remblais, pollution connue ?"
    if industriel:
        hint_sol = ("Un établissement classé est signalé à proximité ; un ancien garage, dépôt ou "
                    "station-service sur la parcelle changerait le coût.")
    q += _q("Ancien usage du site ?", hint_sol, zone=True)
    q += "<h3>Ce que les papiers diraient</h3>"
    q += _q("Servitudes de passage, litiges de voisinage, bornage récent, empiètements connus ?", zone=True)
    q += _q("Hypothèques, procédures en cours ?")
    q += _q("Titre de propriété disponible ? Origine : achat, donation, succession, année ?")
    q += "<h3>Le voisinage et la mairie</h3>"
    q += _q("Les parcelles voisines sont-elles à vendre ? Du même propriétaire ?", zone=True)
    q += _q("Que dit la mairie de ce secteur ? Que disent les voisins ?", "Projets connus, oppositions, associations.", zone=True)
    q += ('<h3>Quatre photos</h3><p class="note">Depuis la voie, aux quatre coins, en tenant la '
          'parcelle au centre.</p>')
    q += "<h3>Votre retour</h3>"
    q += '<div class="cols">' + _q("Date de la visite") + _q("Vos coordonnées") + "</div>"
    q += _q("Remarques libres", zone=True)
    return h + q
