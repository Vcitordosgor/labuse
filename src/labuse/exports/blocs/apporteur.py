"""Bloc « Apporteur » (document « Apporteur », gabarit maquette-apporteur-v3.html — version validée
Vic, RECETTE-3 T1). Un brief confidentiel : la parcelle en un coup d'œil (volontairement pauvre en
analyse) avec son PLAN DE SITUATION (parcelle + voisines du même propriétaire) et sa DERNIÈRE VENTE
datée, puis les questions à poser sur le terrain — en champs REMPLISSABLES (WeasyPrint pdf_forms=True).

RECETTE-3 (T1) : un SEUL bandeau (confidentiel + non-mandat fusionnés) ; plan de situation ; ligne
« À côté » (Blocs fonciers) ; « Dernière vente » datée+chiffrée, omise si inconnue (règle S8) ; le
questionnaire garde son fond, avec le CONTACT en première question, trois questions marquées
« l'essentiel », les photos envoyées par message en citant la référence, et une phrase courte sous
chaque section qui dit pourquoi on la pose. Questionnaire adaptatif (bâti / personne morale / usage
industriel proche). Émetteur = compte de l'utilisateur, non modifiable."""
from __future__ import annotations

import re

from ..lignes import a, val
from ..registre_fmt import fmt_eur, fmt_eur_m2, fmt_m, fmt_m2
from ..rendu import esc, ligne_kv, note, table_kv

# RECETTE-2 (S7) — un apporteur doit avoir la parcelle EN MAIN : au-delà de surface/zone/bâti, on
# ajoute la SDP résiduelle + capacité, les contraintes (aléas, prescriptions ER/EBC/DPU, PEB) et le
# prix de secteur (terrain nu + ancien). Ces ids existent déjà au catalogue (mêmes que le Résumé).
IDS = ("surface_parcelle_m2", "zone_plu_famille", "reglement_plu_bloc", "statut_plu",
       "emprise_batie_m2", "hauteur_bati_m",
       "n_batiments", "type_proprietaire", "prix_achat_historique_eur", "distance_arret_m",
       "sdp_residuelle_m2", "capacite_logements", "aleas_parcelle_liste", "potentiel_verdict",
       "er_emplacement_reserve", "ebc_classe", "dpu_perimetre", "peb_zone",
       "prix_terrain_secteur_eur_m2", "prix_sortie_bati_eur_m2")

# `appearance:auto` : les <input>/<textarea> deviennent des CHAMPS REMPLISSABLES avec
# render_pdf(forms=True) sur les builds WeasyPrint qui émettent les widgets AcroForm ; sinon ils
# s'impriment comme des lignes/champs à remplir à la main (le style border-bottom reste visible).
_INPUT = ('<input type="text" name="q" style="appearance:auto;width:100%;box-sizing:border-box;'
          'border:none;border-bottom:1px solid #1C2320;height:14pt;font:inherit">')
_AREA = ('<textarea name="q" style="appearance:auto;width:100%;box-sizing:border-box;'
         'border:1px solid #D8DED9;height:28pt;font:inherit"></textarea>')

_MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]

# RECETTE-5 (V20d) — le langage de plomberie GPU à retirer de la ligne « Zone » de l'apporteur.
_RE_GPU_PLOMBERIE = re.compile(r"\s*—?\s*Document à jour du GPU.*$", re.IGNORECASE)


def _mois_an(iso) -> str:
    """« 2019-03-15 » → « mars 2019 ». Chaîne vide si non parsable (la date est alors omise)."""
    try:
        y, m = str(iso).split("T")[0].split("-")[:2]
        return f"{_MOIS[int(m)]} {y}"
    except Exception:  # noqa: BLE001
        return ""


def _q(label: str, hint: str = "", *, zone: bool = False, cle: str = "") -> str:
    badge = f'<span class="cle">{esc(cle)}</span>' if cle else ""
    petit = f' <small>{esc(hint)}</small>' if hint else ""
    champ = _AREA if zone else _INPUT
    return f'<div class="q"><div class="l">{badge}{esc(label)}{petit}</div>{champ}</div>'


def _duo(label: str, *, cle: str = "", hint: str = "") -> str:
    """Une question à DEUX champs côte à côte (contact nom+coordonnées, prix attendu+refusé)."""
    badge = f'<span class="cle">{esc(cle)}</span>' if cle else ""
    petit = f' <small>{esc(hint)}</small>' if hint else ""
    return (f'<div class="q"><div class="l">{badge}{esc(label)}{petit}</div>'
            f'<div class="duo">{_INPUT}{_INPUT}</div></div>')


def _boxes(label: str, options: list[str]) -> str:
    cases = "".join(f'<label style="margin-right:12pt;font-size:9pt">'
                    f'<input type="checkbox" name="c" style="appearance:auto;vertical-align:-1pt">'
                    f' {esc(o)}</label>' for o in options)
    return f'<div class="q"><div class="l">{esc(label)}</div><div class="boxes">{cases}</div></div>'


def _aide(texte: str) -> str:
    """La phrase courte SOUS un titre de section : pourquoi on pose ces questions."""
    return f'<p class="aide">{esc(texte)}</p>'


def _sur_place(valeurs) -> str:
    bits = []
    if a(valeurs, "n_batiments"):
        bits.append(f"{int(val(valeurs, 'n_batiments'))} bâtiments")
    if a(valeurs, "emprise_batie_m2"):
        bits.append(f"{fmt_m2(val(valeurs, 'emprise_batie_m2'))} au sol")
    if a(valeurs, "hauteur_bati_m"):
        # RECETTE-11 A3 — devant une valeur MESURÉE (LiDAR HD), plus d'« environ » : on donne le
        # faîtage mesuré et sa date de survol. « environ » ne reste que sur une estimation BD TOPO.
        p = val(valeurs, "potentiel_verdict") or {}
        mesure = isinstance(p, dict) and p.get("hauteur_nature") == "sourcé" \
            and p.get("hauteur_faitage_lidar_m") is not None
        if mesure:
            survol = p.get("hauteur_survol")
            mention = "mesuré au LiDAR HD" + (f", survol de {survol}" if survol else "")
            bits.append(f"{fmt_m(p['hauteur_faitage_lidar_m'])} au faîtage ({mention})")
        else:
            bits.append(f"environ {fmt_m(val(valeurs, 'hauteur_bati_m'))} de haut")
    return " · ".join(bits) or "terrain a priori nu"


def _contraintes(valeurs) -> str:
    """Une ligne « Ce qui gêne » : aléas + prescriptions (ER/EBC/DPU) + zone de bruit (PEB). Vide → ''."""
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


def _a_cote(voisines: dict | None) -> str:
    """RECETTE-3 (T1) — « À côté » : parcelles voisines du même propriétaire (Blocs fonciers). '' si aucune."""
    v = voisines or {}
    n = v.get("n") or 0
    if not n:
        return ""
    refs = ", ".join(m["ref"] for m in v.get("membres", [])[:4] if m.get("ref"))
    reste = " …" if n > 4 else ""
    txt = (f"{n} parcelle{'s' if n > 1 else ''} voisine{'s' if n > 1 else ''} au même propriétaire"
           + (f" ({refs}{reste})" if refs else ""))
    tot = v.get("surface_totale_m2")
    if tot:
        txt += f" — {fmt_m2(tot)} de plus"
    return txt


def _coup_d_oeil(valeurs, ctx) -> str:
    lignes = []
    if a(valeurs, "surface_parcelle_m2"):
        lignes.append(ligne_kv("Surface", fmt_m2(val(valeurs, "surface_parcelle_m2")), ""))
    if a(valeurs, "zone_plu_famille"):
        plu = val(valeurs, "statut_plu")
        libelle = plu.get("libelle") if isinstance(plu, dict) else None
        if libelle:
            # RECETTE-5 (V20d) — on RETIRE le langage de plomberie « Document à jour du GPU — c'est
            # celui qui fait foi » : l'apporteur n'a que faire de la traçabilité GPU (on garde « PLU
            # approuvé le … »). Le reste des documents/écrans, eux, gardent leur mention.
            libelle = _RE_GPU_PLOMBERIE.sub("", libelle).rstrip(" —·").strip()
        # RECETTE-8 W15 — le CODE de zone réel (« Zone Um (famille U) »), le MÊME libellé partagé
        # que le Dossier (verdicts.zone_libelle) : plus de « Zone U » tronqué ici pendant que le
        # Dossier dit « Zone Um » — une donnée, une réponse dans les deux documents.
        from ..verdicts import zone_libelle
        z = zone_libelle(valeurs) or f"Zone {val(valeurs, 'zone_plu_famille')}"
        # RECETTE-9 T4 — le libellé partagé commence par « Zone … » (juste pour les phrases du
        # Dossier : « Zone Um (famille U) — … »). Ici la CLÉ de la ligne est déjà « Zone » → on
        # retire le préfixe redondant, sinon « Zone : Zone Um (famille U) » (le doublon W15).
        z_valeur = re.sub(r"^Zone\s+", "", z)
        suite = (" — " + esc(libelle)) if libelle else (
            " — urbaine, constructible" if str(val(valeurs, "zone_plu_famille")).upper() in ("U", "AU") else "")
        lignes.append(ligne_kv("Zone", esc(z_valeur) + suite, ""))
    lignes.append(ligne_kv("Sur place", esc(_sur_place(valeurs)), ""))
    # RECETTE-2 (S7) — SDP résiduelle + capacité : ce que l'apporteur peut annoncer comme potentiel.
    # RECETTE-5 (V20a) — un ZÉRO ne s'imprime pas : « 0 m² de plancher restant » (SDP nulle) n'a aucun
    # sens pour l'apporteur. La ligne se REFORMULE sur la capacité si elle existe, sinon DISPARAÎT.
    if a(valeurs, "sdp_residuelle_m2") and (val(valeurs, "sdp_residuelle_m2") or 0) > 0:
        cap = f" · ~{esc(str(val(valeurs, 'capacite_logements')))} logements" if a(valeurs, "capacite_logements") else ""
        lignes.append(ligne_kv("Ce qu'on peut y bâtir", f"{fmt_m2(val(valeurs, 'sdp_residuelle_m2'))} de plancher restant{cap}", ""))
    elif a(valeurs, "capacite_logements"):
        lignes.append(ligne_kv("Ce qu'on peut y bâtir", esc(f"~{val(valeurs, 'capacite_logements')} logements"), ""))
    # RECETTE-2 (S7) — contraintes en une ligne (jamais un vide : ligne omise si rien).
    contr = _contraintes(valeurs)
    if contr:
        lignes.append(ligne_kv("Ce qui gêne", contr, ""))
    # RECETTE-2 (S7) — prix de secteur : terrain nu et/ou ancien bâti (repères de négociation).
    prix_bits = []
    tn = val(valeurs, "prix_terrain_secteur_eur_m2")
    if isinstance(tn, dict) and tn.get("prix_m2"):
        prix_bits.append(f"terrain nu {fmt_eur_m2(tn['prix_m2'])}")
    anc = val(valeurs, "prix_sortie_bati_eur_m2")
    if isinstance(anc, dict) and anc.get("median"):
        prix_bits.append(f"ancien {fmt_eur_m2(anc['median'])}")
    if prix_bits:
        lignes.append(ligne_kv("Prix du secteur", esc(" · ".join(prix_bits)), ""))
    # RECETTE-3 (T1) — DERNIÈRE VENTE datée + chiffrée (DVF). Règle S8 : si inconnue, la ligne
    # ne s'imprime PAS (jamais un « — » ni un vide).
    if a(valeurs, "prix_achat_historique_eur"):
        pa = val(valeurs, "prix_achat_historique_eur")
        montant = pa["valeur"] if isinstance(pa, dict) else pa
        mois = _mois_an(pa.get("date_mutation")) if isinstance(pa, dict) else ""
        valeur_html = (f"{esc(mois)} — {fmt_eur(montant)}" if mois else fmt_eur(montant))
        lignes.append(ligne_kv("Dernière vente", valeur_html, ""))
    if a(valeurs, "type_proprietaire"):
        lignes.append(ligne_kv("Propriétaire", esc(str(val(valeurs, "type_proprietaire")).split(" (SIREN")[0]), ""))
    # RECETTE-3 (T1) — « À côté » : voisines du même propriétaire (Blocs fonciers). Omise si aucune.
    a_cote = _a_cote((ctx or {}).get("voisines"))
    if a_cote:
        lignes.append(ligne_kv("À côté", esc(a_cote), ""))
    prox = val(valeurs, "distance_arret_m")
    if isinstance(prox, dict) and isinstance(prox.get("arret"), dict) and prox["arret"].get("distance_m") is not None:
        lignes.append(ligne_kv("Accès", esc(f"arrêt de bus à {prox['arret']['distance_m']} m"), ""))
    return table_kv(lignes)


def _plan_situation(ctx) -> str:
    """RECETTE-3 (T1) — le plan de situation : image ortho (parcelle + voisines) si disponible,
    sinon un cadre neutre légendé (jamais d'erreur, jamais un cadre muet)."""
    plan = (ctx or {}).get("plan")
    if plan and plan.get("img"):
        cap = esc(plan.get("attribution") or "")
        return (f'<div class="plan"><img src="{plan["img"]}" alt="Plan de situation">'
                + (f'<div class="cap">Plan de situation — la parcelle (contour) et ses voisines · {cap}</div>'
                   if cap else '<div class="cap">Plan de situation — la parcelle (contour) et ses voisines</div>')
                + '</div>')
    return ('<div class="plan"><div class="ph">Plan de situation — la parcelle et ses voisines '
            '(fond cartographique momentanément indisponible)</div></div>')


def rendu(valeurs, ctx=None) -> str:
    ctx = ctx or {}
    idu = ctx.get("idu", "")
    adresse = ctx.get("adresse", "")
    is_bati = ctx.get("is_bati", False)
    is_pm = ctx.get("is_pm", False)
    industriel = ctx.get("industriel_proche", False)
    voisines = ctx.get("voisines") or {}

    # RECETTE-2 (S7) — la date d'émission / validité (90 j) passe en TÊTE, discrète : c'est une
    # métadonnée du brief, pas de l'identité de l'émetteur.
    emis = ""
    if ctx.get("emission"):
        emis = (f'<p class="emis">Émis le {esc(ctx["emission"])}'
                + (f" — valable 90 jours (jusqu'au {esc(ctx['validite'])})" if ctx.get("validite") else "")
                + '</p>')
    # RECETTE-6 (F1) — le titre SUIT le contenu : un terrain nu se « sonde », un bien déjà bâti aussi
    # mais on ne l'appelle pas « terrain ». Le brief adaptait déjà ses questions (bâti / PM / industriel)
    # mais gardait un titre « terrain » démenti par la ligne « 2 bâtiments · 151 m² au sol ».
    titre = "Un bien bâti à sonder" if is_bati else "Un terrain à sonder"
    h = ('<div class="brand"><span class="wordmark">LABUSE</span>'
         '<span class="kind">Brief apporteur</span></div>'
         + f'<h1>{esc(titre)}</h1>'
         + (f'<p class="address">{esc(adresse)}</p>' if adresse else "")
         + f'<p class="idu">{esc(idu)}</p>'
         + emis)
    # RECETTE-3 (T1) — UN SEUL bandeau : confidentiel + non-mandat fusionnés (avant : deux blocs).
    h += ('<div class="confidential">Confidentiel, et sans mandat. Ne transmettez ce document ni au '
          'propriétaire ni à des tiers. Vous n\'êtes pas habilité à négocier, à faire une offre, ni à '
          'engager qui que ce soit.</div>')
    h += "<h3>La parcelle</h3>" + _coup_d_oeil(valeurs, ctx)
    # RECETTE-3 (T1) — le plan de situation (parcelle + voisines, ortho IGN).
    h += _plan_situation(ctx)
    # RECETTE-2 (S7) — la section « Qui vous envoie ce brief » (émetteur/contact) est RETIRÉE.
    h += note("Voilà ce qui est public. Le reste — qui décide, à quel prix, ce que cachent les "
              "papiers — ne s'obtient que sur place. C'est ce que les pages suivantes vous demandent.")

    # ── PAGE 2 — Qui décide / La vente ──
    q = '<div class="pb"></div><h3>Qui décide</h3>'
    q += _aide("Une parcelle en indivision, ce sont autant de signatures que d'héritiers — c'est la "
               "première chose qui fait échouer une vente.")
    # RECETTE-3 (T1) — le CONTACT en PREMIÈRE question, marqué « l'essentiel ».
    q += _duo("Nom et coordonnées de la personne à qui vous avez parlé", cle="L'ESSENTIEL")
    if is_pm:
        q += _q("La parcelle est détenue par une société — qui la contrôle, et qui décide de vendre ?",
                "Gérant, associés, nombre de signataires ?", zone=True)
    else:
        q += _q("Qui détient réellement la parcelle, et qui décide de vendre ?",
                "Indivision, succession en cours ? Combien de signataires ?", zone=True)
    q += _boxes("Tous les décideurs sont-ils d'accord pour vendre ?", ["Oui", "Non", "Pas tous", "Ne sait pas"])
    q += _q("Un notaire est-il déjà saisi ? Lequel ?")

    q += "<h3>La vente</h3>"
    q += _aide("Le prix déjà refusé vaut plus qu'un prix annoncé : il dit le plancher réel.")
    # RECETTE-3 (T1) — le PRIX, deuxième « l'essentiel ».
    q += _duo("Quel prix attend-il ? Quel prix a-t-il déjà refusé ?", cle="L'ESSENTIEL")
    q += _q("Est-il vendeur ? Depuis quand, et pourquoi ?",
            "Succession, départ, besoin de liquidités, lassitude…", zone=True)
    q += _q("Qui est déjà passé ?", "Agence, promoteur, particulier — offres reçues et montants si connus", zone=True)
    q += _boxes("Un mandat de vente est-il en cours ?", ["Non", "Simple", "Exclusif"])
    q += _q("Par quel canal le joindre à nouveau ?", "Téléphone, courrier, sur place, via un tiers ?")

    # ── PAGE 3 — Le bâti (adaptatif) / Le sol / Les papiers ──
    q += '<div class="pb"></div>'
    if is_bati:
        q += "<h3>Le bâti et son occupation</h3>"
        q += _aide("Un bail commercial en cours peut geler l'opération plusieurs années — notez-le en "
                   "premier si c'est le cas.")
        q += _boxes("Les bâtiments sont-ils occupés ? Par qui ?", ["Vides", "Le propriétaire", "Des locataires", "Une activité"])
        # RECETTE-3 (T1) — le BAIL, troisième « l'essentiel ».
        q += _q("Sous quel bail ?", "Fin de bail, loyers perçus.", zone=True, cle="L'ESSENTIEL")
        q += _q("État général du bâti ; diagnostics disponibles (amiante, plomb) ?", zone=True)

    q += "<h3>Le sol</h3>"
    hint_sol = "Cuves enterrées, remblais, pollution connue ?"
    aide_sol = "Un ancien garage, dépôt ou station-service peut ajouter des dizaines de milliers d'euros de dépollution."
    if industriel:
        aide_sol = ("Un établissement classé est signalé à proximité ; un ancien garage, dépôt ou "
                    "station-service sur la parcelle changerait le coût.")
    q += _aide(aide_sol)
    q += _q("Quel était l'usage du site avant ?", hint_sol, zone=True)

    q += "<h3>Ce que les papiers diraient</h3>"
    q += _aide("Ce qui ne se voit ni sur le terrain ni au cadastre, et qui peut tout retarder.")
    q += _q("Servitudes de passage, litiges de voisinage, bornage récent, empiètements connus ?", zone=True)
    q += _q("Hypothèques, procédures en cours ?")
    q += _q("Titre de propriété disponible ?", "Origine : achat, donation, succession — et l'année.")

    # ── PAGE 4 — Le voisinage et la mairie / Les photos / Votre retour ──
    q += '<div class="pb"></div><h3>Le voisinage et la mairie</h3>'
    if voisines.get("n"):
        refs = ", ".join(m["ref"] for m in voisines.get("membres", [])[:4] if m.get("ref"))
        q += _aide(f"{voisines['n']} parcelle(s) voisine(s) appartiennent au même propriétaire. Savoir "
                   "s'il les vendrait ensemble change complètement l'opération.")
        q += _q(f"Vendrait-il aussi {refs} ? D'autres voisines sont-elles à vendre ?"
                if refs else "Vendrait-il aussi les parcelles voisines ? D'autres sont-elles à vendre ?",
                zone=True, cle="L'ESSENTIEL")
    else:
        q += _aide("Un achat groupé de parcelles voisines change souvent la faisabilité d'une opération.")
        q += _q("Les parcelles voisines sont-elles à vendre ? Du même propriétaire ?", zone=True, cle="L'ESSENTIEL")
    q += _q("Que dit la mairie de ce secteur ? Que disent les voisins ?", "Projets connus, oppositions, associations.", zone=True)

    # RECETTE-3 (T1) — les PHOTOS ne sont plus collées : envoyées par message en citant la référence.
    q += '<h3>Les photos</h3>'
    q += (f'<p class="aide">Quatre vues : depuis la voie, puis aux quatre coins, en tenant la parcelle '
          f'au centre. Envoyez-les par message en citant la référence <b>{esc(idu)}</b> — n\'imprimez rien.</p>')

    q += "<h3>Votre retour</h3>"
    q += _duo("Date de la visite · vos coordonnées")
    q += _q("Ce qu'il faut savoir et qu'aucune question ne couvre", zone=True)
    return h + q
