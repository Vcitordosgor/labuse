# M145 — Flash écoute le moteur commun (`fix/m145-flash-moteur`)

Branché sur `origin/main` @ `e785e9bb`. Flash cesse d'être un générateur parallèle : chaque valeur
vient des mêmes fonctions que la fiche/les dossiers (héritées de M133/M139/M143/M144). On rebranche,
on ne recopie pas. La structure éditoriale (10 sections, §10, sources par section) est conservée.
CC ne merge jamais.

**Résumé : §02 rebranché sur `parcel_faisabilite` (post-M144) — Flash, argumentaire et fiche donnent
les MÊMES surfaces (vendable 4 652 m², plancher 5 815 m², 64-65 logts au sol). Coefficient local ~15 %
supprimé (rendement 0,80 commun). Deux dates. « (Absent) » retiré. ⚠ gouverne le chiffre (titre + note
AVANT). Marché : tendance héritée (« baisse »), effectif expliqué, artefact terrain écarté. Version 1.3.
Tunnel : filet ROB-B au poll, spinner borné, pdf_path relatif. Partners : cartographié (ne génère pas
de Flash).**

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

## Cartographie du canal partners (hors périmètre)

**Le canal partners NE génère PAS de Flash.** `partners.py` n'appelle jamais `generate_flash_report` /
`collect_report_data` ; il n'emprunte à Flash que la **carte** (`flash.carte.IGN_ORTHO_URL`,
`build_situation_map`) et `flash.report.storage_dir` pour la page de partage `/p/{token}`
(`partners.py:383-384`). Les IDU sont **réels** (ou Cilaos pour la clé démo `demo-labuse-partner-key`,
`partners.py:450-452`), **aucun IDU synthétique**. `FL000985-988` = simples commandes séquentielles
(`order_ref = FL{id:06d}`, `facturation.py`), pas une variante partners. **Rien à corriger ici** (si un
mandat le veut, c'est à part).

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
