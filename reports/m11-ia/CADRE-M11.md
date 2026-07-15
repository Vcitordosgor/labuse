# M11 — DOCUMENT-CADRE : la section IA de LABUSE

**Statut** : VALIDÉ (2026-07-15). Conception seule, aucun dev. Se découpe ensuite en mandats de dev séparés (un par surface).
**Fondé sur** : `reports/m11-ia/AUDIT-EXISTANT-IA.md` (état des lieux constaté, appels IA réels).
**Validation** : corrections CC intégrées et vérifiées contre le code réel (voir Journal des corrections en fin).
**Principe non négociable** : l'IA **orchestre** les moteurs existants ; elle ne **génère jamais un fait**. Chaque chiffre, chaque règle vient d'un moteur traçable (scoring, cascade, faisabilité, PLU calibré, M-VIA). C'est ce qui sépare LABUSE de KelFoncier — une IA qui invente une règle PLU tue ce positionnement.

---

## 0. Socle commun (à construire AVANT les surfaces)

L'audit a montré **3-4 moteurs IA parallèles** qui font des choses proches sans partager de code : `ia.py` (Copilote : search/entretien/synthese/pourquoi), `assistant.py` (fiche `/explain`), `ai/nl_segments.py`, `ai/agent.py` (legacy). Triple duplication de la clé, du client Anthropic, des stubs, des garde-fous. **Décision validée : on unifie d'abord.** Toute évolution future (garde-fou, changement de modèle, budget) se fait alors à un seul endroit.

### 0.1 Ce que le socle unifié fournit à toutes les surfaces
- **Un seul client IA** (provider Anthropic, gestion de clé, choix haiku/sonnet, repli stub flaggé) — plus de duplication.
- **Un contrat de grounding unique** : toute donnée passée au modèle est étiquetée `SOURCÉ` / `ESTIMÉ` / `ABSENT` (le pattern de `/explain`, qui marche déjà et produit du groundé de qualité). Généralisé à **toutes** les surfaces.
- **La liste blanche obligatoire** : le modèle ne reçoit QUE les champs explicitement autorisés pour la tâche, jamais la fiche entière. (C'est précisément l'erreur des 2 endpoints cassés — voir §1.)
- **La validation de sortie** : avant de renvoyer une réponse en prose au client, on vérifie qu'elle ne contient pas d'affirmation non ancrée dans les données fournies. Aujourd'hui absente sur la prose (`synthese`/`pourquoi`) — une hallucination y passerait. Le socle la rend systématique.
- **Le cache par `(idu, run_label)`** : une réponse IA sur une parcelle est identique tant que le run servi ne change pas → on la stocke, on ne rappelle pas le modèle. Réutilise le pattern `parcel_enrichment` déjà présent. **C'est ce qui rend l'IA de fiche économiquement viable** (voir §0.3).

### 0.2 Doctrine anti-hallucination (déjà partiellement en place — à durcir et généraliser)
| Garde-fou | Existe aujourd'hui ? | Cible M11 |
|---|---|---|
| Schéma JSON forcé + validation serveur | Oui (search, entretien) | Généralisé |
| Liste blanche des champs envoyés au modèle | Oui (`/explain`) — **non** (synthese/pourquoi) | Obligatoire partout |
| Provenance SOURCÉ / ESTIMÉ / ABSENT | Oui (`/explain`) | Généralisé |
| Refus propre du hors-scope | Oui (search → `out_of_scope`) | Généralisé |
| Validation de la prose en sortie | **Non — y compris `/explain`** | À créer (socle) — **impératif avant A** |
| L'IA n'accède jamais à la base / ne calcule aucun score | Oui (doctrine affichée, respectée) | Maintenu |

> **L'ordre "socle 0 AVANT A" n'est pas un confort, c'est un impératif** : même `/explain` (le meilleur existant) a la liste blanche en *entrée* mais **aucune validation de la prose en sortie**. Rebrancher/reconstruire la Surface A sans cette validation = un grounding à moitié (l'IA pourrait halluciner dans sa réponse finale). Donc **pas de Surface A livrée sans la validation de sortie du §0.** À écrire noir sur blanc dans le mandat socle.

### 0.3 Budget & performance (contrainte de conception, pas une option)
- Aujourd'hui : aucun cache, appels en lazy-load (sur clic, pas auto). ~944 appels / ~2,96 € sur 7 jours. Le sonnet (synthèse/pourquoi) = 46 % du coût.
- **Chiffre à ne jamais oublier** : IA appelée **automatiquement** à chaque ouverture de fiche ≈ **176 €/mois** à 300 fiches/jour. → **Règle de conception : l'IA de fiche reste sur clic, jamais automatique**, et toute réponse est mise en cache (voir §1.3 pour la clé réelle d'une barre conversationnelle).

---

## 1. Surface A — Recherche par fiche *(priorité 1 — vrai build, pas un simple rebranchement)*

**Le geste** : dans chaque fiche parcelle, une **barre mise en valeur en haut** ("Demandez à l'IA : expliquez un point, un acronyme, ou trouvez une donnée"). Le client tape une question sur CETTE parcelle, l'IA répond en lisant ce que les moteurs ont déjà produit pour elle.

**Exemples de questions cibles** :
- "C'est raccordé à l'assainissement ?" → lit le bloc viabilisation M-VIA.
- "Ça veut dire quoi zone U4c ?" → explique l'acronyme + lie au règlement PLU (deep-link existant).
- "Pourquoi elle est écartée ?" → lit les verdicts cascade (motif exact).
- "Y a-t-il un risque inondation ?" → lit le bloc risques.
- "Combien je peux construire dessus ?" → lit la SDP résiduelle (potentiel de transformation).

### 1.1 Ce que l'audit a trouvé : un bon PATTERN à réutiliser, pas un fil à rebrancher
- `/parcels/{idu}/explain` (`assistant.py`) produit des réponses **groundées, sourcées** (labels SOURCÉ/ESTIMÉ) par **liste blanche** — c'est le bon *pattern*. **MAIS** : il ne prend **aucune question** (il crache un rapport **figé en 5 blocs**), et il lit la fiche **legacy** (`_build_fiche`), pas la premium. Donc la Surface A **n'est PAS "re-pointer un fil"** — c'est **réutiliser le pattern de grounding et construire un vrai endpoint conversationnel**. L'ampleur "petit-moyen" tient, mais ce n'est pas un quick win : c'est un build.
- Les 2 boutons de fiche actuels (`/ia/synthese`, `/ia/pourquoi`) **renvoient HTTP 500** (`Decimal not JSON serializable`, `ia.py:684` — ils sérialisent la fiche ENTIÈRE, sans liste blanche). Le bug est **réel** mais **pas encore vu par des clients** : `usage_compteurs` = 2 sujets sur 30 jours = QA interne, zéro trafic client. → **Pas d'urgence ; le fix (une ligne, `default=str`) est inclus au socle**, pas traité en patch séparé.

### 1.1bis Décision de périmètre : quelle fiche alimente l'IA ? *(à trancher au mandat A)*
Les deux fiches n'ont **pas les mêmes données** (catalogue §8 de l'audit) : la **premium** (`_q_v2_fiche`) porte ICD, score P, potentiel de transformation, M-VIA ; la **legacy** (`_build_fiche`) porte permis, faisabilité, PLH. `/explain` lit la legacy ; le panneau affiche la premium. **Ce que l'IA de fiche pourra répondre dépend de ce choix.** Reco : viser la **premium** (c'est ce que le client voit à l'écran), quitte à y agréger les champs legacy utiles (faisabilité).

### 1.2 Ce que fait la Surface A (3 choses, dans cet ordre)
1. **Construire un endpoint conversationnel** qui réutilise le pattern de grounding par liste blanche de `/explain`, mais accepte une **question libre** du client (pas un rapport figé) et lit la fiche retenue (§1.1bis). Ce nouvel endpoint remplace les 2 boutons cassés → le 500 disparaît par la même occasion.
2. **Passer du rapport pré-formaté à la réponse ciblée** : le client pose SA question, l'IA répond sur les seuls champs autorisés, avec provenance.
3. **Mettre en valeur** : la barre en haut de fiche (voir §1.4, maquette validée).

### 1.3 Garde-fous & coût spécifiques
- Liste blanche = uniquement les champs de LA fiche. L'IA ne peut pas répondre sur une autre parcelle ni inventer.
- Si la donnée demandée est absente → réponse "cette information n'est pas disponible pour cette parcelle" (label `ABSENT`), jamais une invention. **Requiert la validation de sortie du socle** (§0.2 : elle manque même à `/explain`).
- **Cache** : une barre **conversationnelle** ne se cache PAS par `(idu, run)` — deux questions distinctes sur la même parcelle = deux réponses. Clé réelle = `(idu, run, question normalisée)`. Le "premier paie, les suivants lisent" ne vaut que pour les **questions répétées** (les mêmes acronymes reviendront). → **Le budget d'une barre libre est structurellement plus élevé qu'un bouton figé** : à cadrer par un **quota par sujet** + cache des questions fréquentes. Le §0.3 (basé sur l'ancien bouton) est un plancher, pas le coût réel.
- Sur clic / sur saisie, jamais automatique à l'ouverture.

### 1.4 La barre — spécification visuelle (maquette validée en session)
La barre est **mise en valeur** en haut de fiche, pas noyée. Éléments :
- **Accent premium** : bordure violette (`#B497F0`, ton accent projet) → signale "feature premium", cohérent avec le tier Pro/Organisation.
- **Champ libre** : placeholder "Expliquez un point, un acronyme, ou trouvez une donnée…" + raccourci Entrée.
- **Chips de suggestion cliquables** (amorces contextuelles à la parcelle) : "Ça veut dire quoi U4c ?", "Combien je peux construire ?", "Risque inondation ?" — pré-remplissent la question, réduisent la friction.
- **Réponses avec provenance visible** — cœur du design : chaque réponse porte une étiquette de source lisible par le client :
  - `Sourcé · règlement PLU` (vert) + lien direct vers l'article,
  - `Estimé` (ambre) pour un calcul dérivé (ex. SDP),
  - `Absent · aucune donnée` (gris) quand l'info n'existe pas → l'IA répond "cette information n'est pas disponible pour cette parcelle", **jamais une invention**.
- **Effet business** : l'anti-hallucination devient un **argument de confiance visible** ("l'IA de LABUSE cite ses sources et dit quand elle ne sait pas"), pas juste une protection interne. Vendable face à KelFoncier (voir benchmark).

**Pourquoi A en premier** : le pattern existe, le bug est réel, le périmètre est borné (une fiche = faible risque d'hallucination), et ça met de l'IA premium **visible** dans le produit vite. Meilleur ratio valeur/risque des 4 surfaces.

---

## 1bis. Benchmark — ce qu'une IA foncière de référence doit savoir faire

L'IA de LABUSE ne se juge pas dans l'absolu mais **face au marché**. KelFoncier (l'incumbent) et les portails fonciers classiques ont des faiblesses connues : calculette de constructibilité cassée, couches de risque décoratives jamais appliquées au calcul, données périmées sans mention. Une IA plaquée dessus hériterait de ces défauts.

| Capacité attendue d'une IA foncière | Incumbent typique | LABUSE (cible M11) | Avantage |
|---|---|---|---|
| Expliquer une règle PLU en langage clair | Renvoie le PDF brut, pas d'explication | Explique + deep-link article (existe déjà) | ✅ Fort |
| Dire d'où vient chaque affirmation | Aucune provenance | Étiquette Sourcé/Estimé/Absent | ✅ **Différenciateur** |
| Admettre l'absence d'une donnée | Invente ou reste vague | "Non disponible pour cette parcelle" | ✅ **Confiance** |
| Chiffrer une faisabilité sans halluciner | Calculette parfois fausse | Chiffrage 100 % déterministe (IA formule, ne calcule pas) ; calibrage complet Saint-Paul, prudent ailleurs | ✅ Fort (méthode) / couverture partielle |
| Répondre à une question agrégée ("quelle commune…") | Rarement | Cible surface B (moteur, pas invention) | ⚠️ À construire |
| Alerter proactivement sur un changement | Non / newsletter générique | Cible surface D (diff de runs réels) | ⚠️ À construire |
| Accompagner un montage de projet | Non | Cible surface C (copilote + faisabilité) | ⚠️ À construire |

**Lecture** : les 3 premières lignes (explication sourcée, provenance, aveu d'absence) sont **déjà à portée** et constituent le **différenciateur immédiat** — ce que la Surface A livre. Fil conducteur : **LABUSE gagne par l'honnêteté traçable, pas par le volume de features.** Une IA qui dit "je ne sais pas, mais voici la source de ce que je sais" bat une IA qui répond à tout en se trompant parfois — surtout pour un promoteur qui engage des centaines de milliers d'euros sur la réponse.

---

## 2. Surface B — Recherche simple *(page IA)*

**Aujourd'hui** : un **traducteur langage naturel → filtres**, pas un chatbot. "brûlantes à Saint-Pierre" → `{tier: brulante, commune: Saint-Pierre}`. Fonctionne (haiku, temp 0, "n'invente jamais un filtre"). Refuse proprement les questions analytiques (`out_of_scope`).

**Les 2 limites constatées (appels réels)** :
1. **Il ne sait que filtrer.** "Quelle commune a le plus de brûlantes ?" → hors-scope, alors que la donnée existe.
2. **Il droppe silencieusement** ce qu'il ne sait pas traduire : "propriétaire personne morale" a été **ignoré sans le dire**. Le client croit son critère appliqué — il ne l'est pas. **Faux positif de confiance, à corriger en priorité.**

**Cible M11** :
- Passer de "filtre" à "**filtre ET répond**" : les questions agrégées reçoivent une réponse chiffrée, calculée par un moteur (pas inventée), formulée en clair.
- **Transparence du drop** : tout critère non pris en compte est signalé explicitement ("je n'ai pas su filtrer sur *propriétaire personne morale*"), jamais avalé en silence.
- Garde-fous : le socle (grounding, refus propre, validation de sortie).

---

## 3. Surface C — Création de projet accompagnée

**Aujourd'hui (base solide à enrichir, pas à refaire)** :
- Vrai **objet Projet persistant** (table `projets`, 6 lignes réelles), lié au CRM, exportable en PDF.
- **Entretien de cadrage** conversationnel (haiku, schéma fermé) : l'IA dialogue pour comprendre le projet.
- **Tout le chiffrage est déterministe** (formule M22, moteurs SQL, faisabilité) — l'IA ne calcule rien. **Le bon partage** : l'IA dialogue, le moteur chiffre.

**Cible M11** :
- Accompagnement du montage : l'IA orchestre faisabilité + PLU + contraintes en un parcours guidé.
- Restitution en langage clair d'un chiffrage déterministe (le client lit une explication sourcée, pas des colonnes).
- **Décision actée : le PETIT d'abord.** Phase 1 = l'IA **explique en clair un chiffrage qui existe déjà** (faisabilité, charge foncière) — mandat moyen, bon ratio, aucun risque nouveau. Phase 2 (plus tard) = l'assistant de montage multi-étapes complet.

---

## 4. Surface D — Alertes proactives

**Aujourd'hui** :
- `detect-events` génère **4 types d'événements** (bascule de tier, BODACC, veille succession, permis à proximité) — **mais tout est en démo** (`q_v2_demo`), aucun diff de 2 vrais runs.
- **NotifBell** (la cloche) existe, en polling 60 s. Digest email (SMTP) **non branché**.
- Ce qu'un client suit existe **déjà** : `watched_parcels` (liste) **et** `saved_searches` (secteur/veille). Le vrai manque = les **comptes utilisateurs** (M7).

> **⚠️ La bascule M8 est le PIRE premier event, pas le déclencheur.** Le diff q_v5→q_v6 = **~11 718 bascules ▼** (atterrissage ANO-1, quasi toutes vers *écartée*) + 58 ▲. Brancher les alertes là-dessus = **11 000 notifications "parcelle descendue"** = bruit inexploitable, le client désactive tout. **M8 est le cas à EXCLURE.** Premier diff exploitable = **q_v6 → le run suivant** (mouvements organiques), ou un filtre qui **ignore les descentes de recalibration**.

**Nature de la surface** : ce n'est **pas** du conversationnel, c'est du **monitoring**. La part "IA" est faible — l'essentiel est un **système de règles** (diff de runs). L'IA sert à **formuler** l'alerte en clair.

**Cible M11** :
- **Activer sur du réel, mais sur le BON diff** : jamais q_v5→q_v6 ; le run *suivant* q_v6, ou avec un filtre anti-descentes.
- Brancher le digest email (canal proactif — la cloche est passive).
- Distinguer **règle** (déclenchement, déterministe) de **IA** (formulation, sous grounding).
- Dépendance forte : les **comptes utilisateurs** (M7).

---

## 5. Priorisation & séquençage

| Ordre | Surface | Pourquoi ici | Ampleur |
|---|---|---|---|
| **0** | **Socle unifié** (§0) | Prérequis de tout ; solde la dette des 3-4 moteurs ; **contient la validation de sortie, impérative avant A** | Moyen |
| **1** | **A — Recherche fiche** | Pattern de grounding existe ; périmètre borné = faible risque. Vrai build (endpoint conversationnel), pas un rebranchement | Petit-moyen |
| **2** | **B — Recherche simple** | Corrige un faux positif de confiance (drop silencieux), élargit l'existant | Moyen |
| **3** | **D — Alertes** | Surtout des règles ; **dépend des comptes (M7)** et d'un diff propre (jamais M8) | Moyen |
| **4** | **C — Création projet** | Base solide ; on livre d'abord le **petit** (explication d'un chiffrage), l'assistant multi-étapes ensuite | Petit puis Grand |

**Dépendances** : le socle (0) — dont la **validation de sortie** — conditionne A/B/C/D et est **impératif avant A**. A et B s'enchaînent. **D dépend de M7 (comptes)** et d'un diff non-bruité. C se livre en deux temps.

---

## 6. Décisions

### Actées
- ✅ **IA = argument de vente**. Feature premium (tier Pro/Organisation 490 €). Conséquence : barre mise en valeur + provenance visible (maquette §1.4), barre de qualité haute.
- ✅ **Surface C = le petit d'abord** : explication d'un chiffrage existant en phase 1, assistant multi-étapes en phase 2.
- ✅ **Modèle = routeur haiku/sonnet par type de question** : haiku pour l'extraction/le factuel (acronyme, donnée simple), sonnet réservé aux réponses de raisonnement (faisabilité expliquée).
- ✅ **Bug des 2 boutons → corrigé DANS le socle** (pas de patch séparé) : trafic QA-interne (2 sujets/30 j), aucune urgence ; fix = une ligne (`default=str`).
- ✅ **Surface D dépend des comptes (M7)** et ne se déclenche **jamais** sur le diff M8 (bruit).

### Restantes (à trancher avant les mandats concernés, pas bloquantes pour A)
1. **Quota IA par sujet** (Surface A) : combien de questions/fiche avant plafond ? À fixer au mandat A.
2. **Fiche premium vs legacy pour l'IA** (§1.1bis) : reco = premium + agrégation des champs legacy utiles. À confirmer au mandat A.
3. **Filtre anti-bruit des alertes** (Surface D) : ignorer les descentes de recalibration, ou n'alerter que sur les montées ? À trancher au mandat D (après M7).

---

## Résumé en une phrase
M11 unifie d'abord les moteurs IA épars en un socle grounded — dont une **validation de sortie qui manque partout aujourd'hui, y compris à `/explain`** (impératif avant tout) — puis construit 4 surfaces dessus, en commençant par la recherche de fiche : un **vrai endpoint conversationnel** qui réutilise le pattern de grounding existant (pas un simple rebranchement), corrige au passage un bug encore confiné au QA interne, et matérialise le différenciateur commercial de LABUSE — **une IA qui cite ses sources et admet ce qu'elle ignore.**

---

## Journal des corrections (validation CC contre le code réel)
1. Surface A n'est **pas** un rebranchement : `/explain` ne prend aucune question et lit la fiche legacy → vrai build d'un endpoint conversationnel. "Quick win" retiré.
2. Cache `(idu, run)` invalide pour une barre libre → `(idu, run, question)` ; budget structurellement plus élevé, à borner par quota.
3. **Bascule M8 = le PIRE premier event** (11 718 descentes = bruit), pas le déclencheur des alertes. Cas à exclure.
4. La **validation de sortie manque même à `/explain`** → socle avant A = impératif, pas confort.
5. Fiche premium vs legacy = décision de périmètre à figer (données différentes).
6. Bug des 2 boutons = **QA interne, pas de trafic client** → inclus au socle, pas d'urgence.
