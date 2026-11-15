# COUVERTURE — AUDIT-CHIRURGICAL-1

> « Aucun écart » n'est un résultat valable QUE pour ce qui figure dans les tableaux ci-dessous.
> Échantillon : 38 parcelles (`echantillon.csv`). Preuves : `~/Desktop/chasse-1/<idu>/`.

---

## 1. Conformités prouvées (recalcul indépendant = valeur servie)

| Fait | Méthode de contrôle | Couverture | Résultat |
|------|---------------------|-----------|----------|
| **Surface** | `ST_Area(geom_2975)` vs `surface_m2` fiche | 38/38 | **Concorde** (écart 0,0 m² ; cf. `oracle_results.txt` §1). Le `contenance_m2` cadastre diffère légèrement (déclaré ≠ dessin), comportement normal. |
| **Parts d'aléa par niveau** | union `georisque_alea` niveau=fort ÷ surface vs `aleas.liste[].part_pct` | 11 parcelles à aléa fort | **Concorde** à ±1 pt (ex. AM0838 43,4 %≈43 % ; AV0078 55,5 %≈56 % ; AO0050 82,3 %≈82 %). |
| **Emprise bâtie servie** | `ST_Union(ST_Intersection(batiment))` vs `le_bien.emprise_batie_m2` | 38/38 | **Concorde** (ex. AD0887 344,7≈345 ; BW2635 654,8≈655). |
| **Part de zone / EBC** | union `plu_gpu_zone` par `typezone` | parcelles à cheval (IS0448, BN0260) | **Concorde** : IS0448 part N 34,4 % = EBC « 34,4 % » du Dossier. |
| **RNU** | St-Philippe AO0050 | 1/1 | **Correct** : `zone_fam=null`, bloc `rnu` complet, Dossier « Aucun PLU — RNU ». |
| **Dernière vente** | `max(date_mutation)` `dvf_mutations_parcelle` vs fiche | 38/38 | Concorde (p. ex. « (aucune) » des deux côtés sur les parcelles sans mutation). |
| **Anomalies de texte** | scan `None/NaN/undefined/Traceback/{{}}` dans les 38 Dossiers | 38/38 | **Aucune** (le jeton « null » rencontré = mot français « nulle », faux positif écarté). |
| **Dates futures** | scan `>2026-11-15` dans les 38 fiches | 38/38 | **Aucune**. |
| **Écran = API** | fiche AD0887 (surface, zone, pente, nb aléa, SDP) | 1 parcelle, 2 résolutions | **Concorde** (1 703 m², Ud, 1,5°, 1 aléa, 719 m² SDP). Console : 0 erreur. |

Détail chiffré : `oracle.csv`, `oracle_results.txt`, `MATRICE.csv`, `DIVERGENCES_auto.csv`.

---

## 2. Documents réellement générés (document × parcelle)

| Document | Parcelles | n | Preuve |
|----------|-----------|---|--------|
| Fiche (API JSON) | **toutes** | 38 | `chasse-1/<idu>/fiche.json` |
| Dossier PDF | **toutes** | 38 | `chasse-1/<idu>/dossier.pdf` + `.txt` |
| Apporteur PDF | AD0887, HT0538, AO1198, AM0838 | 4 | `chasse-1/<idu>/apporteur.pdf` (refus 200 — cf. E2) |
| Pré-dossier ZIP | AD0887, HT0538 (OK) ; AO1198, AM0838 (422 non constructible) | 4 | `chasse-1/<idu>/predossier.zip` |
| Étude de zone PDF | AD0887, HT0538, AO1198, AM0838 | 4 | `chasse-1/<idu>/etudezone.pdf` |
| Estimer (analyse parcelle) PDF | AD0887, HT0538, AO1198, AM0838 | 4 | `chasse-1/<idu>/analyse.pdf` |
| Étude faisabilité — stationnement (payload) | AD0887, HT0538 | 2 | `chasse-1/_canaris/stationnement_*.json` |

## 3. Oracle indépendant (fait × parcelle)

| Fait recalculé | Couverture | Note |
|----------------|-----------|------|
| surface, emprise (union BD TOPO), nb bâtiments, pente, parts de zone, aléa fort, dernière vente | 38/38 | `oracle.csv` |
| part PPR INTERDICTION (zone rouge réglementaire) | **0/38** | §3bis a dépassé le timeout (géométries PPR lourdes) — **non calculé** ; l'échantillonnage « zone rouge partielle » s'appuie sur `cascade_results.detail` à la place. |
| prix médian terrain secteur (recompute vs servi) | 38 secteurs | **Non concluant** : le recalcul brut diverge du servi, mais la méthode de l'app (exclusion multi-parcelles, retrait d'aberrants) est inconnue → **non vérifiable indépendamment** (pas compté comme écart). |

## 4. Écrans parcourus (navigateur piloté)

| Écran | Parcelle(s) | Résolutions | Résultat |
|-------|-------------|-------------|----------|
| Accueil / Carte | — | 1440×694 | 0 erreur console (après correction du proxy dev, cf. §5). |
| Fiche parcelle | AD0887 | 1440×694 | Valeurs = API ; capture `_ecrans/fiche_AD0887_1440.png`. |
| Fiche parcelle | AM0838 (non constructible) | 1920×1080 | Charge proprement, 0 erreur ; `_ecrans/fiche_AM0838_1920.png`. |

---

## 5. NON testé (et pourquoi) — « aucun écart » ne s'applique PAS ici

- **Documents non générés dans la matrice complète** : *Apporteur, Pré-dossier, Étude de zone, Estimer* n'ont été produits que sur 4 parcelles (temps : Dossier ≈ 24 s/pièce). **Bilan (PDF/Excel)**, **Comparatif**, **Gabarit PDF**, **Analyse par lien d'annonce** : **non générés** (le Bilan exige des saisies + `doc_id` ; le Comparatif exige un couple d'IDU ; l'Analyse-lien exige une URL d'annonce externe).
- **Apporteur** : **non testable** sans compte « société » nommé (env. d'audit `local` sans compte) → seul le chemin de refus a été vu (E2). Le contenu réel (8–20 pages) n'est pas couvert.
- **Étude de faisabilité (moteur M22 complet)** : seul le *payload* de stationnement (sans moteur) a été appelé. Le PDF d'Étude et le calcul d'implantation (30–60 s, process isolé) **non exécutés** → le défaut canari « règle maison sur immeuble » (AD0887) n'est que **partiellement** observé.
- **Prix médian de secteur** : non validable (méthode de filtrage de l'app inconnue) — voir §3.
- **Part de zone rouge PPR réglementaire** : non recalculée (timeout) — voir §3.
- **Mails** (21 mails clients) : **inventoriés** (INVENTAIRE.md §D) mais **non générés/envoyés** (aucun envoi en audit ; déclencheurs = webhooks Stripe / jobs / actions admin).
- **Autres écrans & outils** : Radar, Projets, CRM, Copilote, Docs, et la plupart des **outils** (PLU, Scan patrimoine, Permis, Communes, Blocs, Successions, Solaire, Taxe, Gabarit, Assemblage, Comparer, Courrier, Remonter le temps) — **non parcourus au navigateur** (budget). Seule la Fiche a été vérifiée écran↔API.
- **Browser** : 2 parcelles seulement, Fiche uniquement ; les autres écrans/outils × parcelles ne sont pas couverts.

---

## 6. Réserves de méthode (auto-contrôle, LOT 6)

- **Canaris retrouvés** : HT0538 « aucune place » ✓ ; AD0887 « écart estimation/esquisse » ✓ (méthode **non aveugle**). Le 3ᵉ volet (maison↔immeuble AD0887) nécessite le moteur M22 complet — partiellement couvert.
- **Faux positif évité (adversarial)** : l'emprise « 689 m² » du motif de score aurait pu être signalée comme bug ; la vérification (union réelle BD TOPO∪CoSIA = 457, `p_model_bati` actuel = 425) montre qu'elle vient du **run figé** → rattachée au **calcul de nuit gelé** (connu), **non comptée** (K1).
- **Caveat échantillon** : le groupe A « 1 constructible / commune » utilise un *proxy* (zone U/AU + absence de `parcel_constructibilite`) ; ≥ 5 des 24 se révèlent non-constructibles en fiche live (slivers 0,69–16 m², UE « habitat interdit » AM0838, RNU AO0050). Utile pour les états limites, mais le groupe A n'est pas 100 % « constructible live ». Cet écart proxy↔fiche est lui-même remonté en E3.
- **Proxy dev (`:8000`)** : le front (`vite.config.ts:32`) proxifie par défaut vers `:8000` ; sans `LABUSE_API_DEV=…:7440` le socle affiche 502 partout. **Dev uniquement** (prod = même origine FastAPI) → non compté comme écart client.
- **Dossiers générés avec `env=local`** sans `LABUSE_SECRET_KEY` (clé de session éphémère) ; aucun impact observé sur les faits extraits.
