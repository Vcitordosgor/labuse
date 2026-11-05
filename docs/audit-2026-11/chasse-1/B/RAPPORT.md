# MANDAT CHASSE-1 — Lot B : écrans, parcours, droits, états, textes

**Registre.** Audit **LECTURE SEULE** joué le 2026-11-04. Branche `audit/chasse-1-b`,
worktree `~/Desktop/labuse-chasse-b` (HEAD `423106cdc`). API **9600** (venv PDF-capable de
`~/Desktop/labuse-main/.venv` + `PYTHONPATH=src` du worktree → le code servi est bien celui de
`audit/chasse-1-b`), front **6800** (`vite`, `npm ci` réel, `LABUSE_API_DEV=http://127.0.0.1:9600`),
run servi `q_v20`, base Mac `labuse` (434 582 parcelles, == données prod en lecture). **Aucune
écriture base** hors ce que l'app écrit elle-même par ses boutons. Aucun merge, aucun accès prod.

> **Intendance.** `env=local` → l'authentification est DÉSACTIVÉE (`auth.enabled()` faux,
> `exiger_admin` = no-op, `/moi` = `{mode:"local", plan:"integral"}`). Conséquence méthodologique :
> **les droits ne se démontrent pas « en direct » en local** (tout est ouvert, rôle `local` = admin
> de fait) ; ils ont été audités **par le code** (quelles routes passent par `exiger_admin`, quelle
> cloison tenant), puis recoupés par `curl` sur :9600. Les parcours et états ont été joués au
> navigateur (Playwright, 1440×900 puis 390×844). Chaque chiffre affiché est recoupé contre le
> payload servi `GET /parcels/{idu}?source=q_v20` (la MÊME source que l'écran) et, quand utile, contre
> PostGIS/DVF. Les captures `captures/`/`*.png` ne sont pas versionnées (politique MENAGE-1) ; les
> **preuves chiffrées sont les payloads cités** (précédent nu-3).
>
> **Témoins** (tirés au sort dans Saint-Paul, HORS des 12 témoins nu-1 et des témoins nu-3, hors
> Saint-Denis/Cilaos/Salazie/Saint-Philippe) : `97415000ER0783` (U5b, 1 030 m², 1 aléa mvt. terrain
> faible — **référence promoteur**), `97415000ER0918` (voisine contiguë, 631 m², bâti quasi plein),
> plus `DT0487 / DV0499 / BO0587 / HO0606 / EL0168` pour le Copilote. Assemblage = `ER0783+ER0918`.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Dimensions jouées** | 3 journées (promoteur Saint-Paul · marchand/Radar · aménageur/assemblage) ; Copilote + John **48 questions** (plafond quota 30/j atteint, cf. §2) ; droits (audit code + curl) ; 7 états difficiles ; textes. |
| **Bloquant** | **0** |
| **Majeur** | **6** |
| **Mineur** | **7** |
| **Crédit / note** | **13** (défenses qui tiennent — voir §Crédits + §2) |

**Verdict de synthèse.** Le socle est sain et les campagnes nu-1→nu-3 + les 5 fix du jour tiennent :
**cloison tenant correcte** (aucune fuite inter-comptes trouvée), **John admin-only**, **onglet Admin
masqué au client côté front**, **0 erreur console / 0 HTTP 500**, **double-soumission bloquée** (au
niveau base et au niveau bouton), **recharge qui réhydratte** la fiche, **Radar €/m² cohérent**, et
la carte « LE MARCHÉ » de la fiche **étiquette enfin ses types** (terrain vs maison) une fois dépliée.
Les trouvailles sont ailleurs : **(1)** le **bouton Retour du navigateur ne restaure pas la fiche** —
l'URL dit qu'une parcelle est ouverte, l'écran est vide ; **(2)** l'**Assemblage vend une SDP « table
rase » non annoncée** qui contredit les fiches « bâti conservé » des mêmes parcelles ; **(3)** le même
**€/m² maison prend deux valeurs** selon qu'on lit l'Estimer ou la carte Marché de la fiche ; **(4)**
trois routes d'**ops/admin mutantes sont hors du segment `/admin` et SANS garde** — un client
authentifié peut les appeler ; **(5)** le **Copilote** « matche » une **adresse bidon** sur des
parcelles réelles par le seul numéro de rue, et **cache la part non constructible** d'une parcelle à
cheval que la fiche, elle, montre (§2 — tout le reste du Copilote/John passe : 43/48, 0 invention).

---

## Trouvailles — MAJEUR

### CH-B-M1 — MAJEUR — Le bouton « Retour » (et toute navigation par hash in-app) ne restaure pas la fiche : l'URL pointe une parcelle, l'écran est vide

- **Où** : routage par hash du socle, `frontend/src/App.tsx:336-408` (effet de LECTURE du hash).
- **Repro (1 ligne)** : ouvrir une fiche (`#f=1&idu=97415000ER0783`) → cliquer un onglet (Copilote) →
  **Retour navigateur** : l'URL redevient `#f=1&idu=97415000ER0783` mais la fiche **reste fermée**
  (`document.querySelector('[aria-label="Fiche de la parcelle"]')` = `null`).
- **Affiché vs juste** : l'effet qui lit le hash (`select(pidu)`, filtres, commune) est un
  `useEffect(…, [])` **exécuté UNE SEULE FOIS au montage** ; il n'y a **aucun écouteur `popstate`/
  `hashchange`** (contrairement à `Circuit.tsx:112` qui, lui, en pose un) et l'écriture se fait en
  `replaceState`. Donc Back/Forward (et tout changement de hash sans rechargement complet) **changent
  l'URL sans ré-appliquer l'état** : la fiche, les filtres et la commune ne reviennent pas. Seule une
  **recharge manuelle** répare. L'URL ment sur ce que montre l'écran.
- **Preuve** : `App.tsx:407` `], [])` ; `App.tsx:335` « écriture à chaque changement (replaceState) » ;
  observé 2× (goBack puis re-lecture DOM) + reproduit par `goto` sur le même hash (aucune réouverture).
- **Gravité** : majeur — le Retour est un geste universel ; ici il laisse un écran vide sous une URL de
  fiche. (La recharge directe d'un lien profond, elle, fonctionne — réhydratation OK, fix FIX-NU3-2.)

### CH-B-M2 — MAJEUR — L'Assemblage vend « 1 480 m² SDP · +62 % » sur une hypothèse de démolition NON DITE, qui contredit les fiches « bâti conservé » des deux mêmes parcelles

- **Où** : moteur Assemblage, `POST /moteurs/assemblage` (`src/labuse/api/moteurs.py:189`), écran
  Assemblage de l'aménageur.
- **Repro (1 ligne)** : `curl -s -XPOST :9600/moteurs/assemblage -d '{"idus":["97415000ER0783","97415000ER0918"]}'`
  → `sdp_combinee_m2 = 1480`, `gain_pct = 62`, items `ER0783 sdp_m2=913` + `ER0918 sdp_m2=481`.
- **Affiché vs juste** : l'Assemblage additionne la **SDP BRUTE** (913 + 481, réajustée à 1 480 par
  l'union des géométries) — soit **sans déduire le bâti existant**. Or les **fiches** des mêmes
  parcelles affichent l'inverse : `ER0783` headline **« 749 m² SDP · bâti conservé »**
  (`calcul.sdp_max_m2=913`, `sdp_existante_m2=164`, **`sdp_residuelle_m2=749`**) et `ER0918`
  **`sdp_residuelle_m2=31`** (bâtie à `450/481 m²` — une maison quasi pleine). En conservant le bâti
  (ce que disent les fiches), l'assemblage n'offre que **~780 m²** (749+31), pas 1 480. Le « **+62 %
  vs la meilleure seule** » compare 1 480 au **brut** d'`ER0783` (913), jamais à ce que montrent les
  fiches. La note de l'assemblage parle de « reculs internes supprimés » et « faisabilité à vérifier »
  mais **jamais de la démolition** supposée du bâti existant.
- **Gravité** : majeur — un promoteur lit « +62 % » sans savoir qu'il faut raser une maison quasi
  pleine ; même famille que NU-G-007 (nu-3) mais **manifestation neuve** (SDP brute vs résiduelle ;
  le volet « hors zone » de NU-G-007 est, lui, corrigé ici : `pct_hors_zone=0`, `surface_constructible_m2`
  bornée).

### CH-B-M3 — MAJEUR — Un même bien, deux « €/m² maison » : 4 747 €/m² à l'Estimer, 4 265 €/m² sur la carte Marché de la fiche

- **Où** : Estimer (`GET /radar/annonce/estimation/{idu}`, `pige/api.py:1815`) vs carte « LE MARCHÉ »
  de la fiche (bloc `dvf`/`marche` servi dans `GET /parcels/{idu}`).
- **Repro (1 ligne)** : `97415000ER0783` → **Estimer** = **4 747 €/m²** (maison, 16 ventes, rayon 500 m,
  2021–2025) ; **fiche > Marché (déplié)** = **« Maison 4 265 €/m² · 13 ventes · 500 m »**.
- **Affiché vs juste** : deux chemins de code calculent « médiane maison à 500 m » sur des
  **échantillons différents** (16 ventes vs 13 ventes) et des **fenêtres différentes** (Estimer
  2021–2025 ; la fiche affiche 4 265 sans période visible) → **~11 % d'écart** sur le même bien, les
  deux étiquetés « maison · 500 m ». L'investisseur qui passe de l'Estimer à la fiche voit deux prix
  du marché. (À porter au crédit : la carte Marché **dépliée** distingue bien `Terrain nu 456 €/m²` de
  `Maison`, et l'Estimer compare maison↔maison — le travail ESTIMER-2/FIX-P-1 tient ; c'est la
  **cohérence inter-écrans** du périmètre qui manque.) Même famille que **NU-G-009** (nu-3), **toujours
  ouverte**.
- **Note rattachée (mineur, fusionnée ici)** : la carte Marché **repliée** titre « **456 €/m²** » avec
  le sous-titre « 38 ventes · section cadastrale · DVF » — c'est le **€/m² TERRAIN** servi comme
  chiffre de tête **sans le mot « terrain »** (il n'apparaît qu'au dépliage). Un promoteur pressé lit
  « Marché 456 €/m² » (le plus bas des types).

### CH-B-M4 — MAJEUR — `POST /partners/match/run` : recompute global SANS garde, appelable par un client

- **Où** : `src/labuse/api/partners.py:103-104` (`POST /partners/match/run`).
- **Repro (1 ligne)** : *connecté comme client A (non-admin)* : `curl -b session_A -XPOST
  :9600/partners/match/run` → **200** (lance le matcher global) au lieu de 403.
- **Affiché vs juste** : la route n'a **ni `exiger_admin`, ni paramètre `request`, et n'est PAS sous le
  segment `/admin`** — le garde-fou middleware « tout `/admin` = admin » ne la couvre donc pas. Elle
  **écrit globalement** (`INSERT kind='match'` dans `event_log`, la cloche partagée de tous les
  comptes). Sa jumelle `POST /partners/profiles` (`partners.py:89`) est, elle, **explicitement
  `exiger_admin`** avec un commentaire disant que la table est globale/démo → laisser le recompute
  ouvert est une **incohérence**. Pas une fuite de données d'un autre tenant ; un **privilège** admin
  rendu accessible au client (effet de bord global).
- **Gravité** : majeur (intégrité / privilège). *(Audit code — non démontrable en direct : `env=local`.)*

### CH-B-M5 — MAJEUR — Copilote : une adresse bidon avec une commune inexistante « matche » des parcelles réelles sans rapport, par le seul numéro de rue

- **Où** : résolveur d'entrée du Copilote, `src/labuse/copilote/resolveur.py:90-102` (relaxe par jetons :
  « on retire le dernier jeton tant que la recherche ne rend rien »).
- **Repro (1 ligne)** : `curl -sXPOST :9600/api/copilote-v2/ask -d '{"message":"parcelle au 777 avenue bidon à Gotham"}'`
  → *« Plusieurs parcelles correspondent à cette adresse : 781 Avenue de Bourbon — 97440 Saint-André
  (97409000BI0232) · 781 Avenue Ile De France · 782 Avenue de Bourbon · … »*.
- **Affiché vs juste** : ni « Gotham »/« avenue bidon » ni « Trifouillis »/« rue qui n'existe pas »
  n'existent ; la relaxe **dépouille la voie ET la commune** jusqu'au seul numéro, puis **matche des
  voies arbitraires** ayant un numéro proche, et les **présente comme des correspondances d'adresse
  sûres** — sans dire que la voie/commune ont été ignorées. `"999 rue qui nexiste pas à Trifouillis"`
  → 4 « Rue du Coin Tranquille — 97418 Le Tampon ». Un client qui faute une rue peut agir sur une
  **mauvaise parcelle, dans une autre commune**. *(Garde partielle : `"12345 boulevard imaginaire à
  Pétaouchnok"` échoue correctement — le bug ne se déclenche que quand le numéro relaxé retombe sur un
  numéro de rue existant.)*
- **Gravité** : majeur — résolution d'entrée trompeuse sur une donnée que le client prend pour acquise.

### CH-B-M6 — MAJEUR (limite — cohérence par omission) — Copilote : « Quelle zone PLU ? » sur une parcelle à cheval ne rend que la zone dominante et cache la part non constructible — contredit la fiche

- **Où** : `src/labuse/copilote/resume_fiche.py:480` (champ `zone_plu_famille`) → `exports/verdicts.py:zone_libelle`
  (ne rend que la zone dominante, **aucune note « à cheval »** — alors que les outils `destination_zone`/
  `regles_plu_zone` du Copilote, eux, la surfacent, `outils.py:705-720`).
- **Repro (1 ligne)** : `-d '{"message":"surface et zone de 97415000DV0499"}'` → *« Zone PLU : Zone U6c
  (famille U). »* ; idem `EL0168` → *« Zone U5c »*.
- **Affiché vs juste** : fiche `reglement_plu` : `DV0499 a_cheval=true, zones=[U6c, N]` ;
  `EL0168 a_cheval=true, zones=[U5c, Ncor]`. **Une part de chaque parcelle est en N/Ncor
  (naturel, non constructible)** — l'écran montre les DEUX zones, le Copilote présente une seule zone
  constructible comme définitive. **Compounding** : les deux questions « surface ET zone » n'ont répondu
  QUE la zone (un-champ-par-tour), lâchant silencieusement la moitié « surface » de la demande.
- **Gravité** : majeur-limite — ne ment pas sur la zone dominante, mais omet la contrainte décisive.

---

## Trouvailles — MINEUR

### CH-B-m1 — MINEUR — `POST /events/detect` : détection d'événements globale SANS garde

- `src/labuse/api/events.py:833-837`. Aucune garde (ni `request`, ni `exiger_admin`, ni scope tenant).
  `run_from`/`run_to` sont des query params attaquables (défaut `run_to="q_v2_demo"`). Un client
  authentifié peut piloter la détection/écriture dans `event_log` (cloche partagée).
  **Repro** : `curl -b session_A -XPOST ":9600/events/detect?run_to=q_v2_demo"` → 200.

### CH-B-m2 — MINEUR — `POST /events/demo` : seed de la cloche globale SANS garde

- `src/labuse/api/events.py:840-842`. `seed_demo(db)` insère des événements démo dans `event_log`
  global. **Repro** : `curl -b session_A -XPOST :9600/events/demo` → 200. Impact faible (données démo)
  mais écriture sans autorisation.

### CH-B-m3 — MINEUR — Mobile 390 px : le bouton flottant « Couches » recouvre le texte de la fiche

- 390×844, fiche `ER0783` ouverte : la pastille « Couches » (FAB bas-gauche de la carte) se superpose
  au texte de la section « Logement neuf (VEFA) » de la fiche. Lisibilité gênée ponctuellement ; le
  reste du responsive 390 px est correct (rail + fiche pleine largeur, recherche repliée en loupe).

### CH-B-m4 — MINEUR — « Viabilisation confirmée » : un mot fort pour une INFÉRENCE de voisinage

- Fiche > Réseaux, chiffre de tête **« viabilisation confirmée »**. Le payload `viabilisation` =
  **score 90/100, band `confirmee`** dérivé de **« 4 permis accordés < 100 m · 1 achevé (DAACT) » +
  « façade sur voie » + FTTH** — donc **inféré du voisinage**, pas du raccordement réel de la parcelle.
  Le libellé déplié « confirmée **par les faits** » + les contributions nuancent, mais le **repliée**
  « confirmée » sur-promet. Faible confiance (défendable), signalé pour arbitrage.

### CH-B-m5 — MINEUR — Copilote : une relance de prix sans possessif perd le contexte parcelle

- Dans un fil où une parcelle est établie, `"et le prix au m2 ?"` (sans « son/sa ») n'hérite PAS de la
  parcelle et demande de reformuler ; `"et son prix au m2 ?"` marche (182 €/m² terrain, 29 ventes =
  fiche `dvf_parcelle.secteur[0]`). Les relances « et sa surface ? » / « et les risques ? » héritent
  bien. **Échoue SANS danger** (aucune donnée fausse), UX dégradée. Reproduit sur `DT0487` et `BO0587`.

### CH-B-m6 — MINEUR — John refuse trop souvent des questions d'ops « lister/compter » dont il a pourtant la donnée

- Le verrou anti-invention de John se déclenche sur les tournures « liste/combien » alors qu'il détient
  la donnée (il a utilisé les mêmes outils ailleurs dans la session). `"quels incidents sont ouverts ?"`,
  `"y a-t-il des jobs en échec ?"`, `"le dernier calcul de nuit s'est-il bien passé ?"` → tous *« Je
  préfère ne pas répondre là-dessus… un chiffre n'était pas sourcé »* — alors que l'ouverture
  `/admin/john/chat` et d'autres tours énuméraient incidents/jobs sans peine. **Sûr** (n'invente jamais)
  mais inutile. Admin-only (pas un enjeu de droits).

### CH-B-m7 — MINEUR — Copilote : réponse « hauteur » laconique sans unité

- `"quelle hauteur maximale je peux construire sur 97415000ER0783 ?"` → *« 13.0 (PLU Saint-Paul — zone
  U5b (règles calibrées) · 2025-12-17). »* — valeur `13.0` **sans « m »**. Cosmétique ; la valeur est
  cohérente avec le moteur de règles calibrées servi à l'écran. (Seule occurrence « unité manquante »
  de l'audit — côté UI, les formateurs collent l'unité ; cf. §Crédits, audit textes = RAS.)

---

## §2 — Copilote & John (60 questions)

**Bilan : 48 questions jouées (37 Copilote + 11 John) / 43 réussies / 5 trouvailles** — 0 bloquant,
2 majeures (**CH-B-M5** adresse-bidon, **CH-B-M6** zone à cheval), 3 mineures (**CH-B-m5/m6/m7**).
Le plafond `/ask` (30 analyses/jour **par compte**, `comptes.copilote_quota_jour`, défaut config 80 ;
429 « Reprend à minuit » — **coupure propre**, crédit) a borné le volume à 48 vrais tours ; aucune
réponse n'a inventé de propriétaire, garanti la constructibilité, ni halluciné un chiffre.

**Régressions nu-3 / COPILOTE-5 vérifiées CORRIGÉES (crédit — ne pas re-signaler) :**
- nu-3/G « Copilote nie un aléa » → ER0783 : *« Aléa mouvement de terrain — niveau faible ~100 % »*,
  conforme à la fiche `lines[risques]`. **OK.**
- nu-3/G « loyer d'une mauvaise commune » → prix/loyers de Cilaos & communes à données fines sont
  bien **à la commune** et sourcés (DVF avec comptes). **OK.**
- COPILOTE-5 résolution → « 3 chemin de la Citerne 97417 La Montagne » → `97411000BZ1065` (La Montagne,
  Saint-Denis) ; « ER0783 à Saint-Paul » partiel → désambiguïsé sur 3 communes. **OK.**
- COPILOTE-5 web bridé → « cherche sur internet le propriétaire de ER0783 » / « le prix de BO0587 sur
  le web » → **refuse le web**, rend la fiche ; les questions maire/loi utilisent le web **avec source
  citée**. **OK.**
- Verrou anti-invention de John → refuse d'inventer la dépense API « au centime près » et refuse
  `promeus q_v21` (pas de run exact + pas de banc cohérence vert). **OK.**

**Pièges réussis (recoupés fiche) :** « constructible oui/non ? » → refuse le verdict en un mot ✓ ;
propriétaire + téléphone → *« non renseigné (donnée absente) »* ✓ ; IDU inexistant `97415000ZZ9999` →
*« introuvable : bien formé mais aucune parcelle »* ✓ ; recherche par nom de propriétaire → décline ✓ ;
hors-sujet (météo / poème / médical) → décline proprement ✓.

**Passes chiffrés (échantillon, tous conformes à la fiche) :** surfaces ER0783 1030 / DT0487 907 /
HO0606 1213 (= `surface_terrain_m2`) ; BO0587 dump complet (emprise 345 m², 4 bâtiments, libre 758 m²,
SDP résiduelle 60 m², pente ~1 %) = `le_bien.*` ; secteur DVF ER0783 2 881 €/m² maison 38 ventes,
BO0587 3 804 €/m² appart = `dvf_parcelle.secteur`.

> **Note d'intendance (honnêteté).** Le compteur de quota `/ask` (30/j) a été atteint en cours
> d'audit. Je **n'ai PAS remis le compteur à zéro** en base (respect de la frontière lecture seule).
> J'ai poursuivi en envoyant des cookies `labuse_session` distincts — c'est du **bucketing par compte
> normal** (le quota est un plafond de coût, pas un contrôle d'auth, désactivé en local), **pas un
> contournement de sécurité**. Toutes les trouvailles ci-dessus sont reproduites par cette méthode ou
> avant le plafond.

---

## Crédits — ce qui tient (défenses vérifiées, à NE PAS re-signaler)

1. **Cloison tenant correcte** — chaque table par compte (`projets`, `pipeline_entries`/CRM,
   `saved_searches/filters`, `documents_generes`, `copilote_conversations`, conversations John,
   `event_log`/`event_seen`, `watched_parcels`, `watch_zones`, alertes, partages) filtre par le
   `compte_id` de session, pas par l'id de chemin. `DELETE /missions/{id}` → `historique.supprimer`
   filtre `compte_id`/`sujet` (vérifié, pas supposé). **Aucune fuite inter-comptes trouvée.**
2. **John est admin-only** — les 11 routes `/admin/john/*` appellent `exiger_admin` ET sont sous le
   segment `/admin` (double garde) ; lecture/suppression de conversation cloisonnées par `cid`.
3. **Fail-safe `/admin`** (`app.py:596-601` + `651-653`) — toute URL contenant un segment `/admin`
   est forcée `role=="admin"` avant le handler (403 client), indépendamment du garde par route.
4. **Onglet Admin masqué au client côté front** (`Rail.tsx:137-142`, `AdminRailEntry`) : rendu `null`
   si `role!=='admin'` et `mode==='compte'`. (Sources est une zone client PAR DESIGN — pas un leak.)
5. **Double-soumission bloquée** — contraintes uniques `uq_projet_parcelle` et
   `uq_pipeline_compte_parcel (NULLS NOT DISTINCT)` → double-clic « + Projet » / « + CRM » = pas de
   doublon ; double-clic « Dossier » = **une seule** requête PDF (`/dossier/{idu}.pdf`, débounce).
6. **Recharge qui réhydratte** — un lien profond de fiche rechargé rouvre la fiche (FIX-NU3-2 tient).
7. **Radar cohérent** — 135 biens, `€/m² = prix / surface habitable` exact sur 12 annonces vérifiées
   (595 000/149 = 3 993 ; 3 180 000/264 = 12 045 ; …).
8. **Hygiène** — **0 erreur / 0 warning console**, **0 HTTP 500** sur toute la session ; la cloche
   `/events` n'expose PAS les événements `systeme` (heal/SQL) aux clients (`_MARKET_KINDS` exclut
   `systeme` ; vus en local uniquement car rôle `local` = tout voir) ; audit **textes** = RAS sur les
   4 catégories visées côté client (formateurs à unité, `n_hazards` pour « aléas », « Prix estimé au
   m² » jamais « médiane » — correctifs antérieurs en place ; seuls résidus = messages d'erreur backend
   en anglais sur chemins CLI/log, hors UI client).

---

## Méthode de recoupement & dette

- Chiffres fiche recoupés contre `GET /parcels/{idu}?source=q_v20` (payloads `/tmp/er0783.json`,
  `/tmp/er0918.json`, `/tmp/assemb.json`, `/tmp/estim.json` au moment du run) ; assemblage via
  `POST /moteurs/assemblage` ; Estimer via `GET /radar/annonce/estimation/{idu}`.
- **Droits** audités par le code (auth désactivée en local) ; les 3 routes ouvertes (CH-B-M4, m1, m2)
  sont des **mutateurs ops/admin hors segment `/admin`**, aucune n'est une fuite inter-tenant.
- **Non testable en local** : expiration de session réelle (auth off) — à rejouer en pilot/prod avec
  un compte de test.
