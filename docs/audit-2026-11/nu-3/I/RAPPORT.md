# MANDAT AUDIT-NU-3 — Lot I : Temps · Comptes · Exports · Admin

**Registre.** Audit **LECTURE SEULE** joué le 2026-11-01. Branche `audit/nu-3-i`, worktree `~/Desktop/labuse-nu3-i`, API **9300** (venv PDF-capable emprunté à `labuse-main/.venv`, Python 3.12, WeasyPrint OK ; `PYTHONPATH` du worktree ; `LABUSE_DATABASE_URL` → base Mac `labuse`, **434 582 parcelles**, run servi `q_v20`, SRID 2975, PostGIS). Front **non reconstruit** (`frontend/dist` absent) → les exports sont générés par leurs **routes API réelles** (identiques à ce que le front ouvre) et les constats front sont **statiques + preuves Node**. Aucune écriture base, aucun merge, aucun accès prod, **aucun e-mail envoyé** (dry-run étanche).

> **Intendance horloge.** `sudo`/`systemsetup` exigent le mot de passe administrateur, **absent** dans cette session. Je n'ai donc **jamais pu** déplacer physiquement l'horloge du Mac ni toucher au réglage « heure automatique » — et je ne l'ai pas fait. La preuve de non-altération est au §0. Faute de pouvoir bouger l'heure mur, j'ai exercé **le levier exact que la doctrine `tz.py` redoute** — le **fuseau du process** — via la variable `TZ` (dans un process Node éphémère + raisonnement sur le process Python), ce qui reproduit la divergence « machine ≠ Réunion » sans toucher au système. Le fuseau système n'a jamais été modifié.

> **Captures.** `docs/audit-2026-11/nu-3/I/captures/` est ignoré par le dépôt (politique MENAGE-1 `**/captures/`, binaires hors git) — non forcé. Les PDF générés et images extraites vivent sous `/tmp/nu3i/` (hors dépôt).

---

## §0 — Preuve de non-altération de l'horloge (rendu de main)

| Instant | Valeur |
|---|---|
| Mac local (début) | `2026-11-01 19:19:26 CET (+0100)` |
| Mac local (fin) | `2026-11-01 19:37:51 CET (+0100)` |
| Mac UTC (fin) | `2026-11-01 18:37:51 UTC` |
| Référence externe `Date:` Cloudflare/Google (fin) | `Sun, 01 Nov 2026 18:37:51 GMT` |

L'heure UTC du Mac **égale à la seconde** l'horodatage HTTP de deux serveurs externes → l'horloge est **exacte et synchronisée réseau**. `systemsetup -getusingnetworktime` renvoie « You need administrator access » (confirme que je n'avais pas le privilège de la changer). Aucune commande de réglage d'horloge n'a été émise ; le seul `TZ=` posé l'a été dans un **sous-process Node éphémère**. L'horloge est rendue **inchangée, sur l'heure automatique**.

NB : le Mac tourne en **CET (+01:00)** (01/11 = heure d'hiver métropole depuis le 25/10) — pas CEST ; la docstring `tz.py` qui dit « la machine tourne en CEST » est saisonnièrement datée mais sans incidence (l'écart Réunion est +3 h en été, **+4 h en hiver** → la fenêtre de divergence de jour est encore plus large aujourd'hui qu'écrit).

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Scénarios joués** | **~200** : exports générés sur **20 parcelles** témoins (5 types single-parcel × 20 = 100 PDF + étude-zone ×2, comparatif, pré-dossier zip ×1, courrier ×3) ; 100+ PDF inspectés (`pdfinfo`/`pdftotext`/`pdfimages`/`pdffonts`, rendu `pdftoppm`) ; preuve Node de l'off-by-one date sous 4 fuseaux ; recalcul taxe d'aménagement vs barème 2026 ; vérif job-honnêteté en `psql` sur `job_runs`/`ops_incidents` ; rendu local des 5 e-mails en dépôt ; 3 audits de code forkés (temps/comptes/admin). |
| **Bloquant** | **0** |
| **Majeur** | **5** |
| **Mineur** | **13** |
| **Dette** | **10** |

**Verdict de synthèse.** Le **socle temps du backend est propre** : plus aucun `date.today()`/`datetime.now()` nu ne pilote une fenêtre métier ; `db.py` force `timezone=Indian/Reunion` sur le pool unique (vérifié : les `job_runs` sortent en `+04`) ; les `now()` vivants portent `timezone.utc` (comparés à des `timestamptz`) ou `REUNION_TZ`. **Les exports sont solides** : 0 champ vide imprimé (aucun `None`/`null`/`{{var}}` sur 100+ PDF), cartes embarquées et lisibles, refus propres et motivés (422 JSON) là où une donnée manque. **L'arithmétique est juste** (taxe == barème au centime, totaux == somme des lignes). **Aucun secret/jeton/DSN/trace ne fuit** et **toutes** les routes `/admin/*` sont gardées. Le danger n'est donc ni dans le calcul ni dans la fuite : il est (1) côté **comptes** — un compte « paiement requis » garde **tout l'accès** et peut se reconnecter ; (2) côté **admin/jobs** — un cron **jamais lancé** ou **gelé** peut rester **invisible ou au vert** ; (3) côté **temps du navigateur** — une famille de formateurs de dates ne fige pas `Indian/Reunion` (impact réel faible car l'audience LABUSE est à l'est d'UTC, mais c'est une violation de doctrine) ; (4) un **export ZIP** porte des dates incohérentes (1980 + heure machine CET au lieu de Réunion).

---

## Les 20 parcelles d'export

| rôle | IDU | commune |
|---|---|---|
| nue zone U | 97411000IN0347 | Saint-Denis |
| maison réf (DVF 2024 205 k€) | 97411000IE0241 | Saint-Denis |
| copropriété (RNIC) | 97411000HC0139 | Saint-Denis |
| zone N | 97424000AE0050 | Cilaos |
| zone AU | 97424000AM0893 | Cilaos |
| PPR rouge/bleu | 97421000AB0133 | Salazie |
| très petite | 97411000AO0753 | Saint-Denis |
| très grande (>1 ha) | 97411000EY0173 | Saint-Denis |
| RNU / sans PLU | 97417000BI0076 | Saint-Philippe |
| multi-bâti | 97411000AB0785 | Saint-Denis |
| vente 2025 | 97411000HN0074 | Saint-Denis |
| + 9 communes contrastées | 97402000AB0002 (Bras-Panon) · 97408000AB0026 (La Possession) · 97407000AB0009 (Le Port) · 97422000AB0039 (Le Tampon) · 97409000AB0050 (Saint-André) · 97410000AB0003 (Saint-Benoît) · 97412000AE0014 (Saint-Joseph) · 97413000AC0034 (Saint-Leu) · 97416000CD0012 (Saint-Pierre) | — |

---

## A. TEMPS

### Ce qui est solide (vérifié)
- **Backend** : aucun `date.today()`/`datetime.now()`/`utcnow()` nu ne pilote une fenêtre métier (les occurrences résiduelles sont dans des docstrings documentant leur retrait). `tz.now_reunion()`/`today_reunion()` et les `now() AT TIME ZONE 'Indian/Reunion'` SQL couvrent les surfaces métier (Radar « en vente depuis N j », digests, quotas, millésimes, dates PDF, e-mails). `db.py:87-91` force `-c timezone=Indian/Reunion` sur le moteur **unique** partagé par API, ORM, batchs et worker PDF ; **preuve** : `job_runs.fin` ressort en `+04`. Les `datetime.now(timezone.utc)` (expiry essai, fraîcheur) sont comparés à des `timestamptz` absolus → insensibles au fuseau.
- Les surfaces front **récemment durcies** figent bien `Indian/Reunion` : `admin/Radar.tsx`, `admin/Produit.tsx`, `RadarHub.tsx`, `admin/Licences.tsx` (`fmtVisite`).

### I-TPS-01 — MINEUR — La famille `lib/format.ts` ne fige pas le fuseau → dates **J-1** pour tout navigateur à l'ouest d'UTC
- **Où** : `frontend/src/lib/format.ts:58-89` — `fmtDate`, `fmtDateNum`, `fmtDateSitadel`, `fmtDateSirene` : `new Date("YYYY-MM-DD").toLocaleDateString('fr-FR', …)` **sans** `timeZone`. ~35 appels dans 15 fichiers (fiche, outils, tables) — dates DVF, permis, approbation PLU, création SIRENE.
- **Affiché vs juste** (preuve Node exécutée sous 4 fuseaux) :

  | entrée | Indian/Reunion & Europe/Paris | America/Chicago & Pacific/Honolulu |
  |---|---|---|
  | `fmtDate("2026-11-01")` | **1 nov. 2026** | **31 oct. 2026** |
  | `fmtDateSitadel("2024-01-01")` | **2024** | **31/12/2023** (perd même la forme « année seule ») |
  | `fmtDate("2026-07-12")` | **12 juil. 2026** | **11 juil. 2026** |

- **Nuance honnête** : l'audience réelle de LABUSE (Réunion UTC+4, métropole UTC+1/+2) est **entièrement à l'est d'UTC** → en pratique l'affichage est correct pour tous les clients attendus. Le bug ne se déclenche que pour un navigateur réglé à l'ouest d'UTC (déplacement, VPN, fuseau mal réglé). C'est une **violation de doctrine** (« tout en heure de La Réunion ») à impact utilisateur faible.
- **Amélioration** : poser `timeZone: 'Indian/Reunion'` dans les `toLocaleDateString` et dériver jour/mois/année de `fmtDateSitadel`/`fmtDateSirene` via `Intl.DateTimeFormat('fr-CA',{timeZone:'Indian/Reunion'}).formatToParts`. **Un seul point** corrige les 35 surfaces.

### I-TPS-02 — MINEUR — Export ZIP pré-dossier PC : dates de fichiers incohérentes (1980 + heure machine CET, pas Réunion)
- **Où** : `src/labuse/api/pre_dossier.py:1117-1134`. Les pièces (CERFA, plans, notices) sont écrites par `z.writestr(nom_str, …)` → `zipfile` horodate à `time.localtime()` = **heure locale machine (CET ici)**. Le LISEZMOI est écrit par `z.writestr(zipfile.ZipInfo("…-LISEZMOI.txt"), …)` → `ZipInfo` **sans `date_time`** → défaut **1980-01-01 00:00**.
- **Repro** (exécutée) : `unzip -l` du pré-dossier `97411000IE0241.zip` →
  ```
  11-01-2026 19:31   …-CERFA-13406-17-prerempli.pdf     (et 6 autres pièces, heure CET machine)
  01-01-1980 00:00   …-LISEZMOI.txt
  ```
- **Affiché vs juste** : dans un même livrable client, sept fichiers sont datés **du 01/11/2026 à 19 h 31 CET** (= 21 h 31 Réunion — fuseau machine, pas Réunion) et un huitième **du 01/01/1980**. Un client qui trie son dossier par date voit 1980 et une heure métropole.
- **Amélioration** : construire **tous** les `ZipInfo` avec `date_time = now_reunion().timetuple()[:6]` (source unique, déjà le motif LISEZMOI du module pour les *dates imprimées*) — jamais `writestr(str, …)` nu.

### I-TPS-03 — MINEUR — Horodatages du cockpit admin « Données » en heure navigateur, pas Réunion
- **Où** : `frontend/src/components/admin/circuit/*.tsx` et `admin/Cron.tsx` — ~8 `new Date(iso).toLocaleString('fr-FR', {hour,minute})` **sans** `timeZone`.
- **Affiché vs juste** : l'exploitant en métropole voit les « dernière exécution / prochaine » en **CET**, alors que `admin/Radar.tsx`/`admin/Produit.tsx` (mêmes onglets admin) figent **Réunion** → deux onglets admin affichent des heures contradictoires pour le même instant. Enjeu faible (admin-only) mais même classe de bug.
- **Amélioration** : figer `timeZone:'Indian/Reunion'` partout dans le cockpit, comme Radar/Produit.

### I-TPS-04 — MINEUR — Date du brief Copilote et « Document généré le » : off-by-one date
- **Où** : `copilote/AccueilCopilote.tsx:108` (`toLocaleDateString('fr-FR',{weekday,day,month})` sans TZ, sur `genere_le` = `now_reunion().isoformat()`), `documents/DocumentsView.tsx:366` (`dateFr` via `getDate()/getMonth()/getFullYear()` locaux), `fiche/ContextePanel.tsx:115`.
- **Affiché vs juste** : un brief généré « lundi 7 h Réunion » (= dimanche 21 h UTC) s'affiche « **dimanche** » pour un navigateur à l'ouest ; la ligne « Document généré le JJ/MM/AAAA » de la bibliothèque dérive pareillement. Même nuance d'audience qu'I-TPS-01.
- **Amélioration** : `{ …, timeZone: 'Indian/Reunion' }` sur ces trois formateurs.

### I-TPS-05 — DETTE — E-mail maintenance : fenêtre en ISO brut sans mention « heure Réunion »
- **Où** : `src/labuse/emails.py:143` — `maintenance_email` imprime « Fenêtre de coupure : début `2026-11-02 22:00`, fin `2026-11-02 22:30` » tel que fourni par l'appelant, format ISO, **sans** libellé de fuseau. Les autres e-mails horodatés (`onboarding.py:641`, `mdp_modifie`) disent explicitement « (heure Réunion) ».
- **Amélioration** : formater en français + suffixer « (heure de La Réunion) », comme les autres e-mails.

---

## B. COMPTES & E-MAILS

> **Limite structurante.** Les **corps** des 16 e-mails de cycle de vie (essai, bienvenue, suspension, résiliation, relance carte…) **ne sont pas dans le dépôt** : ils vivent chez **Brevo** ; le code ne détient que l'**ID de template**, le **nom** et la **liste de variables** (`src/labuse/brevo.py:44-98`). Je **ne peux donc pas** relire sujet/accents/montant/TVA de ces 16 templates sans appel réseau Brevo (interdit ici). Les 5 e-mails **en dépôt** (`emails.py`) ont été **rendus et relus** (ci-dessous). La recette de rendu dry-run étanche (`.eml`, aucun réseau) est `mail.ecrire_dryrun_template(key, to, params)` ; l'aperçu du **vrai** corps Brevo nécessiterait `BREVO_API_KEY` + `GET /admin/licences/{id}/mail/{key}/apercu`.

### Cycle de vie (vérifié dans le code)
Statut compte : `invite | actif | paiement_requis | suspendu | resilie` (`comptes.py:74`). Paiement OK → `actif` (`facturation.py:453`) ; fin d'essai → `suspendre_compte` (`comptes.py:436`) ; `invoice.payment_failed` → `paiement_requis` (`facturation.py:470`) ; `subscription.deleted` → `suspendre_compte` (`facturation.py:497`, pose `suspendu`, **jamais** `resilie`). Effacement RGPD **réel** (DELETE + cascade FK + audit anonymisé) mais **CLI seule** (`cli.py:4527`, `effacer_compte_rgpd` `comptes.py:797`).

### E-mails en dépôt — rendus et relus (verts)
`reset_password`, `digest_notifications`, `maintenance_email`, `mise_en_vente_email`, `annonce_email` : **accents propres** (`réinitialisation`, `événements`, vrai signe moins `−5 %`), **liens absolus** (`public_base_url`), expéditeur unique `contact@labuse.immo`, reset anti-phishing + « valable 1 heure », digest avec lien de désinscription, maintenance sans désinscription (correct, message de service). Seule réserve : I-TPS-05 (ISO brut).

### I-CPT-01 — MAJEUR — « Paiement requis » n'ouvre aucune porte de régularisation et **ne coupe rien**
- **Où** : garde d'accès `comptes.py:466` (`if statut_compte in ("suspendu","resilie","invite"): return None` — **`paiement_requis` absent**) ; `POST /login` `app.py:822` a des branches pour `invite` (renvoi Checkout, pas de session), `suspendu` (écran « régulariser », pas de session), admin (2FA) — **aucune branche `paiement_requis`** → tombe en `creer_session` + cookie frais ; `verifier_login` `comptes.py:359` ne bloque que l'utilisateur `("supprime","suspendu","invite")` et un compte `paiement_requis` a un user `actif`.
- **Affiché vs juste** : un compte dont la carte est **refusée** (`invoice.payment_failed`) **garde l'accès complet à 349 €/mois ET peut se reconnecter** tant que Stripe n'escalade pas en `subscription.deleted` (→ `suspendu`). Le « dunning » repose entièrement sur les relances Stripe. Si c'est une grâce payante voulue, **à documenter** ; sinon, `paiement_requis` manque dans la blocklist `comptes.py:466` **et** d'un branchement `/login`. (Ré-confirmation vivante du constat NU-F.)
- **Amélioration** : décider la politique de grâce ; si coupure voulue, ajouter `paiement_requis` à la blocklist et une branche `/login` « abonnement à régulariser » (comme `suspendu`).

### I-CPT-02 — MINEUR — E-mail `resiliation` sans date pour un abonné **payant** résilié
- **Où** : `facturation.py:500` → `DATE_FIN_ACCES = essai_expire_at` (`comptes.py:744` → `""` si jamais d'essai ; `dashboard.py:1086`). L'anti-doublon « le le » n'est appliqué qu'à `DATE_FIN_ACCES` (`dashboard.py:1091`).
- **Affiché vs juste** : le template Brevo affiche probablement « votre accès prend fin le **{{DATE_FIN_ACCES}}** » → pour un abonné payant (jamais passé par un essai), **chaîne vide** → « …prend fin le  ». À confirmer au rendu Brevo. **Amélioration** : passer la vraie fin d'accès (fin de période Stripe), pas `essai_expire_at`.

### I-CPT-03 — MINEUR — E-mail `essai` : risque « le le » sur `FIN_ESSAI`
- **Où** : `dashboard.py:1068` préfixe `FIN_ESSAI` par « le » (`_fmt_reunion`), mais l'anti-doublon n'est posé que sur `DATE_FIN_ACCES` (`:1091`), pas sur `FIN_ESSAI`. Si le sujet/corps Brevo dit « fin **le** {{FIN_ESSAI}} » → « le le 12/11 ». **Amélioration** : étendre l'anti-doublon à `FIN_ESSAI` ou ne pas préfixer.

### I-CPT-04 — MINEUR — Template `souscription` pointe `/souscrire`, qui n'est pas une route servie
- **Où** : `dashboard.py:1070` `LIEN_SOUSCRIPTION = public_base_url + "/souscrire"`. Aucune route `/souscrire` trouvée. **Affiché vs juste** : lien possiblement mort dans l'e-mail de souscription. **Amélioration** : pointer la vraie route de souscription/Checkout.

### I-CPT-05 — DETTE — Template `email_change` **mort** → un changement d'adresse ne notifie pas l'ancienne boîte
- **Où** : `brevo.py:92` (défini) ; **aucun déclencheur** (pas de route de changement d'e-mail, pas de branche params). **Angle sécurité** : si un jour le changement d'e-mail existe sans notifier l'ancienne adresse, c'est un vecteur de prise de compte silencieuse. **Amélioration** : brancher la notification à l'ancienne adresse le jour où le changement d'e-mail existe.

### I-CPT-06 — DETTE — RGPD : effacement **CLI-only**, aucun parcours self-service ni endpoint HTTP
- **Où** : `cli.py:4527` seul appelle `effacer_compte_rgpd`. **Affiché vs juste** : le droit d'effacement (RGPD art. 17) ne peut s'exercer que par intervention manuelle de l'exploitant. Acceptable pour un produit mono-promoteur, **à documenter** (délai/canal).

### I-CPT-07 — DETTE — TVA : mention « franchise 293 B » par défaut, non apposée sur la facture d'abonnement, et dépassement de seuil annoncé
- **Où** : `config.py:306` `facture_mention = "TVA non applicable, art. 293 B du CGI."` posée sur la **facture Stripe du Flash** (`facturation.py:192`) ; l'abonnement Intégral (`subscription`, `facturation.py:135`) **ne force pas** `invoice_creation` → la mention dépend des réglages Stripe. Le commentaire `config.py:303-305` admet lui-même : « le MRR visé **dépasse le seuil de franchise dans l'année** ».
- **Affiché vs juste** : La Réunion (DOM) relève des taux **8,5 %/2,1 %**, pas de la métropole ; tant que Vic reste sous le seuil de franchise, « 293 B, TVA non applicable » est correct et « TTC = HT » (prix `config.py:194,198` cohérents). **Mais** (a) la facture d'**abonnement** peut ne pas porter de mention, (b) au franchissement du seuil annoncé, la mention et le régime devront basculer. **Amélioration** : forcer `invoice_creation.footer` aussi en mode `subscription` ; planifier la bascule d'assujettissement (déjà signalé en commentaire).

> Côté solide confirmé : webhooks signés + dédup transactionnelle (`facturation.py:390`), garde prix `_garde_coherence_prix` (refus de facturer si Stripe ≠ affiché), anti-énumération du reset (`comptes.py:551`), aucun secret/jeton en clair dans les e-mails, tokens stockés en SHA-256, `disableTracking` Brevo. Le lien de désinscription Radar expose `compte_id` en clair dans l'URL (`digests.py:544`) mais est gardé par token (DETTE mineure, non recomptée).

---

## C. EXPORTS

**Méthode.** 20 parcelles × {dossier, financier, apporteur, gabarit, estimer} = 100 PDF + étude-zone (×2), comparatif, pré-dossier (zip), courrier (×3). Mesures : HTTP, octets, pages (`pdfinfo`), temps (`curl %{time_total}`), fontes embarquées (`pdffonts`), images/cartes (`pdfimages`), texte (`pdftotext`), rendu page (`pdftoppm`).

### Ce qui est solide (vérifié)
- **0 champ vide imprimé** : scan `None|null|NaN|undefined|{{var}}|[object Object]` sur 100+ PDF → **aucune occurrence** (les hits `€/m²` sont l'unité, toujours précédée du nombre, ex. « 3 286 €/m² »).
- **Cartes embarquées et lisibles** : chaque Dossier/Apporteur/Étude-zone porte ≥ 1 image (orthophoto) + fontes embarquées ; **aucun** dossier sans carte. Rendu `pdftoppm` : la parcelle est **tracée** (overlay vectoriel) sur l'ortho ; l'ortho reste **lisible en niveaux de gris** (conversion PIL vérifiée).
- **Refus propres et motivés** : `financier` → **422 JSON** « document_non_etablissable » listant les manques (`Programme constructible`, `Régime de TVA`) ; `gabarit` → **422** « donnée réglementaire manquante » quand non calculable ; parcelle disparue → 422 motivé. Jamais de 500, jamais de PDF à moitié rempli.
- **Courrier** : recto/verso composés serveur, destinataire « À l'occupant » (**aucun particulier nommé** — RGPD), cas non adressable **estampillé** « Aperçu — pli non déposable », 0 placeholder `{…}`.
- **Pré-dossier ZIP** : 8 pièces cohérentes (CERFA 13406\*17 pré-rempli *champs terrain seuls*, PCMI1/2/4/7-8, règles zonage, enveloppe, LISEZMOI honnête expliquant la superficie non pré-remplie). CERFA millésime vérifié affiché (21/08/2026).
- **Cohérence écran==PDF** : adresse `40 Chemin du Milieu, 97490 Saint-Denis` identique API/Dossier/Apporteur/Courrier ; « Prix ancien médian 3 286 €/m² » == « Maison 3 286 €/m² » sur la maison IE0241 (NU-A-002 semble corrigé sur ce témoin).

### Tailles / temps / pages observés
| document | HTTP | pages | octets | temps |
|---|---|---|---|---|
| dossier | 200 (20/20) | 9–11 | 223–298 ko | 1,5–2,9 s |
| apporteur | 200 (20/20) | 4 | 130–184 ko | 0,6–0,7 s |
| estimer (analyse-annonce) | 200 (20/20) | 2 | 90–156 ko | **2,5–11,7 s** |
| gabarit | 200 (11/20) · 422 (9/20) | 2–3 | 25–52 ko | < 1 s |
| financier | **422 (20/20)** (config requise) | — | — | < 1 s |
| étude-zone (rayon 2 km) | 200 | **9–24** | 114–178 ko | 5,0–7,3 s |
| comparatif (2 parcelles) | 200 | 2 | 20 ko | 0,9 s |
| pré-dossier (zip) | 200 | 8 fichiers | 1,5 Mo | **15,0 s** |
| courrier | 200 | 2 | ~3,7 ko | < 1 s |

### I-EXP-01 — DETTE — Génération lente de certains documents (Estimer, Pré-dossier, Étude-zone)
- **Où/mesuré** : `analyse-annonce.pdf` jusqu'à **11,7 s** (97411000EY0173, grande parcelle) ; `pre-dossier/*.zip` **15,0 s** ; `etude-zone.pdf` jusqu'à **7,3 s** / **24 pages** (rayon 2 km en zone urbaine dense Saint-Denis).
- **Affiché vs juste** : sans retour de progression, un clic « Générer l'estimation » peut sembler figé 12 s. L'étude-zone à 24 pages est volumineuse pour un livrable « autour d'une parcelle ». (Perf hors cœur de ce lot — cf. [vitesse-3] — signalé comme dette UX.)
- **Amélioration** : indicateur de progression/async sur les générateurs > 5 s ; borner/paginer l'étude-zone dense.

### I-EXP-02 — MINEUR — Le document « Financier/Bilan » n'est **jamais** générable en un clic (422 sur 20/20)
- **Où** : `/financier/{idu}.pdf` (`documents.py:97`) exige `regime_tva_saisi` **et** un programme chiffrable → 422 systématique sans saisie. La tuile fiche « Financier » (`BanquierButton`) et la carte Docs « Bilan » **ouvrent l'écran de saisie** (`BilanEcran`) avant de pouvoir générer ; c'est **par conception**.
- **Affiché vs juste** : comportement correct **si** le front route toujours vers l'écran de saisie et n'ouvre jamais l'URL directe. **À confirmer côté UX** : qu'aucun parcours (bibliothèque « Mes documents », lien profond) n'ouvre `/financier/{idu}.pdf` nu → sinon l'utilisateur reçoit un 422 JSON. **Amélioration** : garantir que tout point d'entrée « Financier » passe par la saisie TVA/programme.

> **Limites honnêtes exports.** (1) Ouverture **dans Aperçu et un navigateur** : non réalisable en session headless — à défaut, structure PDF validée (`pdfinfo`/`pdffonts`/`pdfimages` OK, fontes embarquées, 1 carte/doc). (2) **Lisibilité noir & blanc** : l'orthophoto est lisible en gris (vérifié) ; les **overlays colorés** (tracé parcelle, et toute carte de zonage/PPR rouge-bleu dans Gabarit/Étude) n'ont pas pu être jugés à l'impression N&B réelle → **à vérifier visuellement** (risque de confusion rouge/bleu PPR en gris). (3) « Texte coupé / carte rognée » : non détectable de façon fiable par extraction texte seule ; aucun débordement flagrant au rendu `pdftoppm` échantillonné.

---

## D. ADMIN

**Onglets** : Pilotage · Comptes (Licences/Stripe) · Données (Tableau de bord · Usine · Sources · Circuit · Journal) · IA · Horloge (Cron). **Authz solide** : garde `exiger_admin` (`auth.py:214-239`) par handler sur **toutes** les ~70 routes `/admin/*` (aucune route non gardée trouvée) ; fail-closed hors `local`. **Aucune fuite** de secret/jeton/DSN/trace : pas de dump `os.environ`/`settings`, clé Stripe lue en interne jamais sérialisée, pas de `exception_handler(Exception)` → 500 à corps vide.

### I-ADM-01 — MAJEUR — Un job qui n'a **jamais réussi** est invisible pour la vigie
- **Où** : `ops_alertes.py:327-329` — `le = succes.get(nom); if le is None: continue`. Un job sans ligne `('ok','dry-run')` dans `job_runs` est **sauté** → **aucun** incident `job-retard:` ne s'ouvre ; `job-echec:` ne se déclenche que si le job **a tourné et levé** (`jobs.py:262`). Un cron **jamais installé / jamais déclenché** ne produit **aucune** alerte, nulle part.
- **Repro** (exécutée en `psql`, base locale) :
  ```
  SELECT count(distinct nom) FROM job_runs WHERE statut IN ('ok','dry-run');          -- 5
  SELECT cle FROM ops_incidents WHERE cle LIKE 'job-retard:%' AND resolu_at IS NULL;   -- 2 (les 2 qui ont tourné puis vieilli)
  ```
  Registre = **31 jobs** ; **5** ont déjà réussi, **2** alarment (ran-then-stale), **26 n'ont jamais tourné → 0 incident**. (La base Mac n'est pas une prod vivante, mais le **chemin de code** garantit le silence pour tout cron jamais lancé.)
- **Affiché vs juste** : Pilotage « au vert » / aucune alerte, alors qu'un job critique peut n'avoir **jamais démarré**. **Amélioration** : comparer la liste des jobs `planifie=True` **attendus** à ceux ayant un succès récent, et ouvrir un incident « jamais exécuté » pour les manquants.

### I-ADM-02 — MAJEUR — `/healthz/crons` ne surveille que **11 des 31** jobs
- **Où** : `ops.py:46-49` `_crons_du_registre` ne garde que `nom in TOUCHE_EAU or nom=="backup-postgres"` **et** `planifie` → **11** jobs (10 « eau » + backup). Les **20** autres (dont `mail-queue-consommer`, `digest`, `healthcheck`, `coherence-banc`, `purge-sessions`…) sont absents de l'endpoint que `docs/EXPLOITATION.md` dit de curler pour `"retards": []`.
- **Affiché vs juste** : `{"ok": true, "retards": []}` ne représente qu'un tiers de la flotte ; les 20 autres ne sont couverts que par `_jobs_en_retard`, qui a l'angle mort I-ADM-01. **Amélioration** : étendre `/healthz/crons` à tous les `planifie=True`, ou documenter clairement son périmètre partiel.

### I-ADM-03 — MAJEUR — Un job **gelé** (tué en cours) reste « travaille en ce moment » / vert à vie, et se contredit entre écrans
- **Où** : `jobs.exec_one` écrit `statut:"en_cours"` **avant** l'exécution (`jobs.py:203`) et ne le réécrit qu'après ; un kill dur (OOM/SIGKILL/redémarrage conteneur) laisse l'état figé `en_cours` **sans** ligne `job_runs` terminale. Puis : `_pastille_poste` (`cockpit_resume.py:582`) → **violet « travaille en ce moment » perpétuel** ; `_job_perime` (`:43`) **exclut** les statuts non-`ok` → jamais d'ambre/rouge ; le compteur d'en-tête `_resume_usine` (`:465-471`) range `en_cours` dans « à l'arrêt » → **le même job dit « à l'arrêt » en en-tête et « travaille » dans la grille** ; `Cron.tsx:13` → ambre « EN COURS » à vie.
- **Affiché vs juste** : un job mort paraît actif (violet) ou OK ambre, indéfiniment. **Amélioration** : borner `en_cours` par un *heartbeat*/âge max (au-delà de N× la durée médiane → rouge « bloqué »).

### I-ADM-04 — MINEUR — `Cron.tsx` n'a **aucun** contrôle de retard → pastille verte « OK » sur un job en retard
- **Où** : `Cron.tsx:9-15,23` — la pastille ne lit que `j.dernier.statut` ; un job dont le dernier run `ok` est **très ancien** mais désormais en retard reste **vert « OK »** (la ligne « prochaine » est informative, ne colore rien). L'ambre de péremption existe côté Usine/dashboard mais pas ici (et pas pour `en_cours`, cf. I-ADM-03). **Amélioration** : colorer la pastille Cron selon l'échéance dépassée.

### I-ADM-05 — MINEUR — Le compte « au vert » diverge entre Usine et Tableau de bord
- **Où** : `admin/circuit/Usine.tsx:50` affiche `vert − ambre` ; `TableauDeBord.tsx:144` affiche le `vert` brut. **Affiché vs juste** : deux nombres « au vert » différents pour la même flotte dès qu'il existe de l'ambre. **Amélioration** : une seule définition partagée.

### I-ADM-06 — MINEUR — Fraîcheur des sources : seules **4 des 11** peuvent passer « en retard »
- **Où** : `fraicheur.py:255-279` — `bodacc, catnat, gpu_plu, georisges, sudocuh, ortho_piscine, cosia` n'ont **pas** de `cadence_norme` → `statut_fraicheur = "cadence_libre"` → **jamais** « en_retard ». De plus `gpu_plu`/`georisques` `derniere_donnee` = date d'**ingestion LABUSE**, pas l'horizon amont (`fraicheur.py:156-160`) ; règle « agent gagne » (`etats_sources.py:90-109`) : « à jour » = « pas de version plus récente connue », pas « donnée fraîche ».
- **Affiché vs juste** : un flux BODACC/CatNat/PLU **gelé** reste invisible au verdict de fraîcheur. Conçu anti-faux-positif, mais c'est un angle mort réel. **Amélioration** : au moins un garde-fou d'âge absolu par source critique.

### I-ADM-07 — MINEUR — `traction.coherence` est une lecture d'état figée (jamais re-sondée) ; Journal : résultat inconnu → vert par défaut
- **Où** : `dashboard.py:531` lit l'état fichier `coherence-robinets` sans re-sonder (`verifie_le` daté mais potentiellement vieux) ; `admin/circuit/Journal.tsx:18,37` `couleurResultat` met en **vert (mint)** toute chaîne de résultat non reconnue. **Amélioration** : afficher l'âge de la sonde cohérence ; « inconnu » ≠ vert.

### I-ADM-08 — MAJEUR — Mot de passe « pilote » partagé = admin complet sans second facteur
- **Où** : `auth.py:237-238` — un cookie HMAC « pilote » (mot de passe partagé) ouvre **tout** l'admin ; le 2FA n'est exigé qu'au chemin `/login/2fa`, pas sur le chemin pilote. **Affiché vs juste** : concentration d'autorité (modèle mono-promoteur assumé), mais un secret partagé compromis = admin total sans MFA. **Amélioration** : exiger un second facteur aussi sur le chemin pilote, ou restreindre ce que le pilote peut faire.

### I-ADM-09 — DETTE — Troncatures silencieuses sans total, estimations/chiffres de doc figés en commentaire
- **Où** : `dashboard.py:423-428` (fil 30 / gels 20), `:1366` (runs 10), `:2624-2644` (eau 40 / journal 12) — listes tronquées **sans total affiché** ; `:2888-2893` coût agent **0,04 €/source** en dur ; commentaires-littéraux périmés (« 24 verrous », « 55 couches / 91 sources / 266 données », `:350,2848`) — non servis mais pièges d'audit. **Amélioration** : afficher « N premiers sur M » ; sortir les chiffres de doc des commentaires.

### I-ADM-10 — DETTE — `docs/EXPLOITATION-CRON.md` périmé (crontab legacy) encore cité comme référence
- **Où** : le doc décrit l'ancien monde `/etc/cron.d/labuse-*` (noms de jobs faux, DVF mer vs mardi, backup « 09:30 » vs registre « 13:30 » après migration VPS en `Indian/Reunion`, `ingest-ban` supprimé encore listé) ; cité comme autorité par `EXPLOITATION.md:170,365,391`. (= constat L-JOB-05.) **Amélioration** : régénérer depuis le registre `jobs.py` ou supprimer.

> **Sécurité — note (DETTE)** : `/admin/cron/{nom}/log` (`ops.py:343-354`) renvoie le *tail* brut (≤ 200 lignes) des logs aux admins, **sans** assainissement — si un job loggue un jour son environnement ou une invocation `psql`/`pg_dump`, une chaîne de connexion pourrait apparaître. Gardé admin, risque faible. `/admin/licences`+`/admin/stripe` exposent e-mails/`stripe_customer_id` d'autres utilisateurs (données de facturation gardées, par conception, **pas** de donnée carte) — MINEUR acceptable.

---

## E. ARITHMÉTIQUE (totaux == somme des lignes)

### Vérifié juste
- **Taxe d'aménagement** (IE0241, `surface_taxable_m2=120`, recalcul vs barème 2026) : assiette `120 × 892 = 107 040 €` ✓ ; part communale `×3 % = 3 211,20 €` ✓ ; part départementale `×2,5 % = 2 676,00 €` ✓ ; **`total_eur = 5 887,20 = part_comm + part_dept`** (au centime). La **RAP** `×0,4 % = 428,16 €` est **exclue du total à dessein** et rendue **sous** « Total estimé » avec le libellé « Redevance d'archéologie préventive — taxe DISTINCTE » (`TaxeAmenagement.tsx:415-436`, `TAXE-FIX-1 point 2`) → pas d'écart trompeur. **Correct.**
- **Cohérence écran==PDF==composeur** : adresse (97490) identique partout ; courrier aperçu == PDF (même source `composer`).

> Les grands invariants inter-écrans (SDP, médiane, aléas, surfaces) relèvent des lots A/J/O et de la suite `tests/coherence/` (égalité stricte 1 €/1 m²), hors recomputation ici.

---

## Synthèse des constats

| # | Gravité | Titre | Fichier:ligne |
|---|---|---|---|
| I-CPT-01 | **MAJEUR** | `paiement_requis` ne coupe rien + login re-réussit | `comptes.py:466` · `app.py:822` |
| I-ADM-01 | **MAJEUR** | Job jamais réussi invisible à la vigie | `ops_alertes.py:327` |
| I-ADM-02 | **MAJEUR** | `/healthz/crons` ne couvre que 11/31 jobs | `ops.py:46` |
| I-ADM-03 | **MAJEUR** | Job gelé reste « travaille » / vert à vie + contradiction en-tête | `cockpit_resume.py:43,582,465` |
| I-ADM-08 | **MAJEUR** | Pilote (mot de passe partagé) = admin complet sans 2FA | `auth.py:237` |
| I-TPS-01 | MINEUR | `lib/format.ts` dates J-1 hors est-d'UTC (prouvé Node) | `format.ts:58-89` |
| I-TPS-02 | MINEUR | ZIP pré-dossier : LISEZMOI 1980 + pièces en heure machine CET | `pre_dossier.py:1117-1134` |
| I-TPS-03 | MINEUR | Cockpit admin « Données » en heure navigateur, pas Réunion | `admin/circuit/*.tsx`, `Cron.tsx` |
| I-TPS-04 | MINEUR | Brief Copilote / « généré le » off-by-one date | `AccueilCopilote.tsx:108`, `DocumentsView.tsx:366`, `ContextePanel.tsx:115` |
| I-CPT-02 | MINEUR | E-mail `resiliation` sans date pour abonné payant | `facturation.py:500`, `comptes.py:744` |
| I-CPT-03 | MINEUR | E-mail `essai` risque « le le » sur FIN_ESSAI | `dashboard.py:1068,1091` |
| I-CPT-04 | MINEUR | Template `souscription` → `/souscrire` (route absente) | `dashboard.py:1070` |
| I-EXP-02 | MINEUR | « Financier » jamais générable en un clic (422 ×20) | `documents.py:97` |
| I-ADM-04 | MINEUR | `Cron.tsx` sans contrôle de retard → vert « OK » | `Cron.tsx:9-15` |
| I-ADM-05 | MINEUR | « au vert » diverge Usine vs Tableau de bord | `Usine.tsx:50` vs `TableauDeBord.tsx:144` |
| I-ADM-06 | MINEUR | Fraîcheur : 4/11 sources seulement peuvent « en retard » | `fraicheur.py:255-279` |
| I-ADM-07 | MINEUR | `traction.coherence` figée ; Journal inconnu→vert | `dashboard.py:531` · `Journal.tsx:18` |
| I-TPS-05 | DETTE | E-mail maintenance : ISO brut sans « heure Réunion » | `emails.py:143` |
| I-CPT-05 | DETTE | Template `email_change` mort (pas de notif ancienne boîte) | `brevo.py:92` |
| I-CPT-06 | DETTE | RGPD : effacement CLI-only, pas de self-service | `cli.py:4527`, `comptes.py:797` |
| I-CPT-07 | DETTE | TVA : franchise 293 B non apposée sur abonnement + seuil annoncé | `config.py:306`, `facturation.py:135` |
| I-EXP-01 | DETTE | Génération lente (Estimer 11,7 s, zip 15 s, étude-zone 24 p) | `analyse-annonce`/`pre_dossier`/`etude-zone` |
| I-ADM-09 | DETTE | Troncatures silencieuses + chiffres de doc en commentaire | `dashboard.py:423,1366,2624,2888` |
| I-ADM-10 | DETTE | `EXPLOITATION-CRON.md` périmé cité comme référence | `docs/EXPLOITATION-CRON.md` |

**0 bloquant · 5 majeurs · 13 mineurs · 10 dettes.**

Fil rouge : le **calcul** est juste, les **exports** sont propres et sans champ vide, **aucun secret ne fuit**, l'**horloge serveur/DB est bien en Réunion**. Les risques se concentrent sur (1) l'**accès** d'un compte en défaut de paiement, (2) l'**honnêteté des jobs** (jamais-lancé / gelé invisible ou au vert), (3) le **formatage des dates côté navigateur** (doctrine Réunion non figée, impact faible pour l'audience réelle), et (4) une **incohérence de dates** dans le ZIP de pré-dossier.

---

*Horloge rendue inchangée (preuve §0). API 9300 arrêtée. Aucune écriture base, aucun merge, aucun accès prod.*
