# RAPPORT M55-D stage 9 — PHASE 1 : les chiffres de l'accueil (STOP) + responsive livré

Branche `feat/m55-d-stage9` (base `main` 1237ca7a, **stage 8 mergé — précondition vérifiée**).
**Phase 1 = mesure, STOP — Vic valide les chiffres ET les formulations avant la page (phase 2).**
Le point 3 (responsive) est un FIX indépendant : **livré** (bas de page).

## Le tableau des chiffres (aucun en dur — tout mesuré)

| Chiffre | Requête | Valeur actuelle | Servi comment | Formulation proposée |
|---|---|---|---|---|
| **BLOC 1 — « Je couvre tout »** |
| Parcelles du run servi | `count(parcel_p_score_v2 WHERE run_id=q_v8_calibre)` | **431 663** | dynamique (endpoint léger — même valeur que /filtre total) | « 431 663 parcelles notées » |
| Communes | `count(DISTINCT commune)` parcels | **24 / 24** | statique de fait (constante géographique) mais servie avec le reste | « les 24 communes, sans exception » |
| Sources surveillées | `data_sources WHERE status='connecte'` | **52** (le « 52 » de Vic est EXACT ; +4 partielles, +2 manuelles, 4 à faire = 62 cataloguées) | dynamique (count trivial) | « 52 sources publiques branchées » (« i » : + 4 partielles · catalogue /sources) |
| **BLOC 2 — « Je ne devine pas »** |
| Ventes réelles d'entraînement | `p_model_ext_dataset WHERE label_l2=1 AND annee 2017-2024` (l'échantillon du modèle servi m36-l2f, PAS le total DVF) | **65 326** mutations positives (sur 3 453 304 observations d'apprentissage) | build (le dataset ne bouge qu'au re-train) — jamais figé dans le JSX | « appris sur 65 326 mutations réelles (2017-2024) » |
| Communes calibrées | parcel_zone_plu : 23 communes + Saint-Philippe RNU | **23 calibrées + 1 RNU** | build | « 23 PLU calibrés article par article — Saint-Philippe, au RNU, traité aux règles nationales » |
| Contrôles qualité | golden dataset `golden-parcelles.json` | **118 parcelles-sentinelles, 777 vérifications champ à champ** (le « 116 » historique est passé à 118) | build (le fichier golden versionné) | « 118 parcelles-témoins re-vérifiées champ à champ avant chaque mise en ligne » |
| **BLOC 3 — « Je vois ce que personne ne voit »** |
| Fenêtres défisc actives | `defisc_fenetres WHERE fenetre_active` (définition stage 6 : fenêtre de revente fiscale OUVERTE, estimée sur l'année d'achat neuf) | **797** | dynamique | « 797 fenêtres de sortie de défiscalisation ouvertes » |
| Permis caducs | `pc_caducs` | **2 161** | dynamique | « 2 161 permis estimés caducs » |
| Opérations reconstituées | 2 candidats mesurés : (a) sociétés privées ≥ 3 parcelles = **2 501** ensembles fonciers ; (b) divisions en or = 34 | dynamique | **PROPOSITION : (a)** « 2 501 ensembles fonciers reconstitués (même société, 3 parcelles ou plus) » — (b) trop maigre | |
| Bascules détectées | tiers différents entre les 2 runs SERVIS successifs (q_v7_defisc → q_v8_calibre) | **45 956** bascules, dont **573 devenues brûlantes/chaudes** | build (recalculé à chaque bascule de run) | **PROPOSITION : le 573** — « 573 parcelles devenues brûlantes ou chaudes à la dernière mise à jour » (45 956 brut = surtout du reclassement interne, moins parlant) |

### Notes d'honnêteté (à trancher au STOP)
- **Golden aujourd'hui en local : 85/118 PASS** — les 33 échecs sont un artefact de MON uvicorn
  local lancé sans l'environnement complet (champ `api.score_v2` absent), PAS une mesure produit ;
  la porte de déploiement reste 118/118. La formulation « re-vérifiées avant chaque mise en
  ligne » est la vraie promesse.
- « Bascules détectées » : le produit ne journalise pas (encore) les bascules en continu
  (event_log quasi vide) — le chiffre honnête est celui du DIFF entre les deux runs servis.
- « Opérations reconstituées » : dis-moi si (a) te va, ou si tu veux un autre objet (projets ? 34
  divisions en or ?).

### Mécanique proposée (phase 2)
Un endpoint léger unique `/accueil/chiffres` (counts triviaux + valeurs de build pour
l'entraînement/golden/bascules, agrégés côté serveur, cache 1 h) — chaque chiffre porte son
« i » sourcé. Rien en dur dans le JSX (grep en validation).

**STOP — j'attends ta validation des chiffres, des formulations, et des 2 propositions
(opérations reconstituées · bascules).**

---

## Point 3 — Responsive : LIVRÉ (indépendant du STOP)
- Panneau gauche : largeur **proportionnelle bornée** `clamp(240px, 24vw, 340px)` (au lieu de
  300 px fixes) ; < 640 px = tiroir superposé (existant).
- **ResizeObserver** sur le conteneur carte → `map.resize()` à chaud (largeur du panneau ou
  fenêtre qui change → la carte se recale ; prouvé : canvas 596 → 1036 sur 900→1440).
- **Mesuré aux 6 largeurs demandées** (section Filtres DÉPLIÉE — le pire cas) :

| Fenêtre | Panneau | Carte | Verdict |
|---|---|---|---|
| 1440 | 340 px | 1036 px | OK |
| 1200 | 288 px | 848 px | OK |
| 1024 | 246 px | 714 px | OK |
| 900 | 240 px | 596 px | OK (le cas du constat — plus de bande) |
| 768 | 240 px | 464 px | OK |
| 480 | tiroir | 416 px (pleine largeur) | OK |

Aucun texte tronqué, aucun chevauchement (chips qui s'empilent). Captures `s9_w1440…s9_w480`.

CC ne merge jamais.
