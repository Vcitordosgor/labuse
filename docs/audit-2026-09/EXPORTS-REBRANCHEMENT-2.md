# EXPORTS-REBRANCHEMENT-2 — La forme des quatre documents (compte rendu)

Branche `feat/exports-rebranchement-1`, départ `ce9a082b`. Un commit par lot, poussée.
Sessions : backend `:8075`, base locale. Thème `theme.css` (Inter, chips sourcé/dérivé/estimé/projet).
Référence : `docs/audit-2026-09/EXPORTS/maquettes-v4/` (structure, ordre des sections, lignes).

## Lot 1 — Dossier (= Flash) sur la maquette v4 (`d7f6ab46`)

- **Page de garde** : cartouche 4 champs + **bandeau des six chiffres en 3 × 3** (Surface · Zone ·
  Pente · Exposition · **Risques** · SDP restante) — « Risques » (`n_vigilances`) remplace la TFPB,
  qui descend au §7 ; chaque tuile porte `data-quoi` (V5d). Sommaire 12 entrées + légende. Modèle 3.0.
- **§1** : plan de situation (ortho IGN + contour + voisines du même propriétaire) — `_plan_situation_html`,
  le **même composant que l'Apporteur**.
- **Verdict-phrase en tête de CHAQUE section** : moteurs réels (urbanisme/potentiel/réseaux/risques)
  + synthèses **factuelles déterministes** pour les sections gris (identité/terrain/bâti/fiscalité/
  marché/quartier) — chaque nombre ancré au registre (0 fuite).
- **§10** : capacité/SDP/surélévation gardés ; **le score, la probabilité de vente et les signaux ne
  s'impriment pas** (la surface `fiche_parcelle_score` est déclarée « écran seul » — pas de section
  miroir).
- « Vérifié, sans objet » **compact** (`.sansobjet` : titre + une ligne par couche, petit corps) —
  les 34 absences dites d'AN0347 ne noient plus les lignes servies.
- **§11** encart de renvoi au Financier · **§12** numéroté « Limites et sources » (noms de sources,
  aucun millésime — doctrine PAGE-SOURCES-1).
- Longueur ≈ 9 pages. **Flash = Dossier** (pdftotext identiques, builder).

## Lot 2 — Financier (`10c17c1c`)

- **Questionnaire à UN écran** « Votre opération » : 3 questions en tête (programme logements +
  typologie · prix demandé ou vide=inconnu · régime de TVA) ; le reste = **hypothèses avancées
  pré-remplies et sourcées** (`tri: affiner`, repliées par le front). Le **régime de TVA est la
  seule question bloquante** — le prix de sortie est désormais **pré-rempli depuis le prix ancien du
  secteur (DVF)**, la donnée que le Dossier §8 nomme déjà « référence de revente du neuf reconstruit ».
- **Correction de fond A — VRD sur la SDP du projet** (plus le terrain entier) : sur la parcelle-test
  97422000BO0765, **-58 k€** (90 €/m² × SDP 650) au lieu de **-187 k€** (× terrain 2074), **écart
  128 k€** ; le biais croissait avec la taille de parcelle. Bilan au centime mis à jour (VRD 71 460,
  portage 151 971,6, charge −338 017,07 sur le programme de recette).
- **Correction de fond B — prix d'achat historique (DVF)** imprimé en **§6 « Face au prix demandé »
  à titre d'information, hors calcul** (chip sourcé) ; absent si la parcelle n'a jamais muté seule.
- **Stationnement** : aucun référentiel public de coût par place dans le socle → **aucun défaut**
  (reste « non chiffré », saisie), comme demandé.

## Lot 3 — Apporteur v4 (`fb167e25`)

10 sections numérotées : §1 coup d'œil · **§2 Vous (nouveau — l'apporteur d'abord)** · §3 Qui décide
(+ âge/situation, agent ou notaire) · §4 La vente (**voisines déplacées ici**, + dation/échange) ·
§5 Bâti et occupation (+ activité sur place) · **§6 Le terrain, vu sur place** · §7 À demander au
propriétaire (renommé, + notaire attitré) · §8 Voisinage et mairie (allégé) · §9 Photos · §10 Votre
retour (impression, prochaine étape, chance d'aboutir).

**§6 = questions d'observation conditionnelles aux couches** (mêmes moteurs que le Dossier) : traces
d'eau **si** aléa inondation/ravine/zone humide ; remblais/odeurs **si** sol pollué / ICPE à proximité.
La ligne HTA/HTB (< 50 m) est **omise** faute de couche fiable dans le socle (dit). Retiré : la liste
détaillée PPR/pourcentages. Absents : capacité, SDP, charge foncière, score.

## Lot 4 — Pré-dossier PC (`b5c6326e` + `02276613`)

- **CERFA 13409*17** (collectif) téléchargé de service-public.gouv.fr et **vendorisé** à côté du 13406.
  Il partage les mêmes champs T2* de terrain → le préremplissage marche sur les deux. Le scénario
  choisit le formulaire (maison → 13406, collectif ≥ 3 logements → 13409) ; le ZIP nomme le vrai millésime.
- **Contrôle de millésime en ligne** (`cerfa_millesime_perime`) : lit le millésime courant sur la fiche
  signalétique et le compare au fichier vendorisé ; un millésime **périmé bloque la pièce** (pack sans
  formulaire, dit) plutôt que de servir un CERFA refusé en téléprocédure. **Best-effort et non fatal**
  (réseau coupé/SSL → sert le fichier vérifié), **mis en cache par process** (une lecture au plus par
  CERFA — pas de clignotement d'une génération à l'autre). Rouvre, borné, l'ancien « contrôle écarté ».

## Preuves

- **Écran = PDF, ligne à ligne** (`captures/rebranchement2/*-preuve.txt`) :
  **AN0347 34 identiques · 34 absences dites · 5 non câblées · 0 écart** ;
  **97422000BO0765 (parcelle simple) 37 · 31 · 5 · 0 écart**.
- **Score, probabilité, signaux absents** du Dossier (vérifié : « tier »/« Écartée »/« Priorité »
  n'apparaissent pas — seul « quartier » matche).
- **pdftotext diff Dossier/Flash = vide** ×4 témoins (recette).
- **Pré-dossier : zonage identique au Dossier** (AN0347 : « N 100 % » = §2 « Zone N ») ; CERFA-13406-17
  prérempli présent dans les 2 packs (après mise en cache du contrôle millésime).
- **Apporteur §6** : questions d'eau/pollution imprimées seulement si la couche touche (test dédié).
- **0 fuite / 0 libellé hors registre** sur Dossier ET Apporteur (2 parcelles) ; le crible de
  provenance voit désormais les numéros de section comme structure (`_texte_de` : blocs → sauts de ligne).
- **Recette rejouée** (`scripts/recette_exports1.py`, 4 témoins) : **VERTE** — Flash = Dossier ×4.

## Portes

- **tsc -b vert** · **vitest** questionnaire vert.
- **pytest tests/ complet** : **3126 passed**, **9 failed** dont **5 pré-existants sur main**
  (`circuit2_lot16`, `circuit2_lot5`, `retours11f4` ×2, `garanties::test_g4` — vérifiés labuse-merge
  en REBRANCHEMENT-1) et **4 mis au niveau des changements de ce mandat** (questionnaire à 1 écran :
  `exports2_lot4` ×2, `recette11` ×2 — rejoués verts). Tests suite `test_registre`/`verrous` : 123
  passed, seul `test_g4` rouge (pré-existant).
- **`labuse circuit verrous -w G8`** : avertissement **non bloquant** — sources vitrine sans sonde
  amont (« agent à 0 € ») + rappels manuels échus : état d'exploitation pré-existant, indépendant de
  la branche (gestes Vic : débloquer le budget agent ou pointer les rappels).

## Notes

- Le CERFA 13409 (1,5 Mo) est vendorisé (`git add -f`, comme le 13406 — `data/*` est gitignoré).
- Le front (Fiche.tsx) reste codé en dur ; les documents PDF, eux, sont 100 % déclarés (miroir).
- Nouveaux tests : `tests/test_rebranchement2_cerfa.py` (5).
