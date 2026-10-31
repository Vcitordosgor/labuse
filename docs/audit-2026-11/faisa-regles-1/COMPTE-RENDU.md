# FAISA-REGLES-1 — le moteur n'invente jamais une règle

**Branche** `fix/faisa-regles-1` · worktree `~/Desktop/labuse-faisa` · ports 9160/6360 · base Mac `labuse`
(434 582 parcelles, run servi `q_v20`). Aucun merge, aucun accès prod. Registre lu d'abord :
`docs/audit-2026-11/nu-1/` lots A, D, E + comptes-rendus `ppr-unique-1` et `sdp-unique-1`.

**Règle gravée.** *Le moteur n'invente jamais une règle. Une règle absente ou non validée BLOQUE le calcul
concerné et le DIT ; elle n'est jamais remplacée par une valeur par défaut.* Les correctifs ci-dessous
appliquent cette doctrine à l'implantation, à l'étude de faisabilité, au Gabarit et à la hauteur/pente de
la fiche. (Périmètre tenu : rien touché en estimation/Copilote/marché — sessions MARCHE / COPILOTE en //.)

---

## Ce qui a été fait — treize règles, avant / après

### 1. RNU — plus de zone « UA » inventée (E-055)

`implantation/moteur._resoudre_zone` ne retombe plus sur `"UA"`. Il résout la zone PLU **constructible
dominante** (U/AU) via la source unique `zone_servie.zone_dominante` — là où le moteur implante réellement.
Sans aucune zone PLU opposable → `EtudeHorsPerimetre("rnu")` ; l'étude rend un payload de **refus** net
(`verdict:"Étude hors périmètre"`, `hors_perimetre:true`, 0 logement) au lieu d'un programme fictif.

| témoin RNU `97417000AT1496` (Saint-Philippe) | AVANT | APRÈS |
|---|---|---|
| zone servie | **« UA » inventée** | `null` |
| capacité | **12 logements R+5, 1 245 m² SDP** | **aucune** |
| verdict | « À compléter » / « exploitable en pré-faisabilité » | **« Étude hors périmètre »** (« commune au RNU, aucune zone PLU opposable ») |

### 2. Zone N ou A — aucun programme de logements (D-004)

Quand la parcelle n'a **aucune part constructible** (100 % A/N), `_resoudre_zone` lève
`EtudeHorsPerimetre("zone_non_constructible")` → même refus net, le motif nomme la zone.

| témoin zone N `97424000AN0072` (Cilaos) | AVANT | APRÈS |
|---|---|---|
| verdict / message | « simulation impossible » (message générique « zone 0 m² ») | **« Étude hors périmètre »** — « Zone N (famille N) non constructible : aucun programme de logements n'est chiffrable » |

**Parcelle à cheval** (`97424000AE0050`, 53 % N + 47 % Ub) : `_resoudre_zone` lit désormais la zone
**constructible** (Ub), plus la dominante N. Le moteur charge les règles de Ub et dessine sur Ub.

| à cheval `97424000AE0050` | AVANT | APRÈS |
|---|---|---|
| zone servie (en-tête) | **« N »** (dominante, non constructible) | **« Ub »** (part constructible, 47 %) |
| capacité | **24 logements R+5** (emprise 49 % non plafonnée sur un en-tête « zone N ») | **2 logements R+0** (règles Ub appliquées) |

### 3. Essai R+0 / plafond faîtage (D-005)

`_NIVEAUX` inclut désormais **1 (R+0)** : le moteur essaie un niveau unique. Une zone plafonnée sous 6 m
qui autorise un rez n'est plus « Impossible pour cause de hauteur ». Le message d'impossibilité ne cite la
hauteur que si le plafond n'autorise **même pas un rez-de-chaussée** (hauteur d'un niveau, toiture comptée).

| Uh `97411000IN0347` (égout 4,5 m) | AVANT | APRÈS |
|---|---|---|
| R+0 testé ? | **non** (grille 2→6 niveaux, le plus petit = 6 m > 4,5) | **oui** (candidats R+0 dans la trace) |
| message | « la hauteur réglementaire (**4 m**) n'autorise pas un niveau » (faux : 4,5 m, et R+0 tient) | « simulation impossible : zone trop étroite pour une barre » (cause réelle — la **géométrie**, plus la hauteur) |

(La parcelle Ub `97424000AE0050` **prouve le cas positif** : R+0 = 2 logements désormais tenus.)

### 4. Stationnement près des transports — 800 m (E-056)

Le rayon TCSP des plafonds L151-35/36 passe de **500 à 800 m** (loi n° 2025-1129 du 26/11/2025), dans le
moteur (`_plafond_l151`) **et** ses citations (`service._stationnement_regimes`). Même seuil appliqué et
affiché.

| IN0347, **617 m** d'un TCSP, collectif | AVANT (500 m) | APRÈS (800 m) |
|---|---|---|
| plafond national | **aucun** (617 > 500) | **L151-36 · 1 place/logement** — « à moins de 800 m d'un transport collectif … (loi 2025-1129) » |

### 5. Hauteur réelle mesurée selon le PLU (E-059)

La hauteur du projet n'est plus « niveaux × 3 m » brut. `controles.hauteur_projet_m(conv, regles, niveaux)`
mesure **selon la règle du PLU** : rez-de-chaussée + étages (murs) ; si la règle se mesure au **faîtage**, la
**toiture** est ajoutée (`conv.toiture_m`, faîtage = égout + toiture) — sinon un R+n passerait un plafond de
faîtage en ne comptant que ses murs. **Marge prudente dite** sur le chiffre (« hauteur estimée, toiture
comprise ») quand la toiture est ajoutée. Les hauteurs réglementaires s'affichent désormais au **format FR**
(« 4,5 m », plus « 4 m »).

### 6. Mêmes bases que le dessin pour l'emprise et la pleine terre (E-058)

L'emprise au sol et la pleine terre sont **mesurées sur la géométrie** (EPSG:2975) ; leur plafond
(CES / perméabilité) est donc calculé sur la **surface dessinée constructible** (`terrain.aire_dessin_m2`),
plus sur la contenance cadastrale (qui diffère du dessin de ~1-3 %). Numérateur et dénominateur dans le même
repère — le ratio réel ne peut plus dépasser le CES par le seul écart cadastre↔dessin. Appliqué aux contrôles
ET aux quatre grandeurs servies (`service._grandeurs`).

### 7. Recul séparatif « h/2, minimum N m » appliqué en entier (D-024, Gabarit)

`gabarit/builder` lit enfin `recul_limites_formule` : si la formule lie le recul à la hauteur (`h/2`, `h/3`…),
le recul retenu = **max(minimum, h × fraction)**, h = faîtage de la zone — jamais réduit au seul plancher.

| Um `97411000IE0241` (recul « max(4 m, h/2) », faîtage 10 m) | AVANT | APRÈS |
|---|---|---|
| recul séparatif | **4,0 m** (plancher seul) | **5,0 m** (`max(4, h/2=5)`) |
| zone d'implantation | ~309,7 m² | **260 m²** (−15 %) — écran **et** PDF (« Limites séparatives : 5,0 m ») |

### 8. « Ce qui limite » n'affirme que la contrainte qui mord (D-002)

`service._facteur_limitant_phrase` ne nomme un facteur que si `limitant` est vrai (impact mesuré > 0) ;
plus jamais « stationnement aérien » laissé en tête du tri quand 0 place n'est dessinée et ne limite rien.
Le repli front respecte la même règle (`facteurs.find(f => f.limitant)`). Témoin AE0050 : « ce qui limite :
**hauteur réglementaire** » (réel), plus « stationnement aérien ».

### 9. Parcelle à cheval — écran et PDF Gabarit (D-025, D-026)

- **Écran** : la portion servie porte le nom de la zone **constructible** (lue de `multizone.servie_sur`),
  plus la zone dominante — AE0050 affiche « dont 802 m² en **Ub** (47 %) », plus « en N ».
- **PDF** : la mise en garde « parcelle à cheval » est désormais **imprimée** (elle manquait) — contenance,
  zone constructible servie, et **part NON constructible**. Le calcul (`appliquer_note_a_cheval`) est un
  **helper partagé** par l'endpoint outil et le builder PDF → écran == PDF.

> PDF AE0050 (`pdftotext`) : « Contenance cadastrale 1720 m² — dont ~802 m² en zone Ub (parcelle à cheval). »
> « Part NON constructible (zone A/N) : ~53 % de la parcelle — hors gabarit. »

### 10. Parcelle disparue du cadastre — Gabarit (D-028)

L'outil interactif `GET /outils/gabarit/{idu}` **le dit et ne sert pas de gabarit complet** (status
`incomplete` + message + contour), comme le fait déjà le PDF (422). La requête des parcelles de remplacement
est gardée par `to_regclass` : table absente → « aucune remplaçante connue », **plus de 500** (corrige aussi
NU-A-003, racine partagée fiche + Gabarit).

### 11. Parcelle de plus d'un hectare — un résultat dans la borne (D-003, E-057)

Une grande assiette ne tombe plus en **503** : grille de fractions **grossière** (> 5 000 m²), contour de la
zone **simplifié** (0,5 m, immatériel sur > 1 ha) pour accélérer chaque dessin, et **budget de temps dur**
(`LABUSE_ETUDE_GRILLE_BUDGET_S`, défaut 22 s) qui borne la recherche INCONDITIONNELLEMENT et rend le meilleur
candidat trouvé. Une note dit que la grille a été réduite.

| `97415000CT2637` (U3c, 17 536 m²) | AVANT | APRÈS |
|---|---|---|
| étude | **ne termine pas (> 130 s) → 503 en prod** | **≈ 29 s, verdict rendu** + note « grille réduite », pas de 503 |

### 12. Fiche — badge « sources discordantes » de même nature (A-004)

`discordance_hauteur` compare désormais des hauteurs de **même nature** : la hauteur BD TOPO (haut du bâti,
≈ faîtage) doit tomber dans l'**enveloppe mesurée [égout, faîtage]** du LiDAR. Discordance seulement si BD
TOPO sort de l'enveloppe (au-dessus du faîtage **ou** sous l'égout). On n'utilise plus l'écart égout↔BD TOPO
(nature différente) pour le verdict — fin des faux positifs sur les R+n/toits en pente.

| copro `97411000HC0139` (égout 4,0 · faîtage 13,7 · BD TOPO 15,2) | AVANT | APRÈS |
|---|---|---|
| comparaison du badge | égout 4,0 ↔ BD TOPO 15,2 = **−11,2 m** (gouttière vs faîte) | faîtage 13,7 ↔ BD TOPO 15,2 = **−1,5 m** (même nature) → **cohérent, pas de badge** |

### 13. Fiche — pas de hauteur sans bâtiment, pente selon le maximum (A-005, A-006)

- **A-005** : `bati.le_bien_block` ne sert plus de hauteur « mesurée / sourcée » quand `nb_batiments = 0`
  (micro-emprise < 10 m² : bruit de sol / débord voisin) — il le **dit** (« bâti non significatif »).
  Témoin `97411000AO0753` : hauteur 4,1 m « sourcé » → **non servie** + note.
- **A-006** : `_pente_bande` tient compte de la pente **maximale** : une falaise (un pan ≥ 30°) n'est jamais
  « modérée » ; ≥ 40° ou terrassement lourd → « très forte ». Témoin falaise `97411000EY0173` (moy 14,9°,
  **max 43,9°**) : « modérée » → **« très forte »**.

---

## Recette

- **6 témoins du mandat + Gabarit + fiche**, état AVANT/APRÈS : `recette_temoins.py` →
  `recette_temoins_resultat.json`. RNU → hors périmètre (0,2 s) ; zone N → hors périmètre (0,1 s) ; Uh<6m →
  R+0 essayé ; à cheval → zone Ub, R+0 ; **CT2637 > 1 ha → 29 s, verdict rendu, pas de 503** ; falaise →
  pente « très forte ». E-056 : IN0347 (617 m) → plafond L151-36 « 800 m, loi 2025-1129 ».
- **PDF** (écran == PDF) : Gabarit `97424000AE0050` imprime la mise en garde à-cheval + part NON
  constructible ~53 % ; Gabarit `97411000IE0241` imprime « Limites séparatives : 5,0 m » (recul h/2) ;
  étude `97424000AE0050` rend 200 / zone Ub. (PDF binaires non versionnés — politique MENAGE-1 ; extraits
  `pdftotext` cités ci-dessus.)
- **Hook backend** : `pytest -m "not reel and not local and not network"` = **4 109 passés**, 82 skipped,
  **8 échecs TOUS pré-existants** (vérifiés `git stash` sur base nue : 6 `test_cascade` + `test_pente_exposition::…pas_exclusion`
  + `test_boot_verrou_1::…tables_chaudes` — fixtures/parcelles absentes de `labuse_test`, sans rapport). Les 9
  tests qui encodaient l'ancien comportement (seuil 500 m, discordance égout, pente moyenne seule, site de
  `pctPortionZone`) **mis à jour** au comportement correct : `test_remise1_stationnement_l151`,
  `test_donnees_fix1_discordance`, `test_front_chiffres2_familles`.
- **Hook front** : `tsc -b` **0 erreur** ; vitest vert (EtudeV6/Etude 24 tests).
- **Lint** : `ruff` — **0 erreur introduite** (compte identique avant/après par `git stash` ; le reste =
  dette de style pré-existante, imports locaux + `;` dans `_roles`).

## Fichiers touchés

Backend : `implantation/{moteur,controles,service,conventions,terrain}.py`, `gabarit/builder.py`,
`api/gabarit.py`, `api/app.py`, `bati.py`, `cadastre_disparue.py`, `faisabilite/hauteur_lidar.py`,
`exports/builder.py`, `exports/blocs/gabarit.py`, `config/implantation_conventions.yaml` (`toiture_m`).
Front : `outils/EtudeV6.tsx`, `outils/Gabarit.tsx`.
Tests mis à jour : `test_remise1_stationnement_l151.py`, `test_donnees_fix1_discordance.py`,
`test_front_chiffres2_familles.py`. Recette : `docs/audit-2026-11/faisa-regles-1/`.

## Ce qui n'a PAS été touché (et pourquoi)

- **Le scoring / le run figé `q_v20`** : les correctifs portent sur les surfaces d'AFFICHAGE et de CALCUL
  en direct (étude, Gabarit, fiche hauteur/pente). Aucun re-scoring.
- **Estimation « Estimer un bien », Copilote, marché** : hors périmètre (sessions MARCHE / COPILOTE en
  parallèle). Les items NU du cluster estimation (NU-D-009/010, NU-E-021/022…) ne sont pas traités ici.
- **La géométrie fine de `poser_barre` / `poser_stationnement`** (coût ~5-10 s/candidat sur une grande
  assiette) : non réécrite ; bornée par la grille réduite + le budget de temps (D-003/E-057).
- **Détection d'un égout LiDAR faux quand BD TOPO est cohérente** : A-004 privilégie l'absence de faux
  positifs (comparaison de même nature) ; un égout cassé sous une BD TOPO plausible n'est plus signalé — arbitrage assumé.
