# VEILLE-3 — La Veille en une seule page

**Branche** `feat/veille-3` · worktree `~/Desktop/labuse-veille3` · ports 9040 (API) / 6240 (front) · q_v20
**État** construit + recette verte, **PAS mergé** (le merge est un geste de Vic). Aucun accès prod.

---

## Ce qui change

La Veille tenait sur **trois écrans** derrière la porte « Veille » du hub Radar :
1. un écran intermédiaire **« Choisissez ce que vous voulez surveiller »** (deux portes + réglage du mail) ;
2. une sous-page **« Vos parcelles suivies »** ;
3. une sous-page **« Vos alertes »**.

Elle tient désormais sur **une seule page** à deux colonnes. On y arrive **directement** depuis la carte
« Veille » de la page Radar. Les anciennes routes **redirigent** vers elle.

### En-tête
- Un seul **« ← Radar »**.
- Surtitre **VEILLE**, titre **« Ce que vous surveillez »**.
- Sous-titre **dynamique** : « N événement(s) depuis votre dernier passage » si N > 0, sinon une phrase
  d'explication courte. `N` = parcelles bougées (drapeau `nouveau`, 7 j) + annonces tombées (alertes non en
  pause). Calculé à partir de ce que la veille détecte déjà — rien d'inventé.
- Les **trois chips de fréquence du mail** (Chaque matin · Chaque lundi · Seulement dans la cloche) en haut à
  droite. **Même réglage qu'aujourd'hui** : même source (`/events/prefs`) et même mutation
  (`PATCH /events/prefs/frequence`) que Mon compte — comportement inchangé (y compris le no-op pilote
  documenté VEILLE-FIX-2 : un compte NULL ne persiste pas, défauts servis).

### Colonne gauche — parcelles suivies
- **Omnibox standard** en tête (`ParcelInput`, `withCarte=false`) → ajoute au suivi (`toggleWatch`).
- Chaque ligne : **adresse / secteur** (ou « Parcelle XX 0000, Commune » en repli), **IDU · surface · zone**,
  le **dernier événement détecté en badge** (mise en vente, permis déposé, vente, changement de
  propriétaire) avec son **ancienneté**, ou **« Rien de nouveau »**, et une **croix** pour ne plus suivre.
- **Clic sur la ligne → ouvre la fiche** (`focusParcelle(idu, {fiche:true})`).

### Colonne droite — alertes
- Bouton **« + Nouvelle alerte »** en tête ; le **formulaire de création reste celui d'aujourd'hui**.
- Chaque ligne : **critères en clair** (type · communes · budget), la ligne **« Surveillé : nouvelle annonce,
  baisse de prix, retrait. »**, et en badge le **nombre d'annonces tombées depuis la dernière visite** ou
  **« Rien cette semaine »** (ou « En pause »).
- Un **menu ⋯** : **Modifier** · Voir dans Radar · Mettre en pause/Reprendre · **Supprimer**
  (décision Vic du 30/10 : menu = Modifier + Supprimer, Pause conservée pour ne pas retirer une capacité,
  « Voir dans Radar » rangé dans le menu).
- **Modifier** rouvre le **même formulaire**, pré-rempli, et **remplace les critères en place** (id,
  date de création et pause conservés).

### États vides
Un état vide **par colonne** (titre + une phrase), dans la page — pas de page à part.

### Règles tenues
Aucun défilement horizontal · listes longues en **« Voir 200 de plus »** · formats français
(`1 358 m²`, `1,84 ha`, dates `jj/mm`) · un **seul « Retour »**. La cloche et les mails **ne changent pas de
comportement**.

---

## Implantation

**Front**
- `components/radar/VeilleEcrans.tsx` — réécrit : un seul composant `VeilleEcran` (en-tête + chips + deux
  colonnes `ColonneParcelles` / `ColonneAlertes`), le menu ⋯, le formulaire d'alerte réutilisé en mode
  création **ou** modification. Les anciens exports `VeillePortes`/`VeilleFoncier`/`VeilleAnnonces` sont
  retirés.
- `components/radar/RadarHub.tsx` — `veille`, `veille-foncier` et `veille-annonces` rendent **tous**
  `VeilleEcran` (la redirection des anciennes routes).
- `store/useApp.ts` — `openSurveillance`, `toggleVeilles`, `toggleSuivis` posent `radarEcran:'veille'` (les
  deep-links `#surveillance=parcelles|criteres` atterrissent sur la page unifiée).
- `lib/api.ts` — `SuiviItem` gagne `surface` + `zone` ; nouvelle `modifierRadarVeille(id, criteria)`.

**Back**
- `api/events.py` — `GET /events/suivis` enrichi : **surface de terrain** (`parcels.surface_m2`) et **zone
  PLU dominante** (`parcel_zone_plu`, `COALESCE(zone_lib, zone_fam)`, en une requête, gardée contre
  l'absence de la couche). Clés additives, rien de cassé.
- `pige/veille.py` — `modifier(...)` (remplace les critères en place, garde IDOR compte-scopée) ;
  `existe_identique(..., sauf_id=)` exclut l'alerte éditée (pas de faux doublon).
- `pige/api.py` — `PUT /radar/veille/{id}` : « Modifier » une alerte (409 si les nouveaux critères
  dupliquent une **autre** alerte du compte).

Aucune table ni écran neuf. Le formulaire d'alerte et la chaîne cloche/mail sont intacts.

---

## Recette

Dev sur la base Mac (`postgresql:///labuse`, compte pilote NULL : 9 parcelles suivies, 5 alertes).

| # | Preuve | Capture |
|---|--------|---------|
| 1 | **État rempli** — 2 colonnes, 9 parcelles (adresse/IDU·surface·zone, FR `1 358 m²` / `1,84 ha`, repli « Parcelle AB 0004, Saint-Paul »), 5 alertes (chips, « Surveillé : … », « Rien cette semaine » / « En pause ») | `captures/01-etat-rempli.png` |
| 2 | **État vide** — un état vide par colonne (titre + phrase), dans la page | `captures/02-etat-vide.png` |
| 3 | **Menu ⋯** d'une alerte (Modifier · Voir dans Radar · Reprendre · Supprimer) | `captures/03-menu-alerte.png` |
| 4 | **Modifier** — même formulaire, pré-rempli (commune « Le Tampon », surface 2000), boutons Enregistrer/Annuler | `captures/04-modifier-alerte.png` |
| 5 | **Redirection** — `#surveillance=criteres` (ancienne route) atterrit sur la page unifiée (titre « Ce que vous surveillez », les deux colonnes, **pas** de chooser) | `captures/05-redirection-anciennes-routes.png` |

Vérifié aussi :
- **Entrée directe** — la porte « Veille » du hub Radar ouvre la page unifiée, **sans** l'écran
  « Choisissez ce que vous voulez surveiller » (vérif DOM : `chooserPresent=false`, colonnes `parcelles`+`alertes`).
- **PUT Modifier** (curl) — surface 2000→2500 remplacée puis restaurée ; **dédup = 409** en reprenant les
  critères exacts d'une autre alerte.
- **Fréquence du mail** — même endpoint qu'avant ; le no-op pilote (compte NULL) est le comportement
  pré-existant documenté (VEILLE-FIX-2), donc inchangé.
- **Base non mutée** : l'état vide a été obtenu par **interception réseau** (mock des réponses
  `/events/suivis` et `/radar/alertes`), zéro écriture en base ; 9 parcelles + 5 alertes toujours en place.

> Les captures sont des artefacts locaux (`**/captures/` est `.gitignore` — convention dépôt), non versionnés.

### Tests
- **Front** : `tsc -b` **0** · `vitest` **301/301** · `vite build` **OK**.
- **Back** (base `labuse_test`) : `test_veille3.py` **3/3** (modifier en place · IDOR · dédup `sauf_id`) ;
  `test_pige_api` · `test_pige_socle` · `test_veille_fix2_lot_b` · `test_notifications_m85` ·
  `test_veille_fix1` · `test_veille2_lot1/2` · `test_veille_parite` · `test_pige_digests` ·
  `test_events_bascule` · `test_pige_depot2` · `test_radar_auto1` · `test_pige_client` · `test_pige_marche`
  → **tous verts**.
- **Pré-existant, hors périmètre** : `test_cloisonnement_1::test_copilote_questions_et_plafond_cloison`
  échoue — test `@pytest.mark.reel` (copilote/ia_log, « pas reproduit sur base vierge »), sans rapport avec
  la Veille et non introduit par ce lot.

---

---

## VEILLE-3-FIX (retouches Vic, 30/10 — même branche, pas de merge)

Quatre finitions après la première passe :

1. **Formulaire Modifier / Nouvelle alerte — chaque champ a son étiquette visible.** « Prix max » et
   « Surface min » n'étaient que des *placeholders* (le nom disparaissait dès qu'on tapait un chiffre). Ils
   ont désormais une **étiquette à gauche** (comme Type / Vendeur) ; le placeholder ne porte plus que l'unité
   (`€`, `m²`). Plus aucun chiffre dans un champ sans nom.
2. **Lieu-dits en majuscule initiale.** « le Chemin mon Repos » → **« Le Chemin mon Repos »** (première
   lettre capitalisée à l'affichage ; le reste du libellé est conservé tel quel).
3. **Parcelles suivies — lignes compactes dans un seul cadre.** Fini la carte par parcelle : un **seul cadre
   bordé**, lignes **séparées par un filet** (`border-b`, retiré sur la dernière), padding réduit, le dernier
   événement et la croix passent à droite de la ligne.
4. **Cartes d'alerte — plus de vide avant « Surveillé ».** Le menu ⋯ sort du flux (coin haut-droit absolu) :
   la ligne « Surveillé : … » **suit directement** les critères, marges resserrées.

Frontend seul (`VeilleEcrans.tsx`) — aucun changement back. `tsc -b` **0** · `vitest` **301/301**.

**Captures avant/après** :

| Sujet | Avant | Après |
|-------|-------|-------|
| Page remplie (lieu-dits (2) + cadre/filet (3) + vide alerte (4)) | `captures/fix-05-avant-rempli.png` | `captures/fix-06-apres-rempli.png` |
| Formulaire (étiquettes des champs (1)) | `captures/fix-07-avant-formulaire.png` | `captures/fix-08-apres-formulaire.png` |

---

## Gestes de Vic
Recette sur `:6240`, puis **merge** `feat/veille-3`. Pour relancer en local :
`PYTHONPATH=…/labuse-veille3/src LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost/labuse uvicorn labuse.api.app:app --port 9040`
et `LABUSE_API_DEV=http://127.0.0.1:9040 npm run dev -- --port 6240`.

> ⚠ Session parallèle RECETTE-4 : ce lot n'a touché ni la page Notifications, ni les outils, ni le Radar
> marché — uniquement la Veille (parcelles suivies + alertes) et ses endpoints propres.
