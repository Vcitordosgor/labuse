# RAPPORT — RETOURS VISUELS 1 (corrections après la vérification de Vic)

Branche `fix/retours-visuels-1` (base `8270b4fc` = main + mandat). 9 commits, un par lot R1→R9.
Captures avant/après : `docs/audit-2026-08/RETOURS-VISUELS/captures/` (`*_avant.png` / `*_apres.png`).

## R1 — Menu « Mon compte »
**Demandé** : vrai statut du compte (plan réel + e-mail, source offres.py), « Compte interne » sans prix,
chasse exhaustive « pilote », retrait « Proposer une amélioration ».
**Traité** : `/moi` sert désormais, pour une session compte, l'e-mail + le plan RÉEL (`comptes.plan`,
libellé/prix depuis `offres.py`, `plan_eur_mois=null` pour `interne`) ; une session sans compte devient
`mode='local'` (l'ère pilote ne se dit plus nulle part). Menu : « Plan Intégral · 349 €/mois » /
« Compte interne » / e-mail + rôle / « Session locale (dev) » en local. « Proposer une amélioration »
retiré (doublon du bouton Signaler → /retours) ; l'endpoint `/suggestions` reste au back.
**Chasse « pilote » (front)** — occurrences ÈRE PILOTE, toutes purgées : `Header.tsx:541` (« Accès
pilote — la facturation arrive »), `Header.tsx:548` (« Session pilote »), `Rail.tsx:97` +
`AdminView.tsx:272` (`mode === 'pilote'` → `mode !== 'compte'`), `Produit.tsx:90` et `Courrier.tsx:86`
(« pilote/admin » → « interne »), `api.ts:865` (type `Moi`), `App.tsx:407` (commentaire). Les ~25 autres
occurrences de « pilote » sont le VERBE piloter (« le verdict pilote la carte », `v2Pilote`,
`prixPilote`…) — grammaire, pas l'ère pilote, conservées.
Captures : `r1_menu_compte_{avant,apres}.png`.

## R2 — Panneau de recherche
**Demandé** : retirer la section « Propriétaire » (front seul) ; restaurer le sélecteur de commune
(CP + nom entier au survol) en retrouvant le mandat fautif.
**Traité** : `SectionProprietaire` (PM, dénomination+autocomplétion, SIREN, forme juridique, APE,
dirigeants) retirée de `FiltreLabuse.tsx` — endpoints `/proprietaires/*`, filtres `pm_*` du store/back
et tests INTACTS (réversible). **Historique git** : le CP avait été ajouté par M55-H point 7 (commit
`3838d5d7`, 11/08/2026) et RETIRÉ par **M65 P7** (commit `61dde68b`, « passe visuelle », 27/08/2026,
menu 320→272 px). Restauré à l'état M55-H : menu 320 px, CP depuis `CP_COMMUNES` (source unique
mesurée), nom entier au survol (`title`). Aucune régression sur les autres filtres (tsc + suite).
Captures : `r2_filtres_proprietaire_*.png`, `r2_selecteur_commune_*.png`.

## R3 — Outil Communes restructuré
**Demandé** : écran d'entrée à TROIS boutons (Comparaison / Évolution / Acquisitions récentes) ;
le bloc « Acquisitions PM récentes » quitte la fiche commune.
**Traité** : écran d'entrée à trois portes (gabarit door-hot). « Acquisitions récentes » = sélecteur
des 24 communes + listing des changements de propriétaire PM (nouvel endpoint
`GET /communes/{commune}/acquisitions-pm`, même point de calcul `acquisitions_recentes` KF-2 L1,
limit 50, « N affichées sur M ») ; clic sur une ligne → fiche parcelle ; constat brut (« changement
de millésime, n'affirme pas une vente »), hors scoring ; zéro donnée = état vide honnête.
Vérifié en vif : Saint-Paul = 773 changements, 50 servis.
Captures : `r3_outil_communes_*.png`, `r3_comparaison_apres.png`, `r3_acquisitions_apres.png`.

## R4 — Fusion des deux fiches commune
**Demandé** : une seule fiche commune (celle du contexte), inventaire écrit, union sans perte ni
doublon, « Voir la fiche » du comparateur → fiche contexte en panneau droit.
**Inventaire avant fusion** :
- *Fiche OUTIL* (`CommuneFiche`, supprimée) : en-tête (nom, chip signal marché, « Voir ses
  parcelles → », ancres de navigation) · MARCHÉ local (`MarcheCommune`, 9 lignes sourcées
  Prix/Dynamique/Offre/Loyer + note « prix local ≠ médiane commune entière ») · RARETÉ & ZAN (stock
  foncier, % budget ZAN consommé/restant, reste/budget/rythme/horizon, caveat) · VÉLOCITÉ (tranche
  p25–p75, n dossiers, homogénéité).
- *Fiche CONTEXTE* (`ContextePanel`) : RNU · LE FONCIER DE LA COMMUNE (parcelles, surface, répartition
  zonage, classement servi, prix terrain nu par zone, mutations 12 m, permis 12 m) · MAIRIE (K2) ·
  Acquisitions PM (L1) · SRU · NPNRU · PLH EPCI · Marché logement INSEE RP 2023 · QPV · notes.
- *Doublons* : AUCUN bloc commun (les deux « marchés » sont des séries différentes : 9 lignes locales
  vs occupation INSEE — les deux sont conservées, chacune sous son titre).
**Traité** : ContextePanel = LA fiche commune — sections MARCHÉ local / RARETÉ & ZAN / VÉLOCITÉ
transférées (mêmes clés React Query, 0 fetch en plus), signal marché + « Voir ses parcelles → » hissés
dans l'en-tête. Acquisitions PM retirées (vivent dans R3, uniquement). Le comparateur ouvre cette fiche
(`setContexteCommune`), la porte « Voir le marché de X » de la fiche parcelle aussi. `CommuneFiche`
supprimée — une seule fiche commune dans l'app. Non transféré : les ancres de navigation de
l'ex-en-tête (chrome, aucune donnée) — le panneau se parcourt au scroll.
Captures : `r4_fiche_outil_{avant,apres}.png`, `r4_fiche_contexte_{avant,apres}.png`,
`r4_fiche_contexte_apres_sections.png`.

## R5 — Taxe d'aménagement
**Demandé** : diagnostiquer « Barème indisponible », réparer local + déploiement, vérifier les calculs
contre le barème officiel 974, accès depuis la fiche parcelle.
**Diagnostic** : le barème n'a jamais été cassé — `/outils` était ABSENT du proxy vite dev →
`/outils/taxe-amenagement/config` tombait sur vite (404 HTML) → `cfg.isError` → message. L'endpoint
répond 200 sur :8000 (vérifié en vif). Même famille que /bilan (M58), /anti-fiche (M55-N), M82.
**Traité** : `/outils` (et `/radar`, cf. R9) ajoutés au proxy. En prod FastAPI sert même origine (aucun
proxy) → rien à rejouer au déploiement ; ⚠ si la prod passe par Caddy (TRAIN 8), router ces préfixes.
**Calculs vérifiés contre la source citée** (service-public.gouv.fr A15416, relue ce jour) : valeur
forfaitaire 2026 hors IdF 892 €/m² (IdF 1011 documenté), piscine 251 €/m², PV sol 10 €/m², éolienne
3 000 €/mât, stationnement ext. 2 928 €/place (5 857 sur délibération), part communale 1–5 % (20 %
secteur), part départementale plafond 2,5 % — TOUT conforme au YAML daté/sourcé. Abattement 50 %/100
premiers m² RP + logements aidés (art. L.331-12). Taux communaux : issus des délibérations, non
centralisés → saisie obligatoire, JAMAIS un défaut inventé — l'outil le dit pour chaque commune sans
bloquer les autres (message dédié) ; départemental = plafond légal servi, étiqueté « à confirmer ».
Tests `test_taxe_amenagement.py` : 6 passed.
**Accès fiche** : porte « Taxe d'aménagement » dans la fiche parcelle ; l'outil charge d'emblée le
contexte de la parcelle (commune pré-remplie, surface du terrain en référence — la surface TAXABLE
reste saisie à la main, doctrine).
Captures : `r5_taxe_{avant,apres}.png`.

## R6 — Historique propriétaires par millésime
**Demandé** : enquête (où monté, quelle condition, pourquoi invisible) + bouton « Voir les anciens
propriétaires » dans l'onglet Propriétaire.
**Cause** : le composant est monté (tiroir Propriétaire de la fiche, `Fiche.tsx`) et FONCTIONNE —
mais (a) le fichier PM DGFiP ne couvre que ~19 % des parcelles (82 701) et il faut ≥ 2 millésimes :
sur une parcelle personne physique ou non couverte, il rendait `null` — RIEN, sans un mot ; (b) quand
il s'affichait, le dépli par millésime était un lien gris 10,5 px souligné pointillé, invisible.
**Traité** : vrai bouton mint « Voir les anciens propriétaires — N millésimes (2019–2025) » qui déplie
la timeline ; parcelle PM sans timeline → ligne d'absence honnête ; parcelle PP → silence justifié
(le bloc au-dessus explique déjà le workflow SPF). Constat brut, hors scoring, inchangé.
Captures : `r6_fiche_proprietaire_{avant,apres}.png` (parcelle témoin 97401000AB0001, Les Avirons —
7 millésimes, 1 changement ONF → Direction de l'immobilier de l'État).

## R7 — Intake admin Radar
**Demandé** : diagnostiquer le geste réel, corriger (focus auto, label visible, erreur claire, bouton
réactif), PREUVE Playwright du geste complet.
**Diagnostic** : le champ lien n'existait que par un placeholder gris sous la capture ajoutée (aucun
label, aucun focus) ; « Déposer » sans lien écrivait un message gris discret ; un échec réseau/serveur
n'était PAS catché → promesse rejetée en silence, bouton apparemment mort.
**Traité** : label « Lien de l'annonce * » au-dessus du champ ; focus automatique dès l'ajout d'une
capture ; bordure rouge + message clair sans lien ; « Dépôt… » pendant l'envoi ; échec réseau affiché
en rouge ; succès « ✓ en file d'extraction » en mint.
**PREUVE** : `frontend/qa/radar_intake_geste.mjs` — ajouter une image → focus/label vérifiés →
Déposer sans lien (bordure + message, rien n'est envoyé) → coller le lien → Déposer → la fiche
apparaît en file d'extraction. **9/9 VERT** (`r7_geste_preuve.png`). Les endpoints sont interceptés
(l'extraction réelle = vision IA, clé LIVE + vraie capture d'annonce requises) ; le pipe back est
couvert par la suite pytest pige. Aucune donnée de test en base.
Captures : `r7_admin_radar_{avant,apres}.png`, `r7_geste_preuve.png`.

## R8 — Carte et navigation
**Demandé** : retirer la pastille « Carte à jour au … », retirer le bouton « Zone », une seule
catégorie du rail ouverte à la fois.
**Traité** : pastille retirée — l'AVERTISSEMENT de retard (« ⚠ Carte au … — mise à jour en attente »,
tuiles plus vieilles que le run servi) est conservé (doctrine fraîcheur FIX-CARTE T1 : jamais de
chiffres périmés en silence). Bouton « Zone — Dessinez un polygone » retiré (Distance/Surface/Altitude
intacts ; store + back conservés, réversible). **Bug rail** : `openSources` ne fermait pas
`surveillanceOpen` (repro exact de Vic) — corrigé sur TOUTES les paires : openSources, toggleOutils,
ouvrirEntretien (IA), openParcours, setOpenProjet, setModule, openCompare ferment la Veille ;
toggleSurveillance/openSurveillance/toggleVeilles/toggleSuivis ferment le tiroir Outils ; setView
fermait déjà tout.
Captures : `r8_carte_{avant,apres}.png`, `r8_rail_veille_sources_{avant,apres}.png` (avant : Veille
derrière Sources ; après : Sources seule).

## R9 — Onglet Marché du Radar bloqué en « Chargement… »
**Demandé** : diagnostiquer et corriger l'endpoint ; sortir du chargement infini ; cause au rapport.
**Cause (double)** : (1) `/radar` ABSENT du proxy vite dev — en local tous les fetch du Radar client
tombaient sur vite (404 HTML). **L'endpoint `/radar/marche` est SAIN** : vérifié en vif sur :8000, il
répond proprement à zéro donnée (24 lignes, compteurs 0, `insuffisant=true` — l'état de démarrage digne
existe et s'affiche désormais). (2) `RadarMarche` ne lisait pas `isError` : erreur → `isLoading=false`,
`data=undefined` → « Chargement… » éternel. Corrigé : proxy comblé (commit R5) + état d'erreur honnête
avec « Réessayer » ; même défaut corrigé sur la fiche bien (`BienFiche`, RadarClient).
**Peut frapper d'autres endpoints** : OUI — (a) toute nouvelle route absente de `apiPaths`
(vite.config.ts) reproduit le 404 dev silencieux (historique : /bilan M58, /anti-fiche M55-N, 7 routes
M82, /outils + /radar ici) ; (b) le patron « useQuery sans isError » existe encore dans l'admin Radar
(Extraction/Reverif/Check : listes vides silencieuses en cas d'erreur — non bloquant, signalé, hors
mandat). L'écran Marché sera refondu (maquette en cours) — non refait ici, conformément au mandat.
Captures : `r9_radar_marche_{avant,apres}.png`.

## Gardes
- tsc 0 · build front OK · `test_taxe_amenagement` 6/6 · geste Playwright R7 9/9.
- Golden : 120 FAIL PRÉ-EXISTANTS, identiques à l'état documenté avant mandat (ancre `q_v10_m129` vs
  run servi `q_v11_m137` + libellé zonage M128-2-J) — branch-indépendant, le diff ne touche AUCUN
  fichier de scoring ; GARDE-RUN OK (431 663/431 663 évaluées).
- Suite pytest : **branche 1932 passed / 31 skipped / 0 failed** ; base (worktree `8270b4fc`)
  1931 passed / 32 skipped / 0 failed. Au niveau de la base — l'écart d'1 skip vient des skips
  conditionnels sur la disponibilité de la base réelle (variables entre runs), aucun échec des deux
  côtés. (Dépendance `qrcode` du 2FA absente du venv local — installée avant le run, sans lien avec
  le mandat.)
- Aucune donnée de test résiduelle (dépôts R7 interceptés côté navigateur, jamais en base).
