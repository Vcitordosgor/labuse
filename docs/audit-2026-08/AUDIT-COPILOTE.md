# AUDIT — COPILOTE IA

**Branche** : `audit/copilote` · **Date** : 2026-08-23 · **Type** : audit seul (aucun code modifié, un seul rapport)
**Méthode** : lecture code + deux inventaires (chaîne backend / surfaces front) + vérifications ciblées. Postgres en lecture stricte. **Aucun appel API Anthropic** engagé (audit statique — la chaîne a été lue, pas éprouvée en vrai ; voir §7 si Vic veut une passe live bornée).

Le Copilote a **deux moteurs distincts** qu'il faut ne pas confondre :
- **Copilote v2 conversationnel** (`copilote_v2/`, endpoint `/api/copilote-v2/ask`) — le chat « le client écrit, LABUSE instruit ». C'est le cœur de cet audit.
- **Copilote « run » lourd** (`/api/copilote/runs`, SSE) — l'instruction longue (entonnoir, moteurs), avec quota 429 et flux d'événements. Câblé et gardé ; référencé où utile.

---

## 1. Tableau par capacité

| # | Capacité | Ce qu'elle **promet** | Ce qu'elle **fait** | Verdict |
|---|----------|----------------------|---------------------|---------|
| C1 | **Répondre à une question chiffrée** (compter, fiche, marché, délais…) | Un nombre sourcé de la base | 8 outils **lecture seule** ; le nombre est validé anti-invention avant d'être servi | ✓ |
| C2 | **Cloisonnement par compte** | Un client ne voit que ses données | Conversations / faits / veilles / missions filtrés `compte_id IS NOT DISTINCT FROM :c` ; les outils ne lisent que du **référentiel public** (cadastre/DVF/Sitadel) | ✓ (voir F1) |
| C3 | **« Voir sur la carte » le résultat** | La carte montre exactement les N annoncés | `carte_filtre` = **les critères déjà comptés** ; le front applique en gardant `analyseLabuse=false` pour que le compte carte == compte Copilote (M137-I, mesuré) | ✓ (réserve F2) |
| C4 | **Déclarer les critères non appliqués** | Ne jamais faire passer un critère qu'il n'applique pas | `criteres_non_appliques` (M109) : constructibilité calibrée, charge foncière, densité, rang, fiabilité marché → avertissement déterministe | ✓ |
| C5 | **Anti-invention numérique** | Aucun chiffre non vérifié | `_anti_invention` : tout nombre de la prose doit tracer au `ToolResult` du tour ou au registre de faits du fil, sinon **gabarit sourcé** (le chiffre n'est pas servi) | ✓ |
| C6 | **Recherche web native** | Info réglementaire à jour, marquée « web » | Outil `recherche_web` via l'API Anthropic native, `timeout=45`, `max_retries=1`, résultat marqué | ✓ |
| C7 | **Garde-fous de dépense / quota** | Limiter le coût par compte | **`/ask` n'a AUCUN quota ni rate-limit** malgré le docstring qui l'affirme ; le run lourd, lui, garde (429) | ✗ **F3** |
| C8 | **Comportement clé absente / API en échec** | Message honnête, jamais un 500 | `has_key()` faux → `degraded`, `ERREUR_INFRA` ; exception provider → `degraded` typé ; garde générale `/ask` capture tout, trace serveur | ✓ |
| C9 | **Surface IA distinguable (DA)** | Le mauve signale l'IA ; réponse IA reconnaissable | Dans le Copilote : variant CSS + kicker mono + carte mauve + `AvisIA` + étiquettes Sourcé/Estimé/Absent → **distinguable ✓**. Mais le mauve **n'est pas réservé à l'IA** (LOI-0 = premium/IA/outils) | ⚠ **F4** |
| C10 | **Outils annoncés = outils câblés** | Pas de capacité fantôme | `CATALOGUE` (7 outils) = `OUTILS` **sauf `divisibilite`** : câblé mais absent du catalogue → **injoignable** (mort) | ⚠ **F5** |
| C11 | **Intentions classées non exécutées au chat** | Rediriger vers la bonne surface | 6 intentions (RECHERCHE/PROJET/VÉRIFICATION/VEILLE/OUTIL/HORS_SUJET) → « refus-voie » cliquable (M118). Concepts retirés (M06/M07/ZAN/Quoi-de-Neuf/Suivi) → refus-voie, **pas de lien mort** | ✓ (par conception) |
| C12 | **Écriture déclenchée par le modèle** | Le modèle ne doit rien écrire/envoyer/dépenser seul | Les 8 outils sont lecture seule ; la seule écriture (veille) passe par un `_action` explicite + formulaire, jamais un libre choix du modèle | ✓ |

---

## 2. Chaîne : contexte reçu · droit d'appeler · réponse (périmètre 1)

```
POST /api/copilote-v2/ask  (copilote_v2.py:59)
  ├─ recharge le fil si conversation_id + TTL (history + prior_params + registre_faits)   ← cloisonné compte
  ├─ answer()  (answering.py:413)
  │   ├─ classify()      [haiku]  → intent (7) + params (registre FERMÉ) + clarification
  │   └─ _answer_with_route()
  │        ├─ EXPLIQUER / PREPARER            → [sonnet] pédagogie / script, jamais un chiffre
  │        ├─ QUESTION → _select_tool()  [sonnet] choisit un outil du CATALOGUE (ou refus)
  │        │              → OUTILS[tool](db, …)   ← LECTURE SEULE, référentiel public
  │        │              → _formuler() [sonnet] + _anti_invention()  → sinon gabarit sourcé
  │        └─ RECHERCHE/PROJET/VÉRIF/VEILLE/OUTIL/HORS_SUJET → refus-voie (navigation)
  ├─ persistance : historique.enregistrer() + registre_faits.enregistrer()   ← cloisonné compte
  └─ garde générale : toute exception → message honnête + trace serveur (jamais 500 au visage)
```

**Contexte injecté au LLM** : (a) le message + l'historique du fil (borné TTL), (b) `prior_params` et le **registre de faits** du fil (oracle des chiffres déjà servis), (c) un `contexte.idu` embarqué (id de parcelle **public**), (d) le catalogue d'outils. **Aucune donnée d'un autre compte** n'entre : cf. F1.

**Droit d'appeler** : strictement les 8 outils du registre `OUTILS`, tous lecture seule. Le modèle ne peut pas écrire, envoyer, ni dépenser hors « appeler un modèle » (les appels IA eux-mêmes — cf. F3).

---

## 3. Constats détaillés

### F1 — Cloisonnement : correct, et le « breach » soupçonné est un faux positif · gravité : ✓ / note
**Vérifié.** Les tables **appartenant au compte** sont filtrées : `historique.py:87`, `veilles.py:56`, `registre_faits.py:91` — toutes `WHERE … AND compte_id IS NOT DISTINCT FROM :c`. Les **8 outils** (`outils.py`) ne prennent **aucun** `compte_id` et lisent uniquement du référentiel **public** (facette parcelles, patrimoine SIREN, fiche run servi, contexte commune, Sitadel, DVF). Aucun n'ouvre une table CRM / note / pipeline.
→ La donnée sur laquelle le Copilote répond (« 42 parcelles en procédure à Saint-Paul ») est du **foncier public, identique pour tous** — pas de la donnée d'un client. **L'hypothèse d'une fuite inter-comptes via la fiche/le comptage est donc infondée** ; je la lève explicitement.
**Réserve (note, pas défaut)** : l'isolation repose **entièrement** sur la garde d'auth qui pose `request.state.compte_id` (`tenant.py:94`). En mode pilote / local / sans auth, `compte_id = None` et `IS NOT DISTINCT FROM NULL` **regroupe tout le monde dans le bucket NULL** — comportement attendu du pilote, mais à garder en tête le jour d'un multi-comptes réel (le Copilote fait confiance, il ne re-vérifie pas).

### F2 — « Voir sur la carte » : honnête, une réserve sur le tier · gravité : ⚠ mineure (à confirmer)
Le pont carte est **exemplaire** : `carte_filtre` = les critères **déjà comptés** (aucune requête parallèle, `answering.py:806`), et le front `ouvrirCarte` (`ReponseInline.tsx:43`) applique via le filtre `communes` en **gardant `analyseLabuse=false`** pour que le listing serveur reproduise **exactement** le compte annoncé — commentaire M137-I avec écart mesuré (33 910 vs 66) à l'appui. C'est précisément la parade au piège « scoreMin » (un filtre promis qui ne s'applique pas), bien faite.
**Réserve** : `_criteres_vers_filtres` **peut** émettre `tiers` (si la question portait sur un tier : brûlante/chaude). Or `ouvrirCarte` force `analyseLabuse=false` (mode factuel « toute la trame »). Pour une question **par tier**, le compte facette côté outil a été fait *avec* le tier, mais la carte factuelle pourrait ne pas le reproduire → **compte carte ≠ compte annoncé** sur ce cas précis. À confirmer (survit-`tiers` avec `analyseLabuse=false` dans `getResults` ?).
**Correctif candidat (non fait)** : quand `cf.filtres.tiers` est présent, soit armer `analyseLabuse=true` (et assumer que le compte est l'analysé), soit interdire le tier au comptage en mode factuel.

### F3 — `/ask` sans quota ni rate-limit · gravité : ✗ modérée
Le docstring d'en-tête de `copilote_v2.py:9` affirme « l'enforcement par compte réutilise le mécanisme `protection.py` », **mais l'endpoint `ask()` (ligne 59) n'appelle aucun garde de quota / rate-limit**. Chaque `/ask` déclenche **2 à 3 appels modèle** (haiku classify + sonnet select + sonnet formule), **sans plafond par compte / jour**. Les valeurs de config existent — `copilote_v2_missions_jour: 40`, `copilote_v2_tokens_mission: 40000` (`config.py`) — mais **ne sont pas appliquées sur le chat** (le run lourd `/copilote/runs`, lui, lève bien `CopiloteQuotaError` 429). Seuls protègent : `timeout=25s`, `retries=2`, `max_tokens` par appel, `temperature=0`.
**Exposition** : coût / abus — un compte peut marteler `/ask` sans limite.
**Correctif candidat (non fait)** : brancher un compteur quotidien par compte sur `/ask` (réutiliser `protection.py`), en nombre d'appels **ou** en tokens cumulés, 429 honnête au dépassement (le front sait déjà afficher un état quota rouge). Le cap `copilote_v2_tokens_mission` n'est vérifié nulle part dans `complete()` — à décider si on l'applique.

### F4 — Le mauve n'est pas réservé à l'IA · gravité : ⚠ mineure (doctrine à trancher)
**Dans le Copilote**, l'IA est **distinguable** sans ambiguïté : `data-variant` (ia/warn/err/neutral), kicker mono, carte mauve `cp-ia` (#B497F0), disclaimer `AvisIA` (« L'IA ne juge pas… »), sources en mono, et **chaque chiffre porte son étiquette** Sourcé/Estimé/Absent (`ui.tsx`). ✓
**Mais** le token mauve **n'est pas** un signal « ceci est de l'IA » : le `tailwind.config.js:60` déclare lui-même **LOI-0 · violet = premium / IA / outils**, et le mauve apparaît hors IA — `MapView` (résultats de recherche en violet), `crm/Kanban` (pastille projet), `projets/ProjetsPanel` (bandeau dédup), `Loading` (accent « partie OUTILS »), `BlocLivrable` (note d'opportunité). Ce n'est **pas** une fuite accidentelle vers des données vertes, c'est une **doctrine plus large** que « mauve = IA ». Le premier inventaire front l'a lu « mauve strict IA » — c'est vrai *à l'intérieur* du Copilote, faux à l'échelle de l'app.
**Correctif candidat (non fait) / décision Vic** : soit la DA assume LOI-0 (premium/IA/outils) et on met à jour la prémisse « mauve = IA » ; soit on veut vraiment « mauve = IA seul » et il faut **scinder le token** (un accent IA distinct de l'accent premium/outils). Rien à corriger tant que la doctrine n'est pas tranchée.

### F5 — Outil `divisibilite` mort · gravité : ⚠ mineure (code mort)
`OUTILS["divisibilite"]` est câblé (`outils.py:523`) **mais absent du `CATALOGUE`** montré au modèle (`answering.py:44`). Le dispatch se fait uniquement via `OUTILS[tool]` où `tool` vient du choix du modèle (`answering.py:687`) — qui ne connaît que le catalogue. **Le modèle ne peut donc jamais sélectionner `divisibilite`** ; il n'est appelé par aucun autre chemin. C'est un reliquat de M82 : depuis M129-C, la division est **retirée du chat** (route vers un refus « je ne tranche pas » via `_division`). La fonction `divisibilite()` + son entrée registre sont du **code mort**.
**Correctif candidat (non fait)** : retirer l'entrée `OUTILS["divisibilite"]` et la fonction `divisibilite()` (vérifier au préalable qu'aucun test ne les importe), ou la re-déclarer au catalogue si l'intention de la re-servir existe — auquel cas le dire plutôt que de la laisser injoignable.

### F6 — Défauts TTL divergents (latent) · gravité : cosmétique
Le champ `copilote_v2_contexte_ttl_minutes` vaut **10** par config (`config.py:188`) et est toujours présent. Mais les deux `getattr(..., défaut)` de `copilote_v2.py` divergent : **120** au rechargement du fil (ligne 82) vs **10** servi au front (ligne 113). Aujourd'hui **inoffensif** (le champ existe → le défaut n'est jamais atteint), mais c'est une mine si le champ est un jour renommé : le serveur rechargerait sur 120 min pendant que le front annonce l'expiration à 10.
**Correctif candidat (non fait)** : une seule constante de repli.

---

## 4. Honnêteté des réponses (périmètre 2) — synthèse

Le Copilote est **structurellement honnête** sur les chiffres, à trois verrous :
1. **Registre de faits** (M102-B3) — la reprise d'un chiffre d'un tour antérieur passe par un oracle tracé (outil/source/millésime).
2. **`_anti_invention`** — tout nombre de la prose doit tracer au résultat du tour ou au registre ; sinon la prose modèle est **jetée** au profit d'un gabarit sourcé.
3. **`criteres_non_appliques`** (M109) — la généralisation de la leçon scoreMin : le modèle **doit déclarer** les critères qu'il ne peut pas appliquer (constructibilité calibrée, charge foncière, densité, rang, fiabilité marché), avertissement déterministe.

**scoreMin** : entièrement retiré — absent de `copilote_v2/` (backend) et `api.ts:70` note le retrait front (M129-B). **Aucune autre promesse de filtre non appliqué** trouvée du même genre, **sous réserve de F2** (le tier sur le pont carte).

---

## 5. Garde-fous (périmètre 3) — synthèse

| Garde | État |
|-------|------|
| Clé absente | ✓ `degraded reason=no_key`, `ERREUR_INFRA`, `/ia/status`+`/assistant/status` = `provider:stub` |
| Échec provider | ✓ `degraded` typé (`_note_error` : auth/permission/générique), bandeau honnête |
| 500 au client | ✓ garde générale `/ask` : toute exception → message honnête + trace serveur |
| Timeout / retry | ✓ 25 s / 2 (web : 45 s / 1) ; température 0 |
| Taille de contexte | ~ fil borné TTL + registre plafonné (40 faits) ; **pas** de cap de tokens en entrée |
| **Quota / dépense `/ask`** | ✗ **F3 — aucun** (le run lourd garde, le chat non) |
| Cap `tokens_mission` | ⚠ config défini, **non appliqué** dans `complete()` |
| SSE (run) | ✓ `after_seq` anti-doublon, filet 180 s, `onerror` retry 2 s, 429 quota rouge |

---

## 6. Blocs morts (périmètre 5) — synthèse

- ✗ **`divisibilite`** : câblé, injoignable (F5).
- ○ **6 intentions** classées et non exécutées au chat (M118) → refus-voie : **intentionnel**, pas mort.
- ○ **Concepts retirés** (Foncier Fantôme M07, Bailleur M06, Simulateur ZAN, Quoi de Neuf, Suivi de Secteur) → refus-voie de navigation : **pas de lien mort** (ils redirigent, ne 404 pas).
- ○ **Front** : bouton **PDF** `BlocLivrable` désactivé « bientôt » (M26-C) et **3/5 missions** `actif:false` non proposées à l'accueil — **annoncées mais non câblées**, assumé maquette (labellisé, pas trompeur). À trancher si « bientôt » doit rester visible.

---

## 7. Éprouver le Copilote en vrai (optionnel, borné)

Audit **statique** — aucun appel API engagé. Si Vic veut une passe live, la borner à **≤ 5 requêtes** couvrant : (1) une question chiffrée (« combien de parcelles en procédure à Saint-Paul »), (2) une question **par tier** (pour trancher F2), (3) une question hors périmètre (refus honnête), (4) clé retirée (bandeau dégradé), (5) « voir sur la carte » (égalité des comptes). Coût indicatif : quelques centimes (haiku + sonnet, `max_tokens` bas).

---

## 8. Gravités & priorités

| Réf | Constat | Gravité | Action |
|-----|---------|---------|--------|
| **F3** | `/ask` sans quota / rate-limit | **modérée** | brancher un cap par compte (coût/abus) |
| **F2** | tier sur le pont carte (compte ≠ annoncé ?) | mineure | confirmer, puis armer analyseLabuse ou interdire tier factuel |
| **F4** | mauve ≠ IA seul (LOI-0 premium/IA/outils) | mineure | décision DA Vic : assumer ou scinder le token |
| **F5** | `divisibilite` mort | mineure | retirer (ou re-déclarer si intention) |
| **F6** | défauts TTL divergents (latent) | cosmétique | une seule constante de repli |
| F1 | cloisonnement | ✓ correct | rien — faux positif de fuite levé |

**Conclusion** : le Copilote v2 est **honnête par construction** (anti-invention + critères non appliqués + pont carte égalisé) et **cloisonné** sur la donnée qui appartient au compte. Le seul défaut réel est **l'absence de quota sur le chat** (F3). Le reste est mineur : une réserve à confirmer (F2), une doctrine couleur à trancher (F4), un outil mort (F5), un défaut latent (F6).
