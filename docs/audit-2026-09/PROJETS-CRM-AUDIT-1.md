# PROJETS-CRM-AUDIT-1 — Rien de cassé, tout se suit

**Branche** `feat/projets-crm-audit-1` · **base** `5c12304e` (main) · **21/09/2026**
**Session dédiée** API `:8115` / front `:5315` · run servi `q_v11_m137` · Opus · lecture seule sur le code.
Audit **par l'usage** : chaque parcours joué au navigateur (captures `captures/projets-crm-audit1/`), chiffres recoupés à l'API/DB.

## En tête

**12 parcours joués** (Projets 7 · CRM 5) + **4 contrôles** Lot 3 · **1 en échec** · **2 réserves**.

- 🔴 **1 échec** — `crm_cartes_n` (registre) **≠ l'écran** : le compteur de colonne inclut les cartes **archivées**, l'écran non (C4).
- 🟡 **Réserve 1** — le bouton **« PDF »** du projet pointe vers `/projets/{id}/export.pdf`, endpoint **retiré (410)** : lien mort encore câblé (P7 / vestige).
- 🟡 **Réserve 2** — le message de confirmation d'un **« projet de zéro »** réutilise le texte du vivier (« Le vivier entier est dans le projet ») alors qu'il est vide (cosmétique, P1).
- ✅ Isolation multi-comptes **solide** ; dette IDOR « Grand Balayage » **corrigée** (FIX-CRM-CLOISON) et **re-vérifiée en direct** ; aucun vestige Copilote v1 lu par Projets/CRM.

---

## Lot 1 — Projets, par parcours

| # | Parcours | Verdict | Preuve |
|---|----------|:---:|--------|
| P1 | **Créer** depuis le vivier LABUSE (wizard 5 étapes : nom → périmètre → contexte → cadrage → récap) **et** depuis zéro | 🟢 OK 🟡 | Wizard : `[AUDIT-TEST] vivier wizard` (Le Port · terrain nu), récap **3 021 parcelles** → créé (proj. 244). De zéro : `[AUDIT-TEST] de zero` créé vide (`cadrage {__de_zero__:true}`, counts 0). `01-wizard-recap.png`, `10-projet-de-zero-cree.png`. 🟡 la confirmation « de zéro » affiche le texte du vivier (vide pourtant). |
| P2 | **Cadrage** : filtres du tiroir « À trier » = panneau Filtre de la carte, mêmes critères (**ZFANG/FRR**, dans le hash) | 🟢 OK | Même moteur (`FiltreCriteres`/`/filtre`). Facettes **byte-identiques** tiroir↔carte (`U 9 984 · AU 148 · A 35 · N 28`). Carte {Le Port, nu} = **4 920** ; vivier projet = **3 021** ; réconciliation **exacte** : 4 920 − 1 899 écartées (étage 0/non-constructible, exclusion figeable **libellée**) = 3 021. ZFANG/FRR présents à la carte et **dans le hash** (`…&es=nu&zfa=renforce&frr=totalite`), restaurés au reload. Moteur ZFANG/FRR sain (île : renforce 70 018 / totalité 20 033 ; Le Port = 0, correct). `03-atrier-filtrer-drawer.png`, `04-carte-filtres-leport.png`, `05-carte-hash-zfang-frr.png`. |
| P3 | **Bandeau d'analyse** : N = vivier entier (jamais un plafond) ; classement suit le run servi | 🟢 OK | « LABUSE a analysé **3 021 parcelles : 23 ressortent — 23 À suivre** » = récap = à-trier (aucun plafond ; la liste affiche les 3 021, seule la *shortlist figée* plafonne à 200). Classement = `runs.current() = runs.cascade() = q_v11_m137`. (Les « valeurs au JJ/MM » viennent d'un run marché distinct `m135-run2-ile` — attendu.) `02-projet-kanban.png`. |
| P4 | **Retenir / écarter / remettre à trier** : les 3 listes restent cohérentes (retenues + écartées + à trier = cadrage) | 🟢 OK | Retenir AS1160 + écarter AS1057 → `retenue 1 + ecartee 1 + proposee 3 019 = 3 021` ✓. Remettre à trier → `0 + 1 + 3 020 = 3 021` ✓ (et l'entrée CRM suit : archivée à la remise, restaurée au ré-retenu). `06-tri-1retenue-1ecartee.png`. |
| P5 | Depuis une fiche, le bouton **« Projet »** ouvre le menu de **tous** les projets, aucun mode collant | 🟢 OK | Fiche AS1160 → bouton « ✓ [AUDIT-TEST] vivier wizard » (titre « …rattacher à un autre ») → menu listant **les 10 projets**, le courant marqué « déjà ↗ », les autres sélectionnables. `08-fiche-projet-menu.png`. |
| P6 | Une parcelle **retenue** affiche dans le projet **les mêmes chiffres que sa fiche** (prix, zone, SDP, risques) — même id | 🟢 OK | AS1160 (`97407000AS1160`, même id partout) : surface **175 = 175**, SDP résiduelle **46 = 46**, zone projet **U** = fiche **Uc** (famille vs sous-zone), prix terrain médian **271 €/m²** = secteur DVF fiche 271, risques (ER 2, bruit route) tracés aux prescriptions de la fiche. `07-fiche-AS1160.png`. |
| P7 | **Figer, dater, renommer, supprimer** un projet | 🟢 OK 🟡 | **Figer/dater** : shortlist figée+datée (`figee_le 2026-09-21`, « valeurs au 21/09 »), `rejouer` re-fige. **Renommer** : titre → `[AUDIT-TEST] vivier wizard — renomme`, persisté. **Supprimer** : « Archiver » → `statut=archive` (soft, réversible ; Actifs 10→ Archivés 1). CSV export 200 OK. 🟡 **le PDF figé est retiré** : `/projets/{id}/export.pdf` → **410** (« le document Financier le remplace ») mais le bouton « PDF » (`ProjetKanban.tsx:297`) y renvoie encore = **lien mort**. `09-projet-renomme-header.png`, `15-projets-archive.png`. |

---

## Lot 2 — CRM, par parcours

| # | Parcours | Verdict | Preuve |
|---|----------|:---:|--------|
| C1 | Une parcelle retenue passe en **piste** : apparaît dans le pipeline, **colonne attendue** | 🟢 OK | Retenir AS1160 → entrée pipeline active en **« Contact à préparer »** (`contact_a_preparer`, défaut retenue→CRM), carte portant le lien d'origine « ▸ [AUDIT-TEST] vivier wizard » + propriétaire PM. `11-crm-board.png`. |
| C2 | **Déplacer entre colonnes, changer de statut** ; un seul vocabulaire (dont « répondu ») | 🟢 OK | Glisser AS1160 « Contact à préparer » → **« Contacté »** : `status` passe `contact_a_preparer → contacte`, persiste. Étiquette « retour terrain » (« Ouvert à discuter » → `ouvert_discussion`) = **axe distinct** de la colonne, persiste aussi. Vocabulaire réel listé ci-dessous. `12-crm-AS1160-moved-contacte.png`. |
| C3 | Boucle **fiche → courrier propriétaire → réponse → statut**, sans ressaisie | 🟢 OK | « ✉ Courrier » sur la carte → module Courrier **pré-rempli** avec la parcelle (« AS 1160 · Le Port », 1 destinataire), **aucune ressaisie d'IDU** (identité propriétaire masquée par design — adressage générique SPF/CERFA). Le statut du courrier remonte en chip sur la carte (état vivant « Déposé » observé) ; **clôture** `repondu`/`sans_reponse` câblée (`Kanban.tsx:35`). *Aucune demande réelle soumise* (pour ne pas notifier Vic / créer un artefact hors [AUDIT-TEST]). `14-courrier-prefill-from-piste.png`. |
| C4 | **Compteurs** : cartes/colonne = nombre réel ; `crm_cartes_n` (registre) = ce que l'écran affiche | 🔴 **KO partiel** | **Réel = OK** : le tableau compte les entrées **actives** côté client (`Kanban.tsx:457`), = DB active, = en-tête « N suivies ». **Registre = KO** : `crm_cartes_n` / `cartes_par_colonne` (`plateforme.py:107-109`) compte `pipeline_entries … GROUP BY status` **sans filtre `archived_at`** → inclut les cartes archivées. En direct : registre `contact_a_preparer` = **143** vs écran **142** (état vierge, à cause d'1 carte archivée pré-existante ; reproductible sans mes objets). L'écran est juste, **le registre sur-compte** des archivées. |
| C5 | Notes, dates, **rappels** sur une carte : sauvegardés, rechargés | 🟢 OK | Éditeur de carte AS1160 : note « [AUDIT-TEST] rappeler… » + date de relance `2026-09-28` + priorité → Enregistrer → persistés (DB) puis **rechargés à l'identique après reload**. `13-crm-card-notes-rappel.png`. |

---

## Le vocabulaire des statuts (réel)

Il n'y a **pas un vocabulaire plat unique** mais **des axes orthogonaux cohérents**, reliés aux bons endroits. « répondu » vit dans l'axe *Courrier* et remonte en chip sur la carte CRM.

| Axe | Où | Valeurs réelles |
|-----|-----|-----------------|
| **Projet — statut de parcelle** | tri d'un projet | `proposee` · `retenue` · `ecartee` · `a_analyser` |
| **CRM — colonnes (étapes du pipeline)** | tableau CRM | `reperee` (Repérée) · `proprietaire_a_identifier` · `contact_a_preparer` · `contacte` (Contacté) · `relance_prevue` · `en_discussion` · `chaud` (Opportunité chaude) · `abandonnee` (À abandonner) — défaut `reperee` |
| **CRM — priorité** | carte | `haute` · `moyenne` · `basse` |
| **CRM — retour terrain (étiquette de contact)** | carte | `contacte` · `pas_de_reponse` · `refus_ferme` · `pas_maintenant` · `ouvert_discussion` · `en_negociation` · `vendu_a_nous` · `vendu_a_autre` |
| **CRM — statut propriétaire** | carte | `inconnu` · `a_identifier` · `identifie_manuellement` · `public_probable` · `institutionnel_probable` · `indivision_probable` · `copropriete_probable` |
| **Courrier — statut** | chip carte / Mes courriers / dashboard | `demande` · `depose` (Déposé) · `envoye` · **`repondu`** · `sans_reponse` (les deux derniers = clos) |

**Liens inter-surfaces vérifiés** : Projet `retenue` → CRM `contact_a_preparer` (sync) ; départ de `retenue` → entrée CRM archivée ; Courrier `repondu`/`sans_reponse` → carte « close ». *Observation* : le libellé **« Contacté »** existe à la fois en **colonne** (`contacte`) et en **étiquette retour terrain** (`contacte`) — deux axes distincts, potentiellement déroutant.

---

## Lot 3 — Isolation & vestiges

| Contrôle | Verdict | Preuve |
|----------|:---:|--------|
| **Isolation deux comptes** (aucun projet/carte/note visible de l'autre) | 🟢 OK | Compte réel `31` en base (37 pistes, 8 colonnes) vs session pilote `NULL`. Depuis NULL : la liste `/pipeline` **ne fuit pas** les entrées de 31 (110/95/97 absentes) ; `PATCH`/`DELETE` entrée 110 → **404** ; `PATCH` colonne 33 → **404**. (Aucun projet non-NULL en base → isolation projets confirmée par le code : les 20 routes passent par `_projet_or_404`/`_scope`.) |
| **Dette IDOR « Grand Balayage »** — la vérifier | 🟢 **Corrigée & vérifiée** | La dette = fuite de prospection (PII) par la fiche *legacy* `_build_fiche` (`/explain`, `/export`) qui lisait le pipeline **sans compte**. **Corrigée** (FIX-CRM-CLOISON C1, `app.py:6046-6062` : bloc prospection neutre ; C2 = re-scope de l'UPDATE colonnes). **Re-vérifié en direct** : depuis NULL, `GET /parcels/97413000AC0049/export` (parcelle suivie par le compte 31, note « [GB-TEST] ») rend une prospection **neutre** — aucune note ni PII de 31 ne fuit. |
| **Aucun vestige lu** (Copilote v1, anciens endpoints, statut retiré) | 🟢 OK 🟡 | Copilote v1 : chemin de création **retiré** (`ProjetsPanel.tsx` M118), **aucun** appel v1 ni table `agent_*` depuis Projets/CRM. Aucun statut retiré en usage (vocab = config). 🟡 **seul vestige actif** : le bouton « PDF » projet → `/projets/{id}/export.pdf` **410** (cf. P7). |
| **Purge des objets [AUDIT-TEST] → état identique** | 🟢 OK | Après purge (voir liste) : projets **9 actifs / 0 archivé / 0 AUDIT-TEST**, pipeline NULL **189 actives + 1 archivée** (pré-existante), colonnes **8**, compte 31 **intact** (37/8), « Mes courriers » **16** inchangé. `16-etat-restaure-9-actifs.png`. |

---

## Objets de test créés — **purgés** (préfixe [AUDIT-TEST])

Tous créés en session `compte_id NULL` (pilote), tous supprimés en fin d'audit ; état re-vérifié identique au départ.

| Objet | Détail | Sort |
|-------|--------|------|
| Projet **244** | `[AUDIT-TEST] vivier wizard — renomme` (Le Port · terrain nu · 400 k€) | supprimé (+ 200 `projet_parcelles`) |
| Projet **245** | `[AUDIT-TEST] de zero` (archivé pendant le test) | supprimé |
| Pipeline **302** | piste CRM AS1160 (`contacte`, note « [AUDIT-TEST] rappeler… », relance 2026-09-28), issue du sync retenue→CRM du projet 244 | supprimé |

Rien d'autre créé : **aucune demande de courrier** soumise (`courrier_demandes` inchangé), **aucune colonne CRM** ajoutée, **aucun** objet du compte 31 touché. *(La note « [GB-TEST] note updated » sur une piste du compte 31 est un artefact d'un audit antérieur — hors périmètre, non touchée.)*

---

## Ce qu'on n'a pas fait

Aucune correction. Aucun regard sur le scoring lui-même. Aucun merge, aucune bascule. Un seul commit : ce rapport.

---

## Recommandations (hors périmètre correctif)

1. 🔴 **`crm_cartes_n`** — ajouter `AND archived_at IS NULL` dans `cartes_par_colonne` (`plateforme.py:107-109`) pour que le registre = l'écran (les deux comptent l'actif). *(À noter : l'écran est déjà juste — le tableau recompte côté client ; c'est le registre/API `cards` qui dévie.)*
2. 🟡 **Bouton « PDF » projet** — retirer le lien (`ProjetKanban.tsx:297`) ou le renvoyer vers le document « Financier » qui remplace le PDF retiré (410).
3. 🟡 **Confirmation « projet de zéro »** — texte dédié (le message « Le vivier entier est dans le projet » ne s'applique qu'au vivier).
