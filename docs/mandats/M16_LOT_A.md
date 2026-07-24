# M16 — LOT A : AUDIT du panneau Notifications (lecture seule)

**Branche** `audit/m16-a` (base `main`). **Rapport seul, zéro code.** Décide de ce que le LOT B pourra
promettre honnêtement.

Composant : `NotifBell` — `frontend/src/components/header/Header.tsx:307-382`. Backend :
`src/labuse/api/events.py`. Trois sections : en-tête (compteur + lien « Digest »), liste d'événements,
« Veilles (recherches sauvegardées) ».

---

## A1 — Ce qui déclenche une notification aujourd'hui

Les événements sont produits par `detect_events(db, run_from, run_to)` (`events.py:61-192`), qui
**diffe deux runs de scoring**. Ils sont écrits dans la table `event_log` (`kind, idu, titre, detail,
demo, lu, compte_id`). **4 types RÉELS**, tous **déclenchés par un nouveau run** (pas de temps réel) :

| Type | `kind` | Condition | Réf |
|---|---|---|---|
| **Bascule** | `bascule` | `matrice_statut` d'une parcelle change entre deux runs (▲ montée / ▼ descente) | events.py:61-83 |
| **BODACC** | `bodacc` | une procédure `evenement='rouge'` apparaît sur une parcelle (nouvelle au run cible) | events.py:85-101 |
| **Permis proche** | `permis` | nouveau permis Sitadel **≤ 300 m** d'une parcelle **suivie** (pipeline ou `watched_parcels`), daté < 12 mois | events.py:108-134 |
| **Veille** | `veille` | une **bascule montante** matche les filtres d'une recherche sauvegardée | events.py:103-192 |

### DÉMO : données réelles en base, PAS un mock front
Les entrées badgées **DÉMO** ne sont **pas** codées en dur dans le front. Ce sont de **vraies lignes
`event_log` avec `demo=true`**, semées par le backend `seed_demo()` (`events.py:195-229`) : un run
synthétique `q_v2_demo` sur 8 parcelles, déclenché par `POST /events/demo`. Le front ne fait que les
afficher avec un badge DÉMO (`Header.tsx:351`). Elles sont **rejouables** (`DELETE … WHERE demo` puis
re-seed) et effaçables.

→ **Conséquence B5** : ces entrées existent réellement en base ; le fix n'est pas « supprimer un tableau
JS » mais décider quoi montrer quand l'utilisateur n'a **pas** encore de vraie notification (état vide
honnête) — et garder les DÉMO **badgées** si on les conserve pour la démo commerciale.

### L'incohérence « 0 NON LUE » sur liste pleine
Deux requêtes distinctes :
- **compteur** = `count(*) WHERE NOT lu` (`events.py:247`) → ne compte que les **non lues**.
- **liste** = `… LIMIT 100` **sans filtre `lu`** (`events.py:238-245`) → montre **tout** (lues + non lues).

Après « tout lire » (ou re-seed démo puis lecture), les entrées passent `lu=true` : le compteur tombe à
0 **mais la liste garde les entrées lues** (grisées). Techniquement cohérent (une notif lue reste
visible, grisée), mais **lu comme un bug** : « 0 non lue » au-dessus d'une liste pleine. Le refetch 60 s
(`Header.tsx:312`) peut aussi retarder la mise à jour. → **B5** doit lever l'ambiguïté (ex. « Tout est
lu » explicite, ou séparer « non lues » / « historique »).

---

## A2 — « Veilles (recherches sauvegardées) » : à quoi ça sert

Table `saved_searches (nom, hash, compte_id)` (`events.py:45-48`). Le `hash` encode l'état des filtres
(`#f=1&st=…&q=…`), **même sérialisation que le front** (`_parse_hash_filters`, events.py:139-147).

- **Enregistrer** : `POST /events/searches` (nom + hash des filtres courants). Front : `Header.tsx:317`.
- **Relié aux notifications** : **OUI, et c'est fonctionnel.** À chaque run, toute **bascule montante**
  est confrontée aux filtres de **chaque veille** ; si ça matche → événement `kind='veille'` « 🔭 Veille
  « X » : … correspond » (events.py:150-192), cloisonné au `compte_id` propriétaire.

→ Une veille n'est **pas** juste une recherche mémorisée : c'est un **abonnement à alerte** basé sur des
filtres. Mécanisme **câblé de bout en bout** (save → match au run → événement). Le libellé actuel
(« recherches sauvegardées ») **sous-vend** cette réalité. → **B3** : reformuler + expliquer.

---

## A3 — Envoi par e-mail : ABSENT

Aucun envoi d'e-mail dans l'app. La config SMTP existe mais **n'est pas branchée** (tous les champs
`None`, `config.py:128-133`) et le sous-traitant **Resend a été retiré** (commentaire config.py, refonte
22/07 : « AUCUN email automatique »). Le « Digest » (A4) génère du HTML e-mail-ready mais
**ne l'envoie pas** (« L'envoi SMTP = config à brancher », events.py:375).

→ **Rien à fabriquer côté e-mail dans ce mandat.** L'e-mail de notification est un **chantier d'infra à
part**. Conséquence directe : la **destination du formulaire de suggestion (LOT C) = base**, pas e-mail.

---

## A4 — « Digest » : un récap hebdo (page HTML), pas un envoi

Bouton `Digest →` (`Header.tsx:342`) → ouvre `/events/digest.html` dans un onglet. Backend
`events.py:373-400` : une page HTML « les pépites de la semaine » — **événements des 7 derniers jours**
+ **Top 5 chaudes** de l'île (`_digest_data`, events.py:349-364). C'est un **résumé consultable**,
e-mail-ready mais **non envoyé**.

→ Le mot « Digest » est du jargon. **B2** doit le renommer. Propositions (à trancher en B) :
1. **« Le point de la semaine »** *(recommandé — clair, éditorial, colle au ton « chasse au trésor »)*
2. « Résumé de la semaine »
3. « Récap hebdo »

---

## A5 — Ce qui est techniquement NOTIFIABLE

### Parcelles suivies (le suivi existe et est câblé)
`watched_parcels (idu, compte_id)` + toggle `POST /events/watch/{idu}` (events.py:290-312), plus les
parcelles du pipeline CRM. Sur ces parcelles, un **permis proche ≤ 300 m** est détecté (real, wired).
Les **bascules** et **BODACC** sont détectées sur **toutes** les parcelles (pas besoin de suivi).

### Nouveauté issue d'une mise à jour de source : PAS de notification aujourd'hui
Le **radar de fraîcheur** (`radar.py`) est explicitement un **THERMOMÈTRE, pas un déclencheur** (doctrine
radar.py:7-10) : il détecte les publications amont mais **n'émet aucun événement**. Une mise à jour de
source ne devient visible que **indirectement** — via le nouveau run de scoring qu'elle alimente, qui
produit des bascules.

Sources réellement **auto-sondables** dans `radar.py` (`SONDES`, radar.py:35-58) : **5 en mode `auto`**
— **DVF** (hebdo mer.), **BAN** (mensuel), **BODACC** (quotidien), **DPE ADEME** (hebdo mar.),
**SITADEL** (quotidien) — + **1 manuel** (Cadastre Etalab, semestriel).
⚠ **Écart à consigner** : le mandat (audit M14) parle de **9 sondables / 52** ; `radar.py` n'en **câble
que 5** en `auto` (le reste du catalogue retombe en `non_sondable`, repli HEAD sans signal exploitable).
Le chiffre exact (5 vs 9) **ne change rien à la conclusion** : aujourd'hui **aucune source n'émet de
notification**.

### Verdict — les 3 catégories
| Statut | Événements |
|---|---|
| **Notifiable AUJOURD'HUI** (câblé, réel, run-driven) | Bascule de statut (toute parcelle) · procédure BODACC · permis neuf ≤ 300 m d'une parcelle suivie · match de veille (filtres) |
| **Notifiable avec un travail RAISONNABLE** | « Nouvelle publication » d'une des **5 sources auto** → émettre un événement quand le radar passe `nouvelle_publication` (le radar le sait déjà, il suffit de le brancher sur `event_log`) |
| **PAS notifiable** (ne pas promettre) | **Changement de PLU** sur une parcelle (aucun type d'événement PLU) · **permis ABANDONNÉ** (on ne détecte que l'**apparition** d'un permis, pas son abandon) · les **~43 sources non sondables** |

---

## Ce que le LOT B pourra promettre honnêtement
- **B1 (intro)** : décrire **les bascules de statut, les procédures/permis autour des parcelles suivies,
  et les matchs de veille** — PAS « les mises à jour de nos sources » comme déclencheur direct (faux
  aujourd'hui ; au mieux reformuler « quand de nouvelles données font bouger une parcelle »).
- **B2** : renommer « Digest » → « Le point de la semaine ».
- **B3** : « Veilles » est **fonctionnel** (alerte par filtres) mais sous-expliqué → reformuler + phrase
  d'explication. Ne rien retirer.
- **B4 (saisie langage naturel)** : **possible en réutilisant les veilles** (la brique NL validée par
  schéma → filtres → `saveSearch`), MAIS les exemples doivent coller aux **vrais déclencheurs**
  (ex. « préviens-moi quand une parcelle devient chaude à Saint-Paul » = bascule + filtres = RÉEL).
  **Interdire** les exemples « changement de PLU » / « permis abandonné » (non détectables). Si le
  branchement NL→veille dépasse le cadre, le consigner comme évolution.
- **B5** : DÉMO = vraies lignes `demo=true` → soit vraies notifs, soit **état vide honnête** ; lever le
  « 0 non lue » sur liste pleine. Garder les DÉMO **badgées** si conservées.
