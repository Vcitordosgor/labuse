"""M73-C — le rendu PARTAGÉ des blocs ANC + réhabilitation (blocs_documents). Verrouille la doctrine :
maille + millésime NOMMÉS, jamais un verdict, un taux bas (16 %) ne se lit pas comme un feu vert,
l'absence de potentiel s'AFFICHE (jamais masquée)."""
from __future__ import annotations

from labuse.api.blocs_documents import anc_bloc_html, rehab_bloc_html


def _anc_secteur_16():
    # forme EXACTE servie par anc_service.statut_anc (source_secteur, IRIS, taux bas 16 %)
    return {
        "statut": "source_secteur",
        "libelle": "16 % des logements du secteur ne sont pas raccordés au réseau collectif",
        "taux_non_racc": 16, "maille": "secteur IRIS « Le Port Centre »",
        "maille_type": "iris", "millesime": "RP2022",
        "phrase": ("Dans ce secteur IRIS « Le Port Centre », 16 % des logements ne sont pas raccordés "
                   "au réseau collectif (INSEE RP2022). C'est un taux de SECTEUR, pas l'état de cette "
                   "parcelle. À vérifier auprès du SPANC."),
        "source": "INSEE RP2022 — variable EGOUL, agrégée par IRIS",
    }


def test_anc_secteur_maille_et_millesime_nommes():
    h = anc_bloc_html(_anc_secteur_16())
    assert "16" in h
    assert "Le Port Centre" in h            # la maille est NOMMÉE visiblement, pas en note
    assert "RP2022" in h                    # le millésime est dit
    assert 'data-anc-statut="source_secteur"' in h


def test_anc_taux_bas_ne_se_lit_pas_comme_feu_vert():
    h = anc_bloc_html(_anc_secteur_16()).lower()
    # jamais un verdict parcellaire, jamais « probablement », toujours l'orientation SPANC + maille secteur
    assert "probablement" not in h
    assert "secteur" in h and "spanc" in h
    assert "pas l'état de cette parcelle" in h   # résiste à la lecture « cette parcelle est raccordée »


def test_anc_absent_est_affiche_jamais_vide():
    h = anc_bloc_html({"statut": "absent", "libelle": "Zonage non disponible",
                       "phrase": "Zonage d'assainissement non disponible… Ce n'est pas un raccordement présumé."})
    assert h and "Absent" in h and 'data-anc-statut="absent"' in h


def test_rehab_absence_affichee_jamais_masquee():
    # un zéro n'est pas une absence : sans potentiel, le bloc s'affiche quand même
    h = rehab_bloc_html({"disponible": False})
    assert h and "Non évaluée" in h
    h2 = rehab_bloc_html(None)
    assert h2 and "Non évaluée" in h2


def test_rehab_trop_petit_dit_le_motif():
    h = rehab_bloc_html({"disponible": True, "trop_petit": True,
                         "motif": "Bâti trop petit pour une thèse de réhabilitation."})
    assert "trop petit" in h.lower()


def test_rehab_disponible_rend_le_montant():
    h = rehab_bloc_html({"disponible": True, "achat_max_libelle": "180 000 €",
                         "surface_parcelle_m2": 420,
                         "terrain_nu": {"valeur_libelle": "63 000 €", "prix_m2": 150, "surface_m2": 420}})
    assert "180 000" in h and "63 000" in h and "Estimé" in h
