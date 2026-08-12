# RAPPORT M57 — Fiche / tiroir Urbanisme — PHASE 0 (diagnostic)

Branche `feat/m57-urbanisme`. **PHASE 0 = diagnostic seul, aucun correctif.**
Réponses par la MESURE (app servie à :8000, API, DB, corpus règlement).

> Note de branche : la précondition demandait « sur main », mais `feat/m56-b6`
> (fiche v6 : tiroirs en cartes autonomes) n'est PAS encore mergé dans `main`.
> Brancher de `main` aurait diagnostiqué la fiche PRÉ-b6 (mauvais état). J'ai donc
> branché **depuis `feat/m56-b6`** (HEAD courant). À rebaser si Vic préfère.

Parcelles de mesure : 97418000BE0256 (Sainte-Marie, N+UC), 97418000AC0935 (SM,
A+N+UD), 97418000AE0051 (SM, N+UA+UB), + les 4 M55-O.

---

## Q1 — « Éditer la lettre de vérification de zonage (PDF) » : bug ?

**Route** : `GET /lettre-zonage/{idu}.pdf` (`src/labuse/api/lettre_zonage.py:310`).
Le lien front (`Fiche.tsx:1791`) est `/lettre-zonage/${idu}.pdf` **sans** `?source=`.

**Mesuré** : HTTP **200 `application/pdf`** sur **9 parcelles** testées
(BE0256, AP1647, AI1821, AI0030, AC0935 zone A, AE0051 zone UB, AC0149 zone N —
avec ET sans `source`). Tailles 130–585 Ko, magic `%PDF`. **AUCUN échec HTTP
reproductible.** Dernier commit sur la route = `[M31]` — **pas de régression
M54/M56**.

**Conclusion** : côté serveur, RIEN à réparer — la route génère. Le « bug à
l'écran » n'est PAS un 500 de route. Causes plausibles NON encore confirmées
(il faut l'erreur EXACTE côté mandant — statut affiché / console) :
- **Quota 429** : la route passe par `porte_export` (M23-E : 30/j Intégral,
  200/j Illimité). Un dépassement rend un 429 — le bouton « échoue » alors
  légitimement (pas un bug).
- **Bloqueur de pop-up** : `<a target="_blank">` ouvrant un PDF peut être bloqué.
- Parcelle précise non couverte par mes 9 tests.
**Demande** : l'IDU exact + l'erreur observée (HTTP/console) pour reproduire.
En l'état, je ne peux pas « réparer » ce qui ne casse pas ici.

---

## Q2 — « ⏳ En cours (non servi) : Modifications postérieures… » : conditionnel ou générique ?

**DEUX mécanismes distincts, à ne pas confondre :**

1. **La chaîne citée par le mandant** vient de `src/labuse/api/app.py:2538`
   (constructeur `plu_fraicheur`, `statut == "a_jour"`) :
   ```
   en_cours = "Modifications postérieures éventuelles non intégrées au GPU
               — à confirmer en mairie."   if note else None
   ```
   → **chaîne GÉNÉRIQUE hypothétique** (« éventuelles »), identique pour toute
   commune `a_jour` **qui a un champ `note`** dans `config/plu_millesimes`.
   Ce n'est PAS une procédure détectée, datée, sourcée.
   **Prévalence mesurée** : 24 communes configurées → 20 `a_jour`, dont
   **3 seulement ont un `note`** (INSEE 97410, 97414, 97423) → l'affichent sur
   TOUTES leurs parcelles. **Sainte-Marie (97418) a `note=null` → n'affiche RIEN**
   (vérifié : `en_cours=null` sur BE0256/AC0935/AE0051). Le mandant l'a donc vu
   sur une des 3 communes.

2. `veille_plu.fiche_en_cours(insee)` (procédure PLU active) — CONDITIONNEL RÉEL :
   ne remonte que si procédure active + sourcée, avec **type + date + source**
   (ex. INSEE 97409 → « révision générale du PLU, prescrite le 2022-06-22
   (Sourcé Sudocuh…) »). Alimente le radar procédures, PAS ce libellé.

**Conclusion** : le libellé constaté est **générique** (gated sur `note` config),
pas une procédure. Il porte un ⏳ + « En cours (non servi) » qui sur-dramatise un
« il pourrait y avoir des modifications ». → correspond à la branche Phase 1d
« si générique → reformuler en avertissement neutre, sans sablier ».

---

## Q3 — Repli « Zone hors périmètre calibré du règlement » : condition ? Sainte-Marie ?

**Chaîne** : `src/labuse/plu_reglement.py:81`. **Condition** (`resolve_reglement`) :
`calibree = bool(rules and rules.calibree and articles)` — c'est-à-dire une
référence d'articles calibrés existe pour **(zone, commune)** dans le corpus.
Le repli est **PAR TYPE DE ZONE**, pas par commune.

**Mesuré (Sainte-Marie, corpus servi)** :
| zone | calibree | articles |
|---|---|---|
| A  | **False** | 0 → « hors périmètre » |
| N  | **False** | 0 → « hors périmètre » |
| U (nu) | False | 0 |
| AU | False | 0 |
| Ub / UB | **True** | 6 |
| UC | **True** | 6 |
| UD | **True** | (via AC0935) |

**Réponse à la question du mandant** : Sainte-Marie EST calibrée (le corpus M51
a bien ses zones **constructibles** U*), mais les zones **A (agricole) et N
(naturelle) n'ont PAS d'articles calibrés** dans le corpus → elles tombent
LÉGITIMEMENT dans le repli (0 article à citer). **Ub, en revanche, EST calibrée
(6 articles) — contrairement au constat** : mesure contredit « Ub tombe dans le
repli ». Seules A et N y tombent. (Si le mandant a vu Ub en repli, il me faut
l'IDU exact — possible variante de code zone non résolue ; sur mes mesures Ub=True.)
Ce n'est donc pas un bug de calibration, mais un **libellé** qui fait lire A/N
comme un manque alors que c'est « ce type de zone n'a pas d'articles à outiller ».

---

## Q4 — Lignes de cascade à points (−10, +8…) : d'où ? doublon avec « Pourquoi ce score » ?

**Origine** : le tiroir Urbanisme rend `reglesLines.filter(l => l.result !== 'PASS')`
via `<Line>` → `<Weight>` (`Fiche.tsx:1788`), qui **affiche `line.weight`** (points
signés). Ces poids sont ceux de la **cascade LÉGENDAIRE (scoring ligne à ligne)**
servie dans `fiche.lines[].weight`.
**Mesuré** : sur BE0256/AC0935/AE0051 → **0 ligne pondérée** (rien ne s'affiche).
Sur les M55-O → OUI : brûlante `regles` 2 pondérées (« -10 SDP résiduelle 234 m² »),
nue `regles` 4 (« +15 SDP résiduelle », « +12 Gérant âgé 75 ans », « +8 26 PC »),
déclassée `regles` 3. Donc les points N'apparaissent que sur les parcelles à
signaux pondérés (pas Sainte-Marie).

**Doublon avec « Pourquoi ce score » ?** `score_v2.contributions` (le bloc verdict)
liste d'AUTRES features : `zone_plu`, `piscine`, `canopee_pct`, `tenure_bin`,
`rot_nu`… (le **modèle v2 P×C**, servi). Les poids des lignes regles sont la
**cascade legacy** (SDP, gérant, permis) — **familles différentes → PAS un doublon
littéral**, MAIS :
- même RÔLE (expliquer le score par des contributions signées) ;
- surtout, les points sont visibles dans Urbanisme **sans que l'utilisateur ait
  demandé le verdict** — ils **dévoilent le score avant la demande** (contre la
  doctrine M55-L « verdict à la demande » ; le bloc « Pourquoi ce score », lui,
  est derrière `revelerVerdict`) ;
- ils viennent de la cascade legacy, pas du modèle v2 servi → potentiellement
  **incohérents** avec le verdict affiché.
→ correspond à Phase 1c : garder le FAIT + source + date, RETIRER les points signés.

---

## Q5 — « non constructible » : quelle règle ? exceptions (STECAL, extension, agricole) ?

**Règle (front, présentation seule)** : `Fiche.tsx:1231`
`nonConstructible = /^(A(?!U)|N)/i.test(reglesZone)` — pur **préfixe de code zone**
(A hors AU, ou N). Pilote le libellé Urbanisme « non constructible » et la
Constructibilité « non calculable ».

**Back** : `cascade/layers/phase1.py` (`ZonagePluGpuLayer`) fait une exclusion A/N
**sensible au recouvrement** (A+N ≥ 90 % → HARD_EXCLUDE ; mixte → SOFT_FLAG + bonus
U/AU clippé). Mais **STECAL : « pas de traitement v1 (exception future via
plu_saint_paul.yaml) »** (phase1.py:220).

**Exceptions (STECAL, extension de l'existant, bâtiment agricole)** : **prises en
compte NULLE PART** — ni back (STECAL explicitement différé), ni front (préfixe
brut). Le libellé « non constructible » est donc **catégorique et trop absolu** :
en zone A/N, extension mesurée de l'existant, bâtiment agricole, STECAL restent
possibles réglementairement. → correspond à Phase 1f : « constructibilité très
limitée » + « i » citant les exceptions, SANS toucher le calcul.

---

## Synthèse des 5 points

| # | Nature | Constat mesuré |
|---|---|---|
| Q1 | (dit « bug ») | Route **OK 200 PDF** sur 9 parcelles ; pas de régression. Échec probable = quota 429 ou pop-up, PAS la route. **IDU/erreur exacts requis.** |
| Q2 | fond | Libellé **générique** (gated `note` config, 3 communes) ; ⏳ « En cours » sur-dramatise un hypothétique. |
| Q3 | fond | Repli **par type de zone** ; A/N non calibrées = normal ; **Ub calibrée** (contredit le constat) ; libellé trompeur. |
| Q4 | fond | Points signés = **cascade legacy** ; **dévoilent le score avant la demande** ; rôle redondant avec « Pourquoi ce score » (features distinctes). |
| Q5 | fond | « non constructible » = **préfixe zone brut** ; **STECAL/extension/agricole non traités** (back différés, front absents) — libellé trop absolu. |

---

# PHASE 1 — correctifs (après feu vert du mandant)

Commit `M57-P1 tiroir urbanisme`. Arbitrages appliqués :

**a) Scroll à l'ouverture d'un tiroir** — `RefDrawer` : à l'ouverture, l'en-tête du
tiroir remonte en HAUT de la zone visible (`scrollIntoView({block:'start'})`) après
l'animation (~220 ms), `behavior:'smooth'` ; `'auto'` (immédiat) si
`prefers-reduced-motion`. Porté par RefDrawer → vaut pour les 7 tiroirs. `scrollMarginTop:8`.

**b) Libellé traduction** — `✦ Traduire ma zone en français courant` →
`✦ Demander à l'IA de traduire le PLU` (mauve, inchangé par ailleurs).

**d) Mention « En cours » (générique)** — le diagnostic a tranché : générique.
- Back (`app.py:2538`, statut `a_jour`) : la chaîne devient
  « Des modifications postérieures au document peuvent exister — à confirmer en
  mairie. » (+ `action=None`). Une note de config = assertion d'agent, pas une source.
- Front : pour `statut === 'a_jour'`, rendu NEUTRE (txt-dim), **sans sablier ni
  « En cours (non servi) »**. Les statuts porteurs d'une procédure RÉELLE
  (`annule_partiel`, `opposabilite_en_attente`) GARDENT le cadre « En cours (non
  servi) ». Vérifié : 97414 (a_jour) → neutre ; AI1821/Le Port (annule_partiel) →
  cadre conservé.

**Q3) Repli A/N** — condition INCHANGÉE (calibration par type de zone, légitime).
Seul le libellé (`plu_reglement.py:81`) : « Le règlement des zones agricoles et
naturelles n'est pas indexé article par article dans LABUSE. Consultez le document
complet. » Vérifié servi sur zones A/N de Sainte-Marie.

**Q4) Points de cascade** — `Line` reçoit `hideWeight` ; utilisé dans le tiroir
Urbanisme → la colonne `line.weight` (points signés) n'est plus affichée. Le fait,
la source et la date restent ; le calcul et la donnée en base sont intacts. Vérifié :
« Pourquoi ce score » (bloc Analyse, `score_v2`) affiche toujours ses contributions
(features distinctes, non touchées).

**Q5) « non constructible »** — → « constructibilité très limitée » + « i » :
« Les zones A et N interdisent la construction neuve à usage d'habitation, sauf
exceptions non évaluées par LABUSE : STECAL, extension d'un bâtiment existant,
construction agricole. À vérifier au règlement. » Calcul et règle de zone inchangés.

**Q1 / point (e) — SUSPENDU** : rien à réparer côté serveur (200 partout). Bouton
NON retiré. Point inscrit au **registre `BUGS.md`** (« [M57-Q1] un export peut
échouer sans message ») pour un mandat ultérieur : tout export doit s'ouvrir ou
afficher une erreur explicite (pop-up bloquée / quota).

**Garde-fous P1** : tsc 0 · vitest 32/32 · build OK · console 0 erreur sur les 4
parcelles M55-O + BE0256 · exports générés (premium export.pdf 200 · lettre-zonage
200 · dossier 200 · one-pager 200). Backend redémarré pour servir app.py +
plu_reglement.py.

## STOP
M57 P0 (diagnostic) + P1 (correctifs a/b/d/Q3/Q4/Q5 ; e suspendu au registre)
livrés. **Branche `feat/m57-urbanisme` (de `feat/m56-b6`) NON mergée.**
