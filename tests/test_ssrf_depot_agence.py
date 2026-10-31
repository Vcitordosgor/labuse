"""URGENCE-1 (NU-F-004 / NU-F-007) — SSRF fermé.

Le serveur ne va JAMAIS chercher une URL fournie par le client, sauf le dépôt agence qui n'accepte
QUE des hôtes d'une liste blanche de portails ET jamais une adresse privée/interne. Ces tests ne
touchent pas le réseau : liste blanche par nom d'hôte, rejet d'adresse privée par IP littérale.
"""
from __future__ import annotations

import pytest

from labuse.pige import api


def test_hote_allowlist_portails_connus():
    for ok in ("www.leboncoin.fr", "leboncoin.fr", "m.leboncoin.fr", "www.seloger.com",
               "www.bienici.com", "www.pap.fr", "www.logic-immo.com"):
        assert api._hote_autorise(ok), ok


def test_hote_hors_allowlist_refuse():
    for ko in ("169.254.169.254", "evil.example", "localhost", "metadata.google.internal",
               "leboncoin.fr.evil.com"):
        assert not api._hote_autorise(ko), ko


def test_resout_public_refuse_adresses_privees():
    # IP littérales → pas de DNS : loopback / lien-local / RFC1918 / unspecified tous refusés.
    for priv in ("127.0.0.1", "169.254.169.254", "10.0.0.1", "192.168.1.1", "0.0.0.0", "::1"):
        assert api._resout_public(priv) is False, priv


def test_valider_cible_refuse_schema_et_hote():
    # schéma non http(s)
    with pytest.raises(RuntimeError):
        api._valider_cible("file:///etc/passwd")
    # hôte hors liste blanche (le refus précède toute résolution réseau)
    with pytest.raises(RuntimeError):
        api._valider_cible("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(RuntimeError):
        api._valider_cible("https://interne.local/admin")


def test_valider_cible_refuse_ip_privee_sur_schema_valide():
    # IP privée littérale comme hôte : hors allowlist → refus immédiat (jamais de requête).
    with pytest.raises(RuntimeError):
        api._valider_cible("http://10.1.2.3:8000/")
