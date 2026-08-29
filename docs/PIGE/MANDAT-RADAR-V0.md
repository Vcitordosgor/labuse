# MANDAT — RADAR V0 (pige d'annonces)

**Statut** : gravé le 27/08/2026 — À LANCER (décision Vic : on ne fait plus attendre la ligne avocat, cf. §6).
**Branche** : `feat/radar-v0` (depuis main, arbre labuse, jamais main directement)
**Emplacement docs** : `docs/PIGE/` (ce mandat + rapports de recette par lot)
**Étape 0 obligatoire** : avant toute écriture, CC vérifie `pwd`, branche et arbre propre. Sinon : stop et signalement, zéro écriture.
**Régime AUTONOME de bout en bout.** Commits par lot (P0→P6). Findings RD-001→.

---

## AVENANT RADAR-HTML (29/08/2026) — la collecte passe de la CAPTURE au DÉPÔT DE PAGE HTML

> Cet avenant **remplace** les étapes 2→4 du §1 (« Vic capture les vignettes → agent vision ») et le
> §5 « File d'extraction ». Le reste (doctrines §2, cycle de vie, veilles, digests) tient. Il est écrit
> pour qu'un futur lecteur **comprenne l'arbitrage sans le refaire**.

**Pourquoi.** Une vérification du 29/08 a montré que la capture d'écran jette l'essentiel. Quand Vic
enregistre une page de RÉSULTATS Leboncoin en « page web complète » (Cmd+S), le fichier porte un bloc
`__NEXT_DATA__` où CHAQUE annonce est en JSON : prix, surfaces, `land_plot_surface`, type, DPE,
`first_publication_date` / `index_date`, `location` (city/zip/district/lat/lng + **`source`**), owner
(pro/private, siren)… La doctrine « collecte 100 % humaine » NE BOUGE PAS : le code ne requête jamais un
portail — il parse un **fichier déposé par un humain**. L'agent vision quitte ce chemin.

**Mesure du Lot 0 (échantillon `qa/radar-html/ECH-1.html`, Saint-Denis, 35 annonces) — ce qui a tranché :**

| Mesure | Résultat | Conséquence produit |
|---|---|---|
| M1 rattachables | 17/35 (14 maisons, 3 terrains ; 18 apparts sans objet) | le rattachement ne concerne que la moitié du flux |
| M2 `source=address` | **3/35**, et c'est du **street-level HERE**, pas rooftop (le point tombe dans *une* parcelle, pas toujours la bonne) | address ≠ parcelle exacte → on exige la cohérence de surface |
| M2 `source=city` | 32/32 coords **distinctes** (jitter par annonce), mais > 150 m souvent | floutage local exploitable au rayon serré seulement |
| M3 cascade 150 m + surface ±5 % | **5/17 candidate unique** ; au-delà de 150 m l'unicité s'effondre | rayon = 150 m |
| M4 sincérité | sur 3 « uniques » vérifiés : 1 juste, 1 sur annonce à jeter, 1 **faux** (parcelle vide) | « unique ≠ juste » → corroboration bâti obligatoire |
| M5 nouveautés | **0/35** `first_publication_date` = jour du dépôt ; **34/35 republications** | la date de vérité est `first_publication_date`, pas le tri « plus récentes » |

**Arbitrage Vic (29/08) : « les deux à parts égales ».** Radar = flux de marché filtrable + veilles +
digests + signaux croisés commune/zone (qui NE dépendent PAS du rattachement) **ET** rattachement
automatique dès l'ingestion — mais l'automatisme reste soumis à la doctrine « jamais un fait faux
servi » : RATTACHÉE seulement sur candidate unique **corroborée** (bâti présent pour un bâti), sinon
PISTE. Rattachement fiable mesuré ≈ 2 sur 35 : le produit ne repose donc pas dessus, il repose sur les
signaux de marché — c'est là qu'est le différenciateur (personne d'autre ne croise annonces × DVF ×
référentiel terrain nu calibré à La Réunion).

**Chemin d'entrée (remplace §1.2→4 et §5).**
1. Vic enregistre la page de résultats (Cmd+S, « page web complète ») et la dépose (page admin Radar).
2. `pige/html_next.py` parse `__NEXT_DATA__` — **échec BRUYANT** si absent/altéré/0 annonce (un parseur
   qui renvoie zéro en silence est le pire des cas ; Leboncoin peut changer la structure sans prévenir).
3. `pige/html_ingest.py` ingère : idempotent par `list_id` (re-dépôt = MAJ, jamais doublon), historise
   chaque baisse de prix, conserve TOUS les champs (même inutilisés — recollecte coûteuse sinon),
   ARCHIVE le fichier déposé + sa date (`pige_depots`, répertoire privé jamais servi).
4. `pige/coherence.py` (Lot 2) : une annonce dont les champs se contredisent (un « terrain » à 12 pièces
   de 1942, `habitable==terrain`, prix/m² > 4× le terrain nu de zone) part **À QUALIFIER** — hors stats,
   hors veilles. Jamais un fait faux servi.
5. `pige/rattachement_html.py` (Lot 3) : trois états — **RATTACHÉE** (unique corroborée / address dans
   parcelle cohérente) · **PISTE** (plusieurs candidates, aucun automatisme, bouton « Instruire ») ·
   **NON RATTACHÉE** (copro / sans critère, position = quartier, et c'est DIT).
6. `pige/signaux.py` (Lot 4) : « prix affiché vs référentiel de zone » et « écart demandé/acté » par
   commune (médiane Radar vs médiane DVF), alimentant l'Étude de zone et Communes. ÉCARTS constatés
   entre deux sources datées, jamais une estimation ni une prévision, aucun verdict.
7. Cycle de vie (Lot 5) inchangé SAUF : une republication (`index_date` bouge, `list_id` inchangé) est
   une CONFIRMATION (repousse `a_reverifier`) ; à prix inférieur, une BAISSE. `vendue`/`retiree_sans_vente`
   n'existent que sur une annonce RATTACHÉE, jamais une PISTE, jamais déduites d'un lien mort.

> Le fichier historique du mandat s'appelle `MANDAT-RADAR-V0.md` (le mandat RADAR-HTML citait
> `MANDAT-PIGE-V0.md` — même document ; corrigé ici).

---

## 1. Vision produit (le contrat, en 8 étapes)

1. Vic regarde les nouvelles annonces du jour sur les portails (Leboncoin, SeLoger, PAP, sites d'agences…) — en humain, avec ses recherches sauvegardées et alertes email de particulier.
2. Vic capture les annonces pertinentes du jour (~5 à 30 vignettes).
3. Vic envoie captures + liens dans la page admin « Radar ».
4. L'agent (vision IA) analyse chaque capture et extrait les faits.
5. L'agent tente le rattachement à la parcelle (cascade de matching).
6. L'annonce validée entre en veille : les clients dont les critères matchent sont notifiés.
7. Le client reçoit un digest mail de fin de journée.
8. Le client clique → fiche LABUSE de la parcelle/annonce → gros bouton « Voir l'annonce sur [portail] » → redirection vers le portail source.

**Ce que LABUSE affiche : des FAITS + un LIEN. Jamais l'annonce.**

---

## 2. Doctrines gravées (non négociables)

- **Collecte 100 % humaine.** Aucun code du repo ne requête, ne fetch, ne parse, ne capture un portail d'annonces. Interdiction absolue — recette : `grep -ri "leboncoin\|seloger\|pap.fr\|logic-immo\|bienici" --include="*.py" --include="*.js"` ne doit remonter que des constantes d'affichage (noms de portails, préfixes d'URL pour le bouton sortant). Tout ce qui entre dans le système passe par la saisie admin.
- **Jamais de republication.** Ni photo, ni titre, ni texte d'annonce, ni coordonnées de l'annonceur — nulle part dans l'app, les mails, les exports. Les captures sont des documents de travail internes : répertoire privé non servi par le web (`/srv/labuse/pige/captures/`, hors racine publique, inclus au backup), aucune URL publique, jamais.
- **Sourcé / Estimé / Absent s'applique au rattachement.** Parcelle unique haute confiance = Sourcé. 1-3 candidates = Estimé, candidates affichées avec niveau de confiance — jamais un pin unique faussement sûr. Aucune parcelle plausible = Non rattachée (commune seule). Le faux positif reste le péché cardinal : un négociateur qui frappe à la mauvaise porte à cause de nous ne revient pas.
- **Anti-invention sur l'extraction.** Champ illisible ou absent de la capture = `null` (Absent). L'agent ne devine JAMAIS. Champs sous seuil de confiance surlignés à la validation.
- **Fraîcheur** = date de publication portail si visible sur la vignette, sinon date de saisie — le champ affiché précise laquelle des deux.
- **Domaine transactionnel hors runs** (comme le CRM interne) : les tables `pige_*` vivent en continu, pas de bascule. Déclaré ici pour conformité doctrine « run-scoped ou mort ».
- **Périmètre V0** : VENTE uniquement (pas de location). Maisons, terrains, immeubles, appartements (rattachement appartement = parcelle de la copropriété, étiqueté « copro »). Hors 24 communes = rejet à l'intake avec motif.
- **Le Radar n'entre pas dans le scoring.** Il s'affiche, il ne pondère rien.

---

## 3. Modèle de données — schéma isolé `pige_*`

Tout ce qui est collecté vit dans ses propres tables. **En V0, rien n'arrose le reste de l'app** (pas de badge sur la fiche parcelle, pas d'entrée dans le scoring) : l'arrosage se décidera plus tard, mandat séparé. L'isolement est ce qui rend cette décision réversible.

- `pige_biens` — le bien physique (`bien_id`), sa commune, son rattachement parcelle (idu + niveau Sourcé/Estimé/Absent + confiance), son statut de cycle de vie, ses dates (publication, première saisie, dernière confirmation).
- `pige_annonces` — une occurrence portail d'un bien (`bien_id`, portail, url_sortante, date_saisie). Un même bien peut porter plusieurs annonces (LBC + SeLoger).
- `pige_faits` — les faits extraits et validés : prix, type, pièces, surface_hab, surface_terrain, dpe_classe, dpe_conso, dpe_ges, particulier_pro. Chaque champ porte son étiquette Sourcé/Estimé/Absent.
- `pige_prix_historique` — une ligne par changement de prix constaté (date, ancien, nouveau) → alimente le drapeau baisse et la sparkline.
- `pige_captures` — métadonnées des captures (chemin privé, date, hash) ; **jamais servi par le web**.
- `pige_clics` — chaque clic sortant (client, bien, date) → alimente « usage par outil » du dashboard Produit.

**Événements** dans l'**event_log unifié** existant : `pige.nouvelle`, `pige.baisse_prix`, `pige.statut_change`, `pige.vendue_dvf`, `pige.signalement_client`, `pige.digest_envoye`, `pige.intake_vide_48h`.

**Dédoublonnage inter-portails** (même bien sur LBC + SeLoger) : à la saisie, recherche de `bien_id` existant sur (commune identique) ∧ (prix ±2 %) ∧ (surface_hab ±5 % ∨ surface_terrain ±5 %). Match → rattacher au même `bien_id`, comparer prix (→ baisse éventuelle), proposer la fusion à la validation. Pas de match → nouveau `bien_id`.

---

## 4. Cycle de vie des annonces (statuts + détection, zéro robot)

| Statut | Entrée | Détection |
|---|---|---|
| `active` | validation Vic | — |
| `baisse_prix` (drapeau, pas un statut) | prix_courant < prix précédent | re-saisie dédupliquée OU champ prix de la file de re-vérif |
| `en_vente_longue` | > 90 j depuis date_publication | job quotidien |
| `a_reverifier` | > 60 j depuis date_derniere_confirmation | job quotidien |
| `retiree` | Vic la marque (file de re-vérif) | clic humain ; le signalement client seul ne retire pas (anti-abus), il pousse en tête de file |
| `vendue` | match DVF | job à chaque ingestion DVF : même parcelle (Sourcé uniquement) + mutation dans [3 ; 18] mois après publication → statut + délai + **écart prix affiché / prix acté** |
| `retiree_sans_vente` | retirée + aucun DVF sous 12 mois | job mensuel de recalcul — **la cible en or du service Courrier** (pont V1) |

Rien ne se supprime, jamais. La carte par défaut montre `active` + `en_vente_longue` ; les autres statuts sont des filtres.

---

## 5. Lots de réalisation

### Lot P0 — Socle données + garde légale
Tables `pige_*`, migrations (runner heal-résilient conforme GB-011), répertoire captures privé + inclusion backup, événements event_log, test grep anti-requêtes-portails ajouté à la recette permanente.

### Lot P1 — Intake admin + extraction + validation (la page « Radar » du dashboard)
**Page entière** du dashboard admin (route admin réservée au compte Vic, comme le reste), pensée mobile (saisie depuis le téléphone, upload galerie). Quatre zones :

1. **Saisie du jour** : dropzone multi-captures + champ lien par capture ; détection URL déjà en base (doublon → proposer mise à jour prix au lieu de créer) ; contrôle commune ∈ 24 (sinon rejet motivé).
2. **File d'extraction** : chaque capture → appel vision (branché sur `ia_budget`, quota compté) → fiche pré-remplie JSON strict {prix, type, pièces, surface_hab, surface_terrain, dpe_classe, dpe_conso, dpe_ges, commune, particulier_pro, date_publication?} ; champs incertains surlignés (mauve — surface IA, conforme DA) ; Vic corrige/complète → **Valider** (1 clic). Rien n'est publiable avant validation.
3. **File de re-vérification, à DEUX niveaux** (décision Vic — pas de plafond bas, il peut en absorber beaucoup) :
   - **(a) passage LÉGER, en volume** : une ligne par annonce, lien sortant + un bouton [Toujours en ligne] — l'écran doit permettre d'en enchaîner beaucoup, rapidement, au clavier si possible.
   - **(b) passage ATTENTIF** sur celles qui ont bougé : [Prix modifié → champ] [Retirée], relecture du prix et ajustement du statut.
   - **File priorisée** : les plus anciennes non confirmées, celles proches du seuil de vente longue (90 j), celles suivies par un client — d'abord.
4. **Arbre de check quotidien** (le rituel, en checklist) : captures du jour saisies ✓ · file d'extraction vidée ✓ · file de re-vérif du jour traitée ✓ · signalements clients en attente ✓ · nouveautés / en vente longue / baisses du jour en compteurs. Cible affichée : **≤ 15 min/jour**. Alerte `pige.intake_vide_48h` si aucune saisie depuis 48 h (rappel doux, pas de culpabilisation).

### Lot P2 — Rattachement à la parcelle (cascade)
Cascade de matching, dans l'ordre, chaque étage étiquetant son niveau de confiance :
1. **GPS** si la vignette porte une localisation exploitable → parcelle contenante.
2. **BAN** (adresse ou lieu-dit lisible) → géocodage → parcelle contenante.
3. **DPE ADEME** (déjà ingéré) : croisement classe + conso + surface + commune → adresse probable.
4. **Morphologie / FLAIR** : surface bâtie, présence piscine, surface terrain → candidates plausibles de la commune.

Sortie : parcelle unique haute confiance = **Sourcé** · 1 à 3 candidates = **Estimé** (toutes affichées, avec confiance) · rien de plausible = **Non rattachée**, commune seule. Jamais de pin unique faussement sûr.

### Lot P3 — Écran client (carte + listing + fiche)
Reprend le patron des outils existants : **filtres à gauche, carte à droite**, PLUS un listing (décision Vic).
- **Filtres** : commune, type de bien, fourchette de prix, fourchette de surface, particulier/pro, statut, période, et « rattachée à une parcelle » oui/non.
- **Carte** : **uniquement les biens rattachés** (pins par statut). Branchée sur la carte existante, pas une carte parallèle.
- **Listing** : **TOUS les biens**, rattachés ou non, avec une **pastille distinguant les deux cas** (libellé court et clair, à proposer). Triable (récentes, prix, ancienneté, baisses).
- **Clic dans le listing (décision Vic, précise)** : un bien **rattaché** → va sur la carte, à sa parcelle. Un bien **NON rattaché** → part directement sur le portail source (nouvel onglet, `rel="noopener noreferrer"`).
- **Fiche** : les faits + leurs étiquettes, l'historique de prix, le statut, la parcelle rattachée avec son niveau — et le gros bouton **« Voir l'annonce sur [portail] »** (seul chemin vers la source). Bouton client « Signaler : annonce retirée / erreur » (→ event + tête de file de re-vérif).
- Tous les clics loggés dans `pige_clics`.

### Lot P4 — Veille + digests
- Dans la veille existante : nouveau type « Radar » — le client crée ses critères (ex. terrain > 2 000 m², Saint-Benoît, particuliers uniquement) et coche ses événements (nouvelle / baisse / retour marché).
- **DEUX envois distincts, en fin de journée heure Réunion** (décision Vic) :
  - **(a) digest quotidien** à tous les clients actifs : les nouveautés du jour.
  - **(b) alerte veille** à ceux dont les critères correspondent.
  Un client concerné reçoit **les deux** — ils ne se remplacent pas. **Un mail ne part jamais vide.**
- Via la fonction unique `envoyer_mail` — **template Brevo ID 12 à créer par Vic**. Écris au rapport la **liste exacte des variables** que le template doit porter, pour qu'il le monte sans deviner. Contenu : liste factuelle (type · commune · prix · surface · lien fiche LABUSE) — **jamais de lien portail direct dans le mail** : le clic passe par la fiche, on mesure. Vouvoiement, signé Victor, cohérent avec les templates 4→11.
- Cloche in-app (event_log) en miroir du mail.

### Lot P5 — Cycle de vie automatisé
Jobs quotidiens (statuts par ancienneté), job DVF (statut vendue + écart prix — affiché uniquement si rattachement Sourcé), job mensuel `retiree_sans_vente`. Historique de prix visible sur la fiche (mini-sparkline).
**Garde** : `retiree_sans_vente` ne se déduit JAMAIS d'un simple lien mort. Lien mort = `retiree`. Seule l'absence de mutation DVF sous 12 mois qualifie `retiree_sans_vente` — c'est la cible Courrier, une erreur ici enverrait un courrier à quelqu'un qui vient de vendre.

### Lot P6 — Onglet « Marché » (les stats secteur)
Dans l'outil Radar, un onglet agrégé par commune (24 lignes + total île) : annonces actives · nouvelles /30 j · retirées /30 j · vendues (DVF) /90 j · prix médian €/m² terrain et €/m² bâti · délai médian avant retrait/vente · taux d'échec (retirées_sans_vente / clôturées) · part particuliers. Mini-heatmap île. **Honnêteté statistique gravée** : chaque chiffre affiche son n ; toute cellule avec n < 5 affiche « — (échantillon insuffisant) ». Pas de fausse précision — c'est la boussole appliquée aux stats.

---

## 6. Prérequis — état au lancement
- Dashboard admin V1 livré ✓ (la page Radar s'y insère comme page dédiée).
- `ia_budget` actif ✓ (l'extraction vision compte dans le quota, ligne visible section IA du dashboard).
- Template Brevo ID 12 : **à créer par Vic** — non bloquant pour P0→P3, requis pour P4.
- **Ligne avocat : décision Vic du 27/08/2026 — le mandat se lance sans attendre sa réponse.** La question lui sera posée en parallèle (outil de veille : faits extraits manuellement d'annonces publiques + lien de redirection vers la source, captures conservées en interne, aucune coordonnée de vendeur). Les doctrines du §2 restent la ligne de conduite et ne bougent pas sans son avis écrit. Prévoir la clause CGU : informations issues d'annonces publiques, redirection vers la source, exactitude non garantie, étiquetage Sourcé/Estimé.

## 7. Décisions tranchées par Vic (27/08/2026)
1. **Nom public : « Radar »** (cohérent avec « radar foncier », sans jargon).
2. **Digest : fin de journée**, deux envois distincts (cf. P4).
3. **Appartements INCLUS dès la V0**, avec maisons, terrains et immeubles.
4. **File de re-vérification : pas de plafond bas**, deux niveaux, file priorisée (cf. P1.3).
5. **Écran client** : filtres + carte + listing, carte = rattachés seulement, listing = tout avec pastille, clic conforme à P3.

## 8. Explicitement HORS V0 (V1, mandats futurs)
Badge Radar sur la fiche parcelle · croisement score × annonce (« score élevé + en vente particulier ») · pont automatique retirée_sans_vente → CRM/Courrier · intake WhatsApp (réutilisation plomberie TANIA) · bascule de la collecte sur flux agrégateur (Melo/MoteurImmo) si le rituel dépasse ~30 min/jour ou à l'extension hors 974 · coordonnées vendeurs (jamais sans avis avocat écrit) · label « mise en vente » comme feature d'entraînement du score.

## 9. Recette et fin de mandat
Recette technique : zéro requête sortante vers un portail (grep + revue des logs réseau, à affirmer explicitement au rapport) · aucune photo ni texte d'annonce visible où que ce soit · schéma isolé, zéro écriture dans les tables existantes · carte = rattachés uniquement, listing = tout avec pastille, clic conforme · deux digests distincts · page admin Radar opérationnelle · Radar hors scoring · gardées G1-G6 vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · objets [RADAR-TEST] purgés.
Captures des écrans livrés (390 et 1440) au rapport, avec leur nombre annoncé. Liste des variables du template Brevo 12 au rapport.
Recette d'usage (par Vic, après merge) : deux semaines de rituel réel, puis `docs/PIGE/RECETTE-FINALE.md` — temps quotidien effectif (cible ≤ 15 min), taux de rattachement Sourcé+Estimé, digest reçu conforme.
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (`git merge --no-ff feat/radar-v0`). **Tu ne merges pas.**
