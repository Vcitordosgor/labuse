"""MAILS-1 — le gabarit unique et les 21 mails rendus par l'app.

Vérifie, sur CHAQUE mail (les 21 du catalogue + le mail de fin d'essai rendu par code) :
  · le BOUTON d'action principal (vert) est présent et pointe vers un lien cliquable ;
  · la SIGNATURE « Victor Lagane, fondateur de LABUSE » + le VRAI numéro, sur les mails personnels
    (et son ABSENCE sur les mails automatiques, qui portent une étiquette de couleur) ;
  · le PIED de page : contact, « Gérer mes notifications », « Confidentialité », « Mentions légales »,
    et « Me désinscrire » SAUF sur les mails de sécurité ;
  · aucun LIEN mort (href vide / « # ») ni variable de template non substituée (« {{ … }} ») ;
  · les corrections de fond : plus de numéro factice, pas de mention « créole ».

Fonctions pures (aucune base, aucun réseau) — fait partie de la famille du hook.
"""
from __future__ import annotations

import re

import pytest

from labuse import gabarit_mail as g
from labuse import mails_contenu as mc

TOUS = mc.ORDRE_CATALOGUE + ["essai_fin_proche"]
SECURITE = {"mdp_oublie", "mdp_modifie", "email_change"}
AUTO = {"radar_digest", "radar_alerte", "flash_pret", "smtp_digest_notifications",
        "smtp_annonce", "smtp_maintenance", "smtp_mise_en_vente"}
# FACTURATION / ACCÈS → transactionnels comme la sécurité (pas de désinscription) — mandat Vic V4.
TRANSACTIONNEL = {"souscription", "relance_carte", "suspension", "retablissement", "resiliation",
                  "flash_pret"}
# sans désinscription : sécurité + facturation/accès + maintenance (service non désactivable)
SANS_DESABO = TRANSACTIONNEL | {"smtp_maintenance"}
# mandat Vic : pas de bouton pendant une maintenance (une phrase de reprise à la place)
SANS_BOUTON = {"smtp_maintenance"}

HREF = re.compile(r'href="([^"]*)"')
P_TEXTE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
TAGS = re.compile(r"<[^>]+>")


def _rendu(key):
    return mc.rendre(key, mc.SPECIMENS[key])


@pytest.mark.parametrize("key", TOUS)
def test_sujet_present_et_propre(key):
    m = _rendu(key)
    assert m.sujet and m.sujet.strip(), f"{key} : sujet vide"
    assert "{{" not in m.sujet and "None" not in m.sujet, f"{key} : sujet non substitué"


@pytest.mark.parametrize("key", TOUS)
def test_banniere_et_baseline(key):
    m = _rendu(key)
    assert "LA" in m.html and "BUSE" in m.html, f"{key} : logo absent"
    assert g.BASELINE in m.html, f"{key} : baseline absente du bandeau"
    assert g.BANNER_BG in m.html, f"{key} : bandeau sombre absent"
    # largeur 600 px + tableau (compatibilité Gmail/Apple Mail/Outlook, pas de flex)
    assert "max-width:600px" in m.html and "<table" in m.html
    assert "display:flex" not in m.html and "display:grid" not in m.html


@pytest.mark.parametrize("key", TOUS)
def test_bouton_vert_present_et_cliquable(key):
    m = _rendu(key)
    if key in SANS_BOUTON:                       # maintenance : pas de bouton (mandat Vic)
        assert g.BTN_BG not in m.html, f"{key} : ne doit PAS avoir de bouton"
        assert "réessayez après" in m.html, f"{key} : phrase de reprise attendue à la place du bouton"
        return
    # le bouton reprend EXACTEMENT le jeton de la charte (bg #4ade80, texte #06301a)
    assert g.BTN_BG == "#4ade80" and g.BTN_FG == "#06301a"
    assert g.BTN_BG in m.html and g.BTN_FG in m.html, f"{key} : bouton (jeton charte) absent"
    # le bouton est un <a> cliquable (pas un lien brut dans le texte)
    assert re.search(r'<a [^>]*href="https?://[^"]+"[^>]*>', m.html), f"{key} : bouton sans lien http"


@pytest.mark.parametrize("key", TOUS)
def test_registre_signature_ou_etiquette(key):
    m = _rendu(key)
    if key in AUTO:
        assert "Victor Lagane" not in m.html, f"{key} : mail automatique ne doit PAS être signé"
        assert "border-radius:10px" in m.html, f"{key} : étiquette de nature absente"
    else:  # personnel (y compris sécurité)
        assert "Victor Lagane" in m.html, f"{key} : signature absente"
        assert "gestionnaire relation entreprise" in m.html.lower(), f"{key} : titre de signature"
        assert "+262 693 51 71 53" in m.html, f"{key} : vrai numéro absent de la signature"


def test_signature_sans_je_lis_chaque_reponse():
    """Mandat Vic : « je lis chaque réponse » retiré de la LIGNE de signature (le corps peut le dire)."""
    assert "je lis chaque réponse" not in g.SIGNATURE_LIGNE
    assert g.SIGNATURE_TITRE == "Gestionnaire relation entreprise"


@pytest.mark.parametrize("key", TOUS)
def test_pied_de_page(key):
    m = _rendu(key)
    assert g.CONTACT in m.html, f"{key} : contact absent du pied"
    assert g.URL_CONFID in m.html, f"{key} : Confidentialité absente"
    assert g.URL_MENTIONS in m.html, f"{key} : Mentions légales absentes"
    if key in SECURITE or key in SANS_DESABO:
        assert "Me désinscrire" not in m.html, f"{key} : ne doit PAS avoir de désinscription"
    else:
        assert "Me désinscrire" in m.html, f"{key} : désinscription attendue dans le pied"


@pytest.mark.parametrize("key", TOUS)
def test_aucun_lien_mort_ni_variable(key):
    m = _rendu(key)
    assert "{{" not in m.html and "}}" not in m.html, f"{key} : variable de template non substituée"
    assert "None" not in m.html, f"{key} : « None » rendu dans le HTML"
    for href in HREF.findall(m.html):
        assert href.strip(), f"{key} : href vide"
        assert href == f"mailto:{g.CONTACT}" or href.startswith(("http://", "https://", "mailto:")), \
            f"{key} : lien non cliquable {href!r}"
        assert href != "#", f"{key} : lien mort #"


@pytest.mark.parametrize("key", TOUS)
def test_corrections_de_fond(key):
    m = _rendu(key)
    bas = m.html.lower()
    assert "créole" not in bas, f"{key} : promesse « créole » (dépassée)"
    assert "06 92 00 00 00" not in m.html, f"{key} : numéro factice de la maquette resté"
    # version texte : propre et avec la baseline
    assert g.BASELINE in m.texte and "{{" not in m.texte


def test_reset_unique_un_seul_chemin():
    """UN SEUL mail de réinitialisation : `mdp_oublie` seul ; le doublon `smtp_reset_password` n'existe plus."""
    assert mc.gere("mdp_oublie")
    assert not mc.gere("smtp_reset_password"), "le doublon de reset doit être supprimé"
    assert "smtp_reset_password" not in mc.ORDRE_CATALOGUE
    reset = [k for k in mc.ORDRE_CATALOGUE if "mdp_oublie" == k or "reset" in k]
    assert reset == ["mdp_oublie"], f"un seul chemin de reset attendu, vu {reset}"
    a = mc.rendre("mdp_oublie", mc.SPECIMENS["mdp_oublie"])
    assert "nouveau mot de passe" in a.html.lower()


@pytest.mark.parametrize("key", TOUS)
def test_titres_et_phrases_commencent_par_majuscule(key):
    """Mandat Vic : chaque titre et chaque phrase (paragraphe) commence par une majuscule."""
    m = _rendu(key)
    for bloc in P_TEXTE.findall(m.html):
        txt = TAGS.sub("", bloc).replace("&nbsp;", " ").strip()
        # premier caractère alphabétique du paragraphe
        prem = next((c for c in txt if c.isalpha()), "")
        assert not prem or prem == prem.upper(), \
            f"{key} : paragraphe commence par une minuscule → {txt[:50]!r}"


def test_radar_alerte_liste_chaque_bien():
    """L'alerte Radar liste chaque bien : commune, surface, zone, prix, portail, date."""
    m = mc.rendre("radar_alerte", mc.SPECIMENS["radar_alerte"])
    h = m.html
    assert "La Montagne" in h and "Sainte-Clotilde" in h and "Le Brûlé" in h    # communes
    assert "512 m²" in h and "zone Ua" in h and "Leboncoin" in h                 # surface/zone/portail
    assert "180 000 €" in h and "235 000 €" in h                                 # prix
    assert "VOS CRITÈRES" in h


@pytest.mark.parametrize("key", sorted(TRANSACTIONNEL))
def test_facturation_acces_transactionnel(key):
    """Mandat Vic V4 : abonnement / paiement / accès / rapport acheté = transactionnels comme la
    sécurité — pas de désinscription, pas d'en-tête List-Unsubscribe, pied « ...n'est pas désactivable »."""
    m = _rendu(key)
    assert "Me désinscrire" not in m.html, f"{key} : pas de désinscription"
    # pied « Ce message concerne votre abonnement ; il n'est pas désactivable. » (apostrophe échappée en HTML)
    assert "Ce message concerne votre abonnement" in m.html and "pas désactivable" in m.html, \
        f"{key} : pied transactionnel attendu"
    assert "Ce message concerne votre abonnement ; il n'est pas désactivable." in m.texte
    # aucun en-tête de désinscription posé par le mail lui-même
    assert not any(h.lower() == "list-unsubscribe" for h in (m.headers or {})), \
        f"{key} : pas d'en-tête List-Unsubscribe"


@pytest.mark.parametrize("nb,attendu", [("1", "<b>1 bien</b>"), ("3", "<b>3 biens</b>"),
                                        ("12", "<b>12 biens</b>")])
def test_radar_alerte_gras_mot_entier_et_pluriel(nb, attendu):
    """Mandat Vic V4 : le gras couvre le MOT ENTIER, pluriel juste (« 1 bien » / « 3 biens »)."""
    p = {**mc.SPECIMENS["radar_alerte"], "NB_BIENS": nb}
    h = mc.rendre("radar_alerte", p).html
    assert attendu in h, f"attendu {attendu!r}"
    if nb == "1":
        assert "1 biens" not in h          # pas de faux pluriel
    assert "bien</b>s" not in h and "biens</b>s" not in h   # le « s » n'est jamais hors du gras


def test_objets_pas_de_maj_apres_deux_points():
    """Mandat Vic V4 : maj1 ne capitalise jamais un texte inséré après « : » au milieu d'un objet."""
    m = mc.rendre("smtp_maintenance", mc.SPECIMENS["smtp_maintenance"])
    assert m.sujet == "LABUSE — maintenance programmée : mise à jour serveur", m.sujet
    # le TITRE du corps, lui, est bien capitalisé (début de titre)
    assert "Mise à jour serveur" in m.html


def test_flash_badge_vert():
    """Mandat Vic V4 : le badge du rapport est au vert de la charte (comme les autres badges d'info)."""
    m = mc.rendre("flash_pret", mc.SPECIMENS["flash_pret"])
    import labuse.gabarit_mail as gm
    bg, fg = gm.ETIQUETTES["radar"]          # vert de la charte (badge d'information)
    assert f"background:{bg};color:{fg};" in m.html and "RAPPORT · PRÊT" in m.html


def test_maintenance_dit_quoi_quand_quoi_faire():
    m = mc.rendre("smtp_maintenance", mc.SPECIMENS["smtp_maintenance"])
    assert "Mise à jour serveur" in m.html                # titre avec majuscule (mandat Vic)
    assert "Fenêtre de coupure" in m.html                 # QUAND
    assert "mettons à jour le serveur" in m.html.lower()  # QUOI
    assert "rien à faire" in m.html.lower()               # QUOI FAIRE
    assert "réessayez après 23h00" in m.html              # phrase de reprise (pas de bouton)
    assert g.BTN_BG not in m.html                         # AUCUN bouton pendant la maintenance
    assert "Me désinscrire" not in m.html                 # service non désactivable


def test_annonce_bouton_communes():
    m = mc.rendre("smtp_annonce", mc.SPECIMENS["smtp_annonce"])
    assert "Voir les communes concernées" in m.html and "Découvrir" not in m.html
    assert "Nouvelle source : RNU" in m.html              # titre avec majuscule


def test_flash_validite_en_jours():
    m = mc.rendre("flash_pret", mc.SPECIMENS["flash_pret"])
    assert "valable 30 jours" in m.html                   # durée réelle (flash_token_days)


def test_retour_traite_premiere_personne():
    m = mc.rendre("retour_traite", mc.SPECIMENS["retour_traite"])
    assert "aviez signalé" in m.html and "Voici ma réponse" in m.html   # 1re personne
    assert "MA RÉPONSE" in m.html and "nous aviez" not in m.html and "notre réponse" not in m.html.lower()
