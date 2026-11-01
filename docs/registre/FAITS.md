# FAITS.md — Registre de tout ce que l'app affirme (AUDIT-NU-3, lot N)

> Branche `audit/nu-3-n` · worktree `~/Desktop/labuse-nu3-n` · **lecture seule**, aucun correctif, aucun merge, aucun accès prod.
> Livrable jumeau : [`FAITS.csv`](FAITS.csv) — **1 115 faits**, une ligne par fait, 13 colonnes RFC-4180 (0 ligne malformée, 0 ID doublon).

Ce document est la **carte** du registre : combien de faits par écran, lesquels n'ont jamais été vérifiés,
lesquels n'ont aucun test, lesquels circulent sur plus de trois surfaces (les plus exposés aux
divergences), et les doutes classés par gravité.

---

## 0. Méthode & périmètre

- **Source autoritative : le code.** Chaque fait a été tracé back→front : champ de réponse d'API
  (`fichier:ligne`) → fonction de calcul → rendu JSX portant le libellé exact. Les colonnes `source` et
  `formule` de `FAITS.csv` citent le `fichier:ligne`.
- **Décomposition** en 10 sous-audits parallèles (fiche parcelle A/B ; fiche commune + carte + filtres +
  omnibox ; 3 lots d'outils ; Docs + exports PDF ; Radar + Veille + Copilote ; Projets + CRM + Compte +
  Mails ; Étude de faisabilité). Fragments concaténés depuis `docs/registre/parts/`.
- **Confrontation écran réel : NON réalisée en direct.** L'app n'était pas démarrée (ports 9350/6550
  libres) et booter la pile (API + front + base) aurait partagé la base avec les lots G et J qui
  tournent en parallèle → risque de pollution. Le code reste la référence, mais **la colonne « écran
  réel » du mandat n'a pas pu être cochée** : les libellés sont ceux du JSX, pas d'une capture. C'est la
  limite principale de ce registre — à compléter par une passe Playwright quand les lots voisins seront
  clos.
- **Colonne 12 (vérif indépendante)** renseignée en relisant les rapports `nu-1/{A,B,C,D,E,F}`,
  `nu-2/{A,B}`, et les lots correctifs (`sdp-unique-1`, `ppr-unique-1`, `estimer-2`, `fix-final-1`,
  `radar-4`, `copilote-3`, `faisa-regles-1`, `produit-nu-1`…). **427 faits (38 %) sont « jamais
  vérifiés » par aucun audit.**

---

## 1. Compte total par écran

**1 115 faits** au total.

| Écran | Faits |
|---|---:|
| **Outils** (18 outils) | **435** |
| **Documents** (9 Docs + redirections) | **279** |
| **Fiche parcelle** (A : 65 · B : 78) | **143** |
| **Fiche commune** | **66** |
| **Radar** | **39** |
| **Projets** | **27** |
| **Copilote** | **26** |
| **Mails** (cloche + digests + transactionnels) | **18** |
| **Veille** | **15** |
| **Filtres** | **14** |
| **Carte** | **13** |
| **CRM** | **13** |
| **Compte** | **10** |
| **Omnibox** | **9** |
| **Exports PDF** (blocs partagés hors Docs) | **8** |

### Détail par outil et par document

| Outil | Faits |  | Document | Faits |
|---|---:|---|---|---:|
| Étude de faisabilité (overlay) | 72 | | Dossier | 102 |
| Estimer un bien | 38 | | Étude de faisabilité (PDF) | 38 |
| Étude de zone | 36 | | Financier / Bilan | 29 |
| Permis | 27 | | Estimer | 28 |
| Gabarit | 24 | | Apporteur | 20 |
| PLU | 23 | | Comparatif | 19 |
| Communes | 21 | | Étude-zone | 18 |
| Scan patrimoine | 21 | | Pré-dossier PC | 12 |
| Pièges et risques | 20 | | Gabarit | 10 |
| Taxe d'aménagement | 20 | | Flash | 3 |
| Remonter le temps | 20 | | *(blocs legacy morts : IDENTITE/AUTOUR/COMMUNE/BILAN)* | 4 |
| Comparer des parcelles | 19 | | | |
| Blocs fonciers | 16 | | | |
| Courrier propriétaire | 16 | | | |
| Assemblage | 14 | | | |
| Calculette foncière | 13 | | | |
| Prospection solaire | 13 | | | |
| Successions à venir | 13 | | | |
| Mon secteur (deep-link) | 9 | | | |

### Répartition par type

Types agrégés (une cellule à type composé est comptée à sa composante dominante ; valeurs exactes dans le CSV) :

| Type | Faits |
|---|---:|
| donnée brute | 452 |
| dérivée | 228 |
| verdict | 205 |
| calcul | 156 |
| estimation | 60 |
| référence / étiquette | 12 |
| autre | 2 |

> **265 faits (24 %) sont des verdicts ou des estimations** — les plus sensibles, car ils transforment une
> donnée en jugement affiché au client.

---

## 2. Faits affichés à plus de 3 surfaces — les plus exposés aux divergences

**132 faits** circulent sur plus de 3 surfaces. Ce sont les plus dangereux : un seul calcul servi à 5–7
endroits, où la moindre divergence de source/fenêtre/run produit deux chiffres contradictoires sous le
même libellé. Les 20 premiers (par nombre de surfaces) :

| Surfaces | ID | Fait | Risque connu |
|---:|---|---|---|
| **7** | DOC-DOSSIER-001 | **Surface / contenance** | NU-D-040 : contenance (625) ≠ géométrie (630) selon la surface servie |
| 6 | DOC-DOSSIER-006 | **SDP restante (bâti conservé)** | contradiction phare NU-A-001 ; « SDP » = enveloppe, terme juridique fort (NU-A-020) |
| 6 | DOC-DOSSIER-071 | Terrain nu — secteur | — |
| 6 | DOC-DOSSIER-012 | Géométrie / plan de situation | — |
| 6 | DOC-DOSSIER-011 | Dernière vente DVF | — |
| 6 | DOC-DOSSIER-009 | Adresse | — |
| 5 | FP-B-017 / OUT-RISQUES-007 | **Aléa — nature / part %** | source unique `aleas_parcelle`, 5 surfaces |
| 5 | OUT-COMPARER-005 | SDP max réglementaire / terrain libéré | sdp-unique-1 |
| 5 | OUT-CALC-002 | Prix de sortie €/m² + badge « Estimé » | — |
| 5 | DOC-DOSSIER-070 | **Marché — prix ancien médian** | ex-bloquant NU-A-002 (appart servi sur maison) |
| 5 | DOC-DOSSIER-069 | Taxe d'aménagement — taux communal | barème 2026 |
| 5 | DOC-DOSSIER-067 | Taxe foncière (bâti) | — |
| 5 | DOC-DOSSIER-051 | Aléas (liste) | NU-A-007 : niveau-max masque 100 % |
| 5 | DOC-DOSSIER-002 | Zone PLU | — |
| 5 | DOC-ETUDE-004 | Contenance cadastrale | NU-D-045 |
| 5 | DOC-COMPARATIF-013 | Logements possibles | — |
| 4 | RAD-012 / RAD-013 | **Prix acté maisons / écart demandé-acté** | F-001 : tableau ≠ « Ce bien » |
| 4 | OUT-COMPARER-011 | Prix bâti section cadastrale | NU-A : mélange maison/appartement |
| 4 | OUT-COMPARER-003 | Classement LABUSE (bande/signal) | — |
| 4 | OUT-SECTEUR-006 | Médianes marché par type | — |

> Liste complète des 132 dans `FAITS.csv` (filtrer col. `autres_surfaces`). Les **blocs partagés du
> builder** (`src/labuse/exports/blocs/`) et les **médianes de marché** concentrent l'exposition : un
> correctif sur l'une de ces fonctions se répercute partout — et une régression aussi.

---

## 3. Faits jamais vérifiés indépendamment — 427 (38 %)

Aucun audit (nu-1, nu-2, lot J ou correctifs) n'a recalculé ou confronté ces faits. Répartition :

| Écran | Jamais vérifiés |
|---|---:|
| Outils | 240 |
| Documents | 94 |
| Fiche parcelle | 50 |
| Fiche commune | 30 |
| Exports PDF | 4 |
| Carte | 4 |
| Filtres | 3 |
| Omnibox | 1 |
| Compte | 1 |

**Les outils concentrent 56 % des faits jamais vérifiés.** Les audits nu-1/nu-2 étaient centrés sur la
fiche, la commune/carte et l'Étude de faisabilité ; la **grande majorité des champs** de PLU, Permis,
Étude de zone, Taxe, Solaire, Blocs, Successions, Courrier, Calculette, Mon secteur, Comparer et
Assemblage **n'ont jamais eu de recalcul indépendant**. C'est l'angle mort le plus large du produit :
des chiffres servis en confiance, jamais confrontés à la réalité. Priorité de la prochaine campagne.

---

## 4. Faits sans test automatisé — 556 (50 %)

| Écran | Sans test |
|---|---:|
| Outils | 184 |
| Documents | 106 |
| Fiche parcelle | 106 |
| Fiche commune | 64 |
| Projets | 25 |
| Radar | 23 |
| Mails | 18 |
| Carte | 9 |
| Compte | 8 |
| Filtres | 7 |
| CRM | 5 |
| Omnibox | 1 |

La moitié des faits affichés au client n'est couverte par **aucun** test (`tests/` ou `*.test.tsx`). Les
tests existants protègent surtout des **verdicts** (cascade, PPR, estimation bandes) et des **structures
de rendu** ; les **valeurs chiffrées fines** (fiscalité, médianes par type, chalandise Filosofi/SIRENE,
loyers OLL, blocs lotissement, champs de mails) sont massivement non testées. Croisé avec §3 : **un fait
« jamais vérifié ET sans test » n'a aucun filet** — ni humain ni automatique.

---

## 5. Doutes, par gravité

### 5.1 — GRAVES (bloquant actif ou divergence/fuite vivante)

1. **OUT-BLOCS-001 — fuite RGPD confirmée et NON corrigée.** « Blocs fonciers » affiche à l'écran le nom
   en clair de ~250 indivisions successorales (« SUCCESSION BANA AHMED », pseudo-SIREN `U23718700`).
   `blocs.py:77` groupe tout `siren` non vide sans exclure les pseudo-SIREN `U…` ni filtrer
   `classify_dgfip(...).indivision` — le garde-fou `VEILLE_SUCCESSION_FORMES` qui protège l'outil
   Successions **n'existe pas ici**. (Ex-bloquant NU-D-017, toujours ouvert.)

2. **DOC-FLASH-001 — le Flash (79 €) livre le Dossier intégral (349 €).** La doctrine « Flash = Dossier
   sans la §9 » n'est plus appliquée : `builder.construire` mappe `flash→dossier` et rend le Dossier à
   l'identique (preuve `pdftotext` diff vide). Soit la §9 n'existe plus, soit un client Flash reçoit le
   produit payant complet. **À trancher — décision produit/facturation.**

3. **SDP restante — double source intra-fiche** (FP-A-016, FP-B-011, DOC-DOSSIER-006). La tuile d'en-tête
   lit `parcel_residuel` (vivant, non figé) ; le verdict LABUSE lit `score_labuse` (figé au run q_v20).
   Ex-bloquant NU-A-001 (850 vs 0 sur 5/5 témoins). `sdp-unique-1` affirme servir le run comme la prod ;
   **à reconfirmer que la tuile vivante et le verdict figé ne peuvent plus diverger en prod.**

4. **Radar — double « prix acté maisons »** (RAD-012/013). Le tableau du marché lit `_dvf_bati_type`
   (toutes années) ; « Ce bien · vs acté » lit `marche_commune_bloc` (recâblé par RECETTE-4). Deux
   chiffres pour le même libellé sur le même écran ; l'écart de négociation affiché peut porter sur un
   chiffre jamais montré. (Ex-bloquant NU-F-001.)

5. **Copilote — trois failles de garde** :
   - **COP-026** : le verrou `_verdicts_coherents` vérifie la *présence* d'un champ constructibilité, pas
     sa *polarité* (`answering.py:448`) → un verdict **constructible/inconstructible inversé** par le LLM
     n'est pas attrapé (contrairement à copro/PM/PPR).
   - **COP-018** : le verdict PPR OUI/NON s'appuie sur un **substring** « zone rouge/bleue » dans
     `aleas.nature` (`outils.py:825`) → toute formulation DEAL différente retombe en « NON » silencieux
     sur un risque potentiellement rédhibitoire.
   - **COP-011** : `proprietaire_personne_morale` à `None` (PM inconnue) est traité comme « non PM »
     **ferme** (`_quali_backing:409`), alors que `None` copro = « inconnu » → une absence de donnée peut
     devenir une affirmation négative.

### 5.2 — MAJEURS (libellé qui sur-promet, ou connu-ouvert non fermé)

- **OUT-RISQUES-004 / FP-B-020** — `redhibitoire=True` **uniquement** sur PPR rouge ; EBC, DPU renforcé,
  AU fermée sont bloquants mais ne portent ni puce rouge ni tri en tête. « Aucune servitude détectée dans
  les couches ingérées » peut se lire comme un feu vert.
- **DOC-DOSSIER-051 / fiche §5** — aléas servis au **niveau maximum seul** : « fort 3 % » masque un aléa
  moyen/faible à 100 %. (NU-A-007, ouvert.)
- **DOC-DOSSIER-003 / OUT-SOLAIRE-007** — **pente moyenne seule** : une falaise ponctuelle à 43,9° est
  lissée en « modérée ». (NU-A-006, ouvert.)
- **DOC-DOSSIER-019** — « surface au sol libre » ignore CoSIA : 100 % libre faux quand BD TOPO = 0.
  (NU-A-010, atténué par la part imperméabilisée affichée mais non réconcilié.)
- **OUT-ESTIMER-012 / FP-B-001** — estimation : « précision ±X % mesurée sur les ventes 2025 » est l'écart
  médian d'une **bande**, pas une garantie par bien ; la maison peut afficher « Élevée » au-dessus d'un
  plancher donnée DVF ~27 % infranchissable. « Probabilité 1/5 de vente sous 1 an » se lit comme une
  promesse de liquidité.
- **OUT-COMMUNE-006 / NU-B-003** — deux « neuf » à 14 % d'écart (VEFA 4 878 vs neuf observé 4 275) sous la
  même étiquette ; docstring « 3 ans » ≠ code « 5 ans » (NU-E-037, ouvert).
- **OUT-COMMUNE-017** — « Horizon ZAN : N ans » + verdict couleur (dépassé/creuser/détendu) sur un budget
  interprété −50 % **non publié par le SAR** et un rythme supposé constant.
- **OUT-ZONE-005** — « niveau de vie moyen / an » servi sous le champ JSON `revenu_median_eur` : c'est une
  **moyenne** `sum(ind_snv)/sum(ind)`, pas une médiane ni un revenu. Libellé client corrigé, **nom de
  champ toujours trompeur**.
- **OUT-COMPARER-011** — prix bâti lu « tel quel » ; `DOCS-COHERENCE-1` a unifié la source mais
  l'homogénéité maison/appartement n'est pas garantie (ex-NU-A, −32 %).
- **NU-B-005** — deux dénominateurs pour « nombre de parcelles » (% PPR / % mouvement de terrain incluent
  les `cadastre_disparue` → 38 557 ; en-tête = 38 295 vivantes).
- **CRM-009** — étiquette de contact : 8 valeurs servies, **aucun sélecteur UI** ne les pose ;
  `contact_etiquette_log` = 2 lignes `compte_id` NULL → compteur Pilotage « étiquettes/semaine »
  structurellement ~0 (indicateur mensonger). (NU-F-008 ; décision Vic : laissé + documenté.)
- **CPT-009** — quota : `usage_du_jour()` existe mais **sans aucun appelant** ; le client n'apprend son
  plafond (30 exports/j) que par le 429. Aucun compteur « exports restants » affiché.
- **ML-010** — liens profonds et List-Unsubscribe des mails dépendent de `public_base_url` prod
  (fail-closed en code depuis NU-F-018, mais `readyz` local = `mail_liens.ok=false`). **Risque de
  déploiement** si la variable n'est pas posée.

### 5.3 — MINEURS & dettes

- **OM-009** — un 500 backend de l'omnibox est indistinguable d'« aucun résultat » (`Header.tsx .catch`).
- **OUT-PERMIS-006** — compteur « Autres » = `Tous − Récent − Dormant − Achevé` calculé au front ;
  invariant de partition brièvement violable si un compteur est périmé. Bouton « PLU intégral » retombe
  sur `#` en silence si le GPU est injoignable.
- **OUT-SCAN-011** — le compteur onglet Construction > le « N opérations » de l'autre onglet (inclut les
  programmes) : divergence documentée mais déroutante.
- **OUT-SECTEUR-009 / 006** — seuils d'échantillon incohérents à l'affichage (« < 8 ventes » dans la note,
  « échantillon < 5 » dans les cellules).
- **OUT-FAISA-037** — « SDP autorisée » : mot juridique fort pour une enveloppe emprise×niveaux sans
  déduction R.111-22 (dette NU-A-020). **OUT-FAISA-058/059** — pleine terre 40 % / voirie 5 m par défaut
  quand le PLU ne les sert pas, hypothèse pas toujours signalée comme telle.
- **PRJ-002** — divergence **rapport↔code** : nu-2-B listait NU-F-034 (« Archivées » féminin) ouvert, mais
  le code courant affiche « Archivés » (masculin). À retrancher du suivi.
- **PRJ-009** — « à trier » à deux sens : compteur/pagination feuillettent le vivier vif ; l'export ne voit
  que la table figée ≤ 200. Plafond dit au cadrage, pas dans le kanban.
- **PDF-SOURCES-001..004 (transversal)** — doctrine PAGE-SOURCES-1 : **aucun millésime côté client sur les
  PDF**. L'acheteur ne peut pas juger la fraîcheur d'un PLU/aléa imprimé.
- **4 blocs section legacy morts** (PDF-IDENTITE / AUTOUR / COMMUNE / BILAN) : plus câblés à aucun document
  depuis le refactor miroir, mais des tests protègent encore un rendu qui ne sort plus. Dette + risque de
  divergence silencieuse.

---

## 6. Ce qui ressort

- **L'arithmétique élémentaire est juste** (confirmé par nu-1 A/B/D). Le danger n'est quasiment jamais le
  calcul d'une cellule : c'est **l'assemblage** (une même notion servie par deux sources/runs → deux
  chiffres), le **libellé** (un mot juridique ou une précision promise que la donnée ne porte pas), et le
  **périmètre** (dénominateurs, fenêtres temporelles, seuils d'échantillon).
- **Les surfaces les plus récentes et les moins auditées — les 18 outils — concentrent le risque
  résiduel** : 435 faits, 240 jamais vérifiés, 184 sans test.
- **Deux faits vivants méritent une décision immédiate** : la fuite RGPD de Blocs fonciers
  (OUT-BLOCS-001) et le Flash qui livre le Dossier complet (DOC-FLASH-001).
- **Limite de ce registre** : établi sur le code, pas confronté à l'écran réel (app non démarrée pour ne
  pas gêner les lots G/J). Une passe Playwright sur une parcelle, une commune et chaque outil reste à
  faire pour fermer la boucle.

---

*Registre complet : [`FAITS.csv`](FAITS.csv) (1 115 lignes). Fragments sources : `docs/registre/parts/`.*
