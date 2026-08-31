# FICHE-COMMUNE-2 — vitesse, maquette V2, Veille critères, Radar écarts

**Dossier** `~/Desktop/labuse` · **branche** `feat/outils-1` · arbre propre au départ.
**Golden non touché** (0 fichier scoring/qa modifié). Référence : `docs/maquettes/fiche-commune-v2.html`.
API + front redémarrés avant recette (uvicorn :8000 sert `frontend/dist` sous `/socle/`).

---

## C1 — VITESSE (mesure d'abord)

**Chrono AVANT** (`GET /communes/{c}/contexte`, mesuré) :

| commune | froid | chaud |
|---|---|---|
| Saint-Paul | 24,0 s | 11,6 s |
| Saint-Denis | 20,5 s | 10,9 s |
| Le Tampon | 27,3 s | 18,0 s |

**Ce qui coûte** (à l'ouverture) : comparateur (CTE 6 jointures), Radar `pige/marche.stats`
(PERCENTILE + FILTER ×10), population Filosofi (intersect spatial), densifiables (3 jointures + SUM
SDP), `_foncier_commune` (8 requêtes), risques PPR (intersect spatial ×2), permis. Tout recalculé à
chaque ouverture (mémoïsation en process seulement).

**Correctif** : le payload ENTIER est précalculé par commune dans une table de cache
`commune_contexte_cache` (`commune` PK, `payload` jsonb, `computed_at`), alimentée par un **job du
registre CRON `fiche-commune-cache`** (`jobs.py` + `jobs_impl.py`, 03:00 Réunion, lançable à la main
`labuse jobs run fiche-commune-cache`). L'endpoint SERT le payload tel quel (lecture jsonb) + la date
`cache_calcule_le` (pied de fiche) ; cache absent → calcul en direct (honnête, `cache_calcule_le = null`),
jamais un faux zéro. Chaque commune est isolée dans le job (rollback ciblé), qui DIT ses OK/échecs.

**Chrono APRÈS** (servi depuis le cache) :

| commune | servi |
|---|---|
| Saint-Paul | **0,017 s** |
| Saint-Denis | **0,008 s** |

→ **20–27 s → ~10 ms (≈2000×)**, bien sous l'objectif 500 ms. Job complet des 24 communes exécuté
via la CLI (exit 0, chemin CRON validé de bout en bout).

---

## C2 — MISE EN PAGE = MAQUETTE V2

- **En-tête à 4 chiffres** : terrain nu U · **neuf** · **SRU** · ZAN (l'ancien médian et le délai
  d'instruction restent sur leurs lignes). Bouton vert **« Voir ses parcelles »** pleine largeur ;
  deux actions violettes **⊞ Comparer aux 24 · ◎ Étude de zone**.
- **Le badge « signal : prudence » est RETIRÉ.** Il venait de `marche_commune.market_signal`
  (`marche_commune.py:361`, score < 40 = liquidité DVF faible + offre Sitadel forte) — une boîte noire
  sans règle lisible, qu'un client ne peut ni contester ni adopter.
- **Signaux nommés** qui le remplacent, chacun avec une **règle en constante nommée**, n'apparaissant
  que si vrais (backend `app.py::_signaux_commune`, cachés) :
  - `SRU déficitaire` — taux LLS < objectif ;
  - `ZAN épuisé dans N ans` — `ZAN_SEUIL_ANS = 5` ;
  - `PPR sur N % des parcelles` — `SEUIL_PPR_PART_PCT = 30.0` ;
  - `marché −X % / 12 mois` — évolution 12 mois < 0.
  Sur Saint-Paul : les 4 signaux servis **matchent exactement** la maquette (SRU 18,3 %/25 %,
  ZAN 4,2 ans, PPR 34 %, marché −4,2 %). Le Port : 0 signal (aucun vrai).
- **Pied de fiche** : « Compteurs précalculés le JJ mois AAAA (rafraîchis chaque nuit) ».
- **La refonte visuelle demandée par Vic** (« on ne voit pas la distinction entre les cases,
  inspire-toi des fiches parcelles ») est FAITE : les accordéons deviennent des **LIGNES-CARTES** à la
  grammaire EXACTE de la fiche parcelle — fond carte, bordure, coins arrondis, icône à gauche, titre +
  sous-titre, valeur (ou badge) à droite, chevron. Fermée, la ligne dit déjà l'essentiel ; un clic ouvre
  son détail (le contenu OUTILS-6, rien de perdu ; état mémorisé).
- **Trois groupes titrés en mono, dans l'ordre** : **CONSTRUIRE ICI** (Règles d'urbanisme · Enveloppe ZAN ·
  Logement social SRU · Permis & délais · Programme local PLH) · **LE MARCHÉ** (Prix & tendance · Terrain
  nu · Annonces Radar · Loyers) · **LE TERRITOIRE** (Foncier repéré · Zonage · Risques · Population ·
  Quartiers prioritaires · Mairie). 15 lignes-cartes servies.
- **Les outils en GRILLE de 8 cases** (icône, nom, chiffre), comme la grille d'exports de la fiche
  parcelle : PLU · Permis · Densifier · Radar · Scan patrimoine · Solaire · Étude de zone · Comparer.
- `Acc`/`OutilLigne` (l'ancien style accordéon/liste) retirés.

Captures : `captures/01-fiche-commune-C2.png` (Construire ici + Le marché) · `03b-…-territoire-outils.png`
(Le territoire + grille) ↔ **`captures/04-fiche-parcelle.png`** (la fiche parcelle : mêmes groupes mono
LE TERRAIN / LE CONTEXTE, mêmes lignes-cartes) — **la parenté visuelle saute aux yeux**. Maquette :
`02-maquette-fiche-commune-v2.png`.

---

## C3 — « VOIR SES PARCELLES » : COUCHES REPLIÉ

Le bouton « Voir ses parcelles » de la fiche appelle désormais `openListing()` (panneau sur le
LISTING, Couches replié) → la liste des parcelles occupe l'espace. Le repli est LIÉ à cette arrivée
(un geste), pas un changement du défaut global (Couches reste ouvert par défaut ailleurs).

---

## C4 — VEILLE FONCIER, ONGLET CRITÈRES

`SurveillancePanel::VoletCriteres` aligné sur la veille annonces (RADAR-VEILLE-1) : à l'ouverture,
**« + Créer une veille »** en tête + **« Vos critères enregistrés »** dessous ; les filtres
(`FiltreLabuse enVeille`) n'apparaissent qu'APRÈS clic (état `creating`). Après une création réussie
(la liste grandit), retour automatique à la liste. Avant, les filtres étaient dépliés d'emblée.

---

## C5 — RADAR : LES ÉCARTS À −50 % (diagnostic puis correction)

### Diagnostic (avant tout code) — 86 biens à écart calculable, **1 seul rattaché à une parcelle**

10 écarts les plus NÉGATIFS (extrait) et POSITIFS — surface / prix / référence (type · n) / cause :

```
bien commune       type          surf    prix    aff€/m² ref€/m²  n     écart%  cause
104  Saint-Denis   maison         60    85 000    1 417   3 085  1810   -54,1  référence COMMUNE (trop large)
 94  Saint-Paul    maison        200   370 600    1 853   3 726  1678   -50,3  référence COMMUNE (trop large)
 74  Saint-Denis   maison        200   374 500    1 872   3 085  1810   -39,3  référence COMMUNE (trop large)
 70  Saint-Denis   terrain       353   109 000      309     485  1248   -36,3  référence de zone (terrain)
 …
 19  Saint-Denis   appartement    74   587 000    7 932   2 393  5897  +231,5  bien atypique/premium + réf commune
 57  Saint-Denis   appartement    39   246 000    6 308   2 393  5897  +163,6  réf commune (appts anciens, basse)
 40  Saint-Denis   appartement    63   329 000    5 222   2 393  5897  +118,2  référence COMMUNE (trop large)
```

**Cause dominante : « référence trop large ».** La référence était la médiane DVF du type sur la
COMMUNE ENTIÈRE (Saint-Denis maisons = 3 085 €/m², n=1810 ; appartements = 2 393 €/m², n=5897). Un bien
d'un quartier comparé à toute la commune → **toutes les maisons paraissent « sous le marché » (−24 à
−54 %), tous les appartements « au-dessus » (+70 à +231 %)** — de faux verdicts systématiques. Les
surfaces sont plausibles (pas de misparse massif), sauf 1–2 biens premium atypiques.

### Correction

- **Référence = MÉDIANE LOCALE** du même type autour de la parcelle rattachée (`signaux._ref_local`,
  rayon 500→1500 m, même filtre de retenue que le baromètre, `SEUIL_REF_LOCAL = 8`) — l'esprit du moteur
  « Marché et secteur » de la fiche parcelle. **Repli commune SEULEMENT à défaut, et on le DIT**
  (`repli_commune`). Terrain : garde sa référence de ZONE (déjà étroite).
- **Pas de badge sous le seuil** : le verdict « sous le marché » n'est porté QUE par une référence
  FIABLE (locale, ou terrain-zone) — jamais par une référence commune. Résultat : les **10+ faux
  « sous le marché »** du diagnostic → **0**. L'écart exact reste affiché (informatif), sans verdict trompeur.
- **Même moteur** partout (`badges_pour_biens`) : liste, fiche, mails (idu transmis dans les 3).

**Distribution après** : le bien rattaché (#27 Sainte-Marie, maison) prend la médiane LOCALE
(2 795 €/m², n=27, 500 m → écart honnête +26,9 % au lieu d'un faux « sous le marché » commune) ; les 85
biens non rattachés gardent l'écart affiché mais **sans badge de verdict** (référence commune non
fiable). Le rattachement étant rare (mesuré Lot 0), le local s'applique à peu de biens — la
distribution des écarts change donc peu ; le gain est la **disparition des faux verdicts**.

---

## VÉRIFICATION

- `tsc -b` : **0**. `vite build` : **OK**. `vitest` : **108 passed**.
- `pytest` (modules touchés) : `test_pige_depot2` + `test_fiche_commune2_c5_reference` (4) +
  `test_fiche_commune2_c1_cache` (3) + `test_communes_gold_standard` + `test_front_reliquats` — **78 passed**.
- **Golden intact** : la fiche commune est de la DONNÉE DE CONTEXTE (hors scoring) ; 0 fichier
  scoring/qa touché → golden inchangé par construction. `qa/golden_check.py` (verrou du scoring servi,
  119 parcelles × faces DB/API/cohérence + GARDE-RUN, run q_v11_m137) lancé en ceinture : **119/119
  PASS, 0 FAIL**, GARDE-RUN OK (431 663/431 663).
- Chrono C1 (20–27 s → ~10 ms). Captures `docs/FICHE-COMMUNE-2/captures/` : fiche C2 en lignes-cartes
  (3 groupes + grille 8) ↔ fiche parcelle (parenté) + maquette V2. Couches replié (C3) · Veille critères
  (C4) · tableau C5 + distribution.

**Ne merge pas.**

### Commande de merge (à exécuter par Vic, en dernier, isolé)
```
git checkout feat/outils-1 && git merge --no-ff <ce commit>
```
