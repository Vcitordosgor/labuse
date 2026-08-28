# RAPPORT — RADAR : CHASSE AUX BUGS

Branche `fix/radar-chasse`. Passe ADVERSARIALE de bout en bout sur le Radar (P0→P6). Je n'ai rien
construit : j'ai cherché à casser, corrigé au fil de l'eau, et voici **toutes** les attaques tentées —
y compris celles qui n'ont rien donné (c'est ça qui prouve la couverture).

## Bilan
**~45 attaques tentées · 5 ont cassé · 5 corrigées · 1 observation laissée à Vic (optimisation, pas un bug).**
Suite worktree base `dc1a25c5` = 1915 / branche = 1921, **0 fail**. tsc/build verts. Anti-portail P0 vert.
[CHASSE-TEST] purgés (SQL : `pige_biens`=0, `pige_annonces`=0, `pige_clics`=0, veilles radar=0).

---

## FINDINGS (corrigés)

### RD-503 — 🔴 HAUTE — Le digest crashait en PRODUCTION et n'envoyait JAMAIS un mail
`digests._clients_actifs` sélectionnait `c.prenoms`, **colonne qui n'existe pas dans le schéma réel**
`comptes` (id/nom/plan/statut/sieges/…). Un test de P456 avait créé `prenoms` dans la base de TEST
(`ALTER … ADD COLUMN`), **masquant le bug** : vert en test, `radar-digests` aurait levé un 500
`column c.prenoms does not exist` au premier cron en prod → aucun digest, aucune alerte, jamais.
**Corrigé** : sert `c.nom` (colonne réelle, NOT NULL). Test de masquage retiré ; verrou anti-régression
(`c.prenoms` interdit dans la requête). *Le pire des bugs : silencieux, masqué par un test, mortel en prod.*

### RD-502 — 🟠 MOYENNE — Corrections manuelles hostiles écrites en base OU 500 brut
`intake.valider` écrivait les corrections **sans aucune validation** : prix négatif/zéro/absurde,
`type='chateau'`, `pieces=-3`, `surface=-50`, emoji dans `particulier_pro` → **écrits faux en base** ;
prix texte / chaînes trop longues → **500 psycopg brut** (pas de refus honnête).
**Corrigé** : `valider_corrections()` valide bornes + énumérations + types (prix 1–100 M, pièces 0–100,
DPE A–G, `particulier`/`pro`, type ∈ {maison,terrain,appartement,immeuble}) → `ValueError` propre ;
l'endpoint renvoie `{ok:false, motif}` (jamais un 500). Rien de faux n'entre.

### RD-504 — 🟠 MOYENNE (sécurité) — Lien vide / `javascript:` / `data:` accepté comme bouton client
`deposer` acceptait n'importe quel `lien` → `url_sortante`. Or `url_sortante` est rendu en `<a href>`
au CLIENT (« Voir l'annonce »). Un `javascript:alert(1)` (ou `data:`) collé par erreur = vecteur XSS ;
un lien vide/malformé = bouton mort.
**Corrigé** : `_lien_valide()` exige une URL `http(s)` propre (pas d'espace, ≤ 2000 c) → sinon
`rejet_lien`. Les paramètres de suivi (utm/fbclid) et un portail inconnu restent acceptés (légitimes).

### RD-501 — 🟠 MOYENNE — Répertoire captures inaccessible → crash brut + bien SANS capture committé
`_stocker_capture` levait un `OSError` nu si le répertoire privé était inaccessible (droits, disque
plein, montage read-only), APRÈS avoir déjà inséré bien/annonce/faits → le `session_scope` de l'endpoint
**committait un bien sans sa capture**.
**Corrigé** : la capture est stockée **AVANT** toute écriture en base ; en cas d'échec →
`echec_stockage` propre, **rien n'entre en base**.

### RD-506 — 🟡 FAIBLE — Date de publication dans le futur écrite telle quelle
Une `date_publication` = 2099 (misread) était écrite en base (donnée fausse, fraîcheur fausse).
**Corrigé** : `_clamp_date_publication()` remet à `null` une date future ou illisible (anti-invention :
une date impossible n'est pas une lecture).

---

## OBSERVATION (laissée à Vic — pas un bug, pas de rupture)

### RD-508 — 🟡 Cycle de vie : boucle par-ligne (UPDATE + événement) au lieu d'un set-based
`marquer_en_vente_longue` / `qualifier_retiree_sans_vente` font un `SELECT` puis une boucle
`UPDATE` + `journaliser` par bien. À **~5 000 biens un premier passage massif** ≈ 350 ms ; en régime
quotidien normal (une poignée de biens franchissent le seuil/jour) c'est instantané. **Décision Vic** :
laisser tel quel (lisible, événement par bien) ou passer en `UPDATE … RETURNING` + insert d'événements
en masse si un backfill volumineux est prévu. Aucun comportement cassé — je ne l'ai pas changé.

---

## LA LISTE COMPLÈTE DES ATTAQUES (dont celles sans effet)

### C1 — Parcours complet, en vrai
Chaîne dépôt→extraction→correction→validation→rattachement→client→clic→veille→digest→cycle→Marché
déroulée plusieurs fois, dans des ordres différents. **Un seul défaut de jointure** : le digest ↔ schéma
`comptes` (RD-503). Le reste des jointures : ce qui sort d'une étape entre bien à la suivante.

### C2 — Entrées hostiles (attaques → résultat)
| Attaque | Résultat |
|---|---|
| prix négatif / zéro / 99 M / 1 € | ❌ RD-502 → ✅ refusé proprement |
| prix texte / flottant · pièces texte · DPE trop long | ❌ 500 brut RD-502 → ✅ refusé |
| type `chateau` / type très long | ❌ écrit RD-502 → ✅ refusé |
| pièces négatives · surface négative · emoji `particulier_pro` | ❌ écrit RD-502 → ✅ refusé |
| lien vide / espaces / malformé | ❌ accepté RD-504 → ✅ `rejet_lien` |
| lien `javascript:` / `data:` | ❌ accepté (XSS) RD-504 → ✅ `rejet_lien` |
| lien avec params de suivi (utm/fbclid) | ✅ accepté (légitime) |
| lien portail inconnu | ✅ accepté, `portail='autre'` |
| lien très long (5 000 c) | ✅ refusé (> 2000, RD-504) |
| commune hors 24 (Le Guillaume, Marseille, Sainte-Clotilde, quartier) | ✅ `rejet_commune` motivé |
| commune vide / null | ✅ `rejet_commune` |
| commune « saint-paul » (casse/espace) | ✅ normalisée → acceptée |
| date de publication future (2099) | ❌ écrite RD-506 → ✅ nullée |
| annonce sans aucun champ lisible (tout null) | ✅ refusée (via commune null) |
| même URL déposée ×5 | ✅ 1 annonce (dédup) |
| image 1 px / énorme / corrompue / extension mensongère | ✅ `_bloc_image` (V1) valide format+taille ; illisible → non-JSON honnête |
| répertoire captures inaccessible | ❌ crash RD-501 → ✅ `echec_stockage`, rien en base |

### C3 — Invariants de la doctrine (tous ÉPROUVÉS, tous tenus)
| Invariant | Résultat |
|---|---|
| Aucun contenu d'annonce (base/API/mail/payload) | ✅ aucune colonne titre/texte/photo ; payload = faits + lien |
| Aucune capture servie par le web | ✅ seul `/socle` monté ; `captures_dir` hors racine servie ; aucune route |
| Fuite payload client (chemin_prive / a_verifier / hash / confiances) | ✅ AUCUNE |
| Carte = rattachés seulement (filtre/tri/statut tordus) | ✅ `coords=null` pour tout non-rattaché |
| `retiree_sans_vente` jamais d'un lien mort (retiré 2 mois, 0 DVF) | ✅ reste `retiree` |
| Écart de prix seulement sur Sourcé (Estimé + mutation DVF) | ✅ Estimé non rapproché, écart `null` |
| n < 5 = pas de médiane (commune à 4 biens) | ✅ valeur `null`, `insuffisant=true`, n=4 |
| Anti-invention (champ null en capture → null au client) | ✅ null bout-en-bout, étiquette `absent` |

### C4 — Cloisonnement et droits (tous tenus)
| Attaque | Résultat |
|---|---|
| Client voit les brouillons (non validés) via l'API | ✅ non (`valide_at IS NOT NULL` en lister ET detail) |
| IDOR veille : compte B voit/supprime la veille de A | ✅ non (scopé `compte_id`, FK réelle) |
| Attribution du clic au bon compte | ✅ oui |
| Signalement change le statut | ✅ non (anti-abus) |
| Route `/admin/radar/*` sans garde | ✅ AUCUNE (toutes `exiger_admin`) |

### C5 — Volume et durée (5 000 biens)
| Mesure | À chaud, 5 000 biens |
|---|---|
| `client.lister` (défaut / commune / tri baisses) | 10 / 4 / 11 ms |
| `marche.stats` (24 + île) | 16 ms |
| `cycle.marquer_en_vente_longue` (passage massif) | ~350 ms (obs RD-508) |
Le SQL de la liste est **5 ms** (EXPLAIN ANALYZE) ; le « 429 ms » d'un premier appel à froid était de
l'overhead session/connexion, pas la requête. Aucun index critique manquant.

### C6 — États de démarrage et vides (tous dignes)
| État | Résultat |
|---|---|
| Marché à 0 (taux, part, médianes) | ✅ `insuffisant`, aucune div/0, aucune exception |
| `client.lister` à 0 | ✅ 0, pas d'erreur, pas d'écran blanc |
| Digests à 0 nouveauté | ✅ 0 envoi (jamais un mail vide) |
| Marché à 1 bien | ✅ compteur=1 exact, médianes `insuffisant` |
| Marché à 4 biens (seuil n<5) | ✅ compteurs exacts, aucune médiane |

---

## RECETTE (FIN)
- Findings corrigés verrouillés par `tests/test_pige_chasse.py` (5) + test de masquage RD-503 retiré.
- **gardées vertes** (tous les tests pige 46/46) · **tsc/build verts** · **suite au niveau base**
  (worktree `dc1a25c5` : base 1915 / branche 1921, **0 fail**) · **[CHASSE-TEST] purgés (SQL)** ·
  **anti-portail P0 vert** (5/5).
