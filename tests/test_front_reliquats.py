"""RELIQUATS FRONT (PJ2 · PJ4 · PJ5 · PJ6 + UI O2/O3) — tests d'affichage (pattern test_front_m2 :
marqueurs dans le source servi, garde-fous de régression sans framework JS).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASKBAR = (ROOT / "frontend/src/components/fiche/AskBar.tsx").read_text(encoding="utf-8")
FICHE = (ROOT / "frontend/src/components/fiche/Fiche.tsx").read_text(encoding="utf-8")
# Libellés client centralisés depuis M12/M19 (« texte client centralisé ») → lib/strings.ts (CLIENT.*).
STRINGS = (ROOT / "frontend/src/lib/strings.ts").read_text(encoding="utf-8")


# ───────────────────────── R1 · PJ6 — le panneau IA ne cache plus la fiche ─────────────────────────

def test_r1_replie_par_defaut():
    # M19 : le repli est devenu CONTRÔLABLE (`useState(!!startOpen)`) — replié par défaut, la
    # carte IA (bas de pile) peut l'ouvrir ; l'affordance de réouverture reste présente.
    assert "useState(!!startOpen)" in ASKBAR and "data-askbar-open" in ASKBAR


def test_r1_lien_voir_fiche_present_avec_reponse():
    # lien permanent quand une réponse est affichée ; la réponse reste gardée (pas détruite)
    assert "data-askbar-voir-fiche" in ASKBAR
    assert "Voir l'entièreté de la fiche" in ASKBAR
    assert "réponse reste gardée" in ASKBAR         # title explicite


def test_r1_regle_dure_reponse_bornee_nav_jamais_masquee():
    # RÈGLE DURE : zone de réponse bornée + scroll interne → la nav des onglets ne sort jamais de l'écran
    assert "data-askbar-reponse" in ASKBAR
    assert "max-h-[36vh]" in ASKBAR and "overflow-y-auto" in ASKBAR


def test_r1_redeploiement_sans_perte():
    # replié : le bouton dit que la dernière réponse est gardée ; rouvrir = un clic, cache inchangé.
    # M12/M19 : le libellé « dernière réponse gardée » vit désormais dans lib/strings.ts (CLIENT.*),
    # AskBar le rend via `CLIENT.fiche.ia.gardee` — même texte servi, source unique.
    assert "dernière réponse gardée" in STRINGS
    assert "CLIENT.fiche.ia.gardee" in ASKBAR
    assert "aucun nouvel appel" in ASKBAR


def test_r1_nav_onglets_hors_du_panneau_ia():
    # La fiche est passée en pile scrollée (« plus de navigation par onglets ») ; l'AskBar reste
    # un panneau injecté SÉPARÉMENT et repliable (startOpen/onClose) — il ne masque jamais la fiche (R1).
    # M61-P1 (panneau IA unifié) : le repli booléen `setAskOpen(false)` est devenu l'état à trois
    # valeurs `iaOuvert` → l'onClose réel ferme via `setIaOuvert('aucun')`. La protection tient (AskBar
    # séparé, repliable, `startOpen`), c'est le mécanisme d'état qui a changé de nom.
    assert "<AskBar" in FICHE and "startOpen" in FICHE
    assert "onClose={() => setIaOuvert('aucun')}" in FICHE
    assert "plus de navigation par onglets" in FICHE


# ───────────────────────── R2 · PJ2 — boutons du parcours de tri ─────────────────────────

TINDER = (ROOT / "frontend/src/components/projets/ParcoursTinder.tsx").read_text(encoding="utf-8")
KANBAN = (ROOT / "frontend/src/components/projets/ProjetKanban.tsx").read_text(encoding="utf-8")


def test_r2_trois_decisions_presentes():
    assert "data-decision-ecarter" in TINDER and "data-decision-retenir" in TINDER
    assert "data-decision-analyser" in TINDER       # la 3e décision manquait (PJ2)


def test_r2_couleurs_colonnes_kanban():
    # une décision = la couleur de sa colonne d'arrivée (M2) — revue UI/UX S13/S14 :
    # les hex locaux sont devenus les tokens de palette (mêmes couleurs, source unique)
    assert "st-ecartee" in TINDER and "st-ecartee" in KANBAN   # écartée (#E8695A token)
    assert "st-creuser" in TINDER and "st-creuser" in KANBAN   # à analyser (#E8B44C token)
    assert "bg-mint" in TINDER                                  # retenue (mint plein = la plus forte)


def test_r2_sortie_distincte_des_decisions():
    # Quitter : sobre (txt-mut), dans la barre haute — jamais confondu avec une décision
    assert "data-parcours-quitter" in TINDER and "✕ Quitter" in TINDER
    assert "text-txt-mut" in TINDER.split("data-parcours-quitter")[1][:300]


def test_r2_pas_de_raccourcis_inventes():
    # aucun raccourci clavier n'existe sur les décisions — on n'en affiche pas (règle du lot)
    assert "onKeyDown" not in TINDER.split("DecisionCard")[1]
    assert "on n'en invente pas" in TINDER


# ───────────── R3 · PJ5 — tooltips ×N + jauge, et wording « deux brûlantes » ─────────────

RESULTS = (ROOT / "frontend/src/components/panel/ResultsSection.tsx").read_text(encoding="utf-8")
STATUS = (ROOT / "frontend/src/lib/status.ts").read_text(encoding="utf-8")
LEGEND = (ROOT / "frontend/src/components/map/Legend.tsx").read_text(encoding="utf-8")
TIERBADGE = (ROOT / "frontend/src/components/outils/TierBadge.tsx").read_text(encoding="utf-8")
MAPVIEW = (ROOT / "frontend/src/components/map/MapView.tsx").read_text(encoding="utf-8")
# B2/M12 : le mini-anneau de complétude a quitté la liste (ResultsSection) → carte Kanban CRM.
KANBAN_CRM = (ROOT / "frontend/src/components/crm/Kanban.tsx").read_text(encoding="utf-8")


# Wordings servis VALIDÉS par Vic (arbitrage 07/2026) — tests remis à jour dessus, xfail retirés.

def test_m135_carte_fraction_pas_de_mult():
    # M135 — la carte de tri sert la FRACTION (« 1/5 sous 1 an »), plus jamais un « ×N ».
    assert "data-fraction" in RESULTS
    assert "p.fraction" in RESULTS
    assert "mult_v2.toFixed" not in RESULTS         # aucun ×N nu de scoring ne survit
    assert "RR" not in RESULTS


def test_r3_tooltip_jauge_completude():
    # M36 Lot B : la jauge Complétude est RETIRÉE des cartes CRM (quasi-constante, M35 D3) —
    # le verrou garde désormais son ABSENCE.
    assert "part des sources disponibles" not in KANBAN_CRM
    assert "completeness_score" not in KANBAN_CRM


def test_m135_echelle_action():
    # M135 — l'échelle SERVIE est une échelle d'ACTION (chip court `label`), plus jamais
    # « brûlante/chaude/à creuser/potentiel long terme » servis comme label de tier.
    assert "brulante: { label: 'Priorité'" in STATUS
    assert "chaude: { label: 'À suivre'" in STATUS
    assert "reserve_fonciere: { label: 'Long terme'" in STATUS
    assert "a_creuser: { label: 'Neutre'" in STATUS
    for mot in ("label: 'Brûlante'", "label: 'Chaude'", "label: 'À creuser'", "label: 'Potentiel long terme'"):
        assert mot not in STATUS, f"ancien libellé servi : {mot}"


def test_r3_desambiguisation_cote_a_cote():
    # M37 : la mention secondaire « (matrice : X) » du TierBadge est RETIRÉE (un seul
    # classement à l'écran, le tier servi). Le tooltip de désambiguïsation disparaît (le
    # repli STATUT_META « hors run » reste légitime). Plus de rendu « (matrice : » interpolé.
    assert "Deux classements distincts" not in TIERBADGE
    assert "(matrice :" not in TIERBADGE.replace("« (matrice : X) »", "")
    # M36 Lot A : étiquette de source VRAIE — cas nominal « Classement servi », repli
    # honnête « Classement historique » ; le jargon « Matrice Q×A » ne s'affiche plus.
    assert "Verdict · Classement servi" in LEGEND
    assert "Verdict · Classement historique" in LEGEND
    assert "Verdict · Matrice Q×A" not in LEGEND


def test_r3_marqueur_commune_etiquette_vraie():
    # M35/M36 : le compteur commune sert les TIERS du run servi — le vocabulaire thermique
    # est désormais LE BON (réservé au tier P, règle R3 respectée) et l'étiquette est vraie.
    assert "parcelles prioritaires ou à suivre au classement servi" in MAPVIEW
    assert "en priorité dossier (matrice Q×A)" not in MAPVIEW   # l'étiquette AFFICHÉE fausse a disparu


# ───────────── R5 — UI des outils O2 (scoreur d'adresse) et O3 (anti-fiche) ─────────────

HEADER = (ROOT / "frontend/src/components/header/Header.tsx").read_text(encoding="utf-8")
# FUSION (Vic 21/08/2026) — scoreur d'adresse + calculette = « Étudier un bien ». Les anciens composants
# ScoreurAdresse.tsx / CalculetteFonciere.tsx sont SUPPRIMÉS ; la logique vit dans EtudierBien.tsx.
ETUDIER = (ROOT / "frontend/src/components/outils/EtudierBien.tsx").read_text(encoding="utf-8")
MODULEPANEL = (ROOT / "frontend/src/components/outils/ModulePanel.tsx").read_text(encoding="utf-8")
FICHE_TSX = (ROOT / "frontend/src/components/fiche/Fiche.tsx").read_text(encoding="utf-8")
ANSWERING = (ROOT / "src/labuse/copilote_v2/answering.py").read_text(encoding="utf-8")
POURQUOI = (ROOT / "frontend/src/components/fiche/PourquoiPas.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")
REGISTRY = (ROOT / "frontend/src/components/outils/registry.ts").read_text(encoding="utf-8")


def test_r5_etudier_trouvable_depuis_les_outils():
    # Le créneau PHARE O2 est conservé (clé 'scoreur-adresse' inchangée), relabellisé « Étudier un bien ».
    assert "'scoreur-adresse'" in REGISTRY and "Étudier un bien" in REGISTRY
    assert "phare: true" in REGISTRY.split("scoreur-adresse")[1][:200]


def test_r5_etudier_champs_et_prix_manuel():
    # PATRON OMNIBOX (M137) : UN SEUL champ (ParcelInput) accepte adresse OU IDU — plus de 2e champ
    # IDU séparé. Prix saisi à la main (jamais scrapé). Résultat + porte fiche présents.
    assert "ParcelInput" in ETUDIER and 'dataAttr="etudier-adresse"' in ETUDIER   # rendu data-etudier-adresse
    assert "data-etudier-idu" not in ETUDIER                            # champ IDU séparé RETIRÉ (unifié)
    assert "data-etudier-prix" in ETUDIER and "jamais scrapé" in ETUDIER
    assert "data-etudier-resultat" in ETUDIER and "data-etudier-fiche" in ETUDIER


def test_r5_etudier_constat_nu_sans_verdict_marche():
    # M128-6-§1.3 TIENT après la fusion : le constat est chiffré NU — AUCUN badge/verdict de marché.
    # Le badge « repère marché » M137-S reste NON embarqué (ne pas juger à la place du client).
    assert "data-etudier-constat" in ETUDIER                            # le bloc constat existe
    # AUCUN badge-verdict de marché — ne doit pas réapparaître (ni ancien nom scoreur, ni nouveau)
    for v in ("sous_marche", "dans_marche", "sur_marche", "data-scoreur-prix-verdict",
              "data-etudier-prix-verdict"):
        assert v not in ETUDIER


def test_r5_etudier_referentiel_marche_unique():
    # Arbitrage fusion : LE référentiel marché = prix terrain nu de zone (data-etudier-terrain-zone).
    # `score_e.prix_probable` reste vivant côté serveur mais N'EST PLUS AFFICHÉ dans l'outil fusionné.
    assert "data-etudier-terrain-zone" in ETUDIER
    assert "prix_probable" not in ETUDIER                               # score_e retiré de la surface UI


def test_r5_etudier_deux_marges_chacune_dit_son_referentiel():
    # La marge apparaît deux fois, chacune DIT son référentiel : constat « aux hypothèses calibrées »
    # (bilan servi par secteur) ; calculette « selon vos hypothèses » (réglable, dans Fiche.tsx).
    assert "aux hypothèses calibrées" in ETUDIER and "data-etudier-charge-calibree" in ETUDIER
    assert "data-etudier-marge-calibree" in ETUDIER
    assert "selon vos hypothèses" in FICHE_TSX


def test_r5_etudier_hors_base_honnete():
    # ok:false → le message honnête de l'API est affiché, jamais un verdict inventé
    assert "!d.ok" in ETUDIER and "d.message" in ETUDIER


def test_fusion_deux_cles_resolvent_jamais_404():
    # PIÈGE DES RETRAITS : les DEUX clés doivent résoudre le composant fusionné (aucun 404 sur une
    # porte / un deep-link / le copilote). Créneau phare O2 conservé, clé M23 ALIASÉE (hidden).
    assert "'scoreur-adresse': EtudierBien" in MODULEPANEL
    assert "'calculette-fonciere': EtudierBien" in MODULEPANEL
    # registre : M23 aliasée = hidden (résout l'en-tête, pas de carte en double)
    assert "hidden: true" in REGISTRY.split("calculette-fonciere")[1][:200]
    # la porte fiche ouvre toujours l'outil pré-rempli via la clé M23 (alias) — jamais un 404
    assert "setModule('calculette-fonciere')" in FICHE_TSX and "setCalcPrefill(idu)" in FICHE_TSX
    # le copilote route toujours les deux intentions (charge foncière → calculette-fonciere ; scorer → scoreur-adresse)
    assert "\"calculette-fonciere\"" in ANSWERING and "\"scoreur-adresse\"" in ANSWERING


def test_omnibox_parcelinput_chemin_unique():
    """PATRON OMNIBOX (M137) — un SEUL champ accepte adresse ET IDU, via le composant PARTAGÉ
    ParcelInput. Chemin unique : la reconnaissance d'IDU vit à UN endroit (format.ts `estIdu`,
    LOI-3), AddressAutocomplete la réutilise (plus de regex recopiée), et chaque outil à saisie de
    parcelle passe par ParcelInput (plus de champ IDU brut ni d'onglet par écran)."""
    root = ROOT / "frontend/src"
    PI = (root / "components/ParcelInput.tsx").read_text(encoding="utf-8")
    FORMAT = (root / "lib/format.ts").read_text(encoding="utf-8")
    AAC = (root / "components/AddressAutocomplete.tsx").read_text(encoding="utf-8")
    PP = (root / "components/outils/ParcelPicker.tsx").read_text(encoding="utf-8")
    O5 = (root / "components/outils/blocB.tsx").read_text(encoding="utf-8")
    # 1) la règle IDU a UN seul foyer (format.ts), AddressAutocomplete la réutilise (pas de regex copiée)
    assert "export const estIdu" in FORMAT
    assert "estIdu" in AAC and "d{5}[0-9A-Za-z]" not in AAC
    # 2) ParcelInput = AddressAutocomplete + aiguillage estIdu sur Entrée — le composant unique
    assert "AddressAutocomplete" in PI and "estIdu" in PI and "onEnterRaw" in PI
    # 3) chaque outil à saisie de parcelle passe par ParcelInput (plus de champ IDU séparé / onglet)
    assert "ParcelInput" in ETUDIER                       # Étudier un bien
    assert "ParcelInput" in PP and "<input" not in PP     # ParcelPicker (→ Faisabilité M22) : plus d'input brut
    assert 'dataAttr="o5-idu"' in O5 and "<input data-o5-idu" not in O5   # Risques « une parcelle »
    assert 'dataAttr="courrier-idu"' in MODULEPANEL and 'dataAttr="temps-idu"' in MODULEPANEL  # Courrier + Remonter le temps


def test_r5_pourquoi_pas_onglet_conditionnel():
    # tiroir « Pourquoi pas ? » ajouté SEULEMENT pour écartées/flaggées (conditionnel), rendu via
    # PourquoiPasTab ; l'onglet est un littéral d'union 'pourquoi' (refactor : plus de constante TAB_POURQUOI).
    assert "'pourquoi'" in FICHE and "Pourquoi pas ?" in FICHE
    assert "verdictEcartee" in FICHE and "SOFT_FLAG" in FICHE     # condition écartée / flaggée
    assert "<PourquoiPasTab" in FICHE and "PourquoiPasTab" in FICHE


def test_r5_pourquoi_pas_hierarchise_et_source():
    assert "RÉDHIBITOIRE" in POURQUOI and "VIGILANCE" in POURQUOI
    assert "data-pourquoi-pas" in POURQUOI
    assert "m.source" in POURQUOI                   # chaque motif porte sa source
    assert "Aucun motif" in POURQUOI                # sans motif : on le dit, rien d'inventé


def test_r5_api_helpers():
    assert "scoreurAdresse" in API and "/scoreur-adresse" in API and "prix_demande_eur" in API
    assert "getAntiFiche" in API and "/anti-fiche/" in API


def test_m135_tiers_front_back_alignes():
    """M135 — le mapping des tiers vit à UN endroit canonique (backend tiers_client) ; le front
    status.ts le reflète EXACTEMENT (TS/Python ne partagent pas un littéral → ce test est le
    garde-fou anti-dérive). Chip court `label` + libellé `long`, pour chaque tier v2."""
    import re
    from labuse.scoring.tiers_client import TIERS_CLIENT
    status = (ROOT / "frontend/src/lib/status.ts").read_text(encoding="utf-8")
    # scoper au bloc TIER_V2_META (la matrice STATUT_META porte aussi une clé `chaude`)
    blk = status.split("export const TIER_V2_META", 1)[1].split("LEGEND_V2_ORDER", 1)[0]
    dblk = status.split("export const TIER_DECLASSE_META", 1)[1].split("DECLASSE_ORDER", 1)[0]

    def meta(code: str, src: str) -> tuple[str, str]:
        m = re.search(rf"\b{code}: {{ label: '([^']*)', long: '([^']*)'", src)
        assert m, f"tier {code} introuvable (format label/long)"
        return m.group(1), m.group(2)

    for code in ("brulante", "chaude", "reserve_fonciere", "a_creuser", "ecartee"):
        court, lng = meta(code, blk)
        assert (court, lng) == TIERS_CLIENT[code], (
            f"DÉRIVE front/back sur {code} : front={court!r}/{lng!r} ≠ back={TIERS_CLIENT[code]}")
    # la famille declasse_* collapse sur « Faible / Peu de potentiel » des deux côtés
    dc, dl = meta("declasse_bati_sature", dblk)
    assert (dc, dl) == TIERS_CLIENT["declasse_bati_sature"] == ("Faible", "Peu de potentiel")


def test_m135_fraction_sql_egale_python():
    """M135 P2 — le CASE SQL (geojson caché) donne EXACTEMENT la même fraction que
    fraction_humaine (Python) sur toute la plage : un seul arrondi, config-driven, zéro dérive."""
    import re as _re
    from labuse.scoring.fraction_client import fraction_sql_case, fraction_humaine
    case = fraction_sql_case("P")
    seuil = float(_re.search(r"P < ([\d.]+)", case).group(1))
    bornes = [(m.group(2), float(m.group(1))) for m in _re.finditer(r"P >= ([\d.]+) THEN '(1/\d+)'", case)]

    def sql(p: float):
        if p is None or p < seuil:
            return None
        for txt, lo in bornes:                     # bornes décroissantes
            if p >= lo:
                return txt
        return None

    for i in range(0, 1001):
        p = i / 1000
        py = (fraction_humaine(p) or {}).get("texte")
        if sql(p) == py:
            continue
        # tolérance UNIQUEMENT à l'ex æquo EXACT (milieu de deux paliers équidistants) : le choix
        # y est arbitraire (le flottant tranche d'un côté, le seuil SQL de l'autre) — mesure-zéro.
        ecart = min(abs(1.0 / d - p) for d in fraction_sql_case.__globals__["_cfg"]()["paliers"])
        proches = [d for d in fraction_sql_case.__globals__["_cfg"]()["paliers"] if abs(abs(1.0 / d - p) - ecart) < 1e-9]
        assert len(proches) >= 2, f"dérive SQL/Python à p={p} : sql={sql(p)} py={py}"


def test_m135_raison_front_back_alignes():
    """M135 P3 — le miroir TS raison.ts a les MÊMES clés (features) que le Python
    _RAISON_COURTE (le geojson dérive la raison au front, la liste île la reçoit servie)."""
    import re as _re
    from labuse.scoring.p_v2.libelles_client import _RAISON_COURTE
    ts = (ROOT / "frontend/src/lib/raison.ts").read_text(encoding="utf-8")
    ts_keys = set(_re.findall(r"^  (\w+): \(", ts, _re.M))
    assert ts_keys == set(_RAISON_COURTE), (
        f"DÉRIVE raison front/back : front-back={ts_keys ^ set(_RAISON_COURTE)}")
