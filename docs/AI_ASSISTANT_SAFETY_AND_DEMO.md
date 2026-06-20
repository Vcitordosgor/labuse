# Assistant IA « Expliquer cette parcelle » — sécurité, anti-hallucination & démo

> But : faire de l'assistant un élément **premium, fiable et strictement basé sur les données**.
> L'IA n'invente **jamais** une donnée absente. Deux modes : **synthèse règles** (déterministe, sans
> clé) et **synthèse IA enrichie** (modèle Anthropic, sur activation). Aucune vraie clé n'est commitée.

---

## 1. Fonctionnement

L'assistant vit dans deux fichiers :

| Élément | Fichier | Rôle |
|---|---|---|
| Liste blanche des faits | `src/labuse/api/assistant.py` › `assistant_facts()` | extrait UNIQUEMENT les valeurs déjà calculées/sourcées de la fiche |
| Prompt système strict | `assistant.py` › `SYSTEM` | impose structure 5 blocs + provenance + refus de conclure |
| Synthèse règles (sans clé) | `assistant.py` › `rules_summary()` | 5 blocs déterministes dérivés des seuls faits — aucun LLM |
| Appel modèle | `assistant.py` › `explain_parcel()` | POST API Anthropic, dégrade proprement |
| Statut clé | `GET /assistant/status` | `{"configured": true/false}` → pilote l'UI |
| Explication | `GET /parcels/{idu}/explain` | renvoie la prose IA **ou** la synthèse règles |
| Payload fiche | `GET /parcels/{idu}` › `assistant_rules` | la synthèse règles est jointe à la fiche (rendu immédiat) |
| Rendu | `web/app.js` › `renderAssistant()` | synthèse règles toujours visible + bouton « Enrichir avec l'IA » si clé |

**Flux :**
1. À l'ouverture de la fiche, `assistant_rules` (synthèse règles) est **déjà dans le payload** → rendu
   immédiat, premium, sans appel réseau.
2. Si la clé est présente, un bouton **« Enrichir avec l'IA »** appelle `/explain` → le modèle rédige
   une prose à partir des **seuls** `assistant_facts` (liste blanche).
3. Sans clé / en cas d'erreur / de timeout → la synthèse règles reste affichée, plus un message clair.
   **Jamais de 500, jamais de bloc « cassé ».**

### Données envoyées au modèle (liste blanche `assistant_facts`)
`parcelle` (idu, commune, surface) · `verdict` (statut, scores, micro-opportunité, motif de
déclassement) · `faisabilite` (zone PLU, constructible, capacité, niveaux, hauteur, volume) ·
`bilan_promoteur` (verdict, charge foncière, fiabilité) · `occupation_bati` (label, code, ratio %) ·
`contraintes_et_signaux` (HARD_EXCLUDE / SOFT_FLAG / POSITIVE uniquement) · `completude` (sources
ayant répondu / muettes) · `niveaux_fiabilite` (carte sourcé / estimé / absent) · `resume_metier`.
**Rien d'autre** n'est transmis (le centroïde, par ex., est exclu).

---

## 2. Variables d'environnement

| Variable | Obligatoire | Effet |
|---|---|---|
| `ANTHROPIC_API_KEY` | pour la synthèse IA | active le bouton « Enrichir avec l'IA ». **Jamais commitée.** Absente → mode règles. |
| `LABUSE_ASSISTANT_MODEL` | non | surcharge le modèle (défaut `claude-sonnet-4-6`). |

La clé est lue à l'exécution via `os.environ` — **jamais** écrite dans le code, un fichier suivi par
git, un commit, un log ou un artefact. `GET /assistant/status` ne renvoie qu'un booléen, jamais la clé.

---

## 3. Règles anti-hallucination (imposées par le prompt ET par le code)

1. **Source unique** : le modèle ne raisonne que sur le JSON `assistant_facts`. La synthèse règles ne
   fait que **reformuler** ces faits.
2. **Jamais d'invention** : aucun prix, propriétaire, servitude, règlement, risque ou contrainte qui ne
   figure pas explicitement dans les données.
3. **Provenance imposée** : chaque information est qualifiée **sourcé** (prix DVF, zonage, occupation
   bâtie), **estimé** (capacité constructible, coûts/charge foncière) ou **absent / à vérifier** (champ
   nul, source muette). S'appuie sur `niveaux_fiabilite`.
4. **Jamais « constructible » certain** : toujours « zone X, capacité ESTIMÉE », renvoi à la vérif PLU/CU.
5. **Refus de conclure** si données insuffisantes (complétude faible, bilan non fiable, sources muettes).
6. **Absence ≠ négatif** : une donnée manquante n'est jamais transformée en « pas de risque ».
7. **Mentions obligatoires** en fin de réponse : niveau de **Fiabilité** + liste des **Données manquantes**.
8. **Aucune garantie** réglementaire, de propriété ni de rentabilité.

Verrouillé par `tests/test_assistant.py` (liste blanche, prompt, synthèse règles sur 7 cas).

---

## 4. Exemples de réponses attendues

### 4.a Synthèse RÈGLES (sans clé) — vraie micro-opportunité (97415000DE1325)
```
Potentiel — Opportunité (signal favorable, données suffisantes) · score 78/100 · micro-opportunité
  (≤ 500 m²). Zone U2c, capacité ESTIMÉE ~137 m² de plancher.
Contraintes — Aucune contrainte bloquante dans les données disponibles (une donnée manquante n'est
  pas une absence de risque).
Bâti / libre — Aucun bâti significatif détecté (0 % bâti, BD TOPO).
Économie indicative — Charge foncière INDICATIVE ~182 k€ (prix de sortie fiable ; coûts estimés).
Recommandation — Vérifier le PLU/CU, croiser PPR/SAR, puis identifier le propriétaire avant de
  démarcher. Petite parcelle : étudier l'assemblage avec les voisines.
Fiabilité — complétude des données forte (92/100).
Données manquantes — Fichiers fonciers (Cerema)
```

### 4.b Cas « à creuser » avec données minces
```
Potentiel — À creuser (signal à confirmer ou données incomplètes) · score 67/100. Zone U2c, capacité ESTIMÉE…
Contraintes — Aucune contrainte bloquante dans les données disponibles…
Bâti / libre — Occupation non vérifiée (couche bâtiments non disponible).
Économie indicative — Charge foncière INDICATIVE ~80 k€ (prix de sortie fragile — ordre de grandeur ; coûts estimés).
Recommandation — Compléter les données manquantes (risques, pente, propriétaire) avant d'investir du temps.
Fiabilité — complétude des données faible (35/100). Bilan : prix de sortie fragile.
Données manquantes — PPR, pente
```

### 4.c Cas écarté (contrainte forte)
```
Contraintes — Déclassement : PPR zone rouge.
Recommandation — Ne pas prospecter : contrainte bloquante identifiée.
```

### 4.d Synthèse IA enrichie (avec clé) — comportement attendu
Même structure (5 blocs + Fiabilité + Données manquantes), ton expert, prose plus fluide, **sans
aucun chiffre ni fait absent du JSON**. Si les données sont trop minces, le modèle doit écrire
explicitement « données insuffisantes pour conclure » plutôt qu'inventer.

---

## 5. Procédure d'activation de la clé

1. Obtenir une clé API Anthropic (console Anthropic).
2. La poser en variable d'environnement **côté serveur uniquement** (jamais dans git) :
   - VPS / systemd : `Environment=ANTHROPIC_API_KEY=sk-ant-…` dans l'unit (ou un `EnvironmentFile=`
     hors dépôt, permissions 600), puis `systemctl restart labuse`.
   - Local / test : `export ANTHROPIC_API_KEY=sk-ant-…` avant `labuse api`.
   - (Optionnel) `export LABUSE_ASSISTANT_MODEL=claude-sonnet-4-6`.
3. Vérifier : `GET /assistant/status` → `{"configured": true}` ; le bouton « Enrichir avec l'IA »
   apparaît sur la fiche.
4. **Recette obligatoire** : ouvrir 2–3 fiches contrastées (opportunité, à creuser, écartée) et
   vérifier que la prose ne contient **aucun** chiffre/fait absent du JSON et qu'elle cite la fiabilité
   et les données manquantes. Comparer avec la synthèse règles (même esprit, prose enrichie).

---

## 6. Risques

| Risque | Mitigation en place |
|---|---|
| Hallucination (donnée inventée) | liste blanche stricte + prompt strict + recette obligatoire ; la synthèse règles, elle, ne peut pas halluciner (déterministe) |
| Fuite de clé | clé en env serveur uniquement, jamais commitée, jamais renvoyée par l'API, `.gitignore` standard |
| Coût API | l'IA n'est appelée **que sur clic** (« Enrichir »), jamais en masse ni au chargement de la fiche |
| Panne réseau / timeout | dégradation propre → synthèse règles + message, jamais de 500 |
| Sur-promesse en démo | provenance affichée (sourcé/estimé/absent), bilan toujours « indicatif », pas de garantie |
| Donnée absente lue comme négative | règle explicite « absence ≠ pas de risque » (prompt + synthèse règles) |

---

## 7. Checklist avant démo promoteur

- [ ] `ANTHROPIC_API_KEY` posée côté serveur (ou démo assumée en **mode règles**, déjà premium).
- [ ] `GET /assistant/status` cohérent avec l'état voulu.
- [ ] La synthèse (règles ou IA) s'affiche **immédiatement** à l'ouverture de la fiche, sans bloc « cassé ».
- [ ] Sur une opportunité : 5 blocs présents, capacité **ESTIMÉE**, charge foncière **INDICATIVE**.
- [ ] Sur une parcelle à données minces : la réponse **refuse de conclure** et liste les données manquantes.
- [ ] Aucune mention « constructible » ferme, aucun chiffre absent du JSON.
- [ ] Provenance visible (sourcé / estimé / absent) ; mentions **Fiabilité** + **Données manquantes** en fin.
- [ ] Si clé posée : 2–3 fiches contrôlées en recette (pas d'hallucination) avant le rendez-vous.
- [ ] Clé **absente de tout commit/log** (vérifier `git grep -i ANTHROPIC_API_KEY` → seulement le nom de la variable).

---

*Sans clé, l'assistant est déjà un livrable premium (synthèse règles déterministe, anti-hallucination
par construction). Avec clé, la prose IA enrichit la même structure — sans jamais inventer.*
