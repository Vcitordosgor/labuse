# GRAND BALAYAGE — MANDAT & état de progression

> Fichier de resynchronisation (créé en mode autonome). **RAPPORT.md fait foi pour les findings** ; ce fichier fixe le cadre + le point de reprise. Après une compaction : relire CE fichier + RAPPORT.md avant de continuer.

## Mandat (résumé)
Audit total de l'app LABUSE **par l'usage** (navigateur réel Playwright + statique/SQL lecture). Trouver bugs, faux chiffres, code mort, orphelins, échecs silencieux, promesses non tenues, en usant l'app comme un client de bout en bout. **AUDIT SEUL — aucun fix, aucun code applicatif modifié.** 50 missions en 6 lots.

## Environnement
- Front : **http://localhost:5174/socle/** (PAS 5173). Back : http://localhost:8000. Postgres : `psql -d labuse` (user OS `openclaw`, auth peer ; DSN app `labuse:labuse` mais role `labuse` inexistant → utiliser `psql -d labuse`).
- Branche `audit/grand-balayage`. `.playwright-mcp/` exclu via `.git/info/exclude` (jamais dans un commit).

## Règles
- **Écritures sur le compte principal (session VL)** — décision Vic (pas de compte test). Tout objet créé porte le préfixe **[GB-TEST]** dans son nom/libellé + entrée dans l'**inventaire de purge** (RAPPORT.md). **Je ne supprime rien** (Vic purge sur ma liste).
- **Aucune modification d'objets EXISTANTS de Vic** (pas de décision sur ses vrais projets, pas d'édition de ses prospects ; colonne CRM → créer une [GB-TEST] et renommer celle-là).
- **M45 (IDOR)** : partielle, en contrôle de scoping code + rejeu d'ids non possédés. Noter « à rejouer à deux comptes avant le 2e client ». La cloison `compte_id` est **vérifiée présente en base** (pipeline_entries.compte_id + FK + contrainte) → l'IDOR devrait tenir.
- **Anti-doublon** : toute défaillance qui découle de la cascade GB-011 (courrier, veilles, migration future) = **GB-011-a/-b/-c…** rattachée, PAS un nouveau numéro. Seuls les problèmes indépendants ont leur propre GB-xxx.
- append + commit par lot (« GB lot N ») ; captures seulement sur anomalie (`captures/GB-xxx.png`).
- **Mode AUTONOME jusqu'à la fin** : ne pas s'arrêter aux frontières de lots, pas de questions de checkpoint. S'arrêter UNIQUEMENT pour : action destructive/irréversible hors [GB-TEST], serveur mort non relancé, ambiguïté changeant le sens d'une mission.

## Notes méthodo (durement acquises)
- `window.__labuse` expose les **actions** de l'app (`select(idu)`, `setMsel([])`, `setModule`…) → sélectionner une parcelle / peupler msel de façon fiable depuis `browser_evaluate`.
- **Deep-link outil** `#m=<clé>` : `page.goto()` sur simple changement de hash **ne re-rend PAS** l'outil (quirk driver). Faire un **reload réel** : `browser_evaluate(() => location.reload())` puis attendre ~2,5 s. Ou cliquer la carte d'outil.
- Clés outils (registry) : scoreur-adresse (Étudier), programme (Faisabilité), risques (Pièges), plu, comparer, assemblage, patrimoine (Scan), courriers, prospection-solaire, communes, permis, renouvellement (Densifier), temps.
- **Éviter `querySelectorAll('*')`** dans un evaluate → capture le `<style>` Tailwind (~99 Ko) et fait exploser la sortie.
- Fiches : le panneau est le `complementary`/`aside` de DROITE ; `document.body.innerText.slice(0,400)` ne l'attrape pas (il prend la nav gauche).
- Inputs React contrôlés : setter natif + dispatch `input`/`change` (`Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set`).
- Communes : filtre carte = **codes postaux** (97460=Saint-Paul…), hash utilise le **nom** (`cs=Saint-Paul`). INSEE via `/communes` (Saint-Paul=97415).

## État de progression (mis à jour à chaque lot)
- **LOT 1** ✅ complet — GB-001..004
- **LOT 2** ✅ complet (missions 1-15) — GB-005..009
- **LOT 3** ✅ complet (16,17,18,20,21,22,23,24,25,27,28 + 19/26 couverts) — **GB-011 🔴 + GB-011-a**
- **LOT 4** ⬜ (missions 29-38) ← REPRENDRE ICI
- **LOT 5** ⬜ (39-46, M45 scoping)
- **LOT 6** ⬜ (47-50 code mort)
- **Livrable final** ⬜ (TOP 10 + consolidation + purge + commande merge)

**Finding phare : GB-011 🔴** — `courrier.ensure_tables` splitte le DDL sur `;` en coupant un commentaire à `;` interne → CREATE/ALTER courrier_demandes jamais appliqué → Courrier 500 ; **cascade** : abandonne le heal restant au boot (crm_columns/veilles/comptes/scoping IDOR/copilote) ; `/readyz` ment (schema.ok:true). Redémarrage NE corrige PAS.
