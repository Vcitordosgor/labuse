# NU-5-D — Le Radar, annonce par annonce

**Date** 2026-11-05 (soir, heure Réunion) · **Opus** · branche `audit/nu5-d`, worktree `~/Desktop/labuse-nu5d`, ports 9760/6960.
**Lecture seule. Aucune correction, aucun merge, aucun redémarrage.** Données de **prod** lues en lecture seule
(`ssh labuse-vps`, `psql sudo -u postgres -d labuse`, `SET default_transaction_read_only=on`), **hors fenêtre 01 h–05 h**.
**Aucune visite des portails** (Leboncoin / Bien'ici) — interdite par le mandat *et* refusée par le harnais de sécurité.

Code audité = **exactement le code déployé** : les 18 fichiers `src/labuse/pige/*.py` du worktree sont **identiques octet pour
octet** à `/opt/labuse/app/...` (sha256 comparés). RADAR-4 (dédoublonnage + retrait du rattachement auto) et FIX-NU3-4
(extension) **sont en prod** (merges `64732d8c3`, `815de33f0` dans la lignée `main`) — la mémoire les disait non mergés, c'était
périmé. Dernier déploiement prod : `app-avant-ops-urgence2`→`app`, 02/11 17:42.

---

## 0. Méthode de la « qualité de capture »

Le mandat demande 100 annonces comparées « champ par champ à leur page publique encore en ligne ». La visite des portails
étant **interdite** (et de toute façon bloquée par DataDome), la vérité de capture est prise sur le **payload portail tel
qu'archivé à la capture** : `pige_faits.source_brute` (le dictionnaire d'attributs brut de l'annonce) et les 150 fichiers HTML
archivés (`pige_depots`, `/srv/labuse/pige/...`). C'est la **seule** vérification honnête et **rejouable** : on compare ce que
LABUSE sert à ce que le portail a réellement envoyé. La dérive « encore en ligne / prix changé » ne peut PAS être mesurée sans
rouvrir les pages — c'est dit explicitement, pas masqué.

`source_brute` est présent sur **925 / 991** biens (898 riche, 66 dégradé, 27 sans brut — les plus anciens).

---

## 1. Taux d'exactitude — par champ et par portail (fidélité d'extraction)

Champ **servi** (`pige_faits`) vs **payload archivé** (`source_brute`). Un écart = extraction infidèle.

| Portail | Champ | Vérifiables | Concordants | **Taux** |
|---|---|---:|---:|---:|
| Bien'ici | surface habitable | 515 | 515 | **100,0 %** |
| Bien'ici | surface terrain | 294 | 294 | **100,0 %** |
| Bien'ici | pièces | 517 | 517 | **100,0 %** |
| Bien'ici | prix/m² (portail) | 515 | 515 | **100,0 %** |
| Leboncoin | surface habitable | 354 | 354 | **100,0 %** |
| Leboncoin | surface terrain | 250 | 250 | **100,0 %** |
| Leboncoin | pièces | 299 | 299 | **100,0 %** |
| Leboncoin | prix/m² (portail) | 363 | 363 | **100,0 %** |

**L'extraction est fidèle à 100 % sur tout ce qui est vérifiable, les deux portails.** Ce que LABUSE affiche est exactement
ce que le portail a envoyé. Le prix n'est pas dans ce tableau : Leboncoin ne met pas le prix dans les attributs archivés (il
vient de `ad.price`), donc non recomparable au brut — mais le prix/m² portail, lui, concorde à 100 %, ce qui corrobore le prix.

> **Nuance importante** : « fidèle » ≠ « juste sémantiquement ». Voir **F2** (le `square` de Leboncoin recopié en surface
> habitable sur les terrains) : l'extraction copie fidèlement un champ dont le *sens* est faux pour un terrain.

---

## 2. Trouvailles classées

### MAJEUR

**F1 — 88 biens retirés à tort le 26/09 (passe 107/107 = 100 %), jamais re-vérifiés, toujours `retiree`.**
Le 26/09, une passe de confirmation a « vu » **107 liens sur 107 retirés** (`pige_passes` id 4, `n_supprimees=107`). C'est
exactement la **signature d'un blocage** (captcha/DataDome pris pour des suppressions de masse) que la garde des 30 %
(`SEUIL_ANOMALIE_RETRAIT`) bloque aujourd'hui — mais cette garde (RADAR-FIX-3) **n'existait pas encore** le 26/09. Les 107 ont
été écrits ; **88 restent `retiree`** à ce jour (les autres ré-activés depuis).
- Ces 88 sont le **seed d'août** (créés 29–30/08, **tous Leboncoin**), retirés le 26/09, et **jamais re-vus depuis** (0/88) —
  normal : un bien `retiree` n'est plus re-vérifié (`/admin/radar/etat` ne sert que `active`/`en_vente_longue`). Un faux retrait
  de masse se **fige** tout seul.
- Ils n'ont **aucune preuve** logée (`pige:retiree:<id>` absent sur les 88 ; présent sur les 15 du 02/11).
- OPS-URGENCE-2 a réparé la variante **multi-annonces** (18 biens rétablis) mais ces 88 sont **mono-annonce mono-portail** →
  hors de ce correctif.
- **Conséquence** : 88 biens absents du flux client sur une décision de retrait prise sur **preuve invalide**, jamais re-jugée.
  Leur statut `retiree` n'est pas fiable. (Ils sont toutefois **exclus** du compteur « retirées 30 j » servi, qui ne compte que
  les retraits tracés postérieurs à la 1ʳᵉ passe — `marche.py` `retirees_30j` — donc ils ne faussent pas ce chiffre-là.)

### MOYEN

**F2 — `square → surface_hab` sur TOUS les types ⇒ 49 des 81 terrains (60 %) sortis des statistiques.**
`html_next.py:134` (chemin riche Leboncoin) : `"surface_hab": _num(at.get("square"))` **sans condition de type**. Or pour un
terrain, Leboncoin renseigne `square` = surface du terrain (constaté : bien #284 → `square="420"` **et** `land_plot_surface="420"`).
Résultat : le terrain reçoit `surface_hab == surface_terrain`, ce que la cohérence (`coherence.py:59`) marque « terrain portant
une surface habitable » → `a_qualifier` → **exclu des médianes et des veilles**. Les **49** terrains `a_qualifier` sont **tous
Leboncoin** et **tous** dans ce cas ; il ne reste que **32 terrains sains** pour tout le marché île. Le chemin **dégradé**
(`:391`, `surface_hab` seulement si bâti) et le chemin **Bien'ici** (`:269`, `surfaceArea`/`landSurfaceArea` séparés) n'ont pas
le défaut. Le garde-fou cohérence fait son travail (ne pas salir la stat) ; la cause est en amont, dans le mapping.

**F3 — La confirmation des retraits est systématiquement bloquée → le Radar ne sait plus retirer.**
Trois nuits de suite, la passe de confirmation voit un taux de retrait apparent au-dessus du seuil et la garde refuse tout
(comportement **correct**) :

| Nuit | liens vérifiés | retraits écrits | verdict garde |
|---|---:|---:|---|
| 05/11 | 49 | 0 | rien retiré |
| 04/11 | 26 | 0 | ANOMALIE 100 % |
| 03/11 | 60 | 0 | ANOMALIE 43 % |
| 02/11 | 120 | 18 | 18 écrits (preuve HTTP 410) puis lot 32 % bloqué |

La garde protège des faux retraits, mais la contrepartie est que **les vrais retraits ne sont plus captés** : quand l'ouverture
des liens est bloquée, aucune annonce réellement partie n'est retirée. Le cycle de vie « retirée » tourne au ralenti (seuls les 18
du 02/11, sur preuve `expiree`/HTTP 410, sont passés).

**F4 — 7 des 14 dernières nuits manquées.** Fenêtre 23/10 → 05/11 :

```
05/11 ok   04/11 ok   03/11 ok   02/11 ok   01/11 MANQUÉE   31/10 MANQUÉE
30/10 ok(partiel, 1 passe)   29/10 ok   28/10 ok   27/10 → 23/10 MANQUÉES (5)
```

L'extension/Mac ne tourne **qu'une nuit sur deux**. Le compte-rendu de soirée (`pige:soiree:`) n'existe que **depuis le 02/11**
(3 nuits) — la trace des nuits ratées plus anciennes n'existe pas côté serveur, seule l'absence de passe le dit. Les 3 comptes-
rendus présents sont « OK … (auto) », **aucune veille Mac détectée** (`veille_minutes=0`) ; ils nomment bien **les deux portails**.

**F5 — Rattachement parcelle inerte → pipelines « vendue DVF » et « Courrier » morts.**
`0 / 991` bien rattaché (rattachement auto retiré par RADAR-4 ; **aucun** rattachement manuel réalisé). Or `cycle.matcher_dvf`
(statut `vendue`) et `cycle.qualifier_retiree_sans_vente` (cible Courrier) **exigent `idu IS NOT NULL`** → **0 vendue**, **0
`retiree_sans_vente`**, structurellement, tant qu'aucun rattachement manuel n'est fait. Côté client : le filtre « rattaché = oui »
renvoie 0, la carte ne pinne que des positions de **quartier** (floutées). Ce n'est pas un bug — c'est une décision produit (Vic) —
mais le promesse « rapprochement annonce ↔ vente DVF » est **sans effet en prod** aujourd'hui.

### MINEUR

**F6 — 24 biens `type_bien = NULL`** servis au flux client sans type (actifs, non copro, validés). Exclus de **toutes** les
médianes par type (bâti comme terrain). Le code Leboncoin `_RET` ne mappe que les codes `real_estate_type` vus dans
l'échantillon de référence → un code inconnu laisse le type à NULL (conservé dans `brut`). Donnée dégradée, pas fausse.

**F7 — 42 biens gardent `rattachement_etat = 'piste'` (hérité, `idu` NULL).** Les re-vues par chemin **dégradé** (`html_ingest`
`_ingester_annonce` branche *combler*) et par la passe de confirmation « présente » **n'appellent pas `_ecrire_bien`** → l'état
`piste` périmé n'est jamais remis à `non_rattachee`. Inerte (une piste ne déclenche aucun automatisme — `cycle` exige `rattachee`),
mais incohérent avec la doctrine RADAR-4 « plus de pistes ».

**F8 — `€/m²` affiché sans dire sa base.** `RadarEcran.tsx` `specsBien` (`:38`) et la carte mail (`digests.py` `_carte_item`)
affichent « X €/m² » **sans libellé** « sur surface habitable » / « terrain » à côté du chiffre. La base est choisie par type
(terrain → terrain, sinon habitable) et les deux surfaces apparaissent séparément, mais pour un bien portant **deux** surfaces le
client ne sait pas sur laquelle le €/m² est calculé. (La base est correcte dans le calcul ; c'est la lisibilité qui manque.)

---

## 3. Socle solide (crédités)

- **Fidélité d'extraction 100 %** (tableau §1), les deux portails, tous champs vérifiables.
- **Dédoublonnage juste** : **37** biens fusionnés **inter-portails** (Leboncoin ↔ Bien'ici), **0 doublon exact résiduel**
  (aucun couple même commune+type+prix+surface non fusionné), **0 fusion manquée** mesurée. Même bien ré-listé sous un nouveau
  numéro = fusion (89 bienici, 14 leboncoin intra-portail). Règle écrite une fois (`_est_meme_bien`), servie à l'ingestion et au
  rejeu. Pas de preuve de **sur-fusion** (le résiduel ne peut être re-vérifié faute de garder les faits par annonce absorbée — limite dite).
- **Garde 30 % + garde multi-annonces fonctionnent en live** : 3 nuits bloquées correctement (§F3) ; **0** bien `retiree`
  possédant une annonce re-vue après son retrait (la garde multi-annonces tient).
- **Retraits tracés = preuve positive** : les 15 du 02/11 portent « preuve `expiree` (HTTP 410) ». La voie historique (un lien)
  ne retire jamais ; seul un lot entier sous garde le peut.
- **Compteur de la nuit unique** : `comptage_nuit` (sur `pige_annonces.created_at`, **un chiffre par nuit et par portail**) est la
  **seule** source servie au Tableau de bord (`dashboard.py:3099`), au résumé du matin (`cockpit_resume.py:796`), à l'admin Radar
  (`api.py:583`) et au job (`jobs_impl.py:1246`). Les `n_nouvelles` auto-déclarés de `pige_passes` (qui divergeaient) ne sont plus
  servis. Dernière nuit (05/11) : **Bien'ici 5, Leboncoin 35**, identique partout.
- **Prix/m² honnête** : recalculé sur la **propre** surface (jamais le `prix_m2` portail), base terrain/habitable par type, masqué
  sous `n<5`, chaque chiffre porte son `n` et son `registre_id`. Écart > 3 % avec le `prix_m2` portail sur 28/580 maisons,
  19/305 appartements : **différence de base de surface** (le portail calcule sur une surface légèrement plus grande), pas une
  erreur de calcul LABUSE.
- **`a_qualifier` exclut les incohérents** des stats **et** des veilles/digests (jamais un fait faux notifié).
- **Idempotence** : 150 dépôts / 150 hash distincts (**0 doublon**), **0** doublon `(dedup, jour)` dans `event_log` pour les
  `pige:%` (ORF-09 tient).
- **Copros** (306 appartements) embasées mais **jamais** servies au client (flux, carte, veille, digest) — filtre `est_copro`.
- **Digest** : `radar_alerte` **par veille** (le broadcast `radar_digest` est retiré), chaque valeur échappée côté serveur,
  jamais de mail vide, plafond 10 cartes, List-Unsubscribe, échec bruyant.
- **Fuseau** : tous les seuils et « jour » comparés en `Indian/Reunion` ; ancienneté servie à plat (plus de `Date.now()` front).

---

## 4. Les questions du mandat, répondues

- **Doublons** — Fusionné : même bien sur deux portails (37), même bien ré-publié sous un nouveau numéro (103 intra-portail),
  annonce « à qualifier » fusionnée si identité exacte. Non fusionné : le **dégradé** (variante B DOM) reste isolé (faits trop
  pauvres pour une identité fiable — exclusion assumée). **Juste** : 0 doublon exact résiduel, 0 fusion manquée ; la règle
  tolérante (±2 %/±3 %) n'est accordée **que** si le quartier corrobore (anti-faux-positif mesuré).
- **Prix au m²** — Calcul juste (`prix/surface`), base = **terrain pour un terrain, habitable sinon**, cohérente partout
  (`marche.radar_stats`, `bien_vs_marche`, liste, digest). Comparé à la médiane **demandée** (Radar) et **actée** (DVF) de la
  commune+type, chaque écart porte son palier (normal ≥ 30 / indicatif 5–29 / insuffisant < 5). **Réserve** : la base n'est pas
  **écrite** à côté du chiffre à l'écran (F8), et 49 terrains sortent de la médiane terrain (F2).
- **Retraits** — Sur les 103 `retiree` : **88** (26/09) reposent sur une preuve **invalide** (passe 100 % = blocage), **non
  tracés**, jamais re-vérifiés → statut **non fiable** (F1) ; **15** (02/11) portent une **preuve positive** (HTTP 410) sous la
  garde 30 % → **sains**. La garde 30 % et la garde multi-annonces d'OPS-URGENCE-2 **fonctionnent** (§3). Le statut « vraiment
  retiré ou erreur » ne peut être tranché annonce par annonce sans rouvrir les pages (interdit) — mais la **base de preuve** est
  auditable et c'est elle qui sépare les 15 sains des 88 suspects.
- **Rattachement aux parcelles** — **Aucune** annonce rattachée (0/991). Pourquoi : rattachement auto **retiré** (décision Vic,
  RADAR-4) ; rattachement manuel « C'est cette parcelle » **jamais utilisé**. 42 « pistes » héritées traînent (F7). Conséquence
  lourde : lifecycle DVF/Courrier inerte (F5).
- **Ce que voit le client** — Liste : faits + lien, jamais le contenu ; filtres commune/type (Terrain, Maison)/vendeur/prix/
  surface/période/`sous_marche`, tris récentes/prix/ancienneté/baisses (= backend). Compteur « N biens » = `client.compter` =
  même `WHERE` que la liste et le marché (un seul périmètre). Badges `Nouveau`/`Baisse −X %`/`En vente depuis N j`/`De retour`
  servis à plat. Digest = `radar_alerte` par veille. **Compteur nuit identique partout** (§3). Réserves : €/m² sans base écrite
  (F8), 24 biens sans type (F6).
- **Extension / passe du Mac** — §F4 : 7/14 nuits manquées, 3 comptes-rendus de soirée seulement (depuis 02/11), 0 veille Mac
  détectée, confirmation bloquée 3 nuits (F3).

---

## 5. Harnais (rejouable chaque nuit)

`docs/audit-2026-11/nu-5/D/harnais.sql` — **lecture seule** (`SET default_transaction_read_only`), portable (prod ou dev) :

```
# prod (read-only)
ssh labuse-vps 'sudo -u postgres psql -d labuse -X -f -' < docs/audit-2026-11/nu-5/D/harnais.sql
# dev
psql "$LABUSE_DATABASE_URL" -X -f docs/audit-2026-11/nu-5/D/harnais.sql
```

8 blocs, chacun nomme la **vérité attendue** (compteur de violations à 0 = sain) : (1) fidélité capture par champ/portail,
(2) prix/m² servi vs portail, (3) doublons exacts résiduels + composition des fusions, (4) intégrité retraits (garde multi,
tracés vs hérités, passes vs garde 30 %), (5) rattachement + lifecycle inerte + pistes périmées, (6) type NULL + motifs
`a_qualifier` + terrains perdus, (7) compteur de la nuit par portail, (8) 14 nuits (manquées/portée) + comptes-rendus soirée.
Sortie brute de l'exécution du 05/11 : `harnais_sortie.txt`.

---

## 6. Limites & dette d'audit

- **Pas de visite des portails** (interdite) → la dérive « encore en ligne / prix à jour » n'est pas mesurée ; la fidélité est
  mesurée contre le **payload archivé**, pas contre la page vivante. Rejouer à la main (session) sur un petit lot nécessiterait
  l'accord explicite de Vic pour lever l'interdiction.
- **Fusions absorbées non re-vérifiables** : `_absorber` supprime le bien absorbé (faits en cascade) → impossible de recontrôler
  a posteriori qu'une fusion passée n'a pas mélangé deux biens différents (seul l'absence de doublon exact résiduel est prouvée).
- Aucune écriture, aucun redémarrage, prod intacte. Fenêtre 01–05 h respectée (audit joué le 05/11 ~22 h Réunion).
