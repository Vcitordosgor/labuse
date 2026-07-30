"""Arbitrage RE-RUN pt2.1 (Vic) — une zone AU FERMÉE au règlement ne doit JAMAIS être silencieuse.

Avant : `classify_au_statut` sautait toute zone non-constructible (« déjà declasse_zone_fermee ») → la
mesure a montré 454 parcelles AU fermées SERVIES en tête sans avertissement (le préfixe de phasage
1AU/2AU/3AU échappe au test U/AU de la cascade). Désormais : marquée `declasse_au_fermee` + motif sourcé.
Défensif : une zone NON-AU non constructible (A/N) reste None (gérée par la cascade en amont).
Lit les YAML PLU (pas de DB).
"""
from __future__ import annotations

from labuse.faisabilite.au_statut import classify_au_statut, CLASSE_AU_FERMEE
from labuse.faisabilite.constructibilite import DECLASSE_AU_FERMEE, DECLASSE_LABELS


def test_au_fermee_est_marquee_pas_silencieuse():
    # AU*st (Saint-Louis) et phasage fermé (Le Tampon 2AUe) → marquées fermée, jamais None
    c, motif = classify_au_statut("1AUst", "Saint-Louis")
    assert c == CLASSE_AU_FERMEE == DECLASSE_AU_FERMEE
    assert "fermée" in motif.lower() and "modification" in motif.lower()
    assert classify_au_statut("2AUe", "Le Tampon")[0] == CLASSE_AU_FERMEE
    # declasse_au_fermee EST un tier de déclassement (l'avertissement survit à la bascule)
    assert DECLASSE_AU_FERMEE in DECLASSE_LABELS


def test_non_au_fermee_reste_none():
    # A / N non constructibles ne sont PAS des zones AU → gérées par la cascade, pas ici
    assert classify_au_statut("N", "Saint-Joseph")[0] is None
    assert classify_au_statut("A", "Le Tampon")[0] is None
