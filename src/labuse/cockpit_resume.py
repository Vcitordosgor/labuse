"""COCKPIT-1 (Lot A) — LE TABLEAU DE BORD, composé CÔTÉ SERVEUR.

Le nouvel onglet « Tableau de bord » (remplace « À faire » + « Cohérence ») répond à trois questions,
dans cet ordre, et le front NE RECALCULE RIEN — il rend ce que `composer_cockpit()` produit :

  1. « Qu'est-ce que je dois faire aujourd'hui ? »  — UNE carte PAR PROBLÈME (pas par occurrence) :
     les N sources en nouvelle version = 1 carte, les N verrous cassés = 1 carte, les N sondes en
     panne = 1 carte, etc. Tri : les données à injecter d'abord, puis le reste. Chaque carte porte une
     pastille (jaune = un geste de Vic · rouge = cassé · gris = toléré) et UN bouton primaire
     (Injecter · Reconstruire · Réessayer · Accepter). Ce qui demande du code porte l'étiquette
     « demande du code » + seulement « Voir le détail » (faits techniques + Copier). Plus aucun
     bouton « Décider ».
  2. « Est-ce que tout tourne ? »  — 4 tuiles (veille des sources, livraisons du jour, contrôle de
     nuit, courrier aux clients), chacune lue du registre des jobs (dernier passage).
  3. « Où en est la mise à jour ? »  — 4 étapes (Injecter → Calculer → Basculer → Envoyer en prod),
     chacune fait / à faire avec le bouton de l'étape à faire.

La vérité technique (ids, dates, fichiers) ne sort QUE dans « Voir le détail ». Les identifiants
techniques (V1c, q_v…, noms de table) ne figurent jamais dans les titres/phrases des cartes.
"""
from __future__ import annotations


# ── les quatre « livreurs » des livraisons quotidiennes (famille 2), pour la tuile « Livraisons » ──
LIVRAISONS = ("ingest-bodacc", "ingest-dvf", "ingest-sitadel", "ingest-dpe", "ingest-sirene", "sync-gpu")
# libellés clairs pour la tuile livraisons (jamais d'identifiant technique à l'écran).
_LIVRAISON_NOM = {
    "ingest-bodacc": "BODACC", "ingest-dvf": "DVF", "ingest-sitadel": "Sitadel",
    "ingest-dpe": "DPE", "ingest-sirene": "SIRENE", "sync-gpu": "GPU",
}


def _pastille_job(dernier: dict | None, gel: str | None) -> str:
    """La couleur d'un poste : gris = gelé ou jamais parti · rouge = dernier passage en échec ·
    vert = ok/dry-run. (Le « violet = tourne en ce moment » est décidé côté L'usine, Lot B : ici on
    ne lit que le dernier état journalisé.)"""
    if gel:
        return "gris"
    statut = (dernier or {}).get("statut")
    if statut is None:
        return "gris"
    if statut in ("echec", "timeout"):
        return "rouge"
    return "vert"


def _hhmm(iso: str | None) -> str:
    if not iso:
        return "—"
    s = str(iso)
    # ISO « 2026-10-20T07:00:12+00:00 » → « 07:00 » (on ne reconvertit pas le fuseau : le registre
    # expose déjà l'heure Réunion dans `heure_reunion`, et le dernier passage est en UTC ; la tuile
    # reste volontairement approximative, l'heure exacte vit dans L'usine).
    if "T" in s:
        return s.split("T", 1)[1][:5]
    return s[:5]


def _jour(iso: str | None) -> str:
    if not iso:
        return "jamais"
    return str(iso)[:10]


# ══════════════════════ section 1 — « Qu'est-ce que je dois faire aujourd'hui ? » ══════════════════════

def _carte(cid, pastille, titre, phrase, *, bouton=None, code=False, detail=None, tri=5):
    """Une carte = un problème. `bouton` = le bouton primaire (ou None pour « demande du code »).
    `code=True` → étiquette « demande du code » + bouton secondaire « Voir le détail » automatique.
    `detail` (dict {texte}) → les faits techniques du « Voir le détail » (copiables)."""
    c = {"id": cid, "pastille": pastille, "titre": titre, "phrase": phrase,
         "code": code, "tri": tri}
    if bouton:
        c["bouton"] = bouton
    if detail is not None:
        c["detail"] = detail
    # « Voir le détail » : toujours présent pour ce qui demande du code ; sinon seulement si un détail existe.
    c["voir_detail"] = bool(code or detail)
    return c


def _lignes_par_type(a_faire: dict, type_: str) -> list[dict]:
    return [l for l in (a_faire or {}).get("lignes", []) if l.get("type") == type_]


# COCKPIT-1b (retour recette, point 4) — chaque cache périmé devient une carte EN FRANÇAIS (aucun code
# run/cascade/hash à l'écran : il ne sort que dans « Voir le détail »). Libellé humain par cache.
_CACHE_NOM = {
    "commune_contexte_cache": "fiches communes",
    "mvt_parcels": "couches subdivisées de la carte",
    "spatial_layers_sub": "couches découpées de la carte",
    "tile_cache": "tuiles pré-rendues",
    "ia_cache": "réponses IA pré-calculées",
    "manifeste": "pointeurs du run servi",
    "defisc_bareme": "barème de défiscalisation",
    "derives_regle": "dérivés des règles",
    "parcel_couche_intersection": "servitudes matérialisées",
}


def _carte_cache(cache: dict) -> dict:
    """Une carte « Reconstruire » pour un cache périmé : titre en français (+ compte si le détail en
    porte un), bouton Reconstruire ; les faits techniques (clé attendue/réelle, run) → « Voir le détail »."""
    nom_tech = str(cache.get("cache") or "cache")
    noun = next((v for k, v in _CACHE_NOM.items() if nom_tech.startswith(k)), None) or "un cache"
    det = str(cache.get("detail") or "")
    import re
    m = re.match(r"\s*(\d+)\s+périmée", det)
    titre = (f"{m.group(1)} {noun} en retard sur les dernières sources" if m
             else f"Les {noun} sont en retard sur les dernières sources")
    texte = "\n".join(x for x in [
        nom_tech,
        cache.get("porte_sur"),
        f"attendu {cache.get('cle_attendue')}" if cache.get("cle_attendue") else None,
        f"réel {cache.get('cle_reelle')}" if cache.get("cle_reelle") else None,
        cache.get("detail"),
    ] if x)
    return _carte(
        f"cache:{nom_tech.split(' ')[0]}", "jaune", titre,
        "Reconstruire remet ce cache à jour avec les dernières sources. Quelques minutes.",
        bouton={"label": "Reconstruire", "action": "reconstruire"},
        detail={"texte": texte}, tri=1)


# COCKPIT-1b (retour recette, point 5) — les VIGIES d'exploitation (sauvegarde, disque, copie externe,
# /readyz) ont quitté le rail du Pilotage : quand l'une casse (incident ops ouvert), elle devient une
# carte du Tableau de bord — le point « à faire aujourd'hui » où on la voit vraiment. Mappe la clé
# d'incident → (pastille, titre FR, bouton). Une sauvegarde en retard a un « Réessayer » (relance le dump).
_INCIDENT_CARTE = {
    "sauvegarde-absente": ("rouge", "La sauvegarde ne tourne plus",
                           {"label": "Réessayer", "action": "lancer-job", "nom": "backup-postgres"}),
    "sauvegarde-retrecie": ("rouge", "La dernière sauvegarde a rétréci",
                            {"label": "Réessayer", "action": "lancer-job", "nom": "backup-postgres"}),
    "disque": ("rouge", "Le disque du serveur se remplit", None),
    "readyz": ("rouge", "L'app n'est pas prête à répondre", None),
    "copie-externe-ancienne": ("jaune", "La copie hors ligne est ancienne — branche le disque", None),
}


def _titre_incident_generique(cle: str, sujet: str):
    """DONNEES-ETAT-FIX-2 (Lot C) — titre FR + bouton pour un incident HORS `_INCIDENT_CARTE`
    (job en échec, vérité sources, tout nouveau contrôle) : plus jamais un incident ouvert INVISIBLE."""
    if cle.startswith("job-echec:"):
        nom = cle.split(":", 1)[1]
        return ("rouge", f"Un automate a échoué : {nom}",
                {"label": "Réessayer", "action": "lancer-job", "nom": nom})
    if cle == "verite-sources":
        return ("rouge", "Des valeurs servies divergent des sources officielles", None)
    return ("rouge", sujet or "Un contrôle d'exploitation est au rouge", None)


def _cartes_incidents(incidents: list[dict]) -> list[dict]:
    """Une carte ROUGE par incident OUVERT (ops_incidents) — sauvegarde, disque, copie externe, readyz,
    VÉRITÉ SOURCES, JOB EN ÉCHEC… Un incident FERMÉ n'est plus dans la liste → sa carte disparaît.
    Les détails (seuils, dates, les écarts parcelle↔source…) ne sortent que dans « Voir le détail » ;
    sans action spécifique, un bouton « Accepter » acquitte l'incident (il rouvrira au prochain
    contrôle s'il est toujours réel). DONNEES-ETAT-FIX-2 (Lot C) : plus de `continue` qui masquait
    les incidents inconnus (vérité-sources, job-echec:*)."""
    out = []
    for inc in incidents or []:
        cle = inc.get("cle") or ""
        if cle == "copie-externe-ancienne":
            continue   # DONNEES-ETAT-FIX-2 (Lot B) : rendu par la carte dédiée « copie hors-site »
        conf = _INCIDENT_CARTE.get(cle)
        if conf:
            pastille, titre, bouton = conf
        else:
            pastille, titre, bouton = _titre_incident_generique(cle, inc.get("sujet") or "")
        depuis = (inc.get("ouvert_at") or "")[:16].replace("T", " ")
        texte = "\n".join(x for x in [
            inc.get("sujet"), inc.get("detail"),
            f"ouvert depuis {depuis}" if depuis else None,
            f"{inc['rappels']} rappel(s)" if inc.get("rappels") else None,
        ] if x)
        if bouton is None:   # pas d'action métier → « Accepter » (acquitte l'incident)
            bouton = {"label": "Accepter", "action": "accepter-incident", "cle": cle}
        out.append(_carte(
            f"incident:{cle}", pastille, titre,
            inc.get("sujet") or "Un contrôle d'exploitation est au rouge.",
            bouton=bouton, detail={"texte": texte}, tri=0.5))
    return out


def _carte_copie_externe(ce: dict | None) -> dict | None:
    """DONNEES-ETAT-FIX-2 (Lot B) — carte « copie hors-site » : date de la dernière copie sur le disque
    externe, JAUNE à 7 j, ROUGE à 10 j. Fraîche (< 7 j) → pas de carte (rien à faire).
    `ce` = ops_alertes.lire_copie_externe(backup_dir) enrichi de `age_j`, `derniere`, `seuil_j` ;
    None (marqueur absent : env sans copie hors-site / dev) → pas de carte (l'alerte « aucune copie »
    reste portée par l'incident `copie-externe-ancienne` via le canal mail/cloche)."""
    if not ce:
        return None
    age = ce.get("age_j")
    if age is None or age < 7:
        return None                           # copie fraîche : rien à signaler
    pastille = "rouge" if age >= 10 else "jaune"
    date = ce.get("derniere") or (ce.get("copie_at") or "")[:10]
    texte = "\n".join(x for x in [
        f"Dernière copie hors-site : {date} (il y a {age} jour{'s' if age > 1 else ''})",
        f"Dump copié : {ce.get('dump')}" if ce.get("dump") else None,
        f"Disque : {ce.get('disque')}" if ce.get("disque") else None,
        f"Seuil rouge : {ce.get('seuil_j', 10)} jours.",
    ] if x)
    return _carte("copie-externe", pastille, f"Copie hors-site ancienne ({age} jours)",
                  f"Dernière copie sur le disque externe le {date}. Branche le disque pour en refaire une.",
                  detail={"texte": texte}, tri=0.4)


def _carte_restore_test(rt: dict | None) -> dict | None:
    """DONNEES-ETAT-FIX-2 (Lot A) — carte « test de restauration » (agent Mac mensuel) : date + verdict
    (gris OK · jaune reporté · rouge KO). `rt` = ops_alertes.lire_restore_test(backup_dir) ; None =
    jamais joué → pas de carte."""
    if not rt:
        return None
    statut = (rt.get("statut") or "").lower()
    quand = (rt.get("test_at") or "")[:16].replace("T", " ")
    tables = rt.get("tables") or {}
    lignes = [f"{t} : restauré {v.get('restaure')} / prod {v.get('prod')}"
              for t, v in tables.items() if isinstance(v, dict)]
    if rt.get("run_servi"):
        lignes.append(f"run servi {rt['run_servi']} : {rt.get('run_servi_lignes')} lignes")
    texte = "\n".join(x for x in [f"Test de restauration du {quand}", rt.get("message"), *lignes] if x)
    if statut == "ok":
        return _carte("restore-test", "gris", f"Dernière restauration : vérifiée ({quand[:10]})",
                      "La sauvegarde se restaure et les comptages clés collent avec la prod.",
                      detail={"texte": texte}, tri=0.46)
    if statut == "refuse":
        return _carte("restore-test", "jaune", "Test de restauration reporté",
                      rt.get("message") or "Espace insuffisant — test reporté.",
                      detail={"texte": texte}, tri=0.46)
    return _carte("restore-test", "rouge", "La dernière restauration a échoué",
                  rt.get("message") or "La sauvegarde ne se restaure pas correctement.",
                  detail={"texte": texte}, tri=0.46)


def _cartes_aujourdhui(a_faire: dict, *, noms_source: dict, ecarts_toleres: int,
                       verrous: dict | None, fuites_rob: list[dict],
                       caches_perimes: list[dict], incidents: list[dict], dates: dict | None,
                       copie_externe: dict | None = None, restore_test: dict | None = None) -> list[dict]:
    cartes: list[dict] = []
    dates = dates or {}

    # (0) VIGIES D'EXPLOITATION (sauvegarde en retard, disque, /readyz, vérité-sources, job-echec) — ex-rail.
    cartes.extend(_cartes_incidents(incidents))

    # (0 bis) DONNEES-ETAT-FIX-2 — copie hors-site (Lot B) + test de restauration (Lot A).
    _b = _carte_copie_externe(copie_externe)
    if _b:
        cartes.append(_b)
    _a = _carte_restore_test(restore_test)
    if _a:
        cartes.append(_a)

    # (1) DONNÉES À INJECTER — en premier (tri=0). Les N sources en nouvelle version → UNE carte.
    inj = _lignes_par_type(a_faire, "injecter")
    if inj:
        ids = [l.get("bouton", {}).get("source") for l in inj if l.get("bouton", {}).get("source")]
        noms = [noms_source.get(i) or f"source {i}" for i in ids]
        n = len(inj)
        cartes.append(_carte(
            "injecter", "jaune",
            f"{n} source{'s' if n > 1 else ''} ont une nouvelle version" if n > 1
            else "Une source a une nouvelle version",
            (", ".join(noms[:6]) + (f" et {len(noms) - 6} autre{'s' if len(noms) - 6 > 1 else ''}"
                                    if len(noms) > 6 else "")
             + " — le producteur a publié plus récent que ce que sert l'app."),
            bouton={"label": f"Injecter les {n}" if n > 1 else "Injecter",
                    "action": "injecter", "sources": ids},
            detail={"texte": "Sources en nouvelle version :\n- " + "\n- ".join(noms)},
            tri=0))

    # (2) CACHES PÉRIMÉS — COCKPIT-1b (point 4) : une carte par cache en retard sur les dernières
    # sources (ex. « 23 fiches communes en retard… »), chacune avec « Reconstruire ». Les codes
    # techniques (clé attendue/réelle, run) ne sortent QUE dans « Voir le détail ».
    for cache in (caches_perimes or []):
        if cache.get("perime"):
            cartes.append(_carte_cache(cache))

    # (3) VERROUS CASSÉS — « N contrôles de sécurité échouent » : DEMANDE DU CODE (pas un clic ici).
    casses = list((verrous or {}).get("casses", []))
    if casses:
        n = len(casses)
        # COCKPIT-1b (point 5) — UNE seule date de dernier contrôle des verrous, partout : `dernier_ts`
        # de la synthèse (le MÊME que lisait l'ancienne LED du rail). Plus de date divergente.
        depuis = (verrous or {}).get("dernier_ts") or (verrous or {}).get("depuis")
        texte = (
            "Contrôles en échec : " + ", ".join(casses) + "\n"
            + (f"Depuis : {_jour(depuis)}\n" if depuis else "")
            + "Ce que ça bloque : le déploiement refuse tant que ça tient\n"
            + "Fichiers : VERROUS.md (une phrase par contrôle), src/labuse/circuit_verrous.py")
        cartes.append(_carte(
            "verrous", "rouge",
            f"{n} contrôle{'s' if n > 1 else ''} de sécurité échoue{'nt' if n > 1 else ''}",
            "Pas un clic : à confier à Claude Code. Le détail est prêt à copier.",
            code=True, detail={"texte": texte}, tri=2))

    # (4) SONDES EN PANNE — « N sources ne répondent plus au veilleur de nuit » : Réessayer.
    sondes = _lignes_par_type(a_faire, "decider")
    sondes = [l for l in sondes if l.get("bouton", {}).get("source")
              and "sonde en panne" in (l.get("titre") or "")]
    if sondes:
        ids = [l["bouton"]["source"] for l in sondes]
        noms = [noms_source.get(i) or f"source {i}" for i in ids]
        n = len(sondes)
        cartes.append(_carte(
            "sondes", "rouge",
            f"{n} source{'s' if n > 1 else ''} ne répond{'ent' if n > 1 else ''} plus au veilleur de nuit",
            (", ".join(noms[:6]) + " — trois passages ratés d'affilée. "
             "Souvent un site amont qui a changé d'adresse."),
            bouton={"label": "Réessayer maintenant", "action": "reessayer"},
            detail={"texte": "Sources dont la sonde amont est en panne :\n- " + "\n- ".join(noms)},
            tri=3))

    # (5) FUITES / ÉCARTS OUVERTS entre lectures — DEMANDE DU CODE (un robinet lit hors moteur).
    if fuites_rob:
        n = len(fuites_rob)
        noms = [f.get("nom") or f.get("id") for f in fuites_rob]
        texte = ("Robinets qui lisent hors du moteur :\n- " + "\n- ".join(str(x) for x in noms)
                 + "\nChacun prend son chiffre dans une requête propre au lieu du moteur.")
        cartes.append(_carte(
            "fuites", "rouge",
            f"{n} affichage{'s' if n > 1 else ''} calculé{'s' if n > 1 else ''} hors du moteur",
            "Pas un clic : à confier à Claude Code. Le détail est prêt à copier.",
            code=True, detail={"texte": texte}, tri=4))

    # (6) ÉCARTS TOLÉRÉS (banc de cohérence) — « N petits écarts entre écrans » : Accepter / confier à CC.
    if ecarts_toleres and ecarts_toleres > 0:
        cartes.append(_carte(
            "ecarts-toleres", "gris",
            f"{ecarts_toleres} petit{'s' if ecarts_toleres > 1 else ''} écart"
            f"{'s' if ecarts_toleres > 1 else ''} entre écrans",
            "Aucun ne ment au client. Soit tu les acceptes une fois pour toutes, soit tu les confies "
            "à Claude Code.",
            bouton={"label": f"Accepter les {ecarts_toleres}" if ecarts_toleres > 1 else "Accepter",
                    "action": "accepter-ecarts", "n": ecarts_toleres},
            detail={"texte": f"{ecarts_toleres} écarts tolérés au dernier passage du banc de cohérence "
                             "(0 faux-client). « Accepter » rejoue « labuse coherence --accepter » "
                             "(regénère les témoins golden). Les écarts restent affichés tant qu'ils "
                             "ne sont pas acceptés ou corrigés."},
            tri=6))

    # (7) SOURCES MANUELLES ÉCHUES — à redéposer (un fichier reçu par mail / la DEAL).
    dep = _lignes_par_type(a_faire, "deposer")
    if dep:
        ids = [l.get("bouton", {}).get("source") for l in dep if l.get("bouton", {}).get("source")]
        noms = [noms_source.get(i) or f"source {i}" for i in ids]
        n = len(dep)
        cartes.append(_carte(
            "deposer", "jaune",
            f"{n} source{'s' if n > 1 else ''} manuelle{'s' if n > 1 else ''} à redéposer",
            ", ".join(noms[:6]) + " — la cadence de dépôt est dépassée.",
            bouton={"label": "Déposer un fichier", "action": "deposer", "sources": ids},
            detail={"texte": "Sources manuelles échues :\n- " + "\n- ".join(noms)},
            tri=7))

    cartes.sort(key=lambda c: c["tri"])
    return cartes


# ══════════════════════ section 2 — « Est-ce que tout tourne ? » ══════════════════════

def _job(jobs_par_nom: dict, nom: str) -> dict:
    return jobs_par_nom.get(nom) or {}


def _tuiles_tout_tourne(jobs_par_nom: dict, etats_sources: dict) -> list[dict]:
    def tuile(cid, titre, nom_job, ligne_ok, *, gel_from=None):
        j = _job(jobs_par_nom, nom_job)
        pastille = _pastille_job(j.get("dernier"), j.get("gel"))
        return {"id": cid, "titre": titre, "pastille": pastille, "ligne": ligne_ok(j)}

    veille = tuile(
        "veille", "Veille des sources", "sonde-sources",
        lambda j: (f"Le veilleur est passé à {_hhmm((j.get('dernier') or {}).get('fin'))} · "
                   f"{(etats_sources or {}).get('total', '—')} sources suivies"))

    # Livraisons : état agrégé des 6 livreurs + ceux qui sont ok.
    etats_liv = []
    for n in LIVRAISONS:
        j = _job(jobs_par_nom, n)
        etats_liv.append((_LIVRAISON_NOM[n], _pastille_job(j.get("dernier"), j.get("gel"))))
    past_liv = ("rouge" if any(p == "rouge" for _, p in etats_liv)
                else "gris" if all(p == "gris" for _, p in etats_liv) else "vert")
    oks = ", ".join(nom for nom, p in etats_liv if p == "vert") or "aucune ce jour"
    livraisons = {"id": "livraisons", "titre": "Livraisons du jour", "pastille": past_liv,
                  "ligne": oks}

    controle = tuile(
        "controle", "Contrôle de nuit", "coherence-banc",
        lambda j: "0 chiffre faux chez le client" if _pastille_job(j.get("dernier"), j.get("gel")) == "vert"
        else "dernier passage à revoir")

    courrier = tuile(
        "courrier", "Courrier aux clients", "mail-queue-consommer",
        lambda j: ("part régulièrement" if _pastille_job(j.get("dernier"), j.get("gel")) == "vert"
                   else "dernier passage en échec"))

    return [veille, livraisons, controle, courrier]


def _resume_usine(jobs_list: list[dict]) -> dict:
    """Le compteur « N postes · X au vert · Y en échec · Z à l'arrêt » affiché en tête de section 2
    (et repris par L'usine, Lot B). On ne compte QUE les jobs planifiés+non gelés comme « postes
    actifs » ; les gelés et le job non planifié (agents) comptent « à l'arrêt »."""
    vert = echec = arret = 0
    for j in jobs_list:
        if j.get("gel"):
            arret += 1
            continue
        statut = (j.get("dernier") or {}).get("statut")
        if statut in ("echec", "timeout"):
            echec += 1
        elif statut in ("ok", "dry-run"):
            vert += 1
        else:
            arret += 1
    return {"postes": len(jobs_list), "vert": vert, "echec": echec, "arret": arret}


# ══════════════════════ section 3 — « Où en est la mise à jour ? » ══════════════════════

def _etapes_mise_a_jour(a_faire: dict, *, run_servi: str, candidat: str | None,
                        calculer_present: bool, dernier_calcul: str | None,
                        env: str, prod_run: str | None) -> list[dict]:
    inj = _lignes_par_type(a_faire, "injecter")
    n_inj = len(inj)

    # Étape 1 — Injecter.
    e1 = {"id": "injecter", "titre": "Injecter", "ordre": 1,
          "fait": n_inj == 0,
          "ligne": "Rien en attente" if n_inj == 0
                   else f"{n_inj} source{'s' if n_inj > 1 else ''} attend{'ent' if n_inj > 1 else ''}",
          "bouton": None if n_inj == 0 else {"label": "Injecter", "action": "voir-cartes"}}

    # Étape 2 — Calculer (sur le Mac). « à faire » si des entrées ont changé.
    e2 = {"id": "calculer", "titre": "Calculer", "ordre": 2,
          "fait": not calculer_present,
          "ligne": (f"Dernier calcul {_jour(dernier_calcul)}" if dernier_calcul else "sur le Mac, à ta demande")
                   + (" · des entrées ont changé" if calculer_present else ""),
          "bouton": {"label": "Calculer", "action": "calculer"} if calculer_present else None}

    # Étape 3 — Basculer (chez toi). « à faire » s'il y a un candidat prêt.
    e3 = {"id": "basculer", "titre": "Basculer", "ordre": 3,
          "fait": candidat is None,
          "ligne": (f"Un candidat est prêt" if candidat else "L'app affiche la dernière version"),
          "bouton": {"label": "Basculer", "action": "basculer", "candidat": candidat} if candidat else None}

    # Étape 4 — Envoyer en prod. « à faire » si la prod sert un autre run que le local.
    local_env = (env or "local") == "local"
    retard = prod_run is not None and prod_run != run_servi
    if not local_env:
        ligne4 = "se fait depuis le Mac"
        bouton4 = None
        fait4 = True
    elif prod_run is None:
        ligne4 = "état de la prod en cours de lecture…"
        bouton4 = None
        fait4 = False
    elif retard:
        ligne4 = "Les clients sont encore sur la version précédente"
        bouton4 = {"label": "Envoyer en prod", "action": "envoyer-prod"}
        fait4 = False
    else:
        ligne4 = "Les clients ont la dernière version"
        bouton4 = None
        fait4 = True
    e4 = {"id": "envoyer-prod", "titre": "Envoyer en prod", "ordre": 4,
          "fait": fait4, "ligne": ligne4, "bouton": bouton4,
          "local": local_env}

    return [e1, e2, e3, e4]


# ══════════════════════ l'assemblage ══════════════════════

# ══════════════════════ COCKPIT-1 (Lot D) — la propagation dans le Circuit ══════════════════════

def propagation_reservoir(reservoir: dict, *, eau_rob: set, tuiles_perime: bool,
                          chiffres: dict) -> dict:
    """COCKPIT-1 (Lot D) — pour UN réservoir : par où sa donnée passe et si ses robinets sont à jour.

    RÈGLE DE PROPAGATION (le front ne recalcule rien) : un robinet est « à jour » quand son cache/run a
    été produit APRÈS la dernière injection de chacun de ses réservoirs ; sinon « en retard », avec le
    geste qui le rattrape :
      · le réservoir a une NOUVELLE VERSION pas encore injectée → ses robinets sont en retard · Injecter ;
      · le réservoir est injecté mais le run n'a pas été recalculé (robinet qui sert de l'eau ancienne,
        `eau_rob`) → en retard · Calculer ;
      · sinon à jour.
    (Les tuiles périmées, elles, sont un geste GLOBAL « Reconstruire » — signalé au niveau du bandeau,
    pas par robinet, car la péremption des tuiles ne dépend pas d'UN réservoir.)
    """
    etat = reservoir.get("etat") or ["", ""]
    nouvelle = etat[1] == "nouvelle version"
    taps = []
    for rid in reservoir.get("taps", []):
        if nouvelle:
            verdict, geste = "en_retard", "injecter"
        elif rid in eau_rob:
            verdict, geste = "en_retard", "calculer"
        else:
            verdict, geste = "a_jour", None
        taps.append({"id": rid, "verdict": verdict, "geste": geste})
    moteurs = sorted({(chiffres.get(cid) or {}).get("moteur")
                      for cid in reservoir.get("chiffres_ids", [])
                      if (chiffres.get(cid) or {}).get("moteur")})
    return {"nouvelle": nouvelle, "moteurs": len(moteurs),
            "robinets": taps,
            "en_retard": sum(1 for t in taps if t["verdict"] == "en_retard"),
            "tuiles_perime": bool(tuiles_perime)}


# ══════════════════════ COCKPIT-1 (Lot B) — la page « L'usine » ══════════════════════

FAMILLES_USINE = [(1, "Veille des sources"), (2, "Livraisons quotidiennes"),
                  (3, "Le moteur"), (4, "Contrôle, clients, sécurité")]


def _pastille_poste(job: dict, en_cours: set[str]) -> str:
    """vert = ok · violet = tourne en ce moment (verrou tenu / état en_cours) · rouge = dernier
    passage en échec · gris = gelé ou jamais parti."""
    if job.get("gel"):
        return "gris"
    dernier = job.get("dernier") or {}
    if job["nom"] in en_cours or dernier.get("statut") == "en_cours":
        return "violet"
    statut = dernier.get("statut")
    if statut in ("echec", "timeout"):
        return "rouge"
    if statut in ("ok", "dry-run"):
        return "vert"
    return "gris"


def _poste(job: dict, en_cours: set[str]) -> dict:
    dernier = job.get("dernier") or {}
    statut = dernier.get("statut")
    pastille = _pastille_poste(job, en_cours)
    # le bouton possible : agents IA → « Démarrer » (coût/plafond, géré à part côté front) ; job
    # lançable sans risque et pas gelé → « Lancer maintenant » ; échec → « Voir le détail ».
    bouton = None
    if job["nom"] == "agents-sources":
        bouton = {"label": "Démarrer", "action": "agents"}
    elif job.get("gel"):
        bouton = {"label": "Réveiller…", "action": "reveiller", "nom": job["nom"]}
    elif job.get("lancable"):
        bouton = {"label": "Lancer maintenant", "action": "lancer", "nom": job["nom"]}
    detail = None
    if statut in ("echec", "timeout") and dernier.get("erreur"):
        detail = {"texte": f"{job['nom']} — {statut}\n{dernier.get('erreur')}"}
    return {
        "nom": job["nom"], "libelle": job.get("libelle") or job["nom"],
        "role": job.get("role") or "", "pastille": pastille,
        "cadence": job.get("cadence"), "heure_reunion": job.get("heure_reunion"),
        "dernier": {"statut": statut, "fin": dernier.get("fin"), "duree_s": dernier.get("duree_s")},
        "prochaine": job.get("prochaine_reunion") if not job.get("gel") else None,
        "gel": job.get("gel"), "bouton": bouton,
        "voir_detail": bool(detail), "detail": detail,
    }


def composer_usine(jobs_list: list[dict], *, en_cours: set[str] | None = None) -> dict:
    """Compose « L'usine » : 4 colonnes (familles), chaque poste avec son libellé/rôle, dernier &
    prochain passage, pastille et le bouton possible. Les postes GELÉS sortent de leurs colonnes et
    vivent dans un bandeau en bas (« volontairement à l'arrêt … Réveiller… »)."""
    en_cours = en_cours or set()
    postes = [_poste(j, en_cours) for j in jobs_list]
    par_nom = {j["nom"]: j for j in jobs_list}
    familles = []
    for n, nom in FAMILLES_USINE:
        dedans = [p for p in postes if par_nom.get(p["nom"], {}).get("famille") == n and not p["gel"]]
        familles.append({"n": n, "nom": nom, "postes": dedans})
    geles = [p for p in postes if p["gel"]]
    return {"familles": familles, "geles": geles, "resume": _resume_usine(jobs_list),
            "legende": [["vert", "au vert"], ["violet", "travaille en ce moment"],
                        ["rouge", "en échec"], ["gris", "à l'arrêt"]]}


def composer_cockpit(*, a_faire: dict, etats_sources: dict | None, reservoirs: list[dict],
                     verrous: dict | None, fuites_rob: list[dict],
                     caches_perimes: list[dict] | None, incidents: list[dict] | None,
                     ecarts_toleres: int, jobs_list: list[dict],
                     run_servi: str, candidat: str | None, calculer_present: bool,
                     dernier_calcul: str | None, env: str, prod_run: str | None,
                     dates: dict | None = None, copie_externe: dict | None = None,
                     restore_test: dict | None = None) -> dict:
    """Compose le payload du Tableau de bord (trois sections). Tout est déjà calculé en amont par
    l'endpoint — ici on ne fait que GROUPER par problème et formuler en français. `prod_run` est
    None quand l'état prod n'est pas encore lu (le front le complète via /admin/cockpit/etat-prod)."""
    noms_source = {r["id"]: r.get("nom") for r in (reservoirs or [])}
    jobs_par_nom = {j["nom"]: j for j in (jobs_list or [])}

    cartes = _cartes_aujourdhui(
        a_faire, noms_source=noms_source, ecarts_toleres=ecarts_toleres, verrous=verrous,
        fuites_rob=fuites_rob, caches_perimes=caches_perimes or [], incidents=incidents or [], dates=dates,
        copie_externe=copie_externe, restore_test=restore_test)

    return {
        "aujourdhui": {"n": len(cartes), "cartes": cartes},
        "tout_tourne": {"resume": _resume_usine(jobs_list),
                        "tuiles": _tuiles_tout_tourne(jobs_par_nom, etats_sources or {})},
        "mise_a_jour": {"etapes": _etapes_mise_a_jour(
            a_faire, run_servi=run_servi, candidat=candidat, calculer_present=calculer_present,
            dernier_calcul=dernier_calcul, env=env, prod_run=prod_run)},
    }
