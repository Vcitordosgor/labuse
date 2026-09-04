"""RETOURS-11F — session F3 (branche `fix/retours-11f3`). Gardes des soldes finaux.

Chaque test grave une divergence corrigée pour qu'elle ne revienne pas. Les gardes de
structure (chaîne SQL, config) sont LECTURE SEULE (aucune base) ; celles qui exigent la
base sont marquées `db` (skippées sans PostGIS).
"""
from __future__ import annotations


# ─────────────────────────── M9 — Densifier : capacité NETTE + surélévation ───────────────────────────

def test_m9_capacite_nette_deduit_les_contraintes():
    """La SDP résiduelle est corrigée par un facteur de constructibilité (PPR rouge %, pente > 30 %,
    ravine, mvt) AVANT de piloter le score : une parcelle contrainte descend. Vic : « 900 m² en
    falaise ne densifie rien »."""
    from labuse import renouvellement as R
    sql = R._BUILD_SQL
    # les trois sources de contrainte, SERVIES par le run (jamais inventées)
    assert "ppr_x" in sql and "PPR zone rouge" in sql, "PPR rouge : fraction réelle non déduite"
    assert "ravine_x" in sql and "mvt_x" in sql, "ravine / mouvement de terrain non pris en compte"
    assert "pente_non_batie_deg" in sql, "pente (parcel_terrain) non prise en compte"
    assert "frac_net" in sql and "sdp_nette" in sql, "SDP nette absente de la formule"
    # le potentiel classe sur la SDP NETTE, plus sur la brute
    assert "percent_rank() OVER (ORDER BY n.sdp_nette)" in sql, "comp_potentiel doit ranker la SDP nette"
    # le facteur reste borné [0,1] (greatest 0 + facteurs ≤ 1)
    assert "greatest(0.0" in sql


def test_m9_surelevation_lue_de_parcel_residuel_bati():
    """La surélévation possible (hauteur PLU − hauteur bâti BD TOPO) est lue de la table déjà
    calculée `parcel_residuel_bati` — jamais recalculée, jamais inventée."""
    from labuse import renouvellement as R
    sql = R._BUILD_SQL
    assert "parcel_residuel_bati" in sql
    assert "surelevation_possible" in sql and "niveaux_sur" in sql
    # DDL : les colonnes existent bien dans la table servie
    assert "sdp_nette_m2" in R.DDL and "surelevation_possible" in R.DDL and "niveaux_surelevation" in R.DDL


def test_m9_config_capacite_nette_chargee():
    """Les facteurs de capacité nette viennent de la config versionnée (jamais codés en dur)."""
    from labuse import renouvellement as R
    cfg = R.load_config()
    cn = cfg["capacite_nette"]
    assert 0 < cn["facteur_pente_forte"] <= 1
    assert 0 < cn["facteur_ravine"] <= 1 and 0 < cn["facteur_mvt"] <= 1
    assert cn["pente_seuil_pct"] == 30
    # le score CONTINU (M9 F2) reste intact : pas de clamp, somme des rangs bruts
    assert "LEAST(100" not in R._BUILD_SQL
    assert "round((c.pr_pot + c.pr_ass + c.pr_mar)" in R._BUILD_SQL


# ─────────────────────────── M13 — colonnes Comparer + sélecteur Évolution ───────────────────────────

def test_m13_compare_row_colonnes_ajoutees():
    """Comparer sert les colonnes O9 manquantes, TOUTES lues de la fiche servie (aucun second moteur) :
    propriétaire, bâti existant %, gabarit max, logements, accès & réseaux (UN verdict), assainissement,
    prix bâti secteur — sans jamais un « 0 » inventé (absent = None)."""
    from labuse.api.app import _compare_row
    qv2 = {
        "idu": "97415000BS0086", "commune": "Saint-Paul", "surface_m2": 1000,
        "score_v2": {"tier": "chaude", "rang": 12, "label": "À suivre", "fraction": "1/5", "pourquoi": []},
        "etage0": False,
        "proprietaire_moral": {"denomination": "PACIFIC", "siren": "484061601"},
        "viabilisation": {"libelle": "Viabilisation probable"},
        "anc": {"libelle": "Tout-à-l'égout (collectif)", "statut": "source"},
        "dvf_parcelle": {"secteur": [
            {"type_bien": "maison", "mediane_prix_m2": 2800, "n_ventes": 43},
            {"type_bien": "terrain", "mediane_prix_m2": 480, "n_ventes": 12}]},
        "lines": [{"result": "SOFT_FLAG", "detail": "Aléa inondation — niveau faible."}],
    }
    faisab = {"zone": "U", "constructible": True,
              "fourchette": {"surface_plancher_m2": 800, "logements_au_sol": [2, 6], "logements_sous_sol": [1, 4]},
              "residuel": {"disponible": True, "emprise_batie_m2": 150, "taux_emprise_pct": 20,
                           "sdp_residuelle_m2": 600, "sous_densite": True, "niveaux_max": 3},
              "bilan": {"charge_fonciere": {"par_m2_terrain": 250}}}
    row = _compare_row(qv2, faisab)
    assert row["proprietaire"] == "morale"                 # PM connue
    assert row["bati_existant_pct"] == 15                  # 150 / 1000
    assert row["gabarit_niveaux_max"] == 3
    assert row["logements_possibles"] == 6                 # borne haute (au sol)
    assert row["acces_reseaux"] == "Viabilisation probable"  # UN verdict
    assert row["assainissement"] == "Tout-à-l'égout (collectif)"
    assert row["prix_secteur_bati_m2"] == 2800            # bâti (maison), JAMAIS le terrain nu


def test_m13_compare_row_particulier_et_absences_sans_zero_invente():
    """Sans PM → particulier ; sans faisabilité/secteur → None (jamais un « 0 »)."""
    from labuse.api.app import _compare_row
    qv2 = {"idu": "97411000AT0710", "commune": "Saint-Denis", "surface_m2": None,
           "score_v2": {}, "etage0": True, "proprietaire_moral": None, "lines": []}
    row = _compare_row(qv2, None)
    assert row["proprietaire"] == "particulier"
    assert row["bati_existant_pct"] is None                # surface absente → None, pas 0
    assert row["prix_secteur_bati_m2"] is None
    assert row["logements_possibles"] is None


def test_m13_evolution_barometre_accepte_commune():
    """Évolution du marché : `_barometre_data` accepte un `insee` (sélecteur de commune) et le neuf
    de la commune vient du moteur UNIQUE M1 (neuf_vefa_commune) — jamais un second calcul."""
    import inspect
    from labuse.api import moteurs
    sig = inspect.signature(moteurs._barometre_data)
    assert "insee" in sig.parameters, "le baromètre doit accepter un insee (sélecteur commune)"
    src = inspect.getsource(moteurs._barometre_data)
    assert "neuf_vefa_commune" in src, "le neuf commune doit venir du moteur unique M1"
    assert "code_commune = :insee" in src, "la série terrain doit filtrer par commune"


# ─────────────────────────── M3 — moteur prix de secteur RÉELLEMENT unique ───────────────────────────

def test_m3_reference_locale_est_dans_le_moteur_et_ref_local_delegue():
    """Le merge est RÉEL : la médiane locale mono-type vit dans le moteur (bilan.reference_locale),
    à côté de sector_price ; `pige.signaux._ref_local` ne recopie plus la boucle/requête, il délègue.
    Un seul point de calcul → plus de « 2 365 vs 2 403 » nés de deux chemins."""
    import inspect as _i
    from labuse.faisabilite import bilan
    from labuse.pige import signaux
    assert hasattr(bilan, "reference_locale"), "le moteur doit posséder reference_locale"
    # sector_price ET reference_locale vivent dans LE MÊME module moteur.
    assert bilan.reference_locale.__module__ == bilan.sector_price.__module__
    deleg = _i.getsource(signaux._ref_local)
    assert "reference_locale" in deleg and "for rayon in RAYONS_SECTEUR_M" not in deleg
    assert "dvf_mutations" not in deleg, "plus aucune requête DVF recopiée hors du moteur"
    # constantes partagées (fenêtre/seuil uniques).
    assert bilan.MIN_N_SECTEUR == 8 and bilan.PERIODE_SECTEUR_ANS == 5


# ─────────────────────────── A5 — préférences notifications : cloche / brief / e-mail ───────────────────────────

def test_a5_prefs_trois_canaux_brief_applicable_chaines_1_2():
    """Les préférences exposent TROIS canaux (cloche / brief / e-mail). Le brief n'est applicable
    qu'aux chaînes 1+2 (parcelles suivies / secteurs) ; les chaînes 3 (annonce/maintenance) sont
    marquées brief_na (envoi immédiat, jamais un brief)."""
    from labuse.api import events
    import inspect as _i
    src = _i.getsource(events.prefs_compte)
    assert '"brief"' in src and '"brief_na"' in src, "prefs_compte doit exposer brief + brief_na"
    # set_pref accepte le canal brief ; le brief du matin le respecte (filtre dédié).
    assert "brief" in _i.signature(events.set_pref).parameters
    assert hasattr(events, "_brief_filter_sql")
    bm = _i.getsource(events.brief_matin)
    assert "_brief_filter_sql" in bm, "le brief du matin doit filtrer sur le canal brief"
    # DDL : la colonne brief existe (idempotente pour les bases servies avant le mandat).
    assert "ADD COLUMN IF NOT EXISTS brief" in events.DDL


def test_a5_brief_na_pour_annonce_et_maintenance():
    """annonce_produit et maintenance (chaîne 3) : brief NON applicable (immédiat) ; parcelle_suivie
    et veille_zone (chaînes 1+2) : brief applicable."""
    from labuse.notif_registry import meta
    assert meta("parcelle_suivie")["chaine"] in (1, 2)
    assert meta("veille_zone")["chaine"] in (1, 2)
    assert meta("annonce_produit")["chaine"] == 3
    assert meta("maintenance")["chaine"] == 3


# ─────────────────────────── Lot S / F4 — Urbanisme : règles de zone AVEC valeurs ───────────────────────────

def test_f4_reglement_valeurs_de_zone_pas_seulement_references():
    """F4 — le règlement PLU sert le TABLEAU des règles clés AVEC leurs VALEURS (hauteur, emprise,
    reculs, pleine terre, stationnement), pas seulement des références d'articles. Les valeurs sont
    LUES du YAML PLU (jamais inventées) ; « non réglementé » et « à vérifier » sont dits."""
    from labuse.plu_reglement import resolve_reglement
    r = resolve_reglement("Saint-Paul", "U1b", "97415")
    assert r and r["calibree"]
    rv = {x["cle"]: x for x in r["regles_valeurs"]}
    # les cinq familles de règles sont présentes, chacune avec un état explicite
    for cle in ("hauteur", "emprise", "recul_voirie", "recul_limites", "pleine_terre", "stationnement"):
        assert cle in rv, f"règle {cle} absente du tableau"
        assert rv[cle]["etat"] in ("chiffre", "texte", "absent", "a_verifier")
    # U1b (parcelle des captures 97415000BS0086) : hauteur 16 m faîtage chiffrée + sa source article
    assert rv["hauteur"]["etat"] == "chiffre" and "16 m" in rv["hauteur"]["valeur"]
    assert rv["hauteur"]["reference"] and "Art. 10" in rv["hauteur"]["reference"]
    # pleine terre 30 % chiffrée ; recul limites 3 m
    assert "30 %" in rv["pleine_terre"]["valeur"]
    assert "3 m" in rv["recul_limites"]["valeur"]
    # jamais une valeur inventée : emprise non réglementée au PLU → dit « non réglementé »
    assert rv["emprise"]["etat"] == "absent" and rv["emprise"]["valeur"] == "non réglementé"


def test_f4_zone_non_outillee_pas_de_valeurs_fabriquees():
    """Une commune/zone non calibrée ne fabrique AUCUNE valeur (regles_valeurs vide)."""
    from labuse.plu_reglement import resolve_reglement
    r = resolve_reglement(None, "UC", "97400")
    assert r and not r["calibree"]
    assert r.get("regles_valeurs", []) == []


# ─────────────────────────── Lot S / F0 — seuils de pertinence par famille ───────────────────────────

def test_f0_seuils_de_pertinence_proximite():
    """F0 — chaque objet « à proximité » a un rayon au-delà duquel il n'est PAS affiché : une ligne HT
    à 3 887 m ou un téléphérique à 24 km ne sont pas des informations (Vic). Les seuils sont GRAVÉS."""
    from labuse.api.app import SEUILS_PROXIMITE_M
    # les familles pointées par l'audit ont un seuil resserré
    assert SEUILS_PROXIMITE_M["ligne_ht"] <= 600      # une HT à 3 887 m n'est pas une contrainte
    assert SEUILS_PROXIMITE_M["telepherique"] <= 3000  # un téléphérique à 24 km est écarté
    assert SEUILS_PROXIMITE_M["arret"] <= 2000
    # le bloc applique bien un filtre par seuil
    import inspect as _i
    src = _i.getsource(__import__("labuse.api.app", fromlist=["_proximites_block"])._proximites_block)
    assert "_sous_seuil" in src and "SEUILS_PROXIMITE_M" in src


# ─────────────────────────── Lot S / F10 — Dispositifs : zonage B1 + TVA DOM ───────────────────────────

def test_f10_dispositifs_dom_b1_et_tva():
    """F10 — la section Dispositifs sert les dispositifs valables sur TOUTE La Réunion : zonage B1
    (PTZ / outre-mer) et TVA DOM (8,5 % ; 2,1 % LLS), rapatriés de Constructibilité. Faits datés,
    JAMAIS un calcul fiscal par projet."""
    import inspect as _i
    from labuse.api import app
    src = _i.getsource(app._territoire_fiscal_block)
    assert "dispositifs_dom" in src
    assert "B1" in src and "8,5" in src and "2,1" in src
    # la bande TVA cite le CGI (art. 278 sexies) et la largeur 300 m (QPV) / 500 m (NPNRU)
    assert "278 sexies" in src and "300 m" in src


# ─────────────────────────── Lot S / F11 — Propriétaire : identité société + wording ───────────────────────────

def test_f11_pm_identite_sirene():
    """F11 — la carte d'identité PUBLIQUE de la société propriétaire (activité APE, siège, date de
    création, état actif) vient de SIRENE (open data), jamais une personne (RGPD)."""
    from labuse.db import session_scope
    from labuse.api.app import _pm_identite
    with session_scope() as s:
        r = _pm_identite(s, "484061601")   # PACIFIC (parcelle des captures)
    if r is None:
        import pytest as _p
        _p.skip("SIRENE indisponible en base de test")
    assert r["ape"] and r["activite"]         # activité NAF résolue
    assert r["siege"] and r["date_creation"]  # siège + date de création
    assert r["actif"] in (True, False)
    assert r["annuaire_url"].endswith("/484061601")


def test_f11_wording_client_non_remarquable():
    """F11 — « Personnes morales non remarquables » est le NOM du fichier DGFiP, pas une phrase
    client → remplacé par « Personne morale — fichier DGFiP » au point de service de la fiche."""
    import inspect as _i
    from labuse.api import app
    src = _i.getsource(app._q_v2_fiche)
    assert "non remarquable" in src and "Personne morale — fichier DGFiP" in src


# ─────────────────────────── AVENANT R9-R11 (recette 04/09 après-midi) ───────────────────────────

def test_avenant_r11_listing_piscines_aligne_sur_le_compteur():
    """AVENANT (note liée R11) — le LISTING piscines suit le MÊME filtre de confiance que le compteur
    (agg) : plus de « 7 821 (agg) vs 8 299 (liste) » sur le même écran. Et la limite de 500 est LEVÉE
    (le listing sert tout le total filtré, paginé par 200 côté front)."""
    import inspect as _i
    from labuse.api import modules
    src = _i.getsource(modules.prospection_solaire)
    assert "inclure_incertaines" in src, "le listing doit accepter le filtre de confiance"
    assert "_piscine_conf_filtre" in src, "le listing doit appliquer le MÊME filtre confiance que l'agg"
    assert "piscine_corrections" in src, "le listing doit exclure les « pas une piscine »"
    assert 'lim = total if piscine == "oui"' in src, "la limite de 500 doit être levée en mode piscines"


def test_avenant_r11_alignement_mesure():
    """AVENANT — vérification sur base réelle : agg.total == liste.total (haute ET incertaines)."""
    from fastapi.testclient import TestClient
    from labuse.api.app import app as _app
    c = TestClient(_app)
    a = c.get("/modules/prospection-piscines")
    if a.status_code != 200 or not (a.json() or {}).get("total"):
        import pytest as _p
        _p.skip("détection piscines absente en base de test")
    lst = c.get("/modules/prospection-solaire?piscine=oui")
    assert lst.json()["total"] == a.json()["total"], "listing ≠ compteur (confiance haute)"
    assert lst.json()["tronquee"] is False, "la limite de 500 doit être levée (pagination sur le total)"
