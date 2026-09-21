# DASHBOARD-4 — Pilotage · Données connectée · Comptes (rapport)

Branche `feat/dashboard-4` depuis `3d96bf05`. Un commit par lot, branche poussée.
Maquette de référence : `docs/audit-2026-09/DASHBOARD/maquette-dashboard-v5.html`
(valeurs = exemples ; structure + charte font foi).

**Règle de chiffre tenue** : chaque nombre affiché vient d'une fonction que les
verrous / le circuit lisent aussi (`courrier.deposables`, `deploiement.etat`,
`circuit_garanties.sources_sans_controle` (G8), `catalogue_compteurs.vitrine` (V2a),
`couches_tuyau.registre` (V7a), `registre.donnees.DONNEES`, `circuit_verrous.VERROUS`,
`comptes.licences_actives`, `conso_ia_mois`, `prochaineAction`/`estAToucher`) — jamais
un compte propre à la page.

**Règle de preuve tenue** : chaque point a une capture navigateur dans
`captures/dashboard4/` (avant depuis un worktree pristine sur `3d96bf05` servi par le
même backend ; après sur le worktree courant). Scripts : `frontend/qa/dashboard4_*.mjs`.

Commits : L1 `72a7486f` · L3 `2f9ff197` · L4 `2b610fdc` · L2 `82e09ed9` · L5 `9bfb4dff`.

## Environnement de recette
- Backend `:8135`, front `:5335` (base `labuse` locale). `.env` du worktree : DB +
  Stripe `sk_test` (lecture seule) ; **Brevo/SMTP neutralisés** → tout envoi de mail est
  un **dry-run garanti** (la file `mail_queue` enregistre, rien ne part). Aucun mail ni
  courrier envoyé, aucune bascule, aucun rescoring.

## Tableau des 24 points

| # | Point | État | Constaté au navigateur | Preuve |
|---|-------|------|------------------------|--------|
| **P1** | 5 tuiles pleines cliquables (CA→Comptes · Licences→Comptes · Coût IA mauve→IA · Courriers déposables→Courrier « À déposer » · Tâches→Données) | ✅ | 5 tuiles : `0 €` · `1` · `1,05 €` (mauve) · `25` · `13` ; clic tuile IA → section IA | `AdminView.tsx:99` (Tuile), `:243-260` (tuiles) ; `lot1-pilotage-apres.png` |
| **P1** | « Déposables » = demandes qui PEUVENT partir (corps valide, non opposées), pas les demandes | ✅ | tuile lit `courrier.deposables` (25 déposables ≠ 25 demandes si opposées/incomplètes) | `courrier.py:460` `deposables()` ; `dashboard.py` (courrier.update) |
| **P2** | Charte vert=normal · mauve=IA · rouge=en retard/à vérifier ; compteur élevé ≠ rouge | ✅ | CA/Licences vert, IA mauve `rgb(180,151,240)`, Courriers rouge (plus vieux 19 j ouvrés > 5), Tâches rouge (à corriger) | `AdminView.tsx:99-113` |
| **P2** | Courrier rouge seulement si plus vieux > 5 j OUVRÉS (seuil écrit à l'écran) | ✅ | sous-tuile « le plus ancien attend 19 j ouvrés · seuil 5 j » | `courrier.py:492` `jours_ouvres_depuis` ; `AdminView.tsx:236-256` |
| **P3** | Le bloc rouge « ce qui bloque » + l'horodatage Stripe du haut disparaissent | ✅ | en-tête sans chip « Stripe daté du… » (contrôle : absent) | `AdminView.tsx:484-486` |
| **P3** | UNE liste « À faire, dans l'ordre » calculée (deploiement + jobs + comptes), jamais codée en dur | ✅ | 6 lignes : Déployer · Sondes muettes · Sauvegarder · Déposer 25 · Relire 2 sources · Toucher 3 clients | `AdminView.tsx:262-320` |
| **P3** | « Déployer » : main en avance de N commits (git + dernier deploy), rouge si N>0 | ✅ | « Déployer — 19 commits d'avance sur la prod … dernier déploiement le 21/09 » | `deploiement.py:46` `etat()` ; `deploy.sh` pose `config/deploiement.json` |
| **P3** | « Sondes muettes en prod » : G8 ; UNE ligne nommant la cause vraie (horloges non posées), renvoie à Déployer | ✅ | « Sondes muettes en prod — 90 sources sans contrôle … les horloges ne sont pas posées en prod » | `dashboard.py` (sondes_muettes = `sources_sans_controle`) ; `AdminView.tsx:271-276` |
| **P3** | Sauvegarde rouge si > 24 h | ✅ | « Sauvegarder la base — aucun répertoire de sauvegarde configuré » (local `non_configure`) | `AdminView.tsx:278-289` |
| **P4** | Journal des 3 derniers jours, filtrable, comptes de test masqués | ✅ | Journal présent, fenêtre 3 j + masquage `estCompteTest` | `AdminView.tsx:207-211` (estCompteTest), `:308-317` |
| **D1** | Compteurs de la page = ceux des verrous (91 sources vitrine · 55 couches · 266 données · 22 verrous + 8 garanties) | ✅ | bande « Les compteurs, tels que les verrous les comptent : 91 · 55 · 266 · 22 + 8 » | `dashboard.py:2275` `compteurs_coherence` ; `Resume.tsx:28-37` |
| **D2** | Verrous SUR la page (Résumé) : `labuse circuit verrous` jouable (tâche détachée, progression, résultat persistant), 30 lignes phrase+état+preuve ; les 6 depuis le 9/09 ; cassé = ligne « à corriger » | ✅ | « Rejouer les verrous » → 30 lignes ; V5d/V5e/V5f/V6a/V7a/G8 présents ; « À corriger : V1c » | `dashboard.py:2321` `_executer_verrous`, `:2391` endpoint ; `circuit_taches.py:109` ; `Resume.tsx:39-73` |
| **D3** | Depuis une source : tout ce qu'elle alimente (couches · sections fiche V5d · cartes commune V5e · outils V5f · Radar · Copilote · exports) + sens inverse ; clic mène à l'élément ; ici seulement | ✅ (CIRCUIT-SOURCES-1) | détail réservoir : blocs « Couches carte », « Lignes de la fiche parcelle », « Ailleurs » | `app.py:5577` `/sources/rattachements` ; `Detail.tsx` DetailReservoir ; `lot2-reservoir-detail-apres.png` |
| **D4** | Chaque source : 3 dates (réservoir · producteur · dernier contrôle), cadence, mode (sonde/agent/manuel/interne), page de publication pour les manuelles ; cadastre_epoque interne visible | ✅ (CIRCUIT-P) | détail réservoir : « Dans le réservoir / Chez le producteur / Dernier contrôle » + mode | `Detail.tsx` DetailReservoir ; `lot2-reservoir-detail-apres.png` |
| **D5** | « Envoyer les agents » / « Vérifier que tout coule » hors Résumé (onglet Circuit seulement) | ✅ | boutons absents sur Résumé, présents sur Circuit (contrôle DOM) | `Circuit.tsx:135` (`onglet === 'circuit'`) |
| **D6** | « Destinations PLU » : entrée EN BAS du Circuit (détail plu_destinations) ; plus de « catalogue millésimes en retard », l'étiquette dit la vérité du document lu | ✅ | lien en bas : « Destinations PLU — le détail du réservoir plu_destinations » | `Donnees.tsx:17-25` ; `plu/destinations.py:224-229` (note reformulée) |
| **D7** | Plafond agents (LABUSE_AGENT_PLAFOND_EUR) + crédit API lisibles ici ; plafond 0 dit « aucun agent ne tourne », pas grisé | ✅ | « Agents : plafond à 0 € — aucun agent ne tourne … Crédit API : non exposé … voir la console » | `dashboard.py:2287` `agents_info` ; `Circuit.tsx:164-171` |
| **R1** | Retirer le bandeau « Faits extraits d'annonces publiques… » + « J'ai lu — replier » | ✅ | bandeau « Faits extraits » absent (contrôle : false) | `Radar.tsx:238-240` (retrait) ; `lot3-radar-apres.png` |
| **C1** | « Piste 12 » (id global qui fuit) : rang propre au compte, ou retiré | ✅ (retiré) | colonne « Piste CRM » : « issue du CRM » (aucun « piste #<n> ») | `Courrier.tsx:143-148` ; `lot4-courrier-apres.png` |
| **C2** | Page Courrier admin + tuile lisent COURRIER-2 (vocabulaire unique, panneau opposition, coût prestataire daté, prix saisi) ; aucune autre modif | ✅ | vocabulaire à déposer→déposé→envoyé→répondu, opposition, coût prestataire daté, Prix (saisi) présents | contrôle DOM ; `lot4-courrier-apres.png` |
| **K1** | Deux entrées en haut à droite (Ouvrir un essai 48 h · Créer un client) ; plus d'accordéon, plus de lien brut | ✅ | deux boutons ; ouvrent de vraies pages | `Licences.tsx:501-506` ; `lot5-comptes-apres.png` |
| **K2** | Créer = e-mail + prénom + nom ; « Créer et envoyer l'invitation » + « créer sans envoyer » ; les deux → fiche ; Brevo 4/5, dry-run local, mail_log | ✅ | page créer : 3 champs + 2 gestes + note dry-run ; envoi = souscription(5)/essai(4) par la file | `Licences.tsx:223` CreerPage ; `dashboard.py:886` mail (file) ; `lot5-creer-apres.png` |
| **K3** | 5 statuts (Invité · Invitation envoyée · Actif · Suspendu · Expiré) ; colonne payant/essai à part (Stripe) ; segments ; « À toucher » défaut = invitation sans réponse >7 j · essai <6 h · carte refusée | ✅ | colonnes Statut + Abonnement séparées ; 6 segments ; À toucher via estAToucher (aussi lu par Pilotage) | `Licences.tsx:118-166` (statut5/abonnement/estAToucher) ; `AdminView.tsx:245` |
| **K4** | Essai 48 h : même chemin, expire seul, décompte sur la fiche, bouton « Transformer en client » | ✅ | fiche essai : badge « ESSAI — expire dans N h » + bouton « Transformer en client » | `Licences.tsx:346` transformer, `:382-385` ; `dashboard.py:759` convertir |
| **K5** | Fiche : fil d'Ariane, 4 onglets (Aperçu · Activité · Facturation · IA), gestes haut-droite (Renvoyer · Suspendre/Rétablir · Transformer), faits + phrase calculée ; tous les gestes ici | ✅ | ariane « Comptes › nom », 4 onglets, gestes haut-droite, phrase « … actif … » / « n'est jamais entré » | `Licences.tsx:370-401` ; `lot5-fiche-apres.png` |
| **K6** | Comptes de test masqués partout ; ton-email@test.com : ne pas y toucher, le signaler | ✅ | 33 comptes de test masqués (hors de tout chiffre) ; ton-email@test.com EXCLU du service `/admin/licences` (jamais servi ⇒ jamais touché), garde front défensive + signalé ici | `Licences.tsx` footer + `est_test` ; `dashboard.py` admin_licences |

## Vérifications finales
- **`tsc -b` vert** (frontend). ✔
- **`vitest run` : 178 passed**, seul `circuit/Detail.test.tsx` échoue (2 tests) —
  **PRÉ-EXISTANT** (mêmes 2 échecs sur `3d96bf05`, worktree pristine). Snapshots
  `onglets.snapshot` + `Donnees.test` régénérés (DOM Résumé / lien Destinations modifiés).
- **`pytest tests/`** : **3098 passed, 4 failed, 66 skipped** (16 min). Les 4 échecs sont
  **PRÉ-EXISTANTS / environnementaux**, aucun dans le périmètre DASHBOARD-4 (le diff `src/`
  ne touche QUE `dashboard.py`, `circuit_taches.py`, `courrier.py`, `deploiement.py`,
  `plu/destinations.py` — aucun de ces 4 tests n'en exerce le code, donc résultat identique
  à `3d96bf05`) :
  - `test_amenites::test_compute_distances` / `::test_compute_idempotent` — données d'aménités
    de la base partagée (assert 5 == 1) ;
  - `test_backup::test_backup_puis_restore_sur_base_temporaire` — outillage pg local ;
  - `tests/verrous/test_lot1_tables` — le **V1c** (3 tables orphelines de la base DEV
    partagée : `score_labuse`, `score_labuse_runs`, `ingestion_delta`), déjà documenté.
- **`labuse circuit verrous -w G8`** : **V1c** (3 tables orphelines `score_labuse`,
  `score_labuse_runs`, `ingestion_delta`) est cassé — mais ces tables **ne sont pas dans
  le code de cette branche** : ce sont des artefacts de la **base DEV PARTAGÉE** (créées
  par un worktree voisin), pré-existants (première sonde `/admin/pilotage` : 21/22) et
  **hors périmètre DASHBOARD-4**. G8 = avertissement non bloquant (sources sans contrôle
  en local = horloges non posées). Aucun verrou n'est cassé PAR ce mandat.

## Notes / décisions
- « Déployer » lit un marqueur `config/deploiement.json` (posé par `deploy.sh` à chaque
  déploiement réussi) ; seed baseline = merge `feat/donnees-7` (dernier deploy connu, à
  écraser au prochain deploy). L'avance (19) est un fait git pur (`sha..main`).
- C1 : aucun rang propre au compte n'existe pour la *piste CRM* (≠ la demande) et la piste
  est cloisonnée côté client → on retire le numéro global et on garde la provenance
  (option « retiré » du mandat). Les autres fuites d'id (client `ProjetsPanel`/`ModulePanel`,
  Kanban title) sont HORS périmètre (« aucune autre modification du courrier »).
- « Ne merge pas ».
