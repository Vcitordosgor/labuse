# RAPPORT — Cercle 3 « L'intelligence & le spectaculaire » (LA BUSE v3)

> Ce qui transforme la fiche en outil de décision vivant : assistant, mémoire visuelle, veille, 3D.
> Rapports : `RAPPORT_3A.md`, `RAPPORT_DISPO_3B.md`, `RAPPORT_3C.md`, `RAPPORT_3D.md`.
> **288 tests verts**, ruff clean, baseline 3 000. Ordre exécuté : 3.B → 3.C → 3.D → 3.A.

## 3.B — Photos aériennes historiques ✅
- **Lien « Remonter le temps » (IGN)** sur chaque fiche, paramétré sur le **centroïde réel** (ortho
  actuelle ↔ ~1950-1965, millésime qui couvre La Réunion — vérifié) ; helper testé, injecté hors
  cache + sur le one-pager.
- **Bonus** : 4 millésimes historiques (**1961 / 1980 / 1989 / 2010**, EduGéo La Réunion) en fonds
  sélectionnables sur la carte → « remonter le temps » sans quitter l'app.

## 3.C — Alertes intelligentes ✅
- **Scope défini par l'utilisateur** : **zones de veille** (polygones dessinés) + **parcelles
  suivies** (pipeline). Déclencheurs : **vente DVF** dans une zone, **permis** ≤ 200 m d'une
  parcelle suivie. Détection **idempotente** au rafraîchissement ; liste de **nouveautés** + accusé
  de lecture. Push = hors scope v1 (assumé).

## 3.D — Volume constructible 3D ✅
- **Rapport de faisabilité d'abord** → **axonométrie SVG maison** (zéro dépendance, offline-safe,
  cohérent avec la contrainte de vendorisation ; chemin d'évolution MapLibre documenté).
- **Extrusion de l'emprise constructible à la hauteur PLU**, posée sur la parcelle ; le moteur
  expose désormais `hauteur_m`. Volume = emprise × hauteur. Indicatif (ni archi ni implantation).

## 3.A — Assistant de fiche en langage naturel ★ ✅
- **« Expliquer cette parcelle »** → prose via **API Anthropic**. **Garde-fou anti-hallucination** :
  le prompt ne contient QUE une liste blanche de faits réels de la fiche ; le modèle reformule,
  n'invente rien, signale les données manquantes. Dégrade proprement sans clé.
- **Dépendance Vic** : poser `ANTHROPIC_API_KEY` (doc : `RAPPORT_3A.md` + `DEPLOY_RUNBOOK.md`).
  Recette live (2 parcelles contrastées) exécutable dès la clé en place.

---

## ⛔ STOP & VALIDATE — fin Cercle 3 · Bilan global « la fiche qui décide »

En ouvrant une parcelle, le promoteur a maintenant, **sur un seul écran et tracé à la source** :

1. **Le verdict** (opportunité / à creuser / exclue) + double score, et **pourquoi** (cascade
   lisible : ce qui favorise / contraint / reste à vérifier).
2. **Qui possède** (DGFiP personnes morales, 1.A) + bouton SPF si particulier.
3. **Ce qu'on peut y construire** : capacité PLU réelle (niveaux, SDP, logements) **+ son volume 3D**.
4. **Ce que ça vaut** : bilan promoteur à rebours (charge foncière), calibré par secteur.
5. **Le terrain** : pente/exposition (2.A), vue mer (2.B), recul ravines (2.C).
6. **L'histoire** : photos aériennes 1961→aujourd'hui (3.B).
7. **La dynamique** : permis SITADEL + ventes DVF, et **des alertes** sur ses zones/parcelles (3.C).
8. **En clair** : un assistant qui **explique** la fiche en français (3.A).

### Restent en dépendance Vic (rien de bloquant pour livrer)
| Dépendance | Débloque | État |
|---|---|---|
| **`ANTHROPIC_API_KEY`** | 3.A (recette live) | à poser |
| **Whitelist PEIGEO** | 2.D (50 pas) + 2.E (assainissement) | en cours côté env |
| **Calibration bilan** | fiabilité du chiffrage (1.C) | web d'abord (prompt dédié), terrain ensuite |

**Sur ta validation**, je peux enchaîner — au choix — la **calibration du bilan par recherche web**
(`PROMPT_CALIBRATION_WEB_BILAN.md` : faire disparaître le bandeau « non fiable » avec des valeurs
réelles sourcées), ou la reprise de **2.D / 2.E** dès que PEIGEO répond. Je m'arrête ici pour ta revue.
