# M14 — LOT A : AUDIT (lecture seule)

**Branche** : `audit/m14-a` · **Base** : `main` (M12+M13 mergées, `35febbb`). Zéro code. Bloque LOT E.

## A1 — Fraîcheur des sources : que fait réellement le système ?

### Réponse courte
**Oui, un mécanisme de revérification périodique existe : le RADAR** (`src/labuse/radar.py`, commande `labuse radar-sources`). **Mais il tourne toutes les semaines, PAS toutes les 48 h**, et il ne couvre que les sources **sondables** (9 sur 52). C'est un **thermomètre** (sonde HEAD/métadonnées « as-tu changé ? », zéro téléchargement) — il SIGNALE une publication amont, il ne ré-ingère jamais.

### Faits vérifiés (en base + code)
- **Cron** : `deploy/cron.d/radar` → `40 2 * * 1` = **lundi 02:40, hebdomadaire**. (Pas 48 h.)
- **Table** `source_radar` : **52 sources**, toutes sondées le **2026-07-22 21:40** (dernier passage réel). Colonnes : `statut, derniere_verif, dernier_changement, sonde, url, valeur…`.
- **Répartition** : **9 sondables** (`statut='a_jour'`) / **43 non sondables** (`statut='non_sondable'`).
- **Table `source_checks`** (contrôle MANUEL) : **0 ligne** — jamais alimentée (confirme le « — » de M13-F1). Vic a acté sa suppression.

### Tableau — sondable vs non sondable

| Régime | Sources | Mécanisme de recheck | Sondable auto | Cadence producteur |
|---|---|---|---|---|
| **Sondable** (9) | BODACC, Base Adresse Nationale, Cadastre Etalab, DEAL trait de côte, DPE ADEME, DVF, Inventaire SRU (DHUP), QPV 2024 (ANCT), SITADEL | **radar** (sonde HEAD/JSON `derniere_verif` réelle) | **OUI** | quotidien→semestriel selon la source |
| **Non sondable** (43) | INSEE (BPE, Filosofi, RP), SAFER (DAAF), Géorisques, Urbanisme PLU/GPU, RGE ALTI, Parc National, Forêts ONF, SAR/PEIGEO, Cadastre API Carto, Cerema, … | **radar en repli** → `non_sondable` (pas d'URL datée interrogeable) | **NON** | millésime / grande passe |

### Conséquence pour le LOT E (contraignant)
- **Sources sondables** → on PEUT afficher « Vérifié il y a X » depuis `source_radar.derniere_verif` (date RÉELLE, jamais codée en dur).
- **Sources non sondables** → **techniquement impossible** de checker automatiquement (pas d'URL datée). Afficher **version + cadence producteur seulement**, **aucune date de contrôle**.
- **Le « 48 h » demandé par Vic** : le mécanisme (radar) existe mais tourne **hebdo**. Passer à 48 h = **changer la fréquence du cron** (`40 2 * * 1` → p.ex. `40 2 */2 * *`) — modification d'infra triviale, hors code applicatif. La sonde, elle, est déjà réelle et ne couvrira JAMAIS les 43 non sondables. **Ne pas simuler un contrôle 48 h là où la source n'est pas sondable.**

## A2 — Outil « Zone active » (QA-66)

Barre d'outils verticale droite de la carte (`components/map/MapToolbar.tsx`, `TOOLS`). **4 outils** :

| Icône | `key` | Fonction | Marche ? |
|---|---|---|---|
| Règle/crayon | `distance` | Mesure une distance (clics = points, double-clic termine) | oui |
| Carré | `surface` | Mesure une surface (clics = sommets, double-clic ferme) | oui |
| Montagne | `alti` | Altitude au point cliqué (RGE ALTI) | oui |
| Cadre/sélection | `zone` | **Dessine un polygone → filtre les résultats à la zone** (pointillés verts « Zone active ») | oui, **en mode commune** |

**L'outil « Zone active »** : au tracé (≥3 points + double-clic), il pose un polygone et **filtre réellement la liste + la carte** aux parcelles dans la zone (`setZone` → `matchScope`/`pointInPolygon`, `filters.ts`). Le résultat EST exploité (compteurs, liste, chips). **Il est désactivé en mode « Toute l'île »** (le filtre se calcule client-side sur les features de la commune chargée) — constat déjà documenté en M12-A7/G2. Chip « Zone active × » pour l'effacer.

**Décision d'usage à Vic** — rien modifié. Options : (a) laisser tel quel (filtre géo en mode commune) ; (b) l'étendre à l'île entière (filtre spatial serveur — lourd, cf. M12-A7) ; (c) mieux le faire découvrir (l'état désactivé en mode île déroute).

**FIN A.** Ce tableau décide de ce que le LOT E affichera : date de contrôle **uniquement** pour les 9 sondables (via radar), version seule pour les 43 autres.
