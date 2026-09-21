"""DONNEES-4 — l'oracle indépendant du Dossier attrape les « extracteurs muets ».

L'oracle (`exports/oracle_dossier`) lit la valeur LÀ OÙ LA FICHE RÉACT la lit ; un extracteur
qui lit une mauvaise clé renvoie None → « extracteur muet ». Ces tests cassent si un extracteur
redevient muet (ex. `_c_artif` relit `artif_pct`) et vérifient la cohérence du registre de l'oracle.
"""
from __future__ import annotations

from labuse.exports import oracle_dossier as O
from labuse.exports.robinet_fiche import EXTRACTEURS


def _val(ev):
    """Extracteur → scalaire (l'extracteur rend la valeur brute ou un objet Valeur)."""
    return getattr(ev, "valeur", ev)


def test_oracle_attrape_artif_muet_si_mauvaise_cle():
    """CASSE si on remet `artif_pct` dans `_c_artif` : l'oracle lit `le_bien.ocsge.part_artif_pct`
    (12,6 %), l'extracteur DOIT rendre 12,6 — pas None. Un extracteur qui relit la mauvaise clé
    renvoie None alors que l'oracle a une valeur = extracteur muet."""
    f = {"le_bien": {"ocsge": {"part_artif_pct": 12.6, "us_dominant": "US6.3"}}}
    ov = O.valeur_oracle(f, "part_artificialisee_pct")
    assert ov == 12.6, "l'oracle doit lire part_artif_pct (le chemin du composant React)"
    ev = _val(EXTRACTEURS["part_artificialisee_pct"](None, "97410000AN0347", f))
    assert ev is not None, (
        "extracteur MUET : _c_artif ne lit pas part_artif_pct (mauvaise clé ex. artif_pct)")
    # la règle exacte de l'oracle : oracle présent ET extracteur None = muet
    assert not (O.present(ov) and ev is None)


def test_oracle_attrape_toit_muet_si_mauvaise_cle():
    """Même garde pour les deux muets trouvés en DONNEES-4 : pente_mediane_deg et libelle du toit."""
    f = {"le_bien": {"toit": {"pente_mediane_deg": 11.6, "libelle": "double pente"}}}
    for cid in ("pente_toit_deg", "nature_toit"):
        ov = O.valeur_oracle(f, cid)
        assert O.present(ov), f"oracle {cid} doit voir la valeur du toit"
        ev = _val(EXTRACTEURS[cid](None, "X", f))
        assert ev is not None, f"extracteur MUET : {cid} lit une clé absente du payload toit"


def test_oracle_ignore_sentinels_conditionnels():
    """Les sentinels que la fiche React n'affiche PAS en valeur (DPU non 'servi', PEB 'hors')
    ne sont pas des muets : l'oracle réplique la condition d'affichage."""
    f = {"dispositifs": {"dpu": {"etat": "non_determinee", "detail": "x"},
                         "peb": {"zone": "hors", "detail": "y"}}}
    assert O.valeur_oracle(f, "dpu_perimetre") is None
    assert O.valeur_oracle(f, "peb_zone") is None
    # ... mais une vraie zone PEB / un DPU servi SONT affichés :
    f2 = {"dispositifs": {"dpu": {"etat": "servi", "statut": "renforce"}, "peb": {"zone": "B"}}}
    assert O.present(O.valeur_oracle(f2, "dpu_perimetre"))
    assert O.valeur_oracle(f2, "peb_zone") == "B"


def test_oracle_couvre_chaque_ligne_du_dossier():
    """Chaque extracteur du Dossier est soit dans l'ORACLE (chemin/condition du composant), soit
    déclaré HORS_PAYLOAD (rendu par une autre requête) — aucune ligne sans traitement, aucun
    chevauchement, aucun id inconnu."""
    couverts = set(O.ORACLE) | set(O.ORACLE_FN)
    assert not (couverts & set(O.HORS_PAYLOAD)), "un id ne peut être à la fois oracle ET hors-payload"
    # tout id de l'oracle/hors-payload est un vrai extracteur du registre
    for cid in couverts | set(O.HORS_PAYLOAD):
        assert cid in EXTRACTEURS, f"{cid} n'est pas un extracteur du Dossier"
    # tout extracteur de FICHE (hors run_label_servi méta) est traité par l'un des deux
    manquants = set(EXTRACTEURS) - couverts - set(O.HORS_PAYLOAD)
    assert manquants == set(), f"extracteurs sans oracle ni hors-payload : {sorted(manquants)}"
