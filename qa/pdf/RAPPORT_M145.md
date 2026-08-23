# M145 — Flash écoute le moteur commun (`fix/m145-flash-moteur`)

Branché sur `origin/main` @ `e785e9bb`. Flash cesse d'être un générateur parallèle : chaque valeur
vient des mêmes fonctions que la fiche/les dossiers (héritées de M133/M139/M143/M144). On rebranche,
on ne recopie pas. La structure éditoriale (10 sections, §10, sources par section) est conservée.
CC ne merge jamais.

**Résumé : §02 rebranché sur `parcel_faisabilite` (post-M144) — Flash, argumentaire et fiche donnent
les MÊMES surfaces (vendable 4 652 m², plancher 5 815 m², 64-65 logts au sol). Coefficient local ~15 %
supprimé (rendement 0,80 commun). Deux dates. « (Absent) » retiré. ⚠ gouverne le chiffre (titre + note
AVANT). Marché : tendance héritée (« baisse »), effectif expliqué, artefact terrain écarté. Version 1.3.
Tunnel : filet ROB-B au poll, spinner borné, pdf_path relatif. Partners : ne génère PAS de Flash — les
`FL000985-988` / IDU `974990FL33438E` viennent de la SUITE DE TESTS `test_audit_stripe.py` (effet de
bord, hors comptabilité), pas du produit (voir la vérification post-cartographie ci-dessous).**

---

## Phase A — L'inventaire de la fourche (CW1073)

| Valeur | Source Flash AVANT | Contrepartie commune | Flash avant | Après (= commun) |
|---|---|---|---|---|
| Surface héros | `parcel_residuel.sdp_residuelle_m2` (résiduel BRUT plein gabarit) | `parcel_faisabilite.fourchette.shab_vendable_m2` (scénario retenu au sol) | **9 844 m² plancher** | **4 652 m² vendable** |
| Habitable/vendable | plancher **÷ 1,15** (coef LOCAL) | **rendement 0,80** (valeur testée, chaîne commune) | **8 560 m²** | 4 652 m² |
| Plancher (SDP) | (confondu avec le héros) | vendable ÷ rendement | — | **5 815 m²** |
| Scénario | non nommé | `logements_au_sol` (M144) | — | **64-65, au sol** |
| Silo (alternatif) | absent | `shab_vendable_silo_m2` (prose) | — | ~5 948 m², coût non estimé |
| Dates | **aucune** | `_residuel_run_servi` (flag `is_served`) | — | **2026-08-22, run m135-run2-ile** |
| Marché tendance | `bloc_condense` (déjà partagé) | `marche_commune` (seuil M144 ±2 %) | « **stable** −4,2 % » | « **baisse** −4,2 % » |
| Marché prix (n) | `sector_price` (partagé) | idem + note d'effectif | « n 16 » muet | « n 16 » + note du filtre |
| Comparable terrain | brut | anomalie < 10 m² écartée | « terrain 1 m² » | « — » |

**Trois surfaces, trois coefficients** pour CW1073 le même jour (9 844 / 8 560 via ÷1,15 / un vendable
commun 4 652) → **une seule source** désormais.

## Phase B — Le rebranchement

### B.1 — §02 Constructibilité (le cœur)
- **`_constructibilite` (`flash/data.py`)** : appelle `parcel_faisabilite` (moteur commun). Sert
  `shab_vendable` **au sol** (4 652), plancher = **vendable ÷ rendement 0,80** (5 815). La lecture du
  résiduel BRUT (`parcel_residuel.sdp_residuelle_m2`) est **SUPPRIMÉE** (plus de héros parallèle).
- **Un seul coefficient** : le ~15 % local disparaît (template) ; rendement **0,80** = valeur testée de
  la chaîne commune. Aucune constante propre à Flash.
- **Deux dates** (patron M139/M143) : « Valeurs au JJ/MM — run N » via `_residuel_run_servi`.
- **Le ⚠ gouverne le chiffre** : ouverture non vérifiée dite **AVANT** le chiffre, le potentiel est
  « conditionné », et le **titre lui-même** porte la réserve (« Potentiel constructible *sous réserve
  de l'ouverture à l'urbanisation* — scénario retenu ») — jamais « constructible » asserté en tête
  avec le doute plus bas.
- **« (Absent) »** (jeton interne) **retiré** de la prose.

### B.2 — Marché
- **Tendance** : `bloc_condense` est déjà partagé → hérite du seuil M144 (**±2 %**). Vérifié :
  « stable −4,2 % » devient **« baisse −4,2 % »**. Non recodé.
- **Effectif « n »** : note Flash-locale ajoutée (le « n » = nombre de ventes DVF retenues,
  appartements/maisons du secteur, ≥ 20 m² bâti, prix > 20 k€ ; un petit n = marché peu liquide, pas
  une erreur). **Le libellé partagé `marche_bloc` n'est PAS touché** (fiche/dossiers inchangés).
- **Artefact terrain** : une surface de terrain < 10 m² (anomalie DVF, terrain non renseigné) devient
  « — ». Le comparable reste retenu pour son €/m² **bâti** (valide, filtré des aberrants).

### B.3 — Version du modèle
`TEMPLATE_VERSION` **1.2 → 1.3** (la sémantique des chiffres change). Les rapports 1.2 archivés restent
des instantanés de l'ancien modèle.

## Contrôle 2 — Trois colonnes (CW1073)

| Surface | **Flash (M145)** | Argumentaire | Fiche / calculette |
|---|---|---|---|
| Vendable (au sol) | **4 652 m²** | 4 652 m² | 4 652 m² |
| Plancher (SDP = vendable ÷ 0,80) | **5 815 m²** | 5 815 m² (bilan) | 5 815 m² |
| Scénario | **64-65 logts, au sol** | 64-65 logts, au sol | 64-65 logts, au sol |

Même moteur (`parcel_faisabilite` + rendement 0,80), mêmes chiffres. (Baseline main capturée avant
rebranchement : 9 844 m² plancher héros + 8 560 m² « habitable » via ÷1,15 — l'audit portait sur du
code périmé, cette baseline-ci est la vraie référence.)

## Phase C — Le tunnel

### C.1 — Le poll se donne le droit de vérifier Stripe (F1)
`flash_statut` (`facturation.py`) : sur `en_attente`, appelle le nouveau **`reconcile_flash`** (miroir
de `reconcile_abonnement`, ROB-B) — `stripe.checkout.Session.retrieve(session_id)`, si `paid`/`complete`
→ `_flash_fulfill` (idempotent : `payee` puis génération). **Le webhook reste nominal ; le poll devient
le filet.** Sans clé Stripe → `False`, jamais un crash. *(Non testable en runtime local : `argon2`
absent du venv, comme `typer`/`pytest` — le tunnel tourne en prod/CI ; validé par `py_compile` + la
logique + l'idempotence prouvée de `_flash_fulfill`. Test d'acceptation à rejouer en test Stripe :
commande `en_attente` + session `paid` → `generee` au poll suivant, sans webhook.)*

### C.2 — Le client n'attend plus pour toujours (F2)
Le spinner de `/flash/retour` (`onboarding.py`) est **borné** : après **60 tentatives (~2 min)**, message
honnête (« Votre paiement est bien confirmé… le lien vous parviendra par e-mail, ou rouvrez cette page…
écrivez à votre contact LABUSE avec votre reçu Stripe ») et **arrêt du sondage**. Aucun spinner infini
sur un paiement encaissé.

### C.3 — Les chemins (F3)
`pdf_path` cesse d'être un chemin ABSOLU de dossier de dev : `_flash_fulfill` stocke **le nom de
fichier** (relatif à `flash_storage_dir`). `flash_pdf_par_token` **résout à la lecture** via
`storage_dir()`. **Migration douce, sans UPDATE** : les lignes anciennes (juillet, 9/10, chemin absolu)
sont résolues **par leur nom** dans le répertoire courant si l'absolu n'existe plus (autre
machine/conteneur) → les liens de juillet survivent.

## D'où viennent réellement FL000985-988 / `974990FL33438E` (vérification post-cartographie)

**La première cartographie était FAUSSE (« commandes séquentielles » : contredit par la base). Le vrai
chemin : la SUITE DE TESTS `tests/test_audit_stripe.py`, pas le produit.** Établi :

- `flash_commandes` : ids **1-11**, séquence `last_value = 11`, aucun trou, tous IDU réels. `FL000985-988`
  **n'ont jamais existé** dans cette table → ce ne sont ni des commandes clients, ni du canal partners.
- `partners.py` **ne génère aucun Flash** (confirmé) : il n'emprunte que `build_situation_map` +
  `storage_dir` pour `/p/{token}` (`partners.py:383-387`). Aucun `generate_flash_report`.
- **L'IDU synthétique est fabriqué à `tests/test_audit_stripe.py:34`** :
  `idu = f"974990FL{uuid.uuid4().hex[:6].upper()}"` — soit **exactement** `974990FL` + 6 hex =
  `974990FL33438E`. La fixture `parcelle` INSÈRE une parcelle bidon (`commune='X'`, `section='ZZ'`) puis
  la supprime (`:36-45`).
- **Le PDF est généré pour de vrai** : les 4 tests Flash (`test_flash_recuperable_apres_onglet_ferme`,
  `test_flash_token_ne_donne_que_son_pdf`, `test_flash_lien_expire_apres_30j`, + le test de reprise)
  appellent `_flash_paye` (`:105-114`) → `traiter_webhook(checkout.session.completed)` → `_flash_fulfill`
  → **`generate_flash_report`** → fichier `flash_FL{seq:06d}_974990FL……_v1.x.pdf` écrit dans
  `storage_dir()`. Le `FL{seq:06d}` = la **valeur du SERIAL** au moment du test (984→988 sur le serveur
  audité) ; les 4 tests → **FL000985 à 988**.

**QUI** : la suite de tests du tunnel Flash (`test_audit_stripe.py`). **POURQUOI** : tester le tunnel de
bout en bout (récupérable / cloisonné / expirable) — la génération du PDF est un **effet de bord réel**.

**Le piège** : chaque test **supprime ses lignes** `flash_commandes` + `parcels` (d'où max id = 11) mais
**ne supprime PAS le PDF généré** ni ne rembobine le SERIAL. Donc, exécutée **contre une base non
éphémère** (le serveur, aujourd'hui 13:32), la suite : (1) **avance la séquence** des commandes Flash
(les vraies commandes suivantes sautent 985-988 → trous de numérotation), (2) **laisse des PDF orphelins**
dans `storage_dir` (aucune ligne DB en face). Le commentaire de la fixture (« sans polluer la base »,
`:32-33`) est donc **incomplet** : il nettoie la DB, pas le système de fichiers ni le compteur.

**Peut-il générer hors comptabilité en production ?** **Oui — mais uniquement via la suite de tests
lancée contre une base prod/staging, jamais par le code applicatif.** `facturation`/`onboarding`/
`partners` n'y touchent pas ; le `/flash` de production **valide l'IDU contre `parcels`**
(`onboarding.py:570`), un `974990FL……` serait refusé. Il ne crée **aucune écriture comptable** (ligne
supprimée → pas de revenu, pas de commande fantôme) — la pollution est : séquence avancée + fichiers
orphelins. **Rien à corriger dans ce mandat** (le constat : isoler la base de test / faire nettoyer le
fichier généré par la fixture — mandat à part si Vic le veut).

## Contrôles

1. **Baseline main** capturée avant rebranchement (9 844 / 8 560) = vraie référence. ✓
2. **Flash = argumentaire = fiche** : vendable 4 652, plancher 5 815, 64-65 au sol (trois colonnes). ✓
3. **Deux dates** présentes ; **« (Absent) » = 0** ; **tendance « baisse »**. ✓
4. **Tunnel** : filet ROB-B au poll (en_attente → Stripe → fulfillment) ; spinner borné → message
   d'incident. *(Runtime non rejouable local : `argon2` absent ; `py_compile` vert.)* ✓
5. **Liens de juillet (9/10)** : résolus par nom via `storage_dir()` → survivent après C.3. ✓
6. **Non-régression** : aucun fichier de la chaîne fiche/dossiers/argumentaire modifié (engine, bilan,
   briques_pdf, marche_commune, marche_bloc **intacts**) — seule lecture partagée (`parcel_faisabilite`,
   `_residuel_run_servi`). `ruff` : 0 nouveau warning (pré-existants inchangés). ✓

*Hors périmètre : couche ZAC (dette M144 — Flash en héritera par le moteur commun), posture F4, canal
partners (cartographié). Commits sur `fix/m145-flash-moteur`. Vic merge en `--no-ff`. CC ne merge jamais.*
