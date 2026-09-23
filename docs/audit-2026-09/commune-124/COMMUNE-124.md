# COMMUNE-124 — Outil Communes : comparaison, évolution, acquisitions

Branche `fix/commune-124` (worktree `labuse-commune124`, ports 8215/5415), 3 commits (un par lot),
base main `cb854434`. tsc + build verts ; vitest 178 P / 3 échecs admin **pré-existants** (0 nouveau).
Captures dans `./captures/`.

| Commit | Lot |
|---|---|
| `5fb6c239` | A — Comparaison des 24 communes |
| `674e00eb` | B — Évolution du marché (titre + fix CP/INSEE) |
| `cb3ec2f8` | C — Acquisitions récentes |

---

## Lot A — Comparaison des 24 communes (tableau)

| Point | Attendu | Fait |
|---|---|---|
| A1 | Retirer l'encart bas « MARCHÉ DES ANNONCES — … Radar — N biens collectés à ce jour » | **Fait** — `MarcheAnnoncesRadar` supprimé (fonction + usage) ; le Radar garde sa porte dédiée sur l'écran d'entrée. |
| A2 | Regrouper toute la légende sous un bouton « Légende » en haut à droite ; toggle ; plus de bloc permanent en bas | **Fait** — légende extraite dans `<CommunesLegende/>`, repliée sous le bouton « Légende » (coin haut-droit, à gauche du ✕) ; replié par défaut, clic ouvre/referme. |
| A3 | Fusionner les deux accroches en une : « Comparez les communes, ouvrez leur fiche, triez en cliquant sur leur en-tête. » | **Fait** — le sous-titre du panneau porte la phrase unique ; la Banner « Où investir… » d'O6Comparateur (2e accroche) est retirée. |

Captures : [A-avant-table](captures/A-avant-table.png) · [A-après-table](captures/A-apres-table.png) ·
[A-après-légende-ouverte](captures/A-apres-legende-ouverte.png).

### A4 — Vérif data des colonnes (source · OK/écart)

Audit du code backend (`/comparateur-communes` → `src/labuse/api/comparateur.py` +
`src/labuse/registre/moteurs/commune.py`). **Les 7 colonnes lisent la bonne source ; aucun écart.**

| Colonne (front) | Table.champ lu | Seuil / fenêtre | Verdict |
|---|---|---|---|
| Parcelles à potentiel | `parcel_p_score_v2.tier` (brûlante/chaude/priorite/a_suivre), run servi | run courant | **OK** — palier À suivre, run servi. |
| Instruction (mois) | `m10_permit_delais.delai_mois` (médiane) | `valide`, `famille='logements'`, `delai_mois≥0` | **OK** — délai médian dépôt→autorisation Sitadel (m10). |
| Permis (5 ans) | `sitadel_permits.date` (count) | `CURRENT_DATE − INTERVAL '5 years'` | **OK** — cumul 5 ans glissants (étiquette honnête, pas « 12 m »). |
| Déficit SRU (pts) | `commune_contexte_sru.objectif_pct − taux_lls` | `greatest(…, 0)` | **OK** — écart objectif légal − taux LLS, plancher 0. |
| €/m² ancien | `dvf_mutations` (valeur/surface bâti, médiane) | ventes strictes, €/m²∈[100,12000], **n≥100** | **OK** — même fonction que le baromètre (`prix_ancien_communes`). |
| €/m² neuf | `dvf_mutations_parcelle` VEFA (médiane) | fenêtre 5 ans, €/m²∈[50,20000], seuil config | **OK** — moteur live partagé fiche/carte (`neuf_vefa_commune`). |
| €/m² terrain nu | `dvf_mutations_parcelle` terrain nu par zone PLU (médiane) | zone U sinon AU, €/m²∈[5,5000], **n≥10/cellule** | **OK** — moteur live partagé fiche (`ligne2_terrain_zone`). |

**Rien à laisser à Vic sur A4** : les sources sont conformes aux libellés.

---

## Lot B — Évolution du marché + audit des trous

| Point | Attendu | Fait |
|---|---|---|
| B1 | Titre → « Évolution du marché : ventes et permis » | **Fait** — porte + panneau (`Communes.tsx`). |
| B2 | Audit des trous + corriger un cassé simple | **Fait** — voir tableau ci-dessous ; un cassé systémique **corrigé** (sélecteur CP→INSEE). |
| B3 | Ne pas toucher au « (n) » | **Respecté** — inchangé. |

Captures : [B-avant île](captures/B-avant-ile.png) ·
[B-avant Saint-André = BUG](captures/B-avant-saintandre-BUG.png) ·
[B-après Saint-André = FIX](captures/B-apres-saintandre-FIX.png).

### B2 — Diagnostic des trous

Le baromètre construit 3 séries (`_barometre_data`, `src/labuse/api/moteurs.py`) : Ancien
(`dvf_mutations`, par NOM), Terrain nu (`dvf_mutations_parcelle`, par code commune), Permis
(`sitadel_permits`, par NOM). Aucun seuil d'effectif par cellule ; une cellule sans donnée = « — ».

| Type de vide | Cause | Normal / Cassé | Chiffres réels (base 8215) |
|---|---|---|---|
| Île entière — 2026T1 / 2026T2 vides côté ventes (Ancien + Terrain), pleins côté permis | Latence de publication DVF : `dvf_mutations` s'arrête à 2025T4, `dvf_mutations_parcelle` au 31/12/2025 ; Sitadel va jusqu'à 2026-07. L'axe front = **union** des trimestres → les lignes 2026 nées des permis n'ont pas de DVF. | **NORMAL** | Île : ancien dernier plein 2025T4 (n=1209, méd 2 738) ; permis 2026T1=738, 2026T2=629. DVF 2026 = 0 vente retenue. |
| Saint-André — colonne **Terrain** vide sur 8 trimestres | Le front envoyait le **code POSTAL 97440** (`CP_COMMUNES`) là où l'endpoint attend l'**INSEE cadastral 97409** (`code_commune='97440'` → 0 ligne terrain). | **CASSÉ → CORRIGÉ** | À 97409 : 19–41 mut/trim, médianes 239–323 €/m². Donnée en base, jamais affichée. |
| Saint-André (et 23 autres) — colonnes **Ancien + Permis** montrant l'**île entière** sous le libellé de la commune | Même racine : `parcels WHERE left(idu,5)='97440'` → 0 ligne → `nom=NULL` → le filtre `commune=:nom` devient inerte → séries **île entière** servies silencieusement. | **CASSÉ → CORRIGÉ** (le plus trompeur : faux, pas vide) | CP 97440 renvoyait 2 738 €/m² (n=1209, île) au lieu de 1 600 (n=31, Saint-André réel). |

**Preuve empirique** (curl direct sur l'API) :

```
/moteurs/barometre?insee=97440  → perimetre "île entière …", ancien 2025T4 n=1209 méd 2738, terrain 0 lignes
/moteurs/barometre?insee=97409  → perimetre "Saint-André (DVF communal)", ancien 2025T4 n=31 méd 1600, terrain 8 lignes
```

Les 24 communes servies par `/communes` (INSEE cadastral) résolvent **24/24** dans le baromètre (aucun repli île entière).

#### Corrigé (cassé simple, un seul geste)
- **`M18` se source désormais sur `/communes`** (INSEE cadastral faisant autorité — la MÊME clé que le
  comparateur) au lieu de `CP_COMMUNES` (codes postaux). Une ligne de racine, 24/24 vérifiés. Chaque
  commune sert enfin SES chiffres. `CP_COMMUNES` reste inchangée (elle est correcte pour l'appariement
  BAN adresses ; c'est le seul appel baromètre qui la détournait).

#### Laissé « — » (vrai manque de données, jamais un zéro)
- Île 2026T1/T2 côté ventes : latence DVF. Reste « — » (comportement voulu, `fmt(null)→'—'`).

#### Laissé à Vic (écart de conception, ne se bricole pas)
- **Garde-fou backend** : quand le code ne résout aucune commune, `_barometre_data` retombe
  SILENCIEUSEMENT sur l'île entière (filtre `commune=:nom` inerte quand `nom=NULL`). Mon correctif front
  fait que le back ne reçoit plus jamais un code irrésolvable pour les 24 communes ; mais le garde-fou
  (refuser/signaler plutôt que servir l'île sous un libellé de commune) reste un durcissement défensif
  à décider côté back. `src/labuse/api/moteurs.py` (lignes du filtre `commune=:nom`).
- **Choix de l'axe temps** : le front prend l'**union** des trimestres des 3 séries → l'axe est étiré par
  Sitadel (2026T2) au-delà de la couverture DVF, ce qui fabrique mécaniquement les « — » 2026 à chaque
  affichage île. Honnête mais visuellement lourd : borner l'axe aux trimestres DVF vs garder l'axe
  complet est un arbitrage produit (`M18Tableau`, `moteurs.tsx`).

---

## Lot C — Acquisitions récentes

| Point | Attendu | Fait |
|---|---|---|
| C1 | Filtre à la présentation des autres filtres, modèle Permis : puces actif vert opaque, survol opaque, « Tous » en dernier, chevrons cohérents ; réutiliser les composants partagés | **Fait** — les puces millésime adoptent la grammaire du bloc « Filtrer par état » de Permis : actif `bg-mint text-mint-ink` (vert opaque), survol `hover:bg-mint hover:text-mint-ink` (aplat opaque de sa couleur), puce neutre « Toutes » déplacée **en dernier**. Le sélecteur de commune reste un `<select>` natif (déjà conforme à Permis). |
| C2 | Regrouper par personne morale en accordéons repliés : « SOCIÉTÉ · N parcelles » + chevron ; déplié = liste des parcelles ; chevron fermé = droite, ouvert = bas | **Fait** — une ligne cliquable par société « SOCIÉTÉ · N parcelles » + chevron ; **replié par défaut** ; déplié = « Scan patrimoine → » + la liste des parcelles. Chevron SVG cohérent avec l'app : fermé ▸ (droite), ouvert ▾ (bas). |

Captures : [C-avant](captures/C-avant-acquisitions.png) ·
[C-après repliée](captures/C-apres-replie.png) · [C-après dépliée](captures/C-apres-deplie.png).
