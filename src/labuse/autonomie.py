"""AUTONOMIE-1 — LABUSE voit, décide et agit seule pour tout ce qui ne demande pas un jugement humain.

Trois doctrines, trois politiques PURES (sans effet de bord, donc testables à l'unité ; le câblage
jobs/DB vit dans `jobs_impl.py` et appelle ces fonctions) :

  1. CALCUL DE NUIT (sur le serveur, plus sur le Mac). `controler_run()` juge un run candidat AVANT de
     le promouvoir : manifeste, comptes, cohérence sur les témoins, aucune copropriété ni parcelle
     entièrement rouge en palier actionnable, écart de paliers avec le run précédent sous un seuil.
     Un seul contrôle en échec = PAS de promotion + alerte. `fenetre_nuit()` / `doit_calculer()`
     bornent la fenêtre 01 h–05 h Réunion et la cadence (déclencheur d'entrée, sinon 1×/semaine).

  2. INJECTION PAR PALIERS. Chaque source du registre porte une CLASSE : A (référence à faible risque)
     s'injecte seule la nuit avec contrôles (comptes, géométries valides, couverture 974, écart sous un
     seuil) et RETOUR ARRIÈRE automatique si un contrôle échoue ; B (structurant) attend le clic de Vic,
     demandé par mail. `classe_source()` tranche ; `controler_injection()` juge une injection A.

  3. INCIDENTS VIVANTS — un incident se ferme seul quand sa cause disparaît (déjà porté par
     `ops_alertes.verifier_declencheurs`). Ici : la FUSION « retard / échec » d'un même job (une seule
     carte par job) et le repérage des incidents ouverts depuis plus de N jours (remontée au mail).

Rien ici n'écrit en base ni ne lance de sous-process : ce sont des JUGEMENTS. « Sur-protéger est bénin,
sous-protéger est le bug » — dans le doute, un contrôle qui ne peut pas conclure est un ÉCHEC (on ne
promeut pas, on n'injecte pas), jamais un vert par vacuité.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


# ════════════════════════════════ 1. CLASSES DE SOURCES (A / B) ════════════════════════════════
#
# A = référence à FAIBLE RISQUE : la donnée décrit un fait stable (population, annuaire, périmètres
#     réglementaires d'information), n'alimente PAS directement le classement des parcelles ni une
#     affirmation foncière opposable, et une mauvaise version se voit tout de suite aux contrôles
#     (comptes/géométries/couverture). → injection AUTOMATIQUE la nuit, avec retour arrière.
#
# B = STRUCTURANT : la donnée nourrit le scoring, la cascade, le zonage, le marché ou la propriété —
#     une mauvaise version fausse silencieusement une décision client. → attend le CLIC de Vic
#     (demandé par mail). C'est le DÉFAUT : toute source non classée explicitement est B (prudence —
#     « dans le doute, un humain décide »).

#: name EXACT (data_sources.name / seed_sources.SOURCES) → (classe, raison courte)
SOURCES_CLASSE: dict[str, tuple[str, str]] = {
    # ——— STRUCTURANT (B) : nourrit scoring / cascade / zonage / marché / propriété ———
    "Cadastre (API Carto PCI)": ("B", "assiette foncière — socle de toute la carte et du scoring"),
    "Cadastre Etalab (bulk DGFiP/Etalab)": ("B", "assiette foncière en masse — socle parcellaire"),
    "Urbanisme PLU/GPU (API Carto)": ("B", "zonage opposable — tranche la constructibilité"),
    "GPU — zonages d'assainissement": ("B", "zonage d'assainissement — entre dans la cascade"),
    "DEAL Réunion — PPR / aléas": ("B", "PPR/aléas — zone rouge = exclusion dans la cascade"),
    "DVF / valeurs foncières": ("B", "marché — médianes et estimations servies au client"),
    "RGE ALTI (altimétrie)": ("B", "LiDAR/pente — entre dans la faisabilité et l'emprise"),
    "OCS GE (IGN) — occupation du sol et artificialisation": ("B", "artificialisation — socle topographique"),
    "RNB — Référentiel National des Bâtiments": ("B", "bâtiments — emprise/densité servies"),
    "BD TOPO IGN": ("B", "bâti/réseaux de référence — emprise et contexte servis"),
    "IGN BD CARTO V5 — occupation du sol": ("B", "occupation du sol — contexte de la cascade"),
    "DGFiP — parcelles des personnes morales": ("B", "propriété — nommée au client (RGPD sensible)"),
    "Fichiers fonciers (Cerema)": ("B", "propriété détaillée sous convention — sensible"),
    "SITADEL (autorisations d'urbanisme)": ("B", "permis — nourrit la veille et le scoring"),
    "DPE ADEME (logements existants)": ("B", "DPE — nourrit features du bâti existant"),

    # ——— RÉFÉRENCE À FAIBLE RISQUE (A) : fait stable, hors chemin de décision foncière ———
    "Contours IRIS (IGN/INSEE)": ("A", "contours statistiques — géométries vérifiables, couverture 974"),
    "INSEE RP Logement 2023": ("A", "population/logement — agrégat statistique de contexte"),
    "Population légale (INSEE via geo.api.gouv)": ("A", "population — fait statistique officiel, recoupable"),
    "Annuaire de l'administration (service-public.fr / DILA)": ("A", "annuaire — fait public, recoupable"),
    "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)":
        ("A", "périmètres protégés (Ramsar/sites classés) — information, géométries vérifiables"),
    "Transport public — GTFS (PAN, 7 réseaux)": ("A", "GTFS transport — référentiel public, recoupable"),
    "Filosofi INSEE (carreaux 200 m)": ("A", "niveau de vie carroyé — contexte, non opposable"),
    "MOBPRO (mobilités domicile-travail, INSEE)": ("A", "mobilités — contexte attractivité"),
    "BPE INSEE": ("A", "équipements — aménités de contexte, comptes vérifiables"),
    "SIRENE": ("A", "annuaire d'entreprises — fait public, recoupable"),
    "SIRENE établissements géolocalisés": ("A", "annuaire géolocalisé — concurrents de l'étude de zone"),
    "Recherche d'entreprises (DINUM)": ("A", "annuaire — fait public"),
    "SUP — assiettes GPU (API Carto)": ("A", "servitudes d'utilité publique — périmètres d'information"),
    "Zones exclues EnR sauf toiture (OFB/APER)": ("A", "zonage OFB/EnR — périmètre d'information"),
    "Contraintes EnR près des habitations (Géoplateforme)": ("A", "zonage EnR — périmètre d'information"),
    "Parc National de La Réunion (INPN)": ("A", "périmètre protégé (cf. Ramsar/INPN) — information"),
    "ZNIEFF (INPN/MNHN)": ("A", "périmètre naturel d'inventaire — information"),
    "INPN / patrinat — espaces protégés": ("A", "espaces protégés — périmètre d'information"),
    "Forêts publiques (ONF)": ("A", "forêts publiques — périmètre d'information"),
    "GéoMCE — mesures compensatoires": ("A", "mesures compensatoires — périmètre d'information"),
    "Base Adresse Nationale": ("A", "adresses — référentiel géocodage, non décisionnel"),
    "QPV 2024 (ANCT)": ("A", "périmètre QPV — zonage d'information fiscale"),
    "ABF / Monuments historiques": ("A", "périmètres patrimoine — information"),
    "Classement sonore ITT (Cerema)": ("A", "classement sonore — périmètre d'information"),
    "BD NYME — lieux-dits (IGN)": ("A", "lieux-dits — toponymie de contexte"),
    "CatNat (arrêtés GASPAR / Géorisques)": ("A", "arrêtés CatNat — information réglementaire datée"),
    "50 pas géométriques — limite haute (DEAL)": ("A", "limite des 50 pas — périmètre d'information"),
    "Trafic RN (Région Réunion — SIR)": ("A", "trafic routier — contexte"),
    "Cerema / GéoLittoral — indicateur d'érosion côtière": ("A", "érosion côtière — indicateur d'information"),
    "Cartofriches (Cerema)": ("A", "friches — signal de contexte"),
}

#: Catégories dont le DÉFAUT penche A (information/contexte) quand la source n'est pas nommée ci-dessus.
#: Tout le reste (urbanisme, risques, marche, cadastre, topographie, proprietaire…) reste B par défaut.
_CATEGORIES_DEFAUT_A = frozenset({"attractivite", "economie", "patrimoine"})


def classe_source(name: str, categorie: str | None = None) -> tuple[str, str]:
    """La classe (A/B) + raison d'une source. DÉFAUT = B (structurant → clic de Vic) : on n'injecte
    JAMAIS seule une source non explicitement reconnue à faible risque. Une catégorie purement
    « contexte » (attractivité/économie/patrimoine) non nommée bascule en A par défaut (recoupable)."""
    if name in SOURCES_CLASSE:
        return SOURCES_CLASSE[name]
    if categorie in _CATEGORIES_DEFAUT_A:
        return ("A", f"contexte ({categorie}) — faible risque, recoupable (défaut de catégorie)")
    return ("B", "non classée explicitement — prudence : un humain décide (défaut)")


def sources_par_classe(sources: list[dict]) -> dict[str, list[dict]]:
    """Range une liste de sources (dicts avec `name`, `category`) par classe. Retourne
    {'A': [...], 'B': [...]} où chaque entrée porte name/category/classe/raison."""
    out: dict[str, list[dict]] = {"A": [], "B": []}
    for s in sources:
        cl, raison = classe_source(s.get("name", ""), s.get("category"))
        out[cl].append({"name": s.get("name"), "category": s.get("category"),
                        "classe": cl, "raison": raison})
    return out


# ════════════════════════════════ Verdict de contrôle (commun) ════════════════════════════════

@dataclass
class Verdict:
    """Le résultat d'une batterie de contrôles. `ok` est vrai SEULEMENT si tous passent ET rien n'est en
    attente. `echecs` liste les contrôles TOMBÉS (une phrase chacun, pour le mail URGENT) ; `en_attente`
    liste les contrôles qu'on ne peut pas encore CONCLURE sans faux-négatif (OPS-NUIT-2 : le banc de
    cohérence de 03h45 pas encore passé) — ni vert ni rouge : le run n'est pas promu (prudence) mais ce
    n'est PAS une panne (résumé en INFO, pas d'incident URGENT). `details` garde les mesures brutes."""
    ok: bool
    echecs: list[str] = field(default_factory=list)
    reussis: list[str] = field(default_factory=list)
    en_attente: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def resume(self) -> str:
        if self.echecs:
            return "REFUS — " + " ; ".join(self.echecs)
        if self.en_attente:
            return "EN ATTENTE — " + " ; ".join(self.en_attente)
        return f"OK — {len(self.reussis)} contrôle(s) passé(s)"


# ════════════════════════════════ 1. CALCUL DE NUIT — fenêtre, cadence, contrôles ═══════════════

def fenetre_nuit(maintenant_reunion: datetime, debut_h: int, fin_h: int) -> bool:
    """Vrai si l'heure Réunion `maintenant_reunion` est dans la fenêtre [debut_h, fin_h[ (ex. 01–05 h).
    Fenêtre qui ne franchit PAS minuit (debut < fin) : le cron vise 01 h, elle se ferme à 05 h."""
    return debut_h <= maintenant_reunion.hour < fin_h


def fenetre_depassee(maintenant_reunion: datetime, fin_h: int) -> bool:
    """Vrai si on a DÉPASSÉ la fin de fenêtre (≥ fin_h) : le calcul en cours doit s'abandonner proprement
    plutôt que mordre sur les heures ouvrées."""
    return maintenant_reunion.hour >= fin_h


def doit_calculer(derniere_promotion: datetime | None, declencheur_entree: bool,
                  cadence_min_jours: int, maintenant: datetime) -> tuple[bool, str]:
    """Le calcul de nuit se déclenche :
      · dès qu'une ENTRÉE a changé (nouvelle injection, source avancée) → `declencheur_entree=True` ;
      · sinon AU PLUS une fois par `cadence_min_jours` (anti-churn : on ne recalcule pas pour rien).
    Retourne (doit, raison). `derniere_promotion` None = jamais promu → on calcule."""
    if declencheur_entree:
        return True, "une entrée a changé (injection ou source avancée) depuis le dernier run"
    if derniere_promotion is None:
        return True, "aucun run promu à ce jour — premier calcul"
    age = maintenant - derniere_promotion
    if age >= timedelta(days=cadence_min_jours):
        return True, f"cadence de fond atteinte ({age.days} j ≥ {cadence_min_jours} j, sans déclencheur)"
    return False, (f"rien de neuf et dernière promotion il y a {age.days} j "
                   f"(< {cadence_min_jours} j) — on ne recalcule pas")


def controler_run(mesures: dict, *, palier_delta_max_pct: float) -> Verdict:
    """Les contrôles AVANT de promouvoir un run candidat. `mesures` (gatheré par jobs_impl contre la
    base) porte :
      · manifeste_present   (bool) — le manifeste local du candidat existe et est lisible
      · run_complet         (bool) — score v2 + cascade présents (verify_completude)
      · comptes_parcelles   (int)  — n parcelles du candidat
      · comptes_precedent   (int)  — n parcelles du run servi (doit être égal)
      · coherence_ecarts    (int)  — écarts de la suite de cohérence sur les témoins (doit être 0)
      · coherence_erreurs   (int)  — lecteurs en erreur (banc non probant si > 0)
      · copro_actionnables  (int)  — copropriétés en palier actionnable (doit être 0 — doctrine E-010)
      · rouge_actionnables  (int)  — parcelles ENTIÈREMENT en zone rouge en palier actionnable (doit 0)
      · paliers_change      (int)  — parcelles changeant de palier vs run précédent
      · paliers_total       (int)  — parcelles comparées (base du %)

    Un seul échec = run NON promu. Les contrôles qui ne peuvent pas conclure (mesure manquante) sont
    des ÉCHECS (prudence)."""
    v = Verdict(ok=True)

    def _exige(cond: bool, nom: str, phrase_echec: str) -> None:
        if cond:
            v.reussis.append(nom)
        else:
            v.ok = False
            v.echecs.append(phrase_echec)

    _exige(bool(mesures.get("manifeste_present")), "manifeste",
           "manifeste du candidat absent ou illisible")
    _exige(bool(mesures.get("run_complet")), "complétude",
           "run incomplet (score v2 ou cascade manquant)")

    cp, cprec = mesures.get("comptes_parcelles"), mesures.get("comptes_precedent")
    _exige(cp is not None and cprec is not None and cp == cprec, "comptes",
           f"compte de parcelles divergent (candidat {cp} ≠ précédent {cprec})")

    ec, erl = mesures.get("coherence_ecarts"), mesures.get("coherence_erreurs")
    if not mesures.get("coherence_frais", True):
        # OPS-NUIT-2 (DEPLOY-AUTONOMIE-2, piège cron) — le banc de cohérence tourne à 03h45, APRÈS le
        # démarrage du calcul (02h) : tant qu'il n'a pas produit de passage FRAIS pour cette nuit, la
        # dernière ligne `coherence_runs` est celle d'HIER (ou aucune). On NE conclut PAS dessus — ni
        # faux vert, ni faux rouge « contrôles en échec ». La cohérence est EN ATTENTE du banc : le run
        # n'est pas promu (prudence) mais ce n'est PAS un incident (le verdict part au résumé en INFO).
        v.en_attente.append("cohérence : le banc de 03h45 n'a pas encore produit de passage frais "
                            "pour cette nuit — verdict au prochain résumé")
    else:
        _exige(ec == 0 and (erl or 0) == 0, "cohérence",
               f"suite de cohérence non verte ({ec} écart(s), {erl} lecteur(s) en erreur)")

    _exige(mesures.get("copro_actionnables") == 0, "copro-hors-palier",
           f"{mesures.get('copro_actionnables')} copropriété(s) en palier actionnable (doctrine E-010)")
    _exige(mesures.get("rouge_actionnables") == 0, "rouge-hors-palier",
           f"{mesures.get('rouge_actionnables')} parcelle(s) entièrement en zone rouge actionnable(s)")

    chg, tot = mesures.get("paliers_change"), mesures.get("paliers_total")
    if chg is None or not tot:
        v.ok = False
        v.echecs.append("écart de paliers incalculable (mesure manquante)")
    else:
        pct = round(100.0 * chg / tot, 2)
        v.details["palier_delta_pct"] = pct
        _exige(pct <= palier_delta_max_pct, "ecart-paliers",
               f"écart de paliers {pct}% > seuil {palier_delta_max_pct}% "
               f"({chg}/{tot} parcelles) — dérive anormale")

    # un contrôle EN ATTENTE (cohérence pas encore mesurée cette nuit) bloque la promotion par prudence,
    # sans être un échec : `ok` tombe, mais `echecs` reste vide → le résumé le dit en INFO, pas en URGENT.
    if v.en_attente:
        v.ok = False
    v.details["mesures"] = mesures
    return v


# ════════════════════════════════ 2. INJECTION CLASSE A — contrôles + rollback ═══════════════════

def controler_injection(mesures: dict, *, delta_max_pct: float, couverture_974_min: int,
                        autoriser_vide: bool = False) -> Verdict:
    """Les contrôles d'une injection de source de CLASSE A, AVANT de valider (sinon RETOUR ARRIÈRE).
    `mesures` :
      · comptes_apres    (int)   — lignes après injection (doit être > 0)
      · comptes_avant    (int)   — lignes avant (version précédente ; 0 = première injection, toléré)
      · geometries_invalides (int) — géométries non valides (ST_IsValid faux ; doit être 0)
      · communes_974     (int)   — communes 974 couvertes (doit être ≥ couverture_974_min)
      · a_geometrie      (bool)  — la source porte-t-elle de la géométrie ? (sinon on saute les contrôles géo)

    Règle d'écart : si `comptes_avant` > 0, l'écart relatif |apres-avant|/avant ne doit pas dépasser
    `delta_max_pct` (une livraison qui double ou efface la moitié est suspecte → rollback)."""
    v = Verdict(ok=True)

    def _exige(cond: bool, nom: str, phrase_echec: str) -> None:
        if cond:
            v.reussis.append(nom)
        else:
            v.ok = False
            v.echecs.append(phrase_echec)

    apres = mesures.get("comptes_apres")
    avant = mesures.get("comptes_avant") or 0
    # `autoriser_vide` : pour les tables DÉRIVÉES qui peuvent légitimement être vides (aucun événement
    # datable, aucun candidat) — on exige alors seulement que le compte soit LISIBLE (non-None), pas
    # strictement positif. Les sources EXTERNES (fichier/API) gardent le défaut strict (vide = mauvais
    # téléchargement → refus).
    if autoriser_vide:
        _exige(apres is not None, "comptes-lisibles",
               f"injection illisible (comptes après = {apres})")
    else:
        _exige(apres is not None and apres > 0, "comptes-non-nuls",
               f"injection vide ou illisible (comptes après = {apres})")

    if mesures.get("a_geometrie", True):
        inval = mesures.get("geometries_invalides")
        _exige(inval == 0, "geometries-valides",
               f"{inval} géométrie(s) invalide(s) après injection")
        com = mesures.get("communes_974")
        _exige(com is not None and com >= couverture_974_min, "couverture-974",
               f"couverture 974 insuffisante ({com} communes < {couverture_974_min})")

    if avant > 0 and apres is not None:
        delta = round(100.0 * abs(apres - avant) / avant, 2)
        v.details["delta_pct"] = delta
        _exige(delta <= delta_max_pct, "ecart-version",
               f"écart avec la version précédente {delta}% > seuil {delta_max_pct}% "
               f"({avant} → {apres}) — livraison suspecte")

    v.details["mesures"] = mesures
    return v


# ════════════════════════════════ 3. INCIDENTS VIVANTS — fusion & ancienneté ═══════════════════

def fusionner_retard_echec(incidents: list[dict]) -> list[dict]:
    """FUSION « retard / échec » d'un même job. Les clés `job-echec:<nom>` (échec direct) et
    `job-retard:<nom>` / `job-bloque:<nom>` (vigie) décrivent la MÊME panne d'un même job : on n'en
    montre qu'UNE carte. On garde l'incident le plus ancien (ouvert_at), on fusionne les sujets.
    Les incidents non-job passent inchangés. Entrée/sortie = dicts `incidents_ouverts`."""
    import re
    par_job: dict[str, dict] = {}
    autres: list[dict] = []
    ordre: list[str] = []
    for inc in incidents:
        m = re.match(r"^(job-echec|job-retard|job-bloque):(.+)$", inc.get("cle", ""))
        if not m:
            autres.append(inc)
            continue
        nom = m.group(2)
        if nom not in par_job:
            par_job[nom] = dict(inc)
            par_job[nom]["cles_fusionnees"] = [inc["cle"]]
            ordre.append(nom)
        else:
            cur = par_job[nom]
            cur["cles_fusionnees"].append(inc["cle"])
            # garder la plus ancienne ouverture, le plus grand nombre de rappels
            if inc.get("ouvert_at") and (not cur.get("ouvert_at") or inc["ouvert_at"] < cur["ouvert_at"]):
                cur["ouvert_at"] = inc["ouvert_at"]
            cur["rappels"] = max(cur.get("rappels", 0), inc.get("rappels", 0))
            # un « bloqué » ou « échec » prime sur un simple « retard » dans le sujet
            if "echec" in inc["cle"] or "bloque" in inc["cle"]:
                cur["sujet"] = inc.get("sujet", cur.get("sujet"))
    fusionnes = [par_job[n] for n in ordre]
    return fusionnes + autres


def incidents_anciens(incidents: list[dict], seuil_jours: int, maintenant: datetime) -> list[dict]:
    """Les incidents ouverts depuis plus de `seuil_jours` jours (à remonter dans le mail du matin).
    `maintenant` est tz-aware ; `ouvert_at` est une chaîne ISO."""
    vieux = []
    for inc in incidents:
        quand = _parse_iso(inc.get("ouvert_at"))
        if quand is None:
            continue
        age = maintenant - quand
        if age >= timedelta(days=seuil_jours):
            vieux.append({**inc, "age_jours": age.days})
    return vieux


def _parse_iso(s) -> datetime | None:
    if not s:
        return None
    try:
        from datetime import timezone
        q = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return q if q.tzinfo else q.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


# ════════════════════════════════ ORCHESTRATION (promotion / injection) ═════════════════════════
#
# Ces deux fonctions portent le CONTRÔLE-FLOW du mandat (promouvoir seulement si tout passe ;
# injecter puis revenir en arrière si un contrôle échoue), mais prennent les effets de bord en
# CALLABLES (gatherer/promoteur/alerteur ; injecteur/mesureur/annuleur). Donc testables sans base ni
# flux-run réel ; les vrais callables sont fournis par jobs_impl.

def promouvoir_si_ok(mesures: dict, *, palier_delta_max_pct: float,
                     promouvoir, alerter) -> dict:
    """Juge un run candidat (`controler_run`). Si TOUS les contrôles passent → `promouvoir()` est
    appelé et le run est promu. Sinon → AUCUNE promotion et `alerter(verdict)` part (mail à Vic).
    Retourne {promu: bool, verdict: Verdict, resultat_promotion}. Un `promouvoir()` qui lève est
    rattrapé en « non promu » (on ne laisse jamais un demi-état)."""
    v = controler_run(mesures, palier_delta_max_pct=palier_delta_max_pct)
    out: dict = {"promu": False, "verdict": v, "resume": v.resume()}
    if not v.ok:
        # OPS-NUIT-2 — un run NON promu seulement parce qu'un contrôle est EN ATTENTE (banc de cohérence
        # pas encore passé) n'est PAS une panne : pas de mail « non promu » (il repartira la nuit suivante,
        # ou le banc l'aura mesuré d'ici là). On n'alerte que sur un VRAI échec de contrôle.
        if v.echecs:
            alerter(v)
        return out
    try:
        out["resultat_promotion"] = promouvoir()
        out["promu"] = True
    except Exception as exc:  # noqa: BLE001 — une promotion qui rate N'EST PAS un run promu
        out["erreur_promotion"] = f"{type(exc).__name__}: {exc}"
        alerter(v, erreur_promotion=out["erreur_promotion"])
    return out


def injecter_avec_rollback(*, injecter, mesurer, valider_ok, annuler,
                           delta_max_pct: float, couverture_974_min: int,
                           alerter=None) -> dict:
    """Injecte une source de CLASSE A puis CONTRÔLE (`controler_injection`). Si tout passe →
    `valider_ok()` (commit). Sinon → `annuler()` (ROLLBACK) et, si fourni, `alerter(verdict)`.

      · injecter()  — charge la nouvelle version (dans une transaction / un schéma de travail) ;
      · mesurer()   — renvoie le dict de mesures (comptes/géométries/couverture) APRÈS injection ;
      · valider_ok()/annuler() — commit / rollback de l'injection.

    Toute exception pendant l'injection ou la mesure = ÉCHEC → `annuler()` (on ne garde jamais une
    injection à moitié faite). Retourne {injecte: bool, verdict, ...}."""
    out: dict = {"injecte": False}
    try:
        injecter()
        mesures = mesurer()
    except Exception as exc:  # noqa: BLE001
        annuler()
        out["erreur"] = f"{type(exc).__name__}: {exc}"
        if alerter:
            alerter(Verdict(ok=False, echecs=[out["erreur"]]))
        return out
    v = controler_injection(mesures, delta_max_pct=delta_max_pct, couverture_974_min=couverture_974_min)
    out["verdict"] = v
    out["resume"] = v.resume()
    if v.ok:
        valider_ok()
        out["injecte"] = True
    else:
        annuler()
        if alerter:
            alerter(v)
    return out
