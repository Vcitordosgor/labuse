# JOHN-TAYLOR-1 — le second de bord de LABUSE

**Branche** `feat/john-taylor-1` · worktree `~/Desktop/labuse-johntaylor` · ports 9510/6710 · **Opus**
**Pas de merge. Aucun accès prod.** Date : 2026-11-03 (Réunion +04). DA existante réutilisée.

> **Bilan en une ligne.** John Taylor est livré : un agent d'exploitation (onglet « John Taylor » de la
> page Données, **admin seul**) qui **lit tout** l'état réel de l'app, **répond à Vic en citant sa
> source**, **agit sur ordre dans une liste fermée** (dont deux actions à confirmation), écrit le
> **résumé du matin**, mène la **veille de nuit** et **enquête** sur un incident. Il est bâti sur le socle
> IA existant (`ai/core`, `ai_models`), avec le **même verrou anti-invention que le Copilote**, un
> **plafond de coût mensuel** (50 € par défaut) qui coupe proprement, et un **carnet de bord** en base.
> Recette : **23/23** tests John (10 questions sourcées, ordre exécuté / ordre confirmé / ordre refusé
> journalisés, résumé, veille, enquête, plafond), **banc unitaire 2883/0**, cohérence **6/0**, tsc **0**,
> vitest **268/0** (8 suites carte non chargées = artefact symlink node_modules, cf. recette), secrets 0.
> Vérifié **en direct contre l'API réelle** : enquête et chat répondent, sourcés (copie d'écran plus bas).

---

## Qui est John

L'agent d'exploitation de LABUSE, nommé d'après le second du pirate La Buse. Il parle **français, simple,
sans jargon** ; un clin d'œil de marin au plus, jamais de folklore dans une réponse technique. Il répond
à tout ce qui concerne l'exploitation, **cite la donnée d'où vient chaque affirmation**, et dit « je ne
sais pas » quand rien ne la porte.

**Règle d'or.** John lit tout. Il agit **sur ordre de Vic**, dans une **liste fermée** d'actions, **jamais
de sa propre initiative**. Pas de shell, pas de SQL libre venu du modèle, **aucune écriture hors de la
liste fermée**, aucun secret ni donnée client envoyé à l'API (le contexte est de l'exploitation).

---

## Les modèles — « 5.5 » RÉPOND à l'API : il est servi par défaut (repli 4.x en filet)

Le mandat demande **Opus 5.5** (chat/résumé/enquêtes) et **Haiku 5.5** (veille/lectures de masse).
**Vérifié par un appel réel le 2026-11-03** : `claude-opus-5-5` ET `claude-haiku-5-5` (sans suffixe de
date) **répondent (200, `usage` renvoyé)**. Ce sont donc les **défauts** :

| Usage mandat | Surface (`ia_log`) | Modèle servi (défaut) | Repli si `not_found` |
|---|---|---|---|
| chat / résumé / enquête | `john-chat`, `john-resume`, `john-enquete` | **`claude-opus-5-5`** | `claude-opus-4-8` |
| veille / lectures de masse | `john-veille` | **`claude-haiku-5-5`** | `claude-haiku-4-5` |

`MODEL_OPUS`/`MODEL_HAIKU` (les 5.5) entrent au registre `ai_models` (+ `ACTIVE_MODELS`, + tarif `PRICE`).
Overridable par surface (`LABUSE_IA_MODELE_JOHN_CHAT=…`). **Repli automatique, jamais silencieux** : si un
de ces identifiants tombait un jour en `not_found`, l'appel **rejoue UNE fois sur la lignée 4.x**
(`REPLI_MODELES` + `repli_pour`/`est_not_found`), câblé dans `ai/core.complete` ET dans les clients propres
de John (chat, veille) — un `log.warning` nomme le repli (même leçon que l'incident `claude-3-5-haiku`).

**Correctif réel vérifié contre l'API : les 5.5 — comme Opus 4.8 — REFUSENT le paramètre `temperature`**
(« temperature is deprecated for this model » → 400 ; Haiku 4.5, lui, l'accepte encore). `ai/core.complete`
l'envoyait toujours → le chemin tombait en « dégradé ». Fix à la source : `core` **omet `temperature`**
pour `NO_TEMPERATURE_MODELS` (`{opus-5-5, haiku-5-5, opus-4-8}`). Les clients propres de John (chat, veille)
ne l'envoyaient déjà pas. **Testé en direct** : enquête `ok=True` et chat (boucle d'outils) tournent sur
`claude-opus-5-5` sans erreur, coût tracé au ledger.

**Cache de prompt** : le contexte fixe de John (persona + doctrine + carnet + liste d'actions) est assemblé
une fois par tour et envoyé en `system` — stable d'un tour à l'autre d'une conversation, donc éligible au
cache côté Anthropic.

---

## Ce qui est livré

### Le chat (onglet « John Taylor », admin seul)

- **Outils de LECTURE** (`john/contexte.py` + `john/outils.py`, 100 % lecture seule, aucun SQL du modèle) :
  jobs, incidents, sources + fraîcheur + **classe A/B**, runs servis/calculés + pointeurs, contrôles
  (banc de cohérence), sauvegardes + copie externe, Radar, journaux d'erreur, carnet de bord, rapports du
  dépôt. Le modèle **choisit un outil**, John exécute la lecture, lui rend le JSON.
- **Verrou anti-invention** (`john/chat.anti_invention`, réutilise les utilitaires du socle) : **tout
  chiffre de la réponse doit figurer dans une lecture** réellement faite ; sinon la réponse est refusée et
  remplacée par un repli honnête (on n'affiche jamais la prose douteuse ni le chiffre fautif). Même
  doctrine que le Copilote.
- **Carnet de bord lu en tête** de chaque conversation (décisions de Vic, incidents passés, doctrines).
- **Conversations gardées 90 jours** (`LABUSE_JOHN_CONVERSATIONS_JOURS`), purge au premier usage.

### Les actions — liste fermée, journalisées (`john/actions.py`)

| Action | Confirmation | Contrôles préalables |
|---|---|---|
| `injecter_source` (A ou B) | non | commande d'ingestion connue (sinon « à câbler », rien injecté) |
| `relancer_job` | non | le job doit exister au registre |
| `lancer_sauvegarde` | non | — (relance `backup-postgres`) |
| `accepter_incident` | non | ferme l'incident (`ops_alertes.resoudre`) |
| `accepter_ecart` | non | enregistre l'acceptation **avec raison** (registre `john_ecarts_acceptes`) |
| **`promouvoir_run`** | **OUI** | **contrôles VERTS** (faux-client 0, lecteurs 0) sinon REFUS |
| **`retirer_source`** | **OUI** | `status='retiree'` + raison + veille coupée |

Les deux actions qui **touchent les clients et ne se défont pas d'un clic** demandent d'abord « tu
confirmes ? » (un « oui » suffit — géré **côté serveur**, pas par le modèle : état `pending` sur la
conversation). **Hors liste → refus explicite et journalisé.** Chaque action est tracée dans
`john_journal` (**heure + compte**), y compris les refus. Les effets de bord réels passent par un
`Backend` **injectable** (testé sans sous-process ni bascule réelle).

### Le résumé du matin (`john/resume.py`, câblé au job `resume-matin` 07:30)

John **réécrit** le résumé à partir des **faits du résumé actuel** (`jobs_impl._resume_matin_texte`) : ce
qui s'est passé, pourquoi, ce que Vic doit faire — ou « rien n'attend votre décision ». Deux filets :
(a) **si John échoue** (plafond, dégradé, anti-invention) → **le résumé actuel part tel quel** ; (b)
anti-invention sur le texte de John. Chaque résumé est rangé (`john_resume`) et affiché dans l'onglet ; le
mail part comme avant.

### La veille de nuit (`john/veille.py`, job `john-veille` 03:00, famille 1)

Un passage IA (**Haiku + web_search**, même patron qu'`agent_source`) sur **trois axes** : réglementaire
(Légifrance/BOFiP + PLU/SCOT/PPR 974), sources (millésimes/API), concurrence (KelFoncier/Capaciti). Chaque
élément porte **sa source, sa date et un libellé** (`à intégrer` / `source B à valider` / `info` /
`concurrence`). **Anti-invention** : un item sans source NI date est **écarté**. La veille **informe,
n'injecte rien**. S'arrête proprement au plafond.

### L'enquête sur incident (`john/enquete.py`)

Sur chaque carte « ça casse » du Tableau de bord, un bouton **« Demander à John »** : il lit les journaux
(incidents, jobs en échec, historique du job concerné) et rend **cause probable + correction**. Pour une
carte **« demande du code »**, il rédige en plus un **mandat Claude Code prêt à coller**.

### Le plafond de coût (`john/budget.py`)

Plafond **mensuel configurable** (`LABUSE_JOHN_PLAFOND_EUR`, **50 € par défaut**), coût lu du ledger
`ia_log` sur les surfaces `john-*` du mois (Réunion), **affiché en temps réel** dans l'onglet. **Au
plafond, John est en pause** : aucun appel modèle n'est lancé, il répond qu'il reprend au mois prochain.
Coupure propre (pas une erreur) qui se lève au changement de mois.

### L'onglet (frontend)

5ᵉ onglet « John Taylor » de la page Données (`Circuit.tsx`). **Chat à gauche ; à droite : résumé du
matin, veille, carnet de bord, coût du mois** (`JohnTaylor.tsx`, rendu dans le scope `.cxp` → DA du
Circuit réutilisée). Les propositions de carnet s'y valident/rejettent. Le bouton **« Demander à John »**
des cartes « ça casse » bascule sur l'onglet et lance l'enquête.

---

## RECETTE

| Attendu du mandat | Résultat |
|---|---|
| **Dix questions réelles** avec réponses **sourcées** | ✅ `test_john_1::test_dix_questions_reelles_sourcees` (10 questions → 10 lectures d'outil, réponses non vides, trace en base) |
| Un **ordre exécuté** (injection source A) | ✅ `::test_ordre_injection_source_a_execute` (classe A reconnue, ingestion lancée, **journalisé**) |
| Un **ordre avec confirmation** (promotion simulée) | ✅ `::test_ordre_avec_confirmation_promotion_simulee` (sans « oui » → **demande**, rien fait, rien journalisé ; avec « oui » → **promu**, journalisé `confirme=True`) + refus si contrôles non verts |
| Un **ordre hors liste refusé** | ✅ `::test_ordre_hors_liste_refuse_et_journalise` (refus + journal `ok=False`) |
| Un **résumé du matin produit** | ✅ `::test_resume_du_matin_produit_par_john` (+ `::…_repli_si_john_echoue` : le résumé actuel part) |
| Une **veille de nuit produite** | ✅ `::test_veille_de_nuit_produite` (2 items datés gardés, 1 non daté **écarté**, libellés valides) |
| Une **enquête sur incident simulé** | ✅ `::test_enquete_sur_incident_simule` (cause + correction + **mandat Claude Code** en mode code) |
| Le **plafond atteint coupe proprement** | ✅ `::test_plafond_de_cout_coupe_proprement` (pause, **aucun appel modèle**, message honnête) |
| **Banc complet 0 rouge** | ✅ unitaires **2883 / 0** ; db (John + cockpit) **15 / 0** |
| **Hook vert** | ✅ secrets **0** · tsc **0** · vitest **268/0** (8 suites carte non chargées = artefact symlink node_modules inter-worktree, `maplibre-gl-worker`, **pas une régression** — cf. TABLEAU-1) · unitaires **2883/0** · cohérence **6/0** |
| **Compte-rendu** | ✅ ce fichier |

**Vérifié en direct contre l'API réelle** (clé présente) : `/admin/john/enquete` rend `ok=True` avec une
cause sourcée (« aucun dump `labuse-*.dump` dans /var/backups/labuse… ») ; `/admin/john/chat` mène la
boucle d'outils sur Opus (coût tracé au ledger), répond en citant ses lectures, et **le verrou
anti-invention refuse** un tour dont un chiffre n'était pas sourcé (comportement voulu). Le correctif
`temperature` (ci-dessus) était **nécessaire** : sans lui, tout le chemin Opus tombait en dégradé.

---

## CE QUI RESTE UNE DÉCISION / UN GESTE HUMAIN

1. **Merge** `feat/john-taylor-1 → main` par PR (hors mandat « pas de merge »). Rien n'est actif tant que
   ce n'est pas déployé (onglet, job `john-veille`, résumé écrit par John).
2. **Crédit API** : la veille et le chat consomment Opus/Haiku ; en prod, poser le plafond voulu
   (`LABUSE_JOHN_PLAFOND_EUR`) et vérifier le solde du compte Anthropic.
3. **Validation des lignes de carnet** proposées par John depuis le chat (elles n'entrent qu'après le
   « Valider » de Vic — par conception).

---

## FICHIERS

**Neufs** : `src/labuse/john/{__init__,budget,journal,carnet,contexte,outils,actions,chat,resume,veille,
enquete}.py`, `src/labuse/api/john.py`, `frontend/src/components/admin/circuit/JohnTaylor.tsx`,
`frontend/src/components/admin/circuit/JohnTaylor.test.tsx`, `tests/test_john_1.py`,
`tests/test_john_registre.py`, ce compte-rendu.

**Modifiés** : `src/labuse/ai_models.py` (MODEL_OPUS + surfaces/INTERNE john-*), `src/labuse/ai/core.py`
(tarif Opus + `NO_TEMPERATURE_MODELS`), `src/labuse/config.py` (réglages `LABUSE_JOHN_*`),
`src/labuse/jobs.py` (job `john-veille` + famille), `src/labuse/jobs_impl.py` (résumé écrit par John +
`john_veille`), `src/labuse/api/app.py` (router), `src/labuse/circuit_garanties.py` (lecteur assumé G6),
`frontend/src/lib/api.ts` (endpoints John), `frontend/src/components/admin/circuit/Circuit.tsx` (onglet),
`frontend/src/components/admin/circuit/TableauDeBord.tsx` (bouton « Demander à John »),
`tests/test_cockpit_lot_b.py` (35 jobs), `docs/audit-2026-10/DASHBOARD-FIX-1/HORLOGES.csv` (régénéré).
