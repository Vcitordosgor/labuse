"""MAILS-1 — LE CONTENU des 21 e-mails LABUSE, rendu par l'app via le gabarit unique.

Avant, le contenu des mails du cycle de vie vivait dans des TEMPLATES BREVO (16 modèles) et le reste
dans `emails.py`. Désormais TOUT le texte est ICI, assemblé par `gabarit_mail` : Brevo n'est plus
qu'un transport (`brevo.envoyer_html`). Un seul endroit à relire pour Vic, un seul rendu.

`rendre(key, params) -> gabarit_mail.Mail` : pour chaque clé de mail, lit les paramètres (noms Brevo
historiques `PRENOM`/`LIEN_*` pour le cycle de vie ; dict normalisé pour les mails techniques) et
produit (sujet, html, texte, headers). `gere(key)` dit si une clé est prise en charge ici.

Deux REGISTRES (mandat) :
  · personnel — ton direct, signature « Victor Lagane, fondateur de LABUSE » ;
  · automatique — étiquette de couleur par nature, faits en clair, pas de signature.
Les mails de SÉCURITÉ (mot de passe, adresse) gardent le pied SANS désinscription.

Corrections de fond appliquées (mandat) : plus de numéro factice (vrai numéro dans la signature) ;
UN SEUL mail de réinitialisation (`mdp_oublie` ; le doublon `smtp_reset_password` est supprimé) ; prénom partout où on le
connaît ; aucune promesse dépassée (le Copilote a sa page dans le menu de gauche, aucune mention de
« créole ») ; la maintenance dit quoi / quand / quoi faire ; l'alerte Radar liste chaque bien
(commune, surface, zone, prix, portail, date) ; chaque mail finit sur un seul appel à l'action.
"""
from __future__ import annotations

from . import gabarit_mail as g

APP_URL = "https://app.labuse.immo"   # URL publique réelle (repli pour les boutons sans lien dédié)


def _s(x: object) -> str:
    return str(x if x is not None else "").strip()


def _prenom(p: dict) -> str:
    pr = _s(p.get("PRENOM") or p.get("prenom"))
    return pr


def _greet(p: dict) -> str:
    pr = _prenom(p)
    return f"Bonjour {pr}," if pr else "Bonjour,"


def _lien(p: dict, *noms: str, defaut: str = APP_URL) -> str:
    for n in noms:
        v = _s(p.get(n))
        if v:
            return v
    return defaut


def _pied(p: dict, raison: str, *, securite: bool = False, desabo: bool = True) -> g.Pied:
    return g.Pied(
        raison=raison,
        lien_prefs=_s(p.get("LIEN_PREFS") or p.get("lien_prefs")),
        lien_desabo=(_s(p.get("LIEN_DESABO") or p.get("lien_desabo")) if desabo else ""),
        securite=securite)


R_COMPTE = "Vous recevez ce mail parce que vous avez un compte LABUSE."
# Mails de FACTURATION / ACCÈS (abonnement, paiement, suspension, rétablissement, résiliation, rapport
# acheté) : TRANSACTIONNELS comme la sécurité — pas de désinscription (décision Vic, V4).
R_ABONNEMENT = "Ce message concerne votre abonnement ; il n'est pas désactivable."
R_RADAR = "Vous recevez ce mail parce que vous surveillez des critères dans le Radar LABUSE."
R_SUIVIS = "Vous recevez ce mail parce que vous suivez des parcelles ou surveillez des critères dans LABUSE."
R_SECU = "Ce mail de sécurité vous est envoyé parce que votre adresse est associée à un compte LABUSE."


# ════════════════════════════ MAILS PERSONNELS ════════════════════════════

def _essai(p: dict) -> g.Mail:
    blocs = [g.paragraphe(_greet(p))]
    if p.get("RENVOI"):
        blocs.append(g.paragraphe("Comme demandé, voici un nouveau lien pour ouvrir votre essai."))
    blocs += [
        g.paragraphe("Voici votre accès d'essai à LABUSE : 48 heures pour juger sur pièces, "
                     "sans carte bancaire."),
        g.bouton("Ouvrir mon accès", _lien(p, "LIEN_INVITATION")),
        g.note("Vous choisissez votre mot de passe en arrivant."),
        g.paragraphe(f"Votre essai se termine le {_s(p.get('FIN_ESSAI')) or '—'}. D'ici là, tout est "
                     "ouvert : la carte des 24 communes, les fiches parcelle et le Copilote, dans le "
                     "menu de gauche."),
        g.paragraphe("Ouvrez votre accès et commencez par votre commune."),
    ]
    return g.rendre(sujet="Vos accès d'essai LABUSE — 48 h pour juger sur pièces",
                    registre="personnel", blocs=blocs, apercu="48 heures pour juger, sans carte bancaire.",
                    pied=_pied(p, R_COMPTE))


def _souscription(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Voici votre lien pour activer votre abonnement LABUSE. Le paiement est "
                     "sécurisé et votre accès s'ouvre dès la confirmation."),
        g.bouton("Activer mon abonnement", _lien(p, "LIEN_SOUSCRIPTION")),
        g.paragraphe("Une question avant de vous lancer ? Répondez à ce mail, c'est moi qui lis."),
        g.paragraphe("Activez votre abonnement pour garder vos accès."),
    ]
    return g.rendre(sujet="LABUSE — votre lien d'abonnement", registre="personnel", blocs=blocs,
                    apercu="Activez votre abonnement en une minute.",
                    pied=_pied(p, R_ABONNEMENT, desabo=False))


def _onboarding1(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Bienvenue sur LABUSE. Votre compte est prêt :"),
        g.bouton("Ouvrir mon accès", _lien(p, "LIEN_INVITATION")),
        g.note("Vous choisissez votre mot de passe en arrivant."),
        g.paragraphe("Pour votre première session, trois gestes suffisent, un quart d'heure en tout :"),
        g.etapes([
            ("Ouvrez la carte", "et zoomez sur votre commune. Les parcelles les plus foncées sont "
             "celles qui ont le plus de chances de se vendre."),
            ("Cliquez une parcelle foncée", ": propriétaire, surface, zonage, surface encore "
             "constructible, prix de zone — tout ce que vous iriez chercher sur quatre sites."),
            ("Posez une question au Copilote", "depuis le menu de gauche : « les plus grandes parcelles "
             "constructibles à Saint-Pierre ». Il répond avec les chiffres de la base, jamais d'invention."),
        ]),
        g.paragraphe("LABUSE couvre les 24 communes de La Réunion, plus de 430 000 parcelles, avec des "
                     "données publiques recoupées et datées."),
        g.paragraphe("Un blocage, une question ? Répondez à ce mail : c'est moi qui lis."),
        g.paragraphe("Bonne chasse,"),
    ]
    return g.rendre(sujet="Bienvenue sur LABUSE", registre="personnel", blocs=blocs,
                    apercu="Votre compte est prêt — trois gestes pour commencer.", pied=_pied(p, R_COMPTE))


def _onboarding2(p: dict) -> g.Mail:
    blocs = [g.paragraphe(_greet(p))]
    if p.get("JAMAIS_CONNECTE"):
        blocs.append(g.paragraphe("Vous n'avez pas encore ouvert votre accès — voici pourquoi ça vaut "
                                  "le détour."))
    blocs += [
        g.paragraphe("La plupart des gens cherchent un terrain en lisant des annonces. LABUSE prend le "
                     "problème à l'envers : on part du foncier — qui possède quoi, ce qui est "
                     "constructible, ce qui bouge — et l'annonce n'est que la conséquence."),
        g.paragraphe("En trois minutes sur votre commune :"),
        g.etapes([
            ("Partez de la carte", "les parcelles foncées sont celles qui ont le plus de chances de se vendre."),
            ("Lisez la fiche", "surface constructible restante, zonage, prix de zone, propriétaire."),
            ("Demandez au Copilote", "une liste triée, sans quitter la page."),
        ], deux_points=True),
        g.bouton("Ouvrir LABUSE", _lien(p, "LIEN_APP")),
        g.paragraphe("Une question sur la méthode ? Répondez, je vous montre sur votre commune."),
    ]
    return g.rendre(sujet="La méthode pour trouver ce que les autres ne voient pas",
                    registre="personnel", blocs=blocs, apercu="Partir du foncier, pas des annonces.",
                    pied=_pied(p, R_COMPTE))


def _onboarding3(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Cela fait dix jours que vous avez accès à LABUSE. Je voulais prendre de vos "
                     "nouvelles — pas un mail automatique de plus, une vraie question : est-ce que "
                     "l'outil vous sert ?"),
        g.paragraphe("Si vous bloquez quelque part — une commune, un type de bien, une donnée qui "
                     "manque — dites-le moi : je lis chaque réponse et j'ajuste."),
        g.bouton("Ouvrir LABUSE", _lien(p, "LIEN_APP")),
        g.paragraphe("Répondez à ce mail en une ligne : qu'est-ce qui vous aiderait le plus ?"),
    ]
    return g.rendre(sujet="10 jours de LABUSE — on fait le point ?", registre="personnel", blocs=blocs,
                    apercu="Est-ce que l'outil vous sert ?", pied=_pied(p, R_COMPTE))


def _relance_carte(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Votre dernier paiement LABUSE n'a pas pu aboutir — en général, c'est une carte "
                     "expirée ou un plafond atteint. Rien de grave, et votre accès reste ouvert pour "
                     "l'instant."),
        g.bouton("Mettre à jour mon paiement", _lien(p, "LIEN_PAIEMENT")),
        g.paragraphe("Dès que c'est fait, tout rentre dans l'ordre automatiquement. Une question ? "
                     "Répondez à ce mail."),
    ]
    return g.rendre(sujet="LABUSE — un souci avec votre moyen de paiement", registre="personnel",
                    blocs=blocs, apercu="Votre accès reste ouvert — mettez votre carte à jour.",
                    pied=_pied(p, R_ABONNEMENT, desabo=False))


def _suspension(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Faute de paiement régularisé, votre accès à LABUSE est suspendu. Vos données et "
                     "vos projets sont conservés : rien n'est perdu."),
        g.bouton("Réactiver mon accès", _lien(p, "LIEN_PAIEMENT")),
        g.paragraphe("Un seul paiement régularisé rouvre tout, immédiatement. Besoin d'aide ? Répondez "
                     "à ce mail."),
    ]
    return g.rendre(sujet="LABUSE — votre accès est suspendu", registre="personnel", blocs=blocs,
                    apercu="Vos données sont conservées — réactivez en un clic.",
                    pied=_pied(p, R_ABONNEMENT, desabo=False))


def _retablissement(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("C'est réglé : votre paiement est passé et votre accès à LABUSE est rétabli. Vous "
                     "retrouvez vos projets, vos veilles et vos parcelles suivies, tels que vous les "
                     "aviez laissés."),
        g.bouton("Reprendre sur LABUSE", _lien(p, "LIEN_APP")),
        g.paragraphe("Merci de votre confiance. Une question ? Répondez, c'est moi qui lis."),
    ]
    return g.rendre(sujet="LABUSE — votre accès est rétabli", registre="personnel", blocs=blocs,
                    apercu="Tout est rétabli, comme vous l'aviez laissé.",
                    pied=_pied(p, R_ABONNEMENT, desabo=False))


def _resiliation(p: dict) -> g.Mail:
    fin = _s(p.get("DATE_FIN_ACCES")) or "—"
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe(f"Votre demande de résiliation est bien enregistrée. Votre accès reste ouvert "
                     f"jusqu'au {fin} ; après cette date il se fermera, sans autre prélèvement."),
        g.paragraphe("D'ici là, rien ne change : vous gardez tout. Et si vous changez d'avis, vous "
                     "pouvez réactiver à tout moment."),
        g.bouton("Réactiver mon abonnement", _lien(p, "LIEN_PAIEMENT", defaut=f"{APP_URL}/facturation")),
        g.paragraphe("Si quelque chose n'a pas été à la hauteur, répondez à ce mail : votre retour "
                     "m'est utile."),
    ]
    return g.rendre(sujet=f"Votre abonnement LABUSE prend fin le {fin}", registre="personnel",
                    blocs=blocs, apercu="Accès ouvert jusqu'à la date indiquée.",
                    pied=_pied(p, R_ABONNEMENT, desabo=False))


def _retour_traite(p: dict) -> g.Mail:
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Vous m'aviez signalé ceci :"),
        g.carte("VOTRE MESSAGE", _s(p.get("SON_MESSAGE"))),
        g.paragraphe("Voici ma réponse :"),
        g.carte("MA RÉPONSE", _s(p.get("REPONSE"))),
        g.paragraphe("Merci de m'avoir aidé à améliorer LABUSE."),
        g.bouton("Ouvrir LABUSE", _lien(p, "LIEN_APP")),
        g.paragraphe("Une autre remarque ? Répondez à ce mail."),
    ]
    return g.rendre(sujet="Votre retour a été traité", registre="personnel", blocs=blocs,
                    apercu="Nous avons traité votre signalement.", pied=_pied(p, R_COMPTE))


def _essai_fin_proche(p: dict) -> g.Mail:
    quand = _s(p.get("DATE_FIN")) or "bientôt"
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe(f"Votre essai LABUSE se termine {quand}. Après, l'accès se ferme — mais vos "
                     "projets et vos veilles restent conservés."),
        g.paragraphe("Si LABUSE vous a été utile, vous pouvez activer votre abonnement en une minute "
                     "et ne rien perdre :"),
        g.bouton("Activer mon abonnement", _lien(p, "LIEN_PAIEMENT")),
        g.paragraphe("Pas convaincu ? Répondez à ce mail et dites-moi ce qui a manqué — ça m'aide "
                     "vraiment."),
    ]
    return g.rendre(sujet=f"Votre essai LABUSE se termine {quand}", registre="personnel", blocs=blocs,
                    apercu="Activez votre abonnement pour ne rien perdre.", pied=_pied(p, R_COMPTE))


# ════════════════════════════ MAILS DE SÉCURITÉ ════════════════════════════

def _mdp_oublie(p: dict) -> g.Mail:
    validite = _s(p.get("VALIDITE")) or "1 heure"
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe("Vous avez demandé à réinitialiser votre mot de passe LABUSE. Cliquez ci-dessous "
                     "pour en choisir un nouveau :"),
        g.bouton("Choisir un nouveau mot de passe", _lien(p, "LIEN_RESET")),
        g.paragraphe(f"Ce lien est valable {validite}. Passé ce délai, il faudra en redemander un."),
        g.paragraphe("Si vous n'êtes pas à l'origine de cette demande, ignorez ce mail : votre mot de "
                     "passe reste inchangé et votre compte n'est pas modifié."),
    ]
    return g.rendre(sujet="Réinitialisation de votre mot de passe LABUSE", registre="personnel",
                    blocs=blocs, apercu="Choisissez un nouveau mot de passe.",
                    pied=_pied(p, R_SECU, securite=True, desabo=False))


def _mdp_modifie(p: dict) -> g.Mail:
    quand = _s(p.get("DATE_HEURE")) or "à l'instant"
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe(f"Votre mot de passe LABUSE a été modifié le {quand} (heure de La Réunion)."),
        g.paragraphe("Si c'est bien vous, aucune action n'est nécessaire."),
        g.paragraphe("Si ce n'est pas vous, votre compte est peut-être compromis : réinitialisez votre "
                     "mot de passe immédiatement et prévenez-moi en répondant à ce mail."),
        g.bouton("Sécuriser mon compte", _lien(p, "LIEN_RESET", "LIEN_APP")),
    ]
    return g.rendre(sujet="Votre mot de passe LABUSE a été modifié", registre="personnel", blocs=blocs,
                    apercu="Confirmation de changement de mot de passe.",
                    pied=_pied(p, R_SECU, securite=True, desabo=False))


def _email_change(p: dict) -> g.Mail:
    anc, nouv = _s(p.get("ANCIEN_EMAIL")), _s(p.get("NOUVEL_EMAIL"))
    blocs = [
        g.paragraphe(_greet(p)),
        g.paragraphe(f"L'adresse de connexion de votre compte LABUSE est passée de {anc} à {nouv}."),
        g.paragraphe("Votre mot de passe n'a pas changé. Connectez-vous désormais avec la nouvelle "
                     "adresse."),
        g.bouton("Me connecter à LABUSE", _lien(p, "LIEN_APP")),
        g.paragraphe("Ce message est envoyé aux deux adresses. Si ce changement n'est pas de votre "
                     "fait, répondez immédiatement à ce mail."),
    ]
    return g.rendre(sujet="Votre adresse de connexion LABUSE a changé", registre="personnel", blocs=blocs,
                    apercu="Votre adresse de connexion a changé.",
                    pied=_pied(p, R_SECU, securite=True, desabo=False))


# ════════════════════════════ MAILS AUTOMATIQUES ════════════════════════════

def _biens_bloc(p: dict) -> g.Bloc:
    """Construit la liste de biens à partir d'une liste structurée `BIENS` ({titre,detail,prix})."""
    items = p.get("BIENS") or p.get("biens") or []
    if items:
        return g.biens(list(items))
    return g.paragraphe("")


def _radar_digest(p: dict) -> g.Mail:
    date = _s(p.get("DATE")) or "aujourd'hui"
    nb = _s(p.get("NB_BIENS")) or "0"
    greet = _greet(p)
    blocs = [
        g.etiquette("RADAR · DIGEST", "radar"),
        g.titre_auto(f"Le point Radar du {date}"),
        g.paragraphe(f"{greet} voici les nouveautés repérées sur vos communes "
                     f"({nb} ce jour).", html_brut=f"{g.esc(greet)} voici les nouveautés repérées sur "
                     f"vos communes (<b>{g.esc(nb)}</b> ce jour)."),
    ]
    biens = _biens_bloc(p)
    if biens[0]:
        blocs.append(biens)
    else:
        blocs.append(g.paragraphe("Rien de neuf aujourd'hui sur vos critères."))
    blocs += [
        g.bouton("Ouvrir le Radar", _lien(p, "LIEN_RADAR")),
        g.note("LABUSE ne republie aucune annonce : chaque lien renvoie au portail d'origine. Les "
               "faits affichés sont ceux relevés à la date indiquée."),
    ]
    return g.rendre(sujet=f"Radar — {nb} nouveauté{'s' if nb not in ('0','1') else ''} le {date}",
                    registre="auto", blocs=blocs, apercu="Les nouveautés du Radar sur vos communes.",
                    pied=_pied(p, R_RADAR))


def _radar_alerte(p: dict) -> g.Mail:
    veille = _s(p.get("VEILLE")) or "votre veille"
    nb = _s(p.get("NB_BIENS")) or "0"
    criteres = _s(p.get("CRITERES"))
    greet = _prenom(p)
    # pluriel juste + gras sur le MOT ENTIER (« 1 bien » / « 3 biens »).
    nb_bien = f"{nb} bien{'s' if nb != '1' else ''}"
    intro = (f"Bonjour {greet}, votre veille vient de trouver {nb_bien} correspondant à vos critères."
             if greet else
             f"Votre veille vient de trouver {nb_bien} correspondant à vos critères.")
    intro_html = g.esc(intro).replace(g.esc(nb_bien), f"<b>{g.esc(nb_bien)}</b>", 1)
    blocs = [
        g.etiquette("RADAR · ALERTE", "radar"),
        g.titre_auto(veille),
        g.paragraphe(intro, html_brut=intro_html),
    ]
    if criteres:
        blocs.append(g.carte("VOS CRITÈRES", criteres))
    biens = _biens_bloc(p)
    if biens[0]:
        blocs.append(biens)
    blocs += [
        g.bouton("Ouvrir le Radar", _lien(p, "LIEN_RADAR")),
    ]
    lv = _s(p.get("LIEN_VEILLE"))
    if lv:
        blocs.append(g.lien_secondaire("Modifier cette veille", lv))
    blocs.append(g.note("LABUSE ne republie aucune annonce : chaque lien renvoie au portail d'origine. "
                        "Les faits affichés sont ceux relevés à la date indiquée."))
    return g.rendre(sujet=f"Veille « {veille} » — {nb} correspondance{'s' if nb != '1' else ''}",
                    registre="auto", blocs=blocs, apercu="De nouveaux biens correspondent à votre veille.",
                    pied=_pied(p, R_RADAR))


def _flash_pret(p: dict) -> g.Mail:
    idu = _s(p.get("IDU")) or "votre parcelle"
    commune = _s(p.get("COMMUNE"))
    # VALIDITE réelle = `settings.flash_token_days` (un nombre de jours passé par facturation.py) :
    # on l'écrit en toutes lettres (« 30 jours »), au lieu d'un nombre brut.
    validite = _s(p.get("VALIDITE"))
    if validite.isdigit():
        validite = f"{validite} jour{'s' if int(validite) > 1 else ''}"
    validite = validite or "quelques jours"
    blocs = [
        g.etiquette("RAPPORT · PRÊT", "radar"),    # badge au vert de la charte (comme les autres badges d'info)
        g.titre_auto(f"Votre rapport est prêt — {commune}" if commune else "Votre rapport est prêt"),
        g.paragraphe(f"Le rapport LABUSE de la parcelle {idu}"
                     + (f" ({commune})" if commune else "") + " est généré et prêt à télécharger."),
        g.bouton("Télécharger le rapport (PDF)", _lien(p, "LIEN_PDF")),
        g.paragraphe(f"Ce lien est valable {validite}."),
        g.note("Le rapport reprend les données foncières publiques recoupées à la date de génération."),
    ]
    # « rapport acheté » = transactionnel (comme la facturation) : pas de désinscription.
    return g.rendre(sujet=f"Votre rapport LABUSE — {idu}", registre="auto", blocs=blocs,
                    apercu="Votre rapport est prêt à télécharger.", pied=_pied(p, R_ABONNEMENT, desabo=False))


def _digest_notifications(p: dict) -> g.Mail:
    evs = p.get("EVENEMENTS") or p.get("evenements") or []
    n = len(evs)
    marche = p.get("MARCHE") or p.get("marche") or {}
    greet = _greet(p)
    blocs = [
        g.etiquette("SUIVIS · POINT", "radar"),
        g.titre_auto("Le point sur vos suivis"),
        g.paragraphe(f"{greet} voici ce qui a bougé sur vos parcelles suivies et vos veilles."),
    ]
    for e in evs:
        blocs.append(g.ligne_fait(_s(e.get("titre")), _s(e.get("detail")), _s(e.get("lien")) or None,
                                  "voir la parcelle"))
    if not evs:
        blocs.append(g.paragraphe("Rien de neuf sur vos suivis pour le moment."))
    mt = marche.get("total") if isinstance(marche, dict) else None
    if mt:
        com = marche.get("dans_vos_communes")
        # « dont M dans vos communes » si le compte a des parcelles suivies ; sinon « sur l'île ».
        cadre = f", dont {com} dans vos communes" if com is not None else " sur l'île"
        blocs.append(g.paragraphe(f"Marché : {mt} mouvement{'s' if mt > 1 else ''}{cadre}. Le détail "
                                  "est dans la cloche de l'application."))
    blocs.append(g.bouton("Ouvrir LABUSE", _lien(p, "LIEN_APP")))
    # Sujet FACTUEL : « N changements sur vos suivis » ; s'il n'y a aucun événement personnel mais un
    # résumé marché, le sujet le reflète (fin du « digest vide à vie », M-T V2).
    if n == 0 and mt:
        sujet = f"LABUSE — {mt} mouvement{'s' if mt > 1 else ''} de marché"
    else:
        sujet = f"LABUSE — {n} changement{'s' if n != 1 else ''} sur vos suivis"
    return g.rendre(sujet=sujet, registre="auto", blocs=blocs, apercu="Ce qui a bougé sur vos suivis.",
                    pied=_pied(p, R_SUIVIS))


def _annonce(p: dict) -> g.Mail:
    titre = g.maj1(_s(p.get("TITRE") or p.get("titre")) or "une nouveauté")
    corps = _s(p.get("CORPS") or p.get("corps"))
    blocs = [
        g.etiquette("LABUSE · NOUVEAUTÉ", "annonce"),
        g.titre_auto(titre),
    ]
    if corps:
        blocs.append(g.paragraphe(corps))
    blocs.append(g.bouton("Voir les communes concernées", _lien(p, "LIEN", "lien")))
    return g.rendre(sujet=f"LABUSE — {titre}", registre="auto", blocs=blocs,
                    apercu="Une nouveauté dans LABUSE.", pied=_pied(p, R_COMPTE))


def _maintenance(p: dict) -> g.Mail:
    # titre BRUT pour l'objet (inséré après « : » → casse d'origine) ; le TITRE du corps est
    # capitalisé par `titre_auto` (maj1). Vic : « LABUSE — maintenance programmée : mise à jour serveur ».
    titre = _s(p.get("TITRE") or p.get("titre")) or "maintenance programmée"
    corps = _s(p.get("CORPS") or p.get("corps"))
    fenetre = _s(p.get("FENETRE") or p.get("fenetre"))
    fin = _s(p.get("FIN") or p.get("fin"))   # heure de reprise (fin du créneau)
    blocs = [
        g.etiquette("SERVICE · MAINTENANCE", "maintenance"),
        g.titre_auto(titre),
    ]
    if fenetre:
        blocs.append(g.encadre_info(fenetre, "maintenance"))
    if corps:
        blocs.append(g.paragraphe(corps))
    blocs.append(g.paragraphe("Pendant cette fenêtre, l'application peut être brièvement indisponible. "
                              "Il n'y a rien à faire de votre côté : tout reprend automatiquement à la "
                              "fin de l'opération."))
    # Mandat Vic : PAS de bouton pendant une maintenance — une phrase de reprise à la place.
    reprise = (f"Si l'app ne répond pas pendant ce créneau, réessayez après {fin}." if fin
               else "Si l'app ne répond pas pendant ce créneau, réessayez une fois l'opération terminée.")
    blocs.append(g.paragraphe(reprise))
    return g.rendre(sujet=f"LABUSE — maintenance programmée : {titre}", registre="auto", blocs=blocs,
                    apercu="Maintenance programmée — ce qu'il faut savoir.",
                    pied=_pied(p, "Ce message concerne le fonctionnement de votre service ; il n'est pas "
                               "désactivable.", desabo=False))


def _mise_en_vente(p: dict) -> g.Mail:
    idu = _s(p.get("IDU") or p.get("idu_court")) or "votre parcelle"
    commune = _s(p.get("COMMUNE") or p.get("commune"))
    type_label = _s(p.get("TYPE") or p.get("type_label")) or "bien"
    prix = _s(p.get("PRIX") or p.get("prix"))
    detail = f"{type_label} à {commune}" + (f", {prix}" if prix else "")
    blocs = [
        g.etiquette("RADAR · MISE EN VENTE", "radar"),
        g.titre_auto("Une parcelle que vous suivez est en vente"),
        g.paragraphe(f"Une annonce vient de paraître sur une parcelle que vous suivez : {idu} — {detail}."),
        g.bouton("Voir l'annonce", _lien(p, "LIEN", "lien")),
        g.note("Le lien renvoie au portail d'origine. LABUSE ne republie aucune annonce."),
    ]
    return g.rendre(sujet=f"LABUSE — votre parcelle {idu} est mise en vente", registre="auto", blocs=blocs,
                    apercu="Une parcelle suivie vient d'être mise en vente.", pied=_pied(p, R_RADAR))


# ════════════════════════════ registre & dispatch ════════════════════════════

#: clé de mail → fonction de rendu. UN SEUL mail de réinitialisation (`mdp_oublie`) : le doublon
#: `smtp_reset_password` est supprimé (mandat Vic). `mise_en_vente` est la clé interne de la file.
_BUILDERS = {
    "essai": _essai, "souscription": _souscription,
    "onboarding1": _onboarding1, "onboarding2": _onboarding2, "onboarding3": _onboarding3,
    "relance_carte": _relance_carte, "suspension": _suspension, "retablissement": _retablissement,
    "resiliation": _resiliation, "retour_traite": _retour_traite, "essai_fin_proche": _essai_fin_proche,
    # UN SEUL mail de réinitialisation (mandat Vic) : `mdp_oublie` est l'unique chemin ;
    # la clé historique `smtp_reset_password` est supprimée (plus de doublon).
    "mdp_oublie": _mdp_oublie,
    "mdp_modifie": _mdp_modifie, "email_change": _email_change,
    "radar_digest": _radar_digest, "radar_alerte": _radar_alerte, "flash_pret": _flash_pret,
    "smtp_digest_notifications": _digest_notifications, "smtp_annonce": _annonce,
    "smtp_maintenance": _maintenance, "smtp_mise_en_vente": _mise_en_vente,
    "mise_en_vente": _mise_en_vente,
}


def gere(key: str) -> bool:
    """True si le contenu de `key` est rendu ici (donc par l'app, via le gabarit)."""
    return key in _BUILDERS


def rendre(key: str, params: dict | None = None) -> g.Mail:
    """Rend le mail `key` avec `params`. Lève KeyError si la clé n'est pas gérée."""
    b = _BUILDERS.get(key)
    if not b:
        raise KeyError(f"mail inconnu « {key} » (non géré par mails_contenu)")
    return b(params or {})


#: ORDRE DU CATALOGUE (recette `[V3 nn/NN]`). Le doublon de réinitialisation `smtp_reset_password`
#: (ancien #17) est RETIRÉ — un seul mail de reset (`mdp_oublie`). Il reste donc 20 mails distincts.
ORDRE_CATALOGUE = [
    "essai", "souscription", "onboarding1", "onboarding2", "onboarding3",
    "relance_carte", "suspension", "retablissement", "radar_digest", "radar_alerte",
    "mdp_oublie", "mdp_modifie", "resiliation", "flash_pret", "email_change", "retour_traite",
    "smtp_digest_notifications", "smtp_annonce", "smtp_maintenance", "smtp_mise_en_vente",
]


# ── jeux d'exemple (recette + test automatique) — fictifs mais réalistes (La Réunion) ──
_B = "https://app.labuse.immo"
_DESABO = f"{_B}/events/desabonner?c=140&t=TKTEST"
_PREFS = f"{_B}/events/preferences?c=140&t=TKTEST"
_BIENS_RADAR = [
    {"titre": "Terrain, La Montagne", "detail": "512 m² · zone Ua · vu ce matin sur Leboncoin", "prix": "180 000 €"},
    {"titre": "Terrain, Sainte-Clotilde", "detail": "640 m² · zone Ub · vu ce matin sur Bien’ici", "prix": "235 000 €"},
    {"titre": "Terrain, Le Brûlé", "detail": "1 150 m² · zone AU · vu hier sur Leboncoin", "prix": "149 000 €"},
]
_COMMUN = {"PRENOM": "Camille", "LIEN_PREFS": _PREFS, "LIEN_DESABO": _DESABO, "LIEN_APP": _B}

#: paramètres d'exemple par clé (mêmes valeurs que MAILS-TEST-1 : Camille, La Montagne, BZ1065).
SPECIMENS: dict[str, dict] = {
    "essai": {**_COMMUN, "LIEN_INVITATION": f"{_B}/invitation?token=TKTEST", "FIN_ESSAI": "09/11/2026 à 18h00"},
    "souscription": {**_COMMUN, "LIEN_SOUSCRIPTION": f"{_B}/souscrire?token=TKTEST"},
    "onboarding1": {**_COMMUN, "LIEN_INVITATION": f"{_B}/invitation?token=TKTEST"},
    "onboarding2": {**_COMMUN, "JAMAIS_CONNECTE": True},
    "onboarding3": {**_COMMUN},
    "relance_carte": {**_COMMUN, "LIEN_PAIEMENT": f"{_B}/facturation"},
    "suspension": {**_COMMUN, "LIEN_PAIEMENT": f"{_B}/facturation"},
    "retablissement": {**_COMMUN},
    "radar_digest": {**_COMMUN, "DATE": "07/11/2026", "NB_BIENS": "3", "BIENS": _BIENS_RADAR,
                     "LIEN_RADAR": f"{_B}/radar"},
    "radar_alerte": {**_COMMUN, "VEILLE": "Saint-Denis — terrains de plus de 400 m²", "NB_BIENS": "3",
                     "CRITERES": "Terrain · plus de 400 m² · zone U · Saint-Denis", "BIENS": _BIENS_RADAR,
                     "LIEN_RADAR": f"{_B}/radar", "LIEN_VEILLE": f"{_B}/radar?veille=1"},
    "mdp_oublie": {**_COMMUN, "LIEN_RESET": f"{_B}/reset?token=TKTEST", "VALIDITE": "1 heure"},
    "mdp_modifie": {**_COMMUN, "DATE_HEURE": "07/11/2026 à 14h00", "LIEN_RESET": f"{_B}/reset?token=TKTEST"},
    "resiliation": {**_COMMUN, "DATE_FIN_ACCES": "30/11/2026", "LIEN_PAIEMENT": f"{_B}/facturation"},
    "flash_pret": {"LIEN_PDF": f"{_B}/flash/97411000BZ1065.pdf", "VALIDITE": "30",
                   "IDU": "97411000BZ1065", "COMMUNE": "La Montagne"},
    "email_change": {**_COMMUN, "ANCIEN_EMAIL": "ancienne@exemple.fr", "NOUVEL_EMAIL": "nouvelle@exemple.fr"},
    "retour_traite": {**_COMMUN,
                      "SON_MESSAGE": "Bonjour, la zone PLU d'une de mes parcelles me semble fausse.",
                      "REPONSE": "Merci de votre signalement : c'est corrigé, la parcelle est bien en zone U."},
    "smtp_digest_notifications": {
        **_COMMUN,
        "EVENEMENTS": [
            {"titre": "Vente détectée", "detail": "DVF octobre 2026 · 97411000BZ1065",
             "lien": f"{_B}/socle/#idu=97411000BZ1065"},
            {"titre": "Permis déposé", "detail": "PC 974 11 26 B0012 · La Montagne",
             "lien": f"{_B}/socle/#idu=97411000BZ1065"},
        ],
        "MARCHE": {"total": 7, "dans_vos_communes": 2}},
    "smtp_annonce": {**_COMMUN, "TITRE": "nouvelle source : RNU (règlement national d'urbanisme)",
                     "CORPS": "Une nouvelle source est disponible dans LABUSE : le RNU, pour les "
                     "communes sans PLU. Les fiches concernées l'affichent désormais.",
                     "LIEN": f"{_B}/sources"},
    "smtp_maintenance": {**_COMMUN, "TITRE": "mise à jour serveur",
                         "FENETRE": "Fenêtre de coupure : début 07/11/2026 à 22h00, fin 07/11/2026 à "
                         "23h00, durée estimée 1 h (heure de La Réunion).", "FIN": "23h00",
                         "CORPS": "Nous mettons à jour le serveur qui héberge LABUSE pour améliorer la "
                         "vitesse de la carte."},
    "smtp_mise_en_vente": {**_COMMUN, "IDU": "97411000BZ1065", "COMMUNE": "La Montagne",
                           "TYPE": "terrain", "PRIX": "180 000 €",
                           "LIEN": f"{_B}/socle/#idu=97411000BZ1065"},
    # hors catalogue, mais rendu par code (mandat) :
    "essai_fin_proche": {**_COMMUN, "DATE_FIN": "demain à 18h00", "LIEN_PAIEMENT": f"{_B}/facturation"},
}
