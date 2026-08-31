# PROJETS-V5 — la page projet en quatre étages + l'alignement des deux fiches

**Dossier** `~/Desktop/labuse` · **branche** `feat/outils-1` · arbre propre au départ.
**Golden non touché** : le seul fichier backend est `api/projets.py` (0 fichier scoring/qa).
Référence : `docs/maquettes/projets-v5.html`. API + front redémarrés avant recette.
**DA gravée** : mauve = Copilote IA · vert plein = action principale · contour gris = action
secondaire. Le classement est le **moteur STATISTIQUE** de LABUSE → le bandeau d'analyse est **VERT**
(pas mauve comme dessiné dans la maquette v5, qui confondait avec l'IA).

---

## E1 — QUATRE ÉTAGES, QUATRE CARTES
`ProjetKanban.tsx` réécrit : **identité** (titre, chips périmètre + budget, actions) → **analyse** →
**progression** → **tri** (3 colonnes). Chaque étage est une carte séparée par un vrai espace
(`gap-3.5`). Capture `01-page-projet-4etages.png`.

## E2 — LE BANDEAU D'ANALYSE (correction de sens)
Backend `_analyse_cadrage` : total du cadrage (**la même requête que les compteurs de filtres**,
`_cadrage_total`) + décompte par tier (`count FILTER WHERE tier`). Le bandeau dit la vérité :
« LABUSE a analysé les **N** parcelles de votre cadrage : **M** ont plus de chances… — P en Priorité,
S À suivre. Elles arrivent en tête ; les N−M autres suivent, **sans jugement**. » Prouvé sur tyty :
N=6 830 (== `_cadrage_total`), P=9, S=44, M=53. Sous-ligne : signaux détectés + valeurs au (run) +
marché ancien commune. « Voir pourquoi » → `ScoringExplainer` (le composant de la carte). **Vert.**

## E3 — LE BANDEAU DE PROGRESSION
Une ligne : 3 compteurs (retenues vert · écartées rouge · à trier) + barre à deux segments.

## E4 — LA COLONNE À TRIER
Barre : chips **Tous / Priorité N / À suivre N** (points colorés, N depuis `analyse`) · recherche
adresse/IDU · **⚙ Filtrer** avec pastille du nombre de filtres actifs. Filtres actifs en puces
retirables + « tout effacer ». Lignes : point de tier · adresse (ou « sans adresse — Commune » E7) +
IDU + état/**constructibilité** en mono · **jusqu'à 2 signaux** en chips (fort en rouge, « aucun
signal » gris — backend `_signaux_parcelles`, batch) · surface · gestes ✓/✕. **Colonne « marché
commune » retirée** des lignes (le chiffre est monté dans le bandeau). Pied : **« 50 par page · page
X/Y · suivante → »**.

## E5 — LE TIROIR « FILTRER »
`FiltreDrawer` : ouvre à droite de la colonne, sans quitter la page. Les critères du wizard
(`FiltreFacettes`), servis par la **MÊME requête** (paramètre `sf` fusionné côté serveur ; sémantique
de REMPLACEMENT à périmètre fixe → on peut retirer une facette du projet dans la vue). Le bouton
annonce le résultat en direct : **« Voir 6 830 parcelles »** (capture `02`). « Tout effacer » remet le
cadrage du projet (sf = null).

## E6 — RETENUES ET ÉCARTÉES : LISTES COMPLÈTES
Plus de « + N autres » : les colonnes défilent, le compteur est dans l'en-tête. Mini-lignes (point,
adresse ou « sans adresse », IDU, retour). Pied de Retenues : → CRM · ✉ Courrier (N).

## E7 — « SANS ADRESSE »
Partout dans Projets (lignes À trier + mini-lignes) : `« sans adresse — Commune »` en italique gris +
IDU en clair, jamais le nom de la commune seul comme adresse (`AdresseLigne` + `MiniLigne`).

## E8 — FICHE COMMUNE : LES COULEURS DISENT LE VRAI
`ContextePanel.tsx` : « Comparer aux 24 » et « Étude de zone » (qui ne sont PAS de l'IA) passent de
**mauve** à **neutres** (contour gris, comme PDF / Renommer). « Voir ses parcelles » devient **vert
PLEIN opaque** (le même que « Demander à LABUSE d'analyser » sur la fiche parcelle). Capture `03`.

## E9 — LA GRILLE D'OUTILS DEVIENT UN COMPOSANT PARTAGÉ
`shared/GrilleOutils.tsx` (`GrilleOutils` + `OutilCase`, variantes bouton / lien / désactivée) extrait
de la fiche commune. Servi sur les **DEUX** fiches : la grille des passerelles (commune) ET la grille
d'exports (parcelle : PDF · Dossier · Financier · Cadastre · Argumentaire · Maps · Courrier ·
Pré-dossier PC — tuiles async converties, logique conservée). **8 cases sur chaque fiche, même rendu +
survol** (captures `03`/`04`). Sur la fiche commune, sous la grille : **« Voir plus d'outils → »**.

## E10 — « RÈGLES D'URBANISME : AUCUNE » (diagnostic + correction)
**Diagnostic** : le statut lui-même était CORRECT (« à jour » / « RNU », `_PLU_STATUT` mappe la
procédure `cloturee`/`aucune` → « à jour »). Le « aucune » que lisait le client était le **`libelle`
brut** = le champ **`stade`** de `veille_plu` (ex. Le Tampon `stade = 'aucune'` = *aucune procédure en
cours* ; « approuvee_probable »), affiché **verbatim** dans le détail de la ligne-carte
(`ContextePanel.tsx`). Donnée présente mais **libellé technique servi tel quel**, lu à tort « pas de PLU ».
**Correction** : on ne montre plus le stade ; une phrase claire selon le statut (« Le PLU est
opposable. » / « Pas de PLU opposable : Règlement National d'Urbanisme. ») + **« Voir le PLU → »** qui
ouvre l'outil PLU pré-rempli sur la commune.

## E11 — LES DEUX FICHES SE RÉPONDENT (audit + alignement)
Écarts sans raison métier trouvés (fiche commune `ContextePanel` vs fiche parcelle `Fiche.tsx`,
référence **DA-FICHE-v6**) et traités :

| Écart | Fiche parcelle (réf.) | Fiche commune (avant) | Aligné ? |
|---|---|---|---|
| **Grille d'outils** | `.exp-grid` / `.exp` | `OutilCase` local | ✅ **composant PARTAGÉ** `GrilleOutils` sur les deux (E9) |
| **Survol des cases** | (aucune transition) | `hover:border-mint` | ✅ même survol des deux côtés (composant partagé) |
| **Libellé de groupe** | `.sec` = mono 10px + **filet horizontal**, tracking .13em | `GroupeLabel` mono 10px, tracking .22em, **sans filet** | ✅ aligné : filet + tracking .13em |
| **Boutons secondaires** | contour gris (secondaire) / mauve réservé IA | Comparer/Étude en mauve | ✅ neutres (E8) |
| **Action principale** | vert PLEIN opaque (`.cta`) | « Voir ses parcelles » vert clair | ✅ vert plein (E8) |
| **En-tête 4 chiffres** | 17px | 17px | ✅ déjà identiques |
| **Ligne-carte (bordure/rayon/sous-texte)** | 0.5px, 12px rayon, 11px sous | ~identiques | ✅ déjà alignés (écart négligeable) |

Captures côte à côte : `03-fiche-commune-E8.png` ↔ `04-fiche-parcelle-E9.png` — même grammaire (en-tête
4 chiffres, action verte pleine, groupes mono à filet, lignes-cartes, grille d'outils partagée).

---

## VÉRIFICATION
- `tsc -b` : **0**. `vite build` : **OK**. `vitest` : **108 passed**.
- `pytest` (projet/sécu) : **47 passed** (backend `_analyse_cadrage`/`_signaux_parcelles`/`sf` exercés
  via les tests existants ; analyse.total == `_cadrage_total` prouvé).
- **Golden intact** : 0 fichier scoring/qa touché (seul `api/projets.py` côté back, hors scoring) ;
  `qa/golden_check.py` = **119/119 PASS, 0 FAIL**, GARDE-RUN OK (431 663/431 663, q_v11_m137).
- Captures `docs/PROJETS-V5/captures/` : page projet 1440p (4 étages, bandeau vrais nombres, 50 lignes,
  deux signaux, « sans adresse ») · tiroir « Voir 6 830 parcelles » · fiche commune E8 · grille partagée
  E9 (8+8) · fiches côte à côte E11.

**Ne merge pas.**

### Commande de merge (à exécuter par Vic, en dernier, isolé)
```
git checkout feat/outils-1 && git merge --no-ff <ce commit>
```
