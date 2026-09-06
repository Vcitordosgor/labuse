"""CIRCUIT-P (lot 1.1) — LE RÉSUMÉ, composé CÔTÉ SERVEUR.

La page où Vic ira le plus souvent se lit en dix secondes : le Résumé ne montre QUE ce qui cloche.
Une ligne = un chiffre, un titre, une phrase en français, un verbe, et une CIBLE (où cliquer mène).
Trois groupes, dans cet ordre (règle 2) :
  1. « À faire, un geste de toi »      — un geste humain suffit
  2. « À corriger, un mandat pour CC »  — du code à écrire
  3. « À décider, quand tu veux »       — une décision, sans urgence
Zéro problème → aucune ligne, et la page dit « Tout coule. »

Le front NE RECALCULE RIEN : il rend ce que `composer()` produit. La règle de composition est ici,
avec un test par ligne possible (voir tests/test_circuit_p_lot1.py).

Chaque `cible` porte un `type` (`reservoir` | `robinet` | `pompe`) et des `ids`. Le front s'en sert
pour naviguer : une seule cible → page de détail ; plusieurs → circuit déplié sur ces ids.

Certaines lignes n'ont pas encore de source de données live et sortent donc à 0 (documenté au
compte-rendu comme accroche) : « écarts à la règle » et « choix LABUSE » (CIRCUIT-4, `regles_*`),
« horloge qui ment » (détecteur, `horloges`). La MÉCANIQUE est là et testée ; le branchement suit.
"""
from __future__ import annotations

def _noms(items: list[dict], limite: int = 4) -> str:
    noms = [i.get("nom") or str(i.get("id")) for i in items]
    if len(noms) <= limite:
        return ", ".join(noms)
    return ", ".join(noms[:limite]) + f" et {len(noms) - limite} autre" + ("s" if len(noms) - limite > 1 else "")


def _ligne(n, couleur, titre, phrase, verbe, cible_type, ids):
    if not n:
        return None
    return {"n": n, "couleur": couleur, "titre": titre, "phrase": phrase, "verbe": verbe,
            "cible": {"type": cible_type, "ids": list(ids)}}


def composer(reservoirs: list[dict], robinets: list[dict], *,
             compteurs: dict, residuel: dict | None, run_servi: str, candidat: str | None,
             fuites: list[dict], eau_ancienne: list[dict],
             regles_ecart: list[str] = (), regles_choix: list[str] = (),
             horloges: list[str] = ()) -> dict:
    """Compose le bloc `resume`. Chaque réservoir / robinet porte déjà son `etat` ([couleur, lib])
    (posé par l'endpoint via circuit_etats) : le résumé n'invente pas d'état, il regroupe."""
    # ── groupe 1 — À faire, un geste de toi ──────────────────────────────────────────────────
    # CIRCUIT-P2 (lot 2.4) — les lignes du Résumé sont dérivées du LIBELLÉ d'état déjà calculé
    # (etat_reservoir), source unique de vérité : un réservoir a un seul état, donc une seule ligne.
    # Cela garantit l'aller (chaque id d'une ligne est « à regarder ») ET le retour (chaque réservoir
    # « à regarder » a sa ligne) — un `absente` sans veille sort « vide » (gris), jamais « jamais
    # vérifié ». Un réservoir non couvert (« horloge qui ment », « agent en route ») est transitoire
    # ou 0 live ; sa ligne arrive via un paramètre dédié (horloges) ou un lot ultérieur.
    def lib(r):
        return (r.get("etat") or ["", ""])[1]
    quar = [r for r in reservoirs if lib(r) == "en quarantaine"]
    neuf = [r for r in reservoirs if lib(r) == "nouvelle version à injecter"]
    jamais = [r for r in reservoirs if lib(r) == "jamais vérifié"]
    reverif = [r for r in reservoirs if lib(r) == "à vérifier"]
    injoign = [r for r in reservoirs if lib(r) == "producteur injoignable"]
    agents_route = [r for r in reservoirs if lib(r) == "agent en route"]
    eau_rob = sorted({e["robinet"] for e in eau_ancienne if e.get("statut") == "ouvert"})
    eau_nouvelle = bool(residuel and residuel.get("changees"))

    g1 = [
        _ligne(len(quar), "rouge", "version en quarantaine",
               f"{_noms(quar)} — entrée, mesurée, pas servie : le filtre l'a arrêtée.",
               "Décider", "reservoir", [r["id"] for r in quar]),
        _ligne(len(neuf), "ambre", "réservoir plein, à injecter",
               f"{_noms(neuf)} — le producteur a publié plus récent que ce que sert l'app.",
               "Injecter", "reservoir", [r["id"] for r in neuf]),
        _ligne(1 if eau_nouvelle else 0, "ambre", "eau nouvelle dans la pompe",
               f"{(residuel or {}).get('detail', 'des entrées ont changé')} — à calculer, puis à "
               "basculer après lecture de la note de version.",
               "Calculer", "pompe", []),
        _ligne(len(eau_rob), "ambre", "robinets servent de l'eau ancienne",
               "Calculés sur une version plus vieille que celle du réservoir. Le prochain calcul "
               "les purge.", "Voir", "robinet", eau_rob),
        _ligne(len(jamais), "ambre", "réservoirs jamais vérifiés",
               "Ni sonde ni agent n'est allé voir chez le producteur. Un agent revient avec une "
               "preuve.", "Envoyer les agents", "reservoir", [r["id"] for r in jamais]),
        _ligne(len(reverif), "ambre", "réservoirs à revérifier",
               "Le dernier contrôle est plus vieux que la cadence attendue.",
               "Vérifier", "reservoir", [r["id"] for r in reverif]),
        _ligne(len(injoign), "ambre", "producteurs injoignables",
               f"{_noms(injoign)} — la dernière sonde n'a pas pu joindre le producteur.",
               "Vérifier", "reservoir", [r["id"] for r in injoign]),
        _ligne(len(agents_route), "mauve", "agents en route",
               f"{_noms(agents_route)} — un agent lit chez le producteur, le résultat arrive.",
               "Voir", "reservoir", [r["id"] for r in agents_route]),
    ]

    # ── groupe 2 — À corriger, un mandat pour CC ─────────────────────────────────────────────
    fuite_rob = sorted({f[k] for f in fuites for k in ("robinet_a", "robinet_b") if f.get(k)})
    warn = [r for r in reservoirs if lib(r) == "filtre avec des KO"]
    hm_rob = [rb for rb in robinets if rb.get("hors_moteur")]
    ecart_ids = list(regles_ecart)
    horloge_ids = list(horloges)

    g2 = [
        _ligne(len(fuite_rob), "rouge", "fuites mesurées",
               f"{len(fuite_rob)} robinets donnent un autre chiffre que le moteur sur les témoins. "
               "Chaque fuite a sa cause et son fichier.", "Voir", "robinet", fuite_rob),
        _ligne(len(ecart_ids), "rouge", "écarts à la règle",
               "Le calcul ne dit pas ce que dit le texte officiel. À trancher avec Stéphanie, "
               "extrait en face.", "Voir", "robinet", ecart_ids),
        _ligne(len(horloge_ids), "rouge", "horloge qui ment",
               "Le cron saute des communes déjà peuplées et tamponne quand même « à jour ».",
               "Voir", "reservoir", horloge_ids),
        _ligne(len(warn), "ambre", "filtres passés avec des KO",
               f"{_noms(warn)} — servies, mais des contrôles avertissent.",
               "Voir", "reservoir", [r["id"] for r in warn]),
        _ligne(len(hm_rob), "ambre", "affichages calculés hors moteur",
               f"Dans {len(hm_rob)} robinets : un chemin unique, pas encore un moteur nommé.",
               "Voir", "robinet", [rb["id"] for rb in hm_rob]),
    ]

    # ── groupe 3 — À décider, quand tu veux ──────────────────────────────────────────────────
    choix_ids = list(regles_choix)
    cadences = [r for r in reservoirs if r.get("cadence_statut") == "proposee"]

    g3 = [
        _ligne(len(choix_ids), "gris", "choix LABUSE à confirmer",
               "Des définitions à nous, sans texte officiel derrière. Confirme-les ou change-les.",
               "Voir", "robinet", choix_ids),
        _ligne(len(cadences), "gris", "cadences proposées à valider",
               "Les rythmes de publication devinés pour ces sources. Corrige ceux qui ne collent "
               "pas.", "Voir", "reservoir", [r["id"] for r in cadences]),
    ]

    groupes = [
        {"titre": "À faire, un geste de toi", "lignes": [x for x in g1 if x]},
        {"titre": "À corriger, un mandat pour CC", "lignes": [x for x in g2 if x]},
        {"titre": "À décider, quand tu veux", "lignes": [x for x in g3 if x]},
    ]
    total = sum(len(g["lignes"]) for g in groupes)

    # ── quatre repères — LUS des compteurs uniques (règle 2.2), jamais recalculés ──────────────
    a_jour = compteurs.get("a_jour", 0)
    n_res = compteurs.get("reservoirs", len(reservoirs))
    coh = compteurs.get("robinets_coherents", 0)
    n_rob = compteurs.get("robinets", len(robinets))
    kpis = [
        {"valeur": a_jour, "sur": n_res, "libelle": "réservoirs à jour et vérifiés", "detail": "compteur"},
        {"valeur": coh, "sur": n_rob, "libelle": "robinets sans rien à signaler"},
        {"valeur": compteurs.get("chiffres", len({c for rb in robinets for c in rb.get('chiffres') or []})),
         "libelle": "chiffres définis une fois"},
        {"valeur": run_servi, "candidat": candidat, "libelle": "run servi"},
    ]
    return {
        "total": total,
        "kpis": kpis,
        "groupes": groupes,
        "reste": {"reservoirs": n_res, "robinets": n_rob,
                  "chiffres": compteurs.get("chiffres", 0)},
    }
