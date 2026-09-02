# COMPTE-RENDU — RETOURS-9 (recette 02/09, 21 h)

Branche `fix/retours-9`. Étape 0 vérifiée : `pwd` = `/Users/openclaw/Desktop/labuse`,
branche `fix/retours-9`, arbre propre au départ. Aucun sous-agent n'a touché à git.

---

## Q1 — Circuit vide : LA CAUSE EXACTE (reproduite sur la base réelle de Vic)

**Reproduction réelle** (`LABUSE_DATABASE_URL` du `.env` → `postgresql+psycopg://openclaw@localhost:5432/labuse`,
TestClient sur `GET /admin/flux`, env `local` → `exiger_admin` no-op) :

- statut **200**, réponse **valide** (aucune brique en erreur, `erreurs: null`) — mais **55,75 s**.
- Le front `Flux.tsx` fait `if (!d) return « Chargement… »` : il attend la charge COMPLÈTE avant de
  rendre quoi que ce soit → « Chargement… » interminable (et un reverse-proxy coupe bien avant 55 s).

**Profil par brique** (base réelle) :

| brique | durée |
|---|---|
| `flux.construire_flux` | 0,23 s |
| `releves.bloc_radar` | 0,01 s |
| `coherence_flux.verifier` | 5,65 s |
| **`bascule_flux.runs_termines`** | **53,56 s** |
| `bascule_flux.derniere_bascule` | 0,01 s |

**Cause exacte** : `runs_termines` calcule, pour chacun des runs NON servis (ici 6 sur 7), l'écart au
run courant = `golden_ops.comparer()` (~4,9 s) **+** un `COUNT` avec self-join sur `parcel_p_score_v2`
(**3 021 649 lignes**, ~2,4 s). 6 × ~7,3 s + coherence 5,6 s ≈ **50 s**. Le test passait en base de
test parce que `parcel_p_score_v2` y est minuscule.

**Correctif** (rendu progressif, option §2 du mandat) :
- `/admin/flux` ne calcule plus les runs → il ne garde que les briques rapides (**5,10 s** mesuré),
  et rend le Circuit tout de suite.
- Les runs terminés + écarts arrivent par une 2ᵉ requête `/admin/flux/runs` (`Flux.tsx` : `useQuery`
  dédié, indicateur « Calcul des écarts au run servi en cours… »).
- `runs_termines(limit_ecart=4)` : l'écart coûteux n'est calculé que pour les 4 runs que la page
  affiche (`.slice(0,4)`), plus pour tous → `/admin/flux/runs` retombe de ~53 s à ~33 s.
- Test de rendu **avec la réponse RÉELLE capturée** (`__fixtures__/adminFluxReal.json`) :
  `Flux.circuit.test.tsx` prouve que la page rend (n'est jamais bloquée sur « Chargement… »).

## Q2 — Catalogue : 5 compteurs, somme = 64 (mesuré sur la base locale)

**5ᵉ état ajouté** : `jamais_verifiee` (surveillée mais l'agent n'est pas encore passé, aucun
`dernier_statut`). Avant, ces sources tombaient à tort dans « à jour ».

Compteurs **AVANT** un passage de `sentinelle-sources` (état livré tel quel chez Vic) :

| état | N |
|---|---|
| à jour | 4 |
| nouvelle version | 0 |
| à rafraîchir | 0 |
| non surveillée | 20 |
| **jamais vérifiée** | **40** |
| **somme** | **64** |

→ c'est exactement le constat « 4 sur 64 » : seules 4 sondées, 40 surveillées jamais vérifiées.

Compteurs **APRÈS** un passage réel de `sentinelle-sources` sur la base locale (42 sources sondées,
1 nouvelle version, 1 injoignable) :

| état | N |
|---|---|
| **à jour** | **43** |
| **nouvelle version** | **1** |
| **à rafraîchir** | **0** |
| **non surveillée** | **20** |
| **jamais vérifiée** | **0** |
| **somme** | **64** |

Aussi livré : bouton **« Vérifier toutes les sources maintenant »** (lance le job `sentinelle-sources`,
le même que le CRON — endpoint `/admin/cron/{nom}/run` rendu LOCAL-SAFE, cf. Q2.4) ; action principale
**« Vérifier maintenant »** sur une source jamais vérifiée (plus de « — ») ; étiquette AUTO/MANUELLE
sous chaque nom ; pied « Qui fait quoi » : « En local, le CRON ne sonne pas : cliquez Vérifier toutes
les sources ». Test : `Sources.veille.test.tsx` verrouille la partition (somme des 5 = total).

## Q3 — Barre de recherche du Catalogue retirée.

## Q4 — Surfaces : 21, LE CHIFFRE VRAI

Établi sur la base réelle : **21 surfaces au total = 20 sur `q_v11_m137` + 1 vivante (hors run)**.
La 1 vivante n'est PAS « rattachement adresse → IDU » comme le mandat le supposait : c'est
**« Remonter le temps »** (`key=temps`, groupe Outils, `run='vivant'`). `coherence.n_surfaces`=20
(surfaces run-scopées), `comptes.n_surfaces`=21 (total). Une seule phrase exacte partout :
**« 21 surfaces · 20 sur q_v11_m137 · 1 vivante (hors run) »**, identique au bandeau et à la colonne
(test d'égalité : `Flux.circuit.test.tsx` vérifie 2 occurrences de la MÊME chaîne).

## Q5 — Circuit : ligne d'aide « Cliquez une source, un moteur ou une surface : tout ce qui est relié
s'allume… » + bouton « Tout désélectionner ».

## Q6 — « Horloge » renommé **CRON** partout (onglet, pied « Qui fait quoi », description AdminView,
messages). Clé interne `horloge` → `cron`.

## Q7 — Radar › Instruire : annonce ↔ candidate côte à côte

Écran refondu : deux colonnes **ANNONCE** (type · surface habitable · surface terrain · prix ·
quartier/commune · lien portail photos) et **CANDIDATE** (IDU · surface cadastrale · surface bâtie
BD TOPO · nombre de bâtiments · zone PLU · adresse BAN · ortho centrée) ; une ligne
**« concorde / diverge »** (critères ✓/✗ déjà calculés) + le score de confiance ; décision
**Rattacher · Suivante · Aucune**. Aucun calcul neuf : les faits candidate sont lus de la fiche
parcelle (`parcels`, `p_model_bati`, `parcel_zone_plu`, `adresses`, `bati.fiche_block`), chaque champ
gardé (base partielle → `null`, jamais un 500). Test : `_candidate_fiche` robuste sur IDU inconnu.

## Q8 — Fiche parcelle

Onglets Analyse/Autour/Actions **retirés** → fiche unique qui défile. Sous l'IDU, trois **boutons
pleins** du gabarit des tuiles d'export : **Cadastre Géoportail** (vert) · **Pages jaunes** (jaune) ·
**Google Maps** (blanc) — ils quittent les Exports. Exports en bas sur **2 lignes de 3** :
PDF · Dossier · Finance / Argumentaire · Courrier · Pré-dossier PC (`GrilleOutils cols={3}`). La ligne
**« À proximité »** entre dans la carte **« Autour de cette parcelle »**, en sous-ligne.

## Q9 — État cliqué = PLEIN de sa couleur (encre sombre), partout — composants passés

Règle DA appliquée (`bg-<couleur>` + encre sombre, plus un simple liseré) :

| contrôle | fichier:ligne | classe active |
|---|---|---|
| + CRM (dans le CRM) | `fiche/Fiche.tsx:536` → `.act-cmp` | `styles/index.css:408` : `background:var(--mint); color:var(--mint-on)` |
| + Projet (rattaché) | `fiche/Fiche.tsx:607` → `.act-amber-on` | `styles/index.css:407` : `background:var(--amber); color:var(--ink)` |
| cloche (ouverte) | `header/Header.tsx:363` | `border-mint bg-mint text-mint-ink` |
| contour 3D | `map/MapToolbar.tsx:97` | `border-mint bg-mint text-mint-ink font-medium` |
| outils de la carte | `map/MapToolbar.tsx:115` | `bg-mint text-mint-ink` |
| chips de filtre | `panel/FiltreLabuse.tsx:97` | `border-mint bg-mint text-mint-ink` |
| chips Catalogue | `admin/Sources.tsx:311` | `border-mint bg-mint text-mint-ink font-medium` |
| onglets Données | `admin/Donnees.tsx:56` | `bg-mint font-semibold text-mint-ink` |
| onglets Radar | `admin/Radar.tsx:609` | `bg-mint font-semibold text-mint-ink` |
| chips Sources client | `sources/SourcesPage.tsx` (Toutes/thème) | `border-mint bg-mint text-mint-ink` |
| boutons de tri Radar | `panel/ResultsSection.tsx:369` | `bg-mint font-semibold text-mint-ink` (déjà plein) |

## Q10 — Panneau « Poser une question »

Encart « L'IA ne juge pas le sentiment… » (AvisIA) **retiré** ; suggestion « Pourquoi ce statut ? »
**retirée** ; **toute mention « premium » retirée** côté client (badges AskBar, titre Header, token
`strings.ts`). *Arbitrage* : les commentaires internes « matrice premium v2 » (status.ts/tokens.ts/
types.ts/Fiche.tsx) sont un NOM DE SCHÉMA de scoring, sans rapport avec un palier client — laissés
intacts. Trois exemples cliquables ajoutés au Copilote (« Dis-moi tout sur la parcelle 97415000CV1186 »,
« Combien de parcelles possède CBO Territoria ? », « Quels sont les pièges de la parcelle
97415000CV1186 ? ») — cliquer LANCE la question (raccourcis R12).

## Q11 — Page Sources client

Chips de tri **retirées** → « Toutes » + accordéon replié « Filtrer par thème » (catégorie du
catalogue) ; ligne d'exploitation « N vérifiées automatiquement · radar amont… » **retirée** ;
dernière colonne (méthode de veille) **retirée** ; intro en **pleine largeur** et raccourcie
(« Chaque chiffre LABUSE est traçable jusqu'à sa source publique… ») ; **cinq tuiles** lues des
données réelles (endpoint `/sources/couverture`) :

- **64** sources · **64** à jour · **431 663** parcelles couvertes · **24/24** communes ·
  dernière analyse **arrêtée au 27/08/2026** (`q_v11_m137`).

*Arbitrage* : « transactions DVF analysées » (29 566) et « annonces Radar suivies » (109) sont
disponibles côté serveur mais NON affichées — le mandat plafonne à « cinq tuiles au plus ». Les cinq
retenues racontent la couverture (sources/à jour/parcelles/communes/date d'analyse).

---

## Vérifications

- `tsc --noEmit` : 0 erreur.
- `vitest` front : **130/130**.
- `npm run build` : OK.
- backend `pytest` (suite complète) : **2190 passed, 34 skipped, 0 failed** (277 s).

⚠ Redémarrage serveur nécessaire (changements backend : `etats_sources`, `dashboard`, `ops`, `config`,
`bascule_flux`, `pige/api`, `app`).

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-9
```
