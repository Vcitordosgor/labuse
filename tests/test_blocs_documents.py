"""M73-C — le rendu PARTAGÉ des blocs ANC + réhabilitation (blocs_documents). Verrouille la doctrine :
maille + millésime NOMMÉS, jamais un verdict, un taux bas (16 %) ne se lit pas comme un feu vert,
l'absence de potentiel s'AFFICHE (jamais masquée)."""
from __future__ import annotations

from labuse.api.blocs_documents import (_bloc_html, anc_bloc, anc_bloc_html,
                                        rehab_bloc, rehab_bloc_html)


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


# ── M73-D : la forme NEUTRE (consommée par fpdf) et la PARITÉ avec le HTML ────────────────────────
def test_forme_neutre_anc_porte_le_texte_et_les_etats():
    b = anc_bloc(_anc_secteur_16())
    assert b["statut"] == "source_secteur" and b["etat"] == "Sourcé secteur"
    roles = {r for r, _ in b["lignes"]}
    assert "maille" in roles and "phrase" in roles         # maille = ligne explicite, pas une note
    # le premium fpdf itère ces lignes : le texte servi vit ICI, une fois.
    assert any("RP2022" in t for _, t in b["lignes"])


def test_parite_neutre_html_aucune_divergence():
    # tout texte de la forme neutre se retrouve dans le HTML : les deux médias posent le MÊME texte.
    for src in (anc_bloc(_anc_secteur_16()), rehab_bloc({"disponible": True,
                "achat_max_libelle": "180 000 €", "terrain_nu": {"valeur_libelle": "63 000 €",
                "prix_m2": 150, "surface_m2": 420}})):
        h = _bloc_html(src)
        for _, texte in src["lignes"]:
            assert texte.split(" (INSEE")[0][:20] in h     # fragment stable présent des deux côtés


def test_rehab_neutre_jamais_none_absence_affichee():
    assert rehab_bloc(None)["etat"] == "Non évaluée"        # jamais None, l'absence est un état
