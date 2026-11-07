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
SECURITE = {"mdp_oublie", "mdp_modifie", "email_change", "smtp_reset_password"}
AUTO = {"radar_digest", "radar_alerte", "flash_pret", "smtp_digest_notifications",
        "smtp_annonce", "smtp_maintenance", "smtp_mise_en_vente"}
# non-sécurité mais sans désinscription (transactionnel / service non désactivable)
SANS_DESABO = {"flash_pret", "smtp_maintenance"}

HREF = re.compile(r'href="([^"]*)"')


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
    assert g.BTN_BG in m.html, f"{key} : bouton vert (#1f7a46) absent"
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
        assert "fondateur de labuse" in m.html.lower()
        assert "+262 693 51 71 53" in m.html, f"{key} : vrai numéro absent de la signature"


@pytest.mark.parametrize("key", TOUS)
def test_pied_de_page(key):
    m = _rendu(key)
    assert g.CONTACT in m.html, f"{key} : contact absent du pied"
    assert g.URL_CONFID in m.html, f"{key} : Confidentialité absente"
    assert g.URL_MENTIONS in m.html, f"{key} : Mentions légales absentes"
    if key in SECURITE:
        assert "Me désinscrire" not in m.html, f"{key} (sécurité) : ne doit PAS avoir de désinscription"
    elif key not in SANS_DESABO:
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


def test_reset_unique_meme_contenu():
    """UN SEUL mail de réinitialisation : `mdp_oublie` et `smtp_reset_password` rendent le MÊME corps."""
    a = mc.rendre("mdp_oublie", mc.SPECIMENS["mdp_oublie"])
    b = mc.rendre("smtp_reset_password", mc.SPECIMENS["smtp_reset_password"])
    assert a.sujet == b.sujet
    assert "nouveau mot de passe" in a.html.lower()


def test_radar_alerte_liste_chaque_bien():
    """L'alerte Radar liste chaque bien : commune, surface, zone, prix, portail, date."""
    m = mc.rendre("radar_alerte", mc.SPECIMENS["radar_alerte"])
    h = m.html
    assert "La Montagne" in h and "Sainte-Clotilde" in h and "Le Brûlé" in h    # communes
    assert "512 m²" in h and "zone Ua" in h and "Leboncoin" in h                 # surface/zone/portail
    assert "180 000 €" in h and "235 000 €" in h                                 # prix
    assert "VOS CRITÈRES" in h


def test_maintenance_dit_quoi_quand_quoi_faire():
    m = mc.rendre("smtp_maintenance", mc.SPECIMENS["smtp_maintenance"])
    assert "Fenêtre de coupure" in m.html                 # QUAND
    assert "mettons à jour le serveur" in m.html.lower()  # QUOI
    assert "rien à faire" in m.html.lower()               # QUOI FAIRE
    assert "Me désinscrire" not in m.html                 # service non désactivable
