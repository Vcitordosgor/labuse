# M148 — F4 : qui peut générer quoi, au nom de LABUSE

Branché sur `origin/main` @ `111f2376`. **Audit lecture seule — aucune route ne change, aucune protection
posée.** Ce mandat établit la carte ; Vic arbitre la posture, puis un mandat de correction.

**Correction liminaire à M146.** M146 a conclu « la lettre n'est ni derrière l'auth ni dans
`PREFIXES_PROTEGES` » — c'était mesuré **en local**, où l'auth est désactivée par défaut. La réalité est
plus nuancée et je la corrige d'emblée, parce qu'elle change la gravité : **hors `local`, l'auth est
active en fail-closed** (`auth.enabled()` = `bool(auth_password) or env != "local"`, `auth.py:48-52`).
En prod (`LABUSE_ENV=production|pilot`), un appel anonyme sur `/lettre-zonage/<idu>.pdf` reçoit **401**
(ou 503 si aucun mot de passe) via `_auth_guard` (`app.py:214-240`), car la lettre n'est **pas** dans la
liste publique `_PUBLIC` (`auth.py:35-40`). **Ce qui reste vrai — et grave — est différent** : (1) toute
la posture repose sur UNE variable d'environnement ; (2) la lettre **écrit une référence officielle
numérotée** à chaque génération ; (3) un abonné authentifié peut émettre ces attestations pour **n'importe
quelle parcelle**. Le détail suit.

---

## A — La table d'exposition

Douze routes produisent un document. Colonnes de protection évaluées **en prod** (`env≠local`, la seule
config qui compte pour l'exposition réelle ; le local ouvre tout, c'est la machine de dev).

| # | document | route | fichier:ligne | auth prod ? | `PREFIXES_PROTEGES` (rate-limit) ? | quota `porte_export` ? | **écrit en base ?** | classe de contenu |
|---|---|---|---|---|---|---|---|---|
| 1 | **Lettre de zonage** | `GET /lettre-zonage/{idu}.pdf` | `lettre_zonage.py:364` | ✅ 401 si anon | ❌ non | ✅ (`quota.py:62`) | **OUI — réf `LZ-AAAA-NNNN`** (`lettre_zonage.py:129`) | **attestation** |
| 2 | Argumentaire | `GET /argumentaire/{idu}.pdf` | `argumentaire.py:470` | ✅ | ❌ non | ✅ (`:481`) | non | **position économique** |
| 3 | Dossier banquier | `GET /dossier-banquier/{idu}.pdf` | `banquier.py:282` | ✅ | ✅ (`/dossier*`) | ✅ (`:291`) | non (cache LRU) | public enrichi |
| 4 | Dossier parcelle | `GET /dossier/{idu}.pdf` | `dossier.py:64` | ✅ (plan) | ✅ | ✅ (`:78`) | oui — `usage_compteurs` (compteur, bénin) `:114` | public enrichi (= rapport Flash marqué) |
| 5 | Pré-dossier PC (ZIP) | `GET /pre-dossier/{idu}.zip` | `pre_dossier.py:731` | ✅ (plan) | ✅ | ✅ (`:752`) | non | public enrichi + CERFA |
| 6 | Courrier | `POST /courrier/pdf` | `courrier.py:77` | ✅ | ✅ (`/courrier`) | ❌ | non | texte utilisateur |
| 7 | Fiche premium | `GET /parcels/{idu}/export.pdf` | `app.py:3189` | ✅ | ✅ (`/parcels`) | ❌ | non | public enrichi |
| 8 | Fiche export MD/HTML | `GET /parcels/{idu}/export` | `app.py:4001` | ✅ | ✅ | ❌ | non | public enrichi |
| 9 | Projet PDF | `GET /projets/{pid}/export.pdf` | `projets.py:1332` | ✅ | ❌ non | ❌ | non | **données du compte** (cloisonné) |
| 10 | Projet CSV | `GET /projets/{pid}/export.csv` | `projets.py:1350` | ✅ | ❌ non | ❌ | non | **données du compte** (cloisonné) |
| 11 | Digest veille HTML | `GET /events/digest.html` | `events.py:1050` | ✅ | ❌ non | ❌ | non | données du compte |
| 12 | **Flash (payé 79 €)** | `GET /flash/telecharger?token=` | `onboarding.py:643` | **PUBLIC** (`_PUBLIC`) | ❌ | ❌ | non (sert un fichier déjà généré) | **attestation/dossier payé — token** |

### Ce que couvrent réellement les deux constantes citées par le mandat

- **`_auth_guard` (`app.py:214-240`)** est le VRAI mur, pas `tenant.py`. Ligne 231 :
  `if not auth.enabled() or auth.is_public(path): return call_next`. Donc : **hors local → auth active**,
  et **seules les routes de `_PUBLIC` passent** (`auth.py:35-40` : santé, `/login`, légal, onboarding,
  webhook Stripe, et **les 4 routes `/flash*`**). Aucune route document sauf Flash n'y est.
- **`PREFIXES_PROTEGES` (`protection.py:150-152`)** ne fait PAS d'auth : c'est le rate-limit / quota-fiches
  (`garde_protection`, `protection.py:296-302`). Un chemin hors liste **passe tout droit, sans rate-limit**.
  Résultat : **`/lettre-zonage` et `/argumentaire` n'ont aucun rate-limit** (mais un quota `porte_export`) ;
  `/projets/*` et `/events/digest` n'ont **ni rate-limit ni quota** (mais sont cloisonnés au compte).
- **`tenant.py:1-34`** : la cloison `compte_id` (`IS NOT DISTINCT FROM`) ne s'applique qu'aux **tables
  client** (`SCOPED_TABLES` : projets, filtres, veilles, signalements…). Les **parcelles / scoring /
  zonage sont GLOBAUX** (donnée publique, non cloisonnée). Conséquence directe pour l'attestation :
  **la lettre sert n'importe quel IDU** — il n'existe aucune notion de « ce compte a le droit d'attester
  cette parcelle ».

---

## B — Ce qui est réellement atteignable (testé en local)

> ⚠ Les tests ci-dessous tournent **en local** (`env=local`, auth désactivée) — c'est la config de dev,
> **pas** la prod. Ils prouvent le comportement des couches quand l'auth est off (le scénario du
> mis-configuré), et surtout l'**effet d'écriture**, qui est indépendant de l'environnement.

1. **Chaque route sur un IDU réel, sans session.** En local, `_auth_guard` laisse passer
   (`auth.enabled()` False) → toutes répondent. **En prod, seules les routes `_PUBLIC` (Flash) répondent
   sans session** ; les 11 autres → 401. C'est une lecture de code (`app.py:231` + `auth.py:59-64`),
   pas contournable sans session valide hors local.

2. **La lettre : deux appels → deux réfs `LZ-` consommées ?** **PROUVÉ.** En reproduisant exactement
   `_ref_attestation` (`lettre_zonage.py:113-130`) contre la base réelle :
   ```
   LZ refs avant : 19
   appel 1 → LZ-2026-0020
   appel 2 → LZ-2026-0021   (même IDU, deuxième appel)
   LZ refs après : 21  (delta = 2)
   ```
   **Chaque génération écrit une ligne** dans `lettre_zonage_refs` et incrémente le numéro officiel. La
   numérotation est `count(*) + 1` formatée `%04d` (`:125-127`) — **pas une séquence DB bornée** :
   déborde silencieusement après 9 999, et est sensible aux suppressions (trous / collisions, gérées par
   un retry sur `UNIQUE`). *(Test nettoyé : mes 2 réfs supprimées, base rendue à 19.)*

3. **Flash — le PDF payé est-il obtenable sans payer / le token devinable ?** **NON — tunnel sûr.**
   - Token = `secrets.token_urlsafe(32)` = **256 bits** (`facturation.py:202`), **stocké haché SHA-256**
     (`token_hash`), jamais en clair. Non énumérable, non devinable.
   - Validation : `WHERE token_hash=:h AND expire_at > now() AND statut='generee'` (`facturation.py:214`)
     — comparaison faite par PostgreSQL (pas de fuite de timing Python), **expiration réelle 30 j**
     (`config.py:120` `flash_token_days=30`, posée à la génération `facturation.py:167`).
   - Le PDF n'est généré **qu'après** le webhook Stripe `checkout.session.completed` → `_flash_fulfill`
     → `statut='generee'` (`facturation.py:140-174`), avec filet de réconciliation qui **revérifie le
     paiement chez Stripe** avant tout (`reconcile_flash`). **Le PDF n'est pas obtenable sans paiement.**
   - Le `id serial` (réf `FL000xxx`) n'apparaît dans aucune URL/réponse — seul le token compte.

4. **Le canal Flash de test (M145).** Les fixtures `tests/test_audit_stripe.py` écrivent dans la vraie
   base **uniquement si pytest est lancé contre elle** (constat M145 : IDU synthétique `974990FL…`, réfs
   `FL000985-988`, PDF orphelins, aucune écriture comptable). **Non atteignable par HTTP** — ce n'est pas
   une route, c'est un effet de bord de la suite de tests. Hors surface d'exposition réseau.

---

## C — Ce que ça coûte, en trois angles

### C1 — Juridique (par classe de contenu)

- **Attestation (lettre, #1)** — le cas fort. Document numéroté `LZ-AAAA-NNNN`, clôturé « Édité par
  LABUSE… la référence est enregistrée par LABUSE et permet de vérifier l'authenticité de l'édition »
  (`lettre_zonage.py:265-275`). Un tiers qui en produit une au nom de LABUSE engage **la parole de LABUSE
  devant un notaire/banque**. En prod l'anonyme est bloqué ; **mais** (a) un abonné peut en émettre pour
  **n'importe quelle parcelle** (aucune cloison, cf. A), et (b) si `env` est mal configuré, l'émission
  redevient anonyme. La numérotation officielle est écrite **avant** tout contrôle de compte réel.
- **Position économique (argumentaire, #2)** — le second. Chiffre une décote/contre-offre attribuée à
  LABUSE (`argumentaire.py`, calcul bilan inversé). Diffusé par un tiers, c'est un **avis de valeur** au
  nom de LABUSE. Pas d'écriture en base (moindre que la lettre), mais même dépendance à l'auth.
- **Public enrichi (#3-8, 12)** — faisabilité/zonage/DVF calculés par LABUSE. Risque juridique moindre
  (indicatif, sourcé, disclaimers), mais reste attribué à LABUSE.
- **Données du compte (#9-11)** — cloisonnées ; le risque est la fuite inter-comptes, déjà traitée par
  `tenant.py` (SEC-IDOR).

### C2 — Commercial (Flash = 79 €)

Quelles routes servent **gratuitement** ce que Flash facture ? Réponse rassurante **en prod** : aucune
sans abonnement. Le contenu Flash (faisabilité + bilan + zonage + DVF) est recoupé par le **dossier
parcelle** (`dossier.py` réutilise littéralement `flash.render_report_html`), la **fiche premium**
(`/parcels/{idu}/export.pdf`) et le **dossier banquier** — mais ces trois sont **derrière l'auth + quota
d'abonnement**. Le Flash 79 € est la voie **non-abonné** (public + payé), correctement isolée. **Le
recouvrement n'existe qu'en local / si `env` est mal configuré** : là, `/dossier/{idu}.pdf` sert
gratuitement le rapport Flash complet. C'est le même angle mort que le reste : dépendant de l'environnement.

### C3 — Charge (vecteur d'épuisement)

Non chronométré au banc (deps WeasyPrint/pango absentes en local) ; caractérisation par le code :

| document | compute par génération | rate-limit ? |
|---|---|---|
| Flash `/telecharger` | **~0** (sert un fichier déjà écrit) | non — mais rien à calculer |
| Lettre | `collect_report_data` (résiduel + faisabilité + cascade + DVF) + 1 tuile carte réseau + fpdf2 | **NON** ⚠ |
| Argumentaire | idem + bilan inversé | **NON** ⚠ |
| Dossier / banquier / fiche | `collect_report_data` + **WeasyPrint** (dossier/banquier) — le plus lourd | oui (`/dossier`,`/parcels`) |
| Pré-dossier ZIP | tuiles ortho réseau + plusieurs PDF + zip — **le plus coûteux** | oui (`/pre-dossier`) |
| Projet PDF/CSV | requête shortlist du compte | **NON** (mais borné au compte) |

**Les deux routes sans rate-limit ET à calcul lourd sont la lettre et l'argumentaire** : un appelant
authentifié (ou anonyme si `env` mal posé) peut les marteler dans la limite du quota `porte_export`
(30-200/j) — vecteur de charge modéré, borné par le quota, mais non rate-limité.

---

## D — Les options, avec leurs conséquences

Chacune : ce qu'elle protège · effort · **ce qu'elle casse** · règle-t-elle le cas lettre ?

1. **Statu quo assumé et documenté.** Repose sur `LABUSE_ENV≠local` (fail-closed déjà en place).
   Protège : rien de neuf. Effort : 0 (juste consigner). Casse : rien. **Cas lettre : NON** — l'abonné
   mint toujours pour n'importe quelle parcelle, et une seule mauvaise config rouvre tout.

2. **Session requise pour tout, sauf le tunnel Flash.** = l'état actuel en prod, mais rendu **explicite
   et indépendant de `env`** : ajouter une dépendance « compte requis » sur les routes document (defense-
   in-depth : ne plus dépendre du seul garde global + `env`). Effort : faible. Casse : **un lien envoyé
   à un notaire ne s'ouvre plus sans compte** (à combiner avec l'option 4). **Cas lettre : partiellement**
   (bloque l'anonyme même si `env` mal posé ; ne borne pas l'abonné).

3. **Lecture ouverte / écriture protégée.** Le PDF de la lettre peut se rendre, mais la **numérotation
   officielle `LZ-` n'est écrite qu'avec une session** (garder `_ref_attestation` derrière `compte_id`).
   Effort : très faible (~5 lignes, une garde sur l'écriture). Casse : rien de visible (sans compte, la
   lettre sortirait « réf. non attribuée » — dégradée mais honnête). **Cas lettre : OUI sur le point le
   plus grave** — plus aucune attestation NUMÉROTÉE émise anonymement, quel que soit `env`.

4. **Lien signé à durée limitée pour le partage tiers** (patron du token Flash, déjà éprouvé). Un abonné
   génère un lien signé + expirant pour un IDU ; le notaire l'ouvre **sans compte**. Effort : moyen
   (réutilise l'infra token de `facturation.py`). Casse : rien — **résout le besoin “lien notaire”** sans
   ouvrir la route. **Cas lettre : OUI** (émission tracée, partage borné).

5. **Quota / rate-limit par IP-session sur les routes ouvertes.** Ajouter `/lettre-zonage` et
   `/argumentaire` à `PREFIXES_PROTEGES` (une ligne). Effort : très faible. Casse : rien. **Cas lettre :
   partiellement** — borne la charge et ralentit une énumération si `env` mal posé ; ne traite pas
   l'autorité d'attestation ni l'écriture.

---

## E — Recommandation

**Le cas grave est la lettre** : c'est la seule route qui **émet un artefact officiel numéroté**, pour
**n'importe quelle parcelle**, et toute la protection repose sur une variable d'environnement.

**Geste urgent, minimal, maintenant (option 3) :** mettre l'écriture `_ref_attestation`
(`lettre_zonage.py:113-130`, l'INSERT `LZ-`) **derrière une session `compte_id`**. ~5 lignes, aucune
route ne change de contrat, ni le Copilote ni un lien Flash ne cassent (le PDF continue de se rendre ;
seule la **numérotation officielle** exige un compte). Cela coupe net le risque le plus fort — plus
aucune attestation numérotée LABUSE émise anonymement — **et** rend ce point indépendant d'une mauvaise
config `env` (defense-in-depth). C'est le meilleur rapport risque-réduit / effort.

**Ensuite (chantier, pas urgent), à arbitrer par Vic :**
- **Option 4** (lien signé expirant) pour le partage vers un tiers — c'est le bon patron pour « un lien
  notaire s'ouvre sans compte » sans ouvrir la route, et il ferme aussi la question de l'argumentaire.
- **Décision de fond** : un abonné doit-il pouvoir émettre une attestation pour **une parcelle qu'il
  n'analyse pas** ? (cloison d'attestation — aujourd'hui inexistante, cf. A / `tenant.py`).
- **Option 5** (ajouter lettre + argumentaire au rate-limit) — durcissement à une ligne, gratuit.

**Ops, urgent et gratuit :** garantir `LABUSE_ENV≠local` sur l'instance déployée (le fail-closed existe
déjà côté auth/secret via `exiger_secret_prod` — ajouter la même exigence sur `env` au démarrage
fermerait le dernier « ouvert par accident »). Les docs le signalent déjà
(`docs/AUDIT_COMPLET_LABUSE_APP_CODE.md:169,202`).

**Ce qui peut attendre / n'est PAS un problème :** le **tunnel Flash est sûr** (token 256 bits, payé,
expirant — rien à faire). Les exports **projet/digest** sont cloisonnés au compte (charge only). Le
recouvrement commercial n'existe **qu'en local**.

---

*Contrôles : garde-fou OK (branché `origin/main` @ `111f2376`, hors périmètre de l'avance) ; inventaire
des 12 routes sourcé fichier:ligne ; effet d'écriture `LZ-` prouvé empiriquement contre la base réelle
(2 appels = 2 réfs, nettoyé) ; tunnel Flash vérifié par lecture de code (entropie, hachage, expiration,
gate de paiement). **Aucune route, aucune protection modifiée** (audit lecture seule). CC ne merge jamais
— Vic arbitre la posture, puis un mandat de correction.*
