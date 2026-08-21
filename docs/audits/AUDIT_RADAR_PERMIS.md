# Audit — Radar permis (M03) + 2 corrections (21/08/2026)

Branche `audit/radar-permis`. Audit d'abord, puis corrections. Ne merge pas.

## 1. Audit (mesuré)

### a. Branché de bout en bout
- Tables : **`sitadel_permits`** (`modules.py:260`, liste + carte + compteurs) + **`m10_permit_delais`**
  (`modules.py:261`, LEFT JOIN pour le délai d'instruction). Fiche permis : `permis_fiche` (`modules.py:309`)
  lit `sitadel_permits.raw` (état, nb_lgt, surf_hab, daact, destination, porteur, siren), `idu_codes`, délais.
- **Run-scoping** : NON scopé sur `q_v10_m129` — et c'est CORRECT : les permis sont de la donnée SOURCE
  (SITADEL), pas un produit du scoring. Le scope run n'est pas pertinent ici.

### b. À jour et complet ?
- **Fraîcheur** : millésime SITADEL en base = **2026-06** (dernier publié), `last_sync_at` = **2026-08-14**
  (statut `connecte`). Dernier permis daté **2026-06-30**, soit ~52 j avant aujourd'hui = **délai de
  publication SITADEL normal** (mensuel, ~6 sem de retard), PAS un radar cassé. Le radar tourne (sync il y a 7 j).
- **Volume / profondeur** : **50 292 permis**, du **2013-01-02** au **2026-06-30** (~13,5 ans).
- **Géocodage** : **39 526 / 50 292 = 78,6 %** géocodés → **~10 766 non géocodés** (le trou relevé M123,
  confirmé). Uniforme par commune (76–85 %). Les non géocodés RESTENT listés (jamais masqués), non
  localisables sur la carte (dit à l'écran).
- **LIMIT d'affichage caché → OUI, sur la CARTE** (le 4ᵉ outil de la semaine avec un plafond muet) : la
  requête carte plafonne à **`LIMIT 8000`** (`modules.py:285`). Mesuré : fenêtre 24 mois (défaut) = 5 037
  géocodés (OK) ; **48 mois = 10 791** ; **72 mois = 17 917** → au-delà de 24 mois, la carte **tronque
  silencieusement**. La LISTE, elle, n'est pas plafonnée (« voir plus »). **Corrigé** : le plafond est
  maintenant DIT (« N sur M géocodés — carte plafonnée »).

### c. Vestiges de matrice
- **AUCUN** dans le radar permis : `permis` + `permis_fiche` + le composant M03 ne lisent ni `q_score`,
  ni `a_score`, ni `matrice_statut`. (Les `q_score` de `modules.py` sont dans d'AUTRES modules —
  patrimoine M02, etc. — hors radar.) Radar **propre**.

## 2. Les deux corrections

### a. Les points mauves sont maintenant CLIQUABLES
Avant : seule la LISTE ouvrait la fiche permis (`PermitDrawer`) ; les points carte (`module-pts`) n'avaient
aucun handler. Après : `MapView` écoute le clic sur `module-pts` → `setPermitToOpen(permit_id)` (le
`permit_id` voyage dans les properties de la feature) → M03 ouvre le MÊME drawer (idiome consommé-puis-reset,
comme `parcelPrefill`). Curseur `pointer` au survol.

**Ce que le clic montre** (si l'info existe) : nature du permis, statut, **porteur** (dénomination + SIREN si
personne morale, sinon « personne physique anonymisée »), nombre de lots, surface habitable, dates
dépôt/autorisation/achèvement (DAACT), **délai d'instruction**, parcelle(s) rattachée(s), et un bouton
**« Voir la parcelle sur la carte »** (vole + halo sur la parcelle) — ou un message clair si non géocodé.

### b. Recherche par rue / commune
Ajout de `AddressAutocomplete` (le **MÊME** composant que « Scorer une adresse » — chemin unique, endpoint
interne `/adresses/autocomplete` sur la table `adresses`, aucune 2ᵉ implémentation). Sélection → `setFlyTo`
sur les coordonnées → la carte vole sur le lieu, les permis géocodés du secteur apparaissent (points
cliquables). Rue et commune couvertes par le même champ (le libellé porte la commune).

## Vérif
Captures (`qa/audit-radar-permis/`) : recherche rue, recherche commune, **permis cliqué sur la carte**
(drawer détaillé + « Voir la parcelle »). Clic RÉEL sur un point mauve → drawer ✓ ; recherche rue → carte
vole (Saint-Philippe) ✓. golden 119/119 · garde-run 431 663=431 663 · tsc 0 · build.
