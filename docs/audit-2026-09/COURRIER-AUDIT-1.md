# COURRIER-AUDIT-1 — Peut-on écrire à qui, et que sait-on vraiment ?

**Branche** `feat/courrier-audit-1` · **base main** `8564b1e7` (Étape 0, hash gelé) ·
worktree `~/Desktop/labuse-courrier` · ports :8125 / :5325 · run servi **`q_v11_m137`**.
**LECTURE SEULE** — aucun courrier envoyé, aucun appel prestataire, aucun prélèvement, aucune
bascule. Aucun nom de personne physique dans ce rapport ni dans les captures.

Ce mandat **mesure**. La refonte viendra après, sur ce qui est GO.

---

## En tête — les cinq chiffres + le bloquant

Le service adresse **« À l'occupant » à l'adresse BAN de la parcelle**. Il n'utilise
jamais l'identité du propriétaire pour adresser (voir §A). Les chiffres ci-dessous mesurent donc
la **joignabilité fiable** = *parcelle bâtie ET dotée d'une adresse BAN* (un « occupant » n'existe
que sur du bâti ; sans adresse BAN, pas d'enveloppe fiable). Doctrine **FIABILITÉ > COUVERTURE**.

| Chiffre | Valeur | Lecture |
|---|---|---|
| **% du parc adressable** (bâti + adresse BAN) | **57,1 %** | 246 450 / 431 663 parcelles. Adresse BAN présente tous types confondus : 59,6 %. |
| **% des PP adressables** (à l'occupant) | **61,7 %** | 215 718 / 349 597 parcelles non-PM bâties+BAN. **Jamais nominatif.** |
| **% des PM adressables** (à l'occupant) | **37,4 %** | 30 732 / 82 066 parcelles PM bâties+BAN. Identité PM connue par ailleurs (public). |
| **Verdict PP** | **ATTENTION** | Joignable seulement « à l'occupant » sur le bâti ; aucun nom/adresse propriétaire en base (MAJIC absent). NO-GO sur les terrains nus (8 % d'adresse). |
| **Verdict PM** | **GO conditionnel** | Propriétaire identifiable de façon fiable (DGFiP public : dénomination + SIREN, siège pour ~40 %). Le canal **nominatif n'est pas câblé** — en l'état, PM part aussi « à l'occupant ». |

> ### 🔴 BLOQUANT — `stop@labuse.immo` n'existe pas
> Il n'y a **aucun mécanisme d'opposition postale** : pas d'adresse entrante `stop@`, pas de
> table de suppression (do-not-mail), aucune vérification avant envoi, aucun blocage inter-comptes.
> Le seul opt-out du code est le **`List-Unsubscribe` du digest e-mail du CLIENT** (ses propres
> notifications — `src/labuse/api/events.py:332`), sans rapport avec un destinataire postal qui
> demanderait à ne plus recevoir de lettre. **À traiter avant tout envoi réel** (obligation
> déontologique et RGPD : droit d'opposition d'une personne démarchée). Détail §B7.

**Second point dur (fiabilité du contenu, §B2) :** 3 demandes vivantes sur 28 (`courrier_demandes`
ids 43-45) portent un corps où les gabarits **`{parcelle}` / `{commune}` / `{surface}` n'ont
jamais été substitués** — si Vic les dépose, la lettre imprime littéralement `{parcelle}`
(capture `pdf-defaut-placeholders-demande45`).

---

## A — Qui est adressable (le lot bloquant)

Population = les **431 663 parcelles** du run servi (`parcels` = `mvt_parcels`, q_v11_m137).
Comptages SQL directs (base `labuse`).

### A1 — Propriétaires

| Catégorie | Parcelles | % parc | Source |
|---|---|---|---|
| **Personne morale identifiable** (dénomination + SIREN) | 82 066 | 19,0 % | `parcelle_personne_morale` (DGFiP « locaux des personnes morales », open data) |
| **Autres** (présumées personnes physiques + public + indivisions) | 349 597 | 81,0 % | *déduction* : non présentes dans le fichier PM |
| dont propriétaire **nommément identifiable** | **0** | 0 % | **aucune source MAJIC / fichiers fonciers en base** |

Il n'existe **aucune table de propriétaires particuliers** (recherche : seule
`pm_proprietaires_millesimes` existe, = PM à nouveau). **MAJIC / fichiers fonciers ne sont pas
ingérés.** Conséquence : pour 81 % du parc, on ne connaît **pas** le nom du propriétaire, et pour
les 19 % restants (PM) on connaît le nom mais **pas** son adresse fiable en tant que propriétaire
(cf. A2).

### A2 — Adresse postale du DESTINATAIRE (distincte de l'adresse de la parcelle)

**Constat central : il n'y a pas d'adresse de correspondance du propriétaire dans le circuit.**
La demande (`courrier_demandes`) ne porte **aucune** colonne adresse — elle stocke seulement la
liste d'IDU + le corps. L'adresse est résolue **en aval, à la main par Vic** au moment du dépôt,
à partir de l'adresse **BAN de la parcelle**, et le pli part **« À l'occupant »**
(`src/labuse/courrier.py:380` ; `src/labuse/api/courrier.py:305`).

| Chemin | Personne physique | Personne morale |
|---|---|---|
| **SOURCE** | — (aucune) | SIRENE via `owner_enrichment` (siège social) |
| **TABLE** | — | `owner_enrichment.payload->'siege'` |
| **CHAMP** | — | `adresse`, `code_postal`, `libelle_commune` |
| **TRANSFORMATION** | — | jointure `parcelle_personne_morale.siren = owner_enrichment.siren` |
| **ADRESSE FINALE** | **inexistante** | siège dispo pour **32 872 / 82 066 PM (40,1 %)** — *non utilisée par le courrier* |

Réponse nette à la question du mandat : **les adresses de personnes physiques n'existent pas en
base** (pas de MAJIC sous convention). **Seules les PM** peuvent avoir une adresse (siège SIRENE,
open data DGFiP), pour ~40 % d'entre elles — mais ⚠ un siège SIRENE est souvent une domiciliation
(expert-comptable, boîte), *pas* forcément le décideur, et **le courrier ne s'en sert pas
aujourd'hui**. L'unique adresse réellement employée est **l'adresse BAN de la parcelle**.

### A3 — Adresse de la PARCELLE (BAN)

| | Parcelles | % |
|---|---|---|
| Adresse BAN présente (`parcel_adresse.ban_voie`) | 257 340 | 59,6 % du parc |
| — dont **bâties** | 246 507 | **83,6 % des bâties** |
| — dont **nues** | ~10 900 | **8,0 % des nues** |
| Sans adresse BAN | 174 323 | 40,4 % |

Bâti mesuré via `parcel_filtre_bati` : **294 865 bâties (68,3 %)** vs **136 798 nues (31,7 %)**.

**Substitution silencieuse adresse parcelle → adresse propriétaire ?** **Non — et pour cause :
il n'existe aucune adresse propriétaire à substituer.** Le seul flux est parcelle→BAN→«À
l'occupant». Aucun endroit du code ne remplace une adresse de parcelle par une adresse de
propriétaire. (À l'inverse, l'aperçu PDF n'imprime **même pas** de bloc adresse — il ne montre que
l'objet, le corps et le pied ; l'adresse est apposée au dépôt.)

### A4 — Taux d'adressabilité et verdicts

| Segment | Adresse BAN présente | Fiable (bâti + BAN) |
|---|---|---|
| Parc entier | 59,6 % | **57,1 %** |
| Bâties | 83,6 % | 83,6 % |
| Terrains nus | 8,0 % | — (occupant inexistant) |
| PP (non-PM) | 63,7 % | **61,7 %** |
| PM | 42,1 % | **37,4 %** |

- **PP → ATTENTION.** Joignable uniquement « à l'occupant », sur le bâti (61,7 %). On n'écrit
  jamais au propriétaire nommé (impossible : MAJIC absent) — on écrit à **l'occupant actuel**, qui
  peut être un locataire. Sur terrain nu : **NO-GO** (8 % d'adresse, et personne pour ouvrir la
  boîte). Fiable *en tant que pli à l'occupant d'un bâti*, pas *en tant que courrier au
  propriétaire*.
- **PM → GO conditionnel.** C'est le seul segment où un courrier **fiable et nominatif** est
  atteignable : dénomination + SIREN sont publics et sûrs. **Condition** : câbler l'adresse de
  siège (`owner_enrichment`, dispo 40 %), valider sa fiabilité (domiciliations), et l'utiliser à la
  place de « à l'occupant ». En l'état (à l'occupant, 37,4 % bâti+BAN) le potentiel n'est pas
  exploité.

---

## B — Ce que le système fait aujourd'hui

### B1 — Le circuit réel (depuis une fiche)

| Étape | Endpoint / geste | Handler | État |
|---|---|---|---|
| Ouvrir depuis la fiche | bouton **« Courrier »** (`Fiche.tsx:1688`) → module pré-rempli | — | **existe** |
| ① Destinataires | saisie IDU/adresse (`ModulePanel.tsx` M09) | — | **existe** |
| ② Rédaction | 4 modèles à variables, corps éditable | — | **existe** |
| Aperçu PDF (relecture) | `POST /courrier/pdf` | `courrier_pdf` (`api/courrier.py:302`) | **existe** |
| ③ Envoi → **« Demander l'envoi à LABUSE »** | `POST /courrier/demande` | `creer_demande` (`courrier.py:164`) | **existe & vivant** |
| Notification Vic | cloche + e-mail (voir ci-dessous) | `api/courrier.py:143-164` | **fonctionne** |
| Dashboard admin | `GET /admin/demandes` | `demandes_admin` (`courrier.py:225`) | **existe & vivant** |
| Faire avancer le statut | `POST /admin/demandes/{id}/statut`, `…/deposer-tout` | `api/courrier.py:221-279` | **existe** |
| Retour client | `POST /demandes/{id}/statut` (repondu/sans_reponse) | `api/courrier.py:194` | **existe** |
| *(legacy)* envoi direct API | `POST /courrier/envois` | `courrier_envoyer` | **DORMANT** (provider stub → bouton masqué, aucun front ne l'appelle) |

**« Demander l'envoi » arrive-t-il au dashboard ? Oui.** Le POST crée la ligne
(`statut='demande'`, dédup 120 s) puis notifie Vic par **deux canaux best-effort** (n'empêchent
jamais la création) : (1) **cloche** `event_log` `kind='systeme'`, `compte_id=NULL` (fil admin) ;
(2) **e-mail Brevo** async vers `admin_email` (`mail.py:111`). La demande apparaît ensuite dans le
Courrier admin (capture `06`) et au Journal Pilotage (capture `07`). Vérifié en direct : 28
demandes réelles, dont « 25 à déposer ».

### B2 — Le PDF actuel : ce qu'il imprime

L'aperçu (`api/courrier.py:302-360`) imprime **uniquement** : en-tête « LABUSE / Intelligence
foncière — La Réunion », **le corps saisi tel quel**, pied de page légal (« Courrier préparé avec
LABUSE — à partir de données publiques… Ni conseil juridique ni offre d'achat »). Une seule page
(recto ; pas de verso ; pied sur la même page). Captures `pdf-recto-full`, `pdf-fallback-sansdonnee`.

- **Nom de personne physique ?** Jamais. Destinataire = « À l'occupant » (adresse apposée au
  dépôt, absente de l'aperçu). Colonne « Propriétaire » du dashboard = **compte de PM** (« 1
  personne morale »), jamais une identité de particulier (« — »).
- **Capacité / SDP / logements / prix estimé ?** **Aucun.** Le PDF ne fait **aucune** requête
  donnée ; il ne rend que `body.texte`. `body.idu` sert seulement à nommer le fichier.
- **Chiffre marketing (« 94 sources ») ?** Absent partout dans le flux courrier.
- **null / undefined / phrase cassée ?** Deux régimes :
  - **Chemin front (actif)** : `remplirGabaritCourrier` (`ModulePanel.tsx:1241`) supprime le
    **segment entier** quand commune/surface manquent — rendu propre, sans `à —` ni `( )`
    (capture `pdf-fallback-sansdonnee` : « votre parcelle ZK 0112 » sans reste). **Fiable.**
  - **Chemin back (`modules.py:1478` `_COURRIER.format`)** : `.format()` **plante en KeyError**
    si `ref`/`commune` sont NULL (aucun fallback). Et surtout, **défaut vivant** : 3 demandes
    (`courrier_demandes` 43-45) portent un corps **avec `{parcelle}`/`{commune}`/`{surface}` non
    substitués** — la lettre déposée imprimerait ces accolades (capture
    `pdf-defaut-placeholders-demande45`, rendu du corps réel de la demande #45).

### B3 — Les ouvertures personnalisées

| Modèle | Surface d'origine | Donnée dont il dépend | Affirme une estimation ? |
|---|---|---|---|
| `standard` | front (`ModulePanel.tsx:1219`) | parcelle, surface, commune | **Oui** — « potentiel de construction encore ouvert » |
| `dormance` | front | parcelle, surface, commune | **Oui** — « sa valorisation soulève des questions » |
| `voisin` | front | parcelle, surface, commune | Non (projet à proximité, factuel) |
| `libre` | front | aucune | Non (texte client) |
| `standard` (back) | `modules.py:1478` | ref, surface, commune | **Oui** — « un réel potentiel » |
| `indivision` (back) | `modules.py` | ref, surface, commune | Non (juridique) |
| `succession` (back) | `modules.py` | ref, surface, commune | **Oui** — « étude sérieuse et confidentielle de sa valeur » |

Aucune ouverture ne s'appuie sur une donnée de capacité/SDP/prix **réellement calculée** : les
mots « potentiel / valorisation / valeur » sont des **formules de prose**, pas des chiffres tirés
d'un moteur. C'est le point de fiabilité à trancher : une lettre qui affirme un « potentiel de
construction » sur une parcelle non qualifiée est une **affirmation incertaine** (contraire à
FIABILITÉ > COUVERTURE). Le modèle `voisin` et `libre` en sont exempts.

### B4 — Les statuts (vocabulaire réel par surface)

Vocabulaire canonique unique (`courrier.py:92-101`) :
`demande → depose → envoye → repondu / sans_reponse`, alias legacy
`tarif_confirme→demande`, `imprime→depose`, `poste→envoye`.

| Surface | Libellés vus |
|---|---|
| Fiche | aucun (courrier pas encore créé) |
| Outil Courrier / « Vos demandes » (client) | **Demandé · Déposé · Envoyé · Répondu · Sans réponse** (`ProjetsPanel.tsx:169`) |
| Carte CRM (Kanban) | même jeu, puce colorée |
| Dashboard admin (Courrier) | **À déposer** · Déposé · Envoyé · Répondu · Sans réponse (capture `06`) |
| Journal Pilotage | mélange : entrées récentes « Déposé », **entrées anciennes « Imprimé » / « Posté »** (legacy non ré-écrit, capture `07`) |

⚠ **Incohérences réelles** : (1) le statut `demande` s'affiche **« À déposer »** côté admin mais
**« Demandé »** côté client — deux mots pour le même état ; (2) le Journal montre encore les
libellés legacy **« Imprimé » / « Posté »** sur les vieux événements, à côté du nouveau « Déposé ».

**« Répondu » / « Sans réponse » : comment posés ?** **Clic manuel du CLIENT** dans « Vos
demandes », uniquement après `envoye` (`ProjetsPanel.tsx:264` → `postCourrierClientStatut`).
L'admin peut aussi les poser. **Aucune** automatisation, **aucun** délai, **aucun** lien CRM
automatique. Tant que Vic n'a pas fait avancer la demande jusqu'à `envoye`, le client ne peut rien
déclarer — or l'envoi réel n'existe pas (provider stub), donc en pratique **0 « Répondu », 0 «
Sans réponse »** aujourd'hui (vérifié : filtres à 0).

### B5 — Le prix

- **Affiché au client avant dépôt : rien.** Ni à l'étape ①, ni ②, ni ③ (capture `03` : le récap
  ne montre que « Courriers / Communes / Adressage »). Message **après** dépôt : « LABUSE vous
  rappelle sous 24 h ouvrées avec le tarif ». C'est **voulu** (« aucun prix affiché côté client »,
  `api/courrier.py:87`).
- **D'où vient le montant :** `tarif()` (`courrier.py:336`) = `courrier_cout_lettre_eur` ×
  `courrier_marge`. Config par défaut : **2,69 € × 1,5 = 4,04 €** (vérifié en direct sur
  `/courrier/statut`).
- **Tarif prestataire codé sans source ?** Semi : `courrier_cout_lettre_eur = 2,69` est une
  **constante de config** (« lettre verte 3 pages Merci Facteur, grille 2026 », `config.py:148`),
  sourcée par **commentaire de code / `NOTES_WAVE_ACI.md`**, pas par une table de tarifs à jour.
  ⚠ Le `tarif()` (4,04 €) est **renvoyé dans le payload de `/courrier/statut`** même s'il n'est pas
  rendu à l'écran — donc lisible via l'API.

### B6 — La facturation (Stripe, tel quel)

| Capacité | Aujourd'hui |
|---|---|
| Abonnement (Intégral 349 €/mois) | **Oui** — `checkout.session.completed` → `actif`, `invoice.paid`, `invoice.payment_failed` → relance, `subscription.deleted` → suspension (`facturation.py:345-466`) |
| Paiement unique (Flash) | **Oui** — `mode='payment'` |
| Dédup webhooks | **Oui** — `stripe_events` (185 lignes) |
| Ligne **hors abonnement** / metered pour un courrier | **Non** — aucun appel `Invoice.create` / `Usage.record` |
| Facture automatique du courrier | **Non** |

`courrier_envois.cout_eur/prix_eur` sont **enregistrés mais jamais transmis à Stripe**. La
facturation courrier prévue = **« facture séparée mensuelle »** (`courrier.py:14`), **manuelle,
non câblée**. Le dashboard affiche d'ailleurs **« Stripe non configuré »** (capture `07`).

### B7 — `stop@labuse.immo`

**Le mécanisme n'existe pas.** Recherche exhaustive (code + schéma) :
- Aucune adresse entrante `stop@`, aucun handler d'e-mail entrant.
- Aucune table de suppression / do-not-mail / blocklist (recherche
  `suppress|exclu|opposi|desab|refus|stop` sur `pg_tables` → néant).
- `courrier.envoyer` (`courrier.py:376`) et le dépôt **ne vérifient rien** avant d'émettre. Un même
  destinataire peut être ciblé par plusieurs comptes sans blocage inter-comptes.
- Le seul opt-out du code = **`List-Unsubscribe` du digest e-mail du client** (`events.py:332`),
  qui coupe les *notifications du client*, pas les *plis postaux d'un tiers*.

**BLOQUANT** : un envoi postal réel sans canal d'opposition ni registre de suppression est
intenable (droit d'opposition de la personne démarchée). À poser **avant** de sortir le provider
du mode stub.

---

## Décisions à prendre par Vic (liste fermée)

1. **stop@ / opposition (BLOQUANT).** Créer une table de suppression (clé = adresse normalisée
   et/ou IDU + destinataire), une entrée `stop@labuse.immo`, et une **vérification pré-dépôt**
   opposable **inter-comptes**. Aucun envoi réel avant.
2. **Modèle d'adressage PP.** Assumer le « à l'occupant » sur bâti (61,7 % des PP) comme **seul**
   canal PP, et **exclure les terrains nus** du courrier PP (NO-GO). Le valider explicitement dans
   l'UI (« pli à l'occupant, non nominatif »).
3. **PM nominatif : go/no-go.** Câbler l'adresse de siège `owner_enrichment` (40 % des PM) pour un
   pli **nominatif** PM — ou rester en « à l'occupant ». Trancher la fiabilité des sièges
   (domiciliations).
4. **Corps à placeholders non substitués (fiabilité).** Nettoyer/rejouer les 3 demandes vivantes
   43-45 ; **interdire le dépôt** d'un corps contenant `{…}` (garde serveur) ; retirer ou
   sécuriser le chemin back `modules.py` `.format()` (KeyError).
5. **Affirmations d'estimation dans les modèles.** Décider si « potentiel / valorisation / valeur »
   restent dans les ouvertures `standard`/`dormance`/`succession`, ou si on n'affirme un potentiel
   **que** sur parcelle qualifiée (sinon garder `voisin`/`libre`).
6. **Vocabulaire de statut.** Aligner « À déposer » (admin) et « Demandé » (client) sur un seul
   mot ; ré-écrire les libellés legacy « Imprimé/Posté » du Journal.
7. **Prix.** Confirmer le principe « pas de prix affiché avant rappel » ; noter que `tarif()` fuit
   dans le payload `/courrier/statut` — le retirer si le prix doit rester hors ligne. Sourcer le
   coût prestataire (2,69 €) autrement qu'en constante de code.
8. **Facturation courrier.** Choisir : facture séparée manuelle (statu quo) vs ligne Stripe
   metered/hors-abonnement — et brancher, sinon `prix_eur` reste un chiffre mort.
9. **Statuts de retour.** Décider comment « Répondu / Sans réponse » se posent une fois l'envoi
   réel actif (clic client seul aujourd'hui ; aucun délai/automatisation).

---

## Preuves — `captures/courrier-audit1/`

| Fichier | Contenu |
|---|---|
| `00-fiche-bouton-courrier.png` | Fiche parcelle → bouton **« Courrier »** (entrée du parcours) |
| `01-outil-courrier-etape1-destinataires.png` | Étape ① destinataires (« aucune identité de propriétaire particulier ») |
| `02-outil-courrier-etape2-redaction.png` | Étape ② rédaction (4 modèles) |
| `03-outil-courrier-etape3-avant-depot-et-liste.png` | Étape ③ **écran avant dépôt** (sans prix) + « Vos demandes » (liste client) |
| `06-dashboard-courrier-demandes.png` | Dashboard **Courrier** admin (statuts, colonne « Propriétaire » = compte de PM, jamais un particulier) |
| `07-dashboard-pilotage-journal.png` | Pilotage + **Journal** (mélange de libellés legacy, « Stripe non configuré ») |
| `pdf-recto-full.pdf` / `-1.png` | Aperçu recto, données complètes |
| `pdf-fallback-sansdonnee.pdf` / `-1.png` | **PDF d'une parcelle sans donnée** — fallback propre (chemin front) |
| `pdf-defaut-placeholders-demande45.pdf` / `-1.png` | **Défaut vivant** : corps réel de la demande #45, `{parcelle}`/`{commune}`/`{surface}` imprimés bruts |

*Aucun nom de personne physique ne figure dans les captures (destinataires « à l'occupant »,
colonne propriétaire au compte de PM).* Le pli est **mono-page** : « verso » = pied de page légal
sur la même page (pas de seconde page).

---

*Méthode : comptages SQL directs sur la base `labuse` (run servi q_v11_m137) ; lecture de code
(`courrier.py`, `api/courrier.py`, `mailfile`/`mail.py`, `facturation.py`, `modules.py`,
`ModulePanel.tsx`, `ProjetsPanel.tsx`, `admin/Courrier.tsx`) ; navigation directe de l'app
(:8125 / :5325) sans jamais soumettre de demande ni déclencher d'envoi. tsc -b vert.*
