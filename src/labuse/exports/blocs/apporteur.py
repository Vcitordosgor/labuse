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
from ..registre_fmt import fmt_eur, fmt_m2
from ..rendu import esc, ligne_kv, note, table_kv

# RECETTE-12 E1 — la spec FERMÉE (docs/audit-2026-09/EXPORTS/APPORTEUR-SPEC.md) : la page 1 ne porte
# QUE surface, zone, « sur place » (bâtiments + emprise), « ce qui gêne », accès, dernière vente,
# voisines, plan. RETIRÉS de RECETTE-2/11 (répétés au propriétaire ou devenus l'ancre du vendeur) :
# la CAPACITÉ CONSTRUCTIBLE (sdp/capacité), le PRIX DE SECTEUR, la HAUTEUR LiDAR (inutile à sa mission).
IDS = ("surface_parcelle_m2", "zone_plu_famille", "reglement_plu_bloc", "statut_plu",
       "emprise_batie_m2", "n_batiments", "type_proprietaire", "prix_achat_historique_eur",
       "distance_arret_m", "aleas_parcelle_liste",
       "er_emplacement_reserve", "ebc_classe", "dpu_perimetre", "peb_zone")

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
# EXPORTS-REBRANCHEMENT-1 lot 4 — la phrase de fraîcheur du PLU a changé au lot 0 (« Document
# opposable — il fait foi à ce jour ») : l'abréviation de l'Apporteur suit (il garde le fait
# « PLU approuvé le … », la mention d'opposabilité reste aux autres documents).
_RE_GPU_PLOMBERIE = re.compile(r"\s*—?\s*Document (à jour du GPU|opposable).*$", re.IGNORECASE)


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
    # RECETTE-12 E1 — « sur place » = nombre de bâtiments + emprise au sol SEULEMENT. La HAUTEUR
    # LiDAR (ajoutée à tort en RECETTE-11) est retirée : inutile à la mission de l'apporteur.
    bits = []
    if a(valeurs, "n_batiments"):
        bits.append(f"{int(val(valeurs, 'n_batiments'))} bâtiments")
    if a(valeurs, "emprise_batie_m2"):
        bits.append(f"{fmt_m2(val(valeurs, 'emprise_batie_m2'))} au sol")
    return " · ".join(bits) or "terrain a priori nu"


def _contraintes(valeurs) -> str:
    """Une ligne « Ce qui gêne » : aléas + prescriptions (ER/EBC/DPU) + zone de bruit (PEB). Vide → ''."""
    bits: list[str] = []
    liste = val(valeurs, "aleas_parcelle_liste") or []
    # RECETTE-11 D7 — « Ce qui gêne » reprend la liste du Dossier §4 : on prend la description de
    # l'aléa (libellé court avant « — »), pas seulement sa `nature`. Sinon un PPR « inondation ET
    # mouvement de terrain » se réduisait à « Inondation » — le mouvement de terrain manquait.
    natures = [((x.get("libelle") or "").split(" — ")[0].strip() or x.get("nature"))
               for x in liste if isinstance(x, dict) and (x.get("nature") or x.get("libelle"))]
    bits += list(dict.fromkeys(n for n in natures if n))
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
    # RECETTE-12 E1 — RETIRÉ « Ce qu'on peut y bâtir » (capacité constructible) : la spec du 05/09
    # l'exclut, l'apporteur la répéterait au propriétaire. RETIRÉ « Prix du secteur » : un prix dans
    # la main d'un apporteur devient l'ancre du vendeur (absent de la spec).
    # RECETTE-2 (S7) — contraintes en une ligne (jamais un vide : ligne omise si rien).
    contr = _contraintes(valeurs)
    if contr:
        lignes.append(ligne_kv("Ce qui gêne", contr, ""))
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
    # RECETTE-12 E1 — L'ÉMETTEUR nommé (nom + téléphone) : c'est à lui que l'apporteur renvoie ses
    # réponses et ses photos (Vic a refusé l'anonymat de l'émetteur le 05/09). Retiré à tort en RECETTE-2.
    em = ctx.get("emetteur") or {}
    if em.get("nom") or em.get("coordonnees") or em.get("email"):
        contact = " · ".join(x for x in (em.get("coordonnees"), em.get("email")) if x)
        h += ('<div class="emetteur">Émetteur : <b>' + esc(em.get("nom") or "") + '</b>'
              + (" — " + esc(contact) if contact else "")
              + '<br><small>C\'est à cet émetteur que vous renvoyez vos réponses et vos photos.</small></div>')
    # ── §1 — La parcelle en un coup d'œil (coup d'œil + plan + note) ──
    h += '<h3>1. La parcelle en un coup d\'œil</h3>' + _coup_d_oeil(valeurs, ctx)
    h += _plan_situation(ctx)   # RECETTE-3 (T1) — ortho IGN + contour + voisines du même propriétaire
    h += note("Absents volontairement : capacité constructible, SDP, charge foncière, score. "
              "L'apporteur n'a pas à connaître ce que le promoteur compte faire ni combien ça vaut. "
              "Le reste — qui décide, à quel prix, ce que cachent les papiers — s'obtient sur place.")

    dest = esc(em.get("nom")) if em.get("nom") else "l'émetteur (en tête)"

    # ── §2 — Vous (NEW v4 : l'apporteur d'abord — à qui renvoyer, quand, comment il connaît le vendeur) ──
    q = '<div class="pb"></div><h3>2. Vous</h3>'
    q += _duo("Votre nom, téléphone, e-mail", cle="EN PREMIER")
    q += _q("Date de la visite ou du contact")
    q += _q("Comment vous connaissez le propriétaire", "Voisin, famille, hasard, démarche…", zone=True)

    # ── §3 — Qui décide (décideur réel, indivision, âge/situation, déjà confié à agent/notaire) ──
    q += "<h3>3. Qui décide</h3>"
    q += _aide("Une parcelle en indivision, ce sont autant de signatures que d'héritiers — la première "
               "chose qui fait échouer une vente.")
    if is_pm:
        q += _q("La parcelle est détenue par une société — qui la contrôle, et qui décide de vendre ?",
                "Gérant, associés, nombre de signataires ?", zone=True)
    else:
        q += _q("Qui détient réellement la parcelle, et qui décide de vendre ?",
                "Propriétaire, mandataire, tuteur — nom du décideur réel.", zone=True)
    q += _boxes("Plusieurs propriétaires ? (indivision, succession en cours, époux)",
                ["Non", "Oui", "Ne sait pas"])
    q += _q("Âge approximatif du décideur, situation", "Retraite, éloignement, santé…", zone=True)
    q += _q("Le bien est-il déjà confié à un agent ou un notaire ? Lequel ?")

    # ── §4 — La vente (l'essentiel : prix ; + voisines déplacées ici ; + dation/échange) ──
    q += "<h3>4. La vente</h3>"
    q += _aide("Le prix déjà refusé vaut plus qu'un prix annoncé : il dit le plancher réel.")
    q += _boxes("Envisage-t-il de vendre ? Dans quel délai ?", ["Oui", "Non", "Peut-être", "Ne sait pas"])
    q += _duo("Prix attendu, ou ordre d'idée · prix déjà refusé", cle="L'ESSENTIEL")
    if voisines.get("n"):
        refs = ", ".join(m["ref"] for m in voisines.get("membres", [])[:4] if m.get("ref"))
        q += _q((f"Vendrait-il aussi {refs} ? (voisines du même propriétaire, listées en §1) "
                 "D'autres voisines à vendre ?") if refs
                else "Vendrait-il aussi les parcelles voisines du même propriétaire ? D'autres à vendre ?",
                zone=True)
    else:
        q += _q("Les parcelles voisines sont-elles à vendre ? Du même propriétaire ?", zone=True)
    q += _q("Préfère-t-il vendre le terrain, ou participer à l'opération ?", "Dation, échange…", zone=True)

    # ── §5 — Le bâti et son occupation (si bâti ; + activité sur place) ──
    if is_bati:
        q += '<div class="pb"></div><h3>5. Le bâti et son occupation</h3>'
        q += _aide("Un bail commercial en cours peut geler l'opération plusieurs années.")
        q += _boxes("Occupé ? Par qui ?", ["Vides", "Le propriétaire", "Des locataires", "Une activité"])
        q += _q("Si loué : sous quel bail ?", "Fin de bail, loyers perçus.", zone=True, cle="L'ESSENTIEL")
        q += _q("État apparent du bâti ; diagnostics disponibles (amiante, plomb) ?",
                "Entretenu, dégradé, ruine, travaux récents.", zone=True)
        q += _q("Activité sur place ?", "Commerce, atelier, élevage, dépôt…", zone=True)

    # ── §6 — Le terrain, vu sur place (questions d'observation, conditionnelles aux couches) ──
    q += '<div class="pb"></div><h3>6. Le terrain, vu sur place</h3>'
    q += _aide("Questions générées depuis les couches de la parcelle : seules celles qui s'appliquent "
               "sont imprimées.")
    q += _q("Accès : depuis quelle voie, largeur, portail, servitude de passage visible ?", zone=True)
    q += _q("Pente, talus, murs de soutènement ?", zone=True)
    if ctx.get("obs_eau"):
        q += _q("Traces d'eau : inondation, ravine, zone humide, drainage ?",
                "La parcelle est concernée par un aléa d'eau (inondation / ravine / zone humide).", zone=True)
    if ctx.get("obs_ligne_ht"):
        q += _boxes("Ligne électrique, pylône, transformateur sur ou au bord ?", ["Non", "Oui"])
    if ctx.get("obs_pollution"):
        q += _q("Remblais, déchets, cuves, dépôt, odeur ?",
                "Un ancien site industriel ou un sol pollué est signalé à proximité (analyse de risques).",
                zone=True)
    q += _q("Arbres remarquables, boisement, clôtures, limites incertaines ?", zone=True)

    # ── §7 — À demander au propriétaire (renommé de « Ce que les papiers diraient ») ──
    q += "<h3>7. À demander au propriétaire</h3>"
    q += _aide("L'apporteur ne lit pas les actes : il pose la question.")
    q += _q("Servitudes privées connues ?", "Passage, vue, canalisation.", zone=True)
    q += _q("Hypothèque, prêt en cours, litige, procédure ?", zone=True)
    q += _q("Projet déjà tenté ?", "Permis, promoteur passé, refus de la mairie.", zone=True)
    q += _q("A-t-il un notaire attitré ?")

    # ── §8 — Le voisinage et la mairie (allégé : les voisines sont passées au §4) ──
    q += '<div class="pb"></div><h3>8. Le voisinage et la mairie</h3>'
    q += _q("Voisins : opposants probables, projets en cours, nuisances ?", zone=True)
    q += _q("Ce que la mairie en dit, si vous l'avez approchée ?", zone=True)

    # ── §9 — Les photos (par message, en citant la référence — jamais collées) ──
    q += "<h3>9. Les photos</h3>"
    q += (f'<p class="aide">Cinq vues, aux mêmes points que le pré-dossier de permis (PCMI7-8). '
          f'Envoyez-les à {dest} par message en citant la référence <b>{esc(idu)}</b> et le numéro '
          "de vue — pas collées ici.</p>")

    # ── §10 — Votre retour (impression, prochaine étape, chance d'aboutir) ──
    q += "<h3>10. Votre retour</h3>"
    q += _q("Votre impression en trois lignes", zone=True)
    q += _q("Prochaine étape convenue avec le propriétaire", "Rappel, visite, rien…", zone=True)
    q += _boxes("Chance que ça aboutisse, selon vous", ["Forte", "Moyenne", "Faible"])
    return h + q
