# PLU-CALIBRAGE-5 lot 1 — triage des 419 règles `propose`

**419 propose** — A (formules déduites) **43** · B (écarts / attributions) **335** · C (citation non retrouvée) **41**.

**Méthode.** On classe par TRAITEMENT (ce que feront les lots 2-4), depuis la `raison` de chaque propose et le CONTENU de sa citation :
- **A — formules déduites** : la valeur est une interprétation du texte, pas un chiffre écrit — barème de stationnement (`non chiffrable`), recul relatif (H/2, « sur limite OU recul »), renvoi (« se reporter au règlement de la zone »). Une `valeur non numérique` dont la citation contient un tel motif de formule.
- **B — écarts / attributions** : une citation est trouvée mais la valeur (ou son attribution de secteur) est à CONFIRMER contre la page — `harmonisation ≠ texte` (l'ancien nombre n'est pas dans la citation), `attribution douteuse` (citation sous secteur None), ou `valeur non numérique` dont la citation porte un chiffre RÉCUPÉRABLE. La plus grosse.
- **C — citation non retrouvée** : `non retrouvée` / `INTROUVABLE` — la règle existe, le texte n'a pas été localisé.

La frontière A/B reste provisoire : une règle B peut, à la relecture (lot 2), révéler une formule (traitée comme A) ou l'absence de règle (→ `absent`).

## Répartition rubrique × famille

| rubrique | A | B | C |
| --- | --- | --- | --- |
| hauteur | 0 | 95 | 15 |
| emprise_sol | 0 | 30 | 4 |
| retraits | 9 | 142 | 5 |
| stationnement | 32 | 14 | 13 |
| pleine_terre | 2 | 54 | 4 |

## Les 419, par famille


### Famille A — formules déduites (43)

| commune | zone | rubrique | valeur proposée | pourquoi propose | p. |
| --- | --- | --- | --- | --- | --- |
| L'Étang-Salé | AUa | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 84 |
| L'Étang-Salé | AUb | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 84 |
| L'Étang-Salé | AUc | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 84 |
| L'Étang-Salé | UA | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 22 |
| L'Étang-Salé | UB | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 33 |
| L'Étang-Salé | UBv | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 33 |
| L'Étang-Salé | UC | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 42 |
| L'Étang-Salé | UD | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 51 |
| Le Port | 1AUm | retraits.voie | — | valeur non numérique ('a_verifier') | 146 |
| La Possession | AUAv | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 21 |
| La Possession | AUEm | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 54 |
| La Possession | UApsfr2 | retraits.limites_separatives | — | valeur non numérique ('a_verifier') | 15 |
| La Possession | UAv | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 21 |
| La Possession | UE | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 45 |
| La Possession | UEm | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 54 |
| Saint-André | UA | stationnement.par_logement | — | stationnement non chiffrable ("1 place min par logement (locatif aide, <50m2, ou <500m d'une gare routiere) ; 1,5 place min par logement >=50m2 (arrondi entier inferieur)") | 20 |
| Saint-André | UB | stationnement.par_logement | — | stationnement non chiffrable ("1 place min par logement (locatif aide, <50m2, ou <500m d'une gare routiere) ; 1,5 place min par logement >=50m2 (arrondi entier inferieur)") | 31 |
| Saint-André | UC | stationnement.par_logement | — | stationnement non chiffrable ("1 place min par logement (locatif aide, <50m2, ou <500m d'une gare routiere) ; 1,5 place min par logement >=50m2 (arrondi entier inferieur)") | 42 |
| Saint-André | UD | stationnement.par_logement | — | stationnement non chiffrable ("1 place min par logement (locatif aide, <50m2, ou <500m d'une gare routiere) ; 1,5 place min par logement >=50m2 (arrondi entier inferieur)") | 53 |
| Saint-André | UE | stationnement.par_logement | — | stationnement non chiffrable ("Non reglemente pour l'habitation (normes UE 12.2 = commerces/bureaux, artisanat/industrie, entrepots, equipements ; pas de norme logement)") | 65 |
| Saint-André | US | stationnement.par_logement | — | stationnement non chiffrable ('1 place min par logement') | 76 |
| Saint-André | UT | stationnement.par_logement | — | stationnement non chiffrable ('1 place min par logement') | 85 |
| Saint-Benoît | Ua | retraits.limites_separatives | — | valeur non numérique ('sur limite(s) séparative(s) latérale(s) OU recul ≥ 1 m') | 11 |
| Saint-Benoît | Ub | retraits.limites_separatives | — | valeur non numérique ('sur limite(s) séparative(s) latérale(s) OU recul ≥ 1 m') | 11 |
| Saint-Benoît | Ue | retraits.limites_separatives | — | valeur non numérique ('sur limite(s) séparative(s) latérale(s) OU recul ≥ 1 m') | 11 |
| Saint-Benoît | Up | retraits.limites_separatives | — | valeur non numérique ('sur limite(s) séparative(s) latérale(s) OU recul ≥ 1 m') | 11 |
| Saint-Benoît | Ut | retraits.limites_separatives | — | valeur non numérique ('sur limite(s) séparative(s) latérale(s) OU recul ≥ 1 m') | 11 |
| Saint-Joseph | 1AUto | retraits.limites_separatives | — | valeur non numérique ('a_verifier') | 109 |
| Saint-Joseph | 1AUtok | retraits.limites_separatives | — | valeur non numérique ('a_verifier') | 109 |
| Saint-Paul | AU5e | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 263 |
| Saint-Paul | U1e | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 48 |
| Saint-Paul | U1l | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 48 |
| Saint-Paul | U1pru | stationnement.par_logement | — | stationnement non chiffrable par logement ('exempté : aucune place imposée') | 30 |
| Saint-Paul | U1pso | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 30 |
| Saint-Paul | U2e | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 97 |
| Saint-Paul | U2h | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 76 |
| Saint-Paul | U3e | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 154 |
| Saint-Pierre | AUdma | stationnement.par_logement | — | stationnement non chiffrable par logement ('a_verifier') | 91 |
| Saint-Pierre | Ucv | stationnement.par_logement | — | stationnement non chiffrable par logement ('1 place par tranche de 75 m² de surface de plancher') | 72 |
| Saint-Pierre | Ud | stationnement.par_logement | — | stationnement non chiffrable par logement ('1 place par tranche de 75 m² de surface de plancher') | 93 |
| Saint-Pierre | UdBO | stationnement.par_logement | — | stationnement non chiffrable par logement ('1 place par tranche de 75 m² de surface de plancher') | 93 |
| Saint-Pierre | Udl | stationnement.par_logement | — | stationnement non chiffrable par logement ('1 place par tranche de 75 m² de surface de plancher') | 93 |
| Sainte-Marie | 1AUep | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 41 |

### Famille B — écarts / attributions (à confirmer contre la page) (335)

| commune | zone | rubrique | valeur proposée | pourquoi propose | p. |
| --- | --- | --- | --- | --- | --- |
| Les Avirons | AUa | hauteur.egout | m=12.0 | attribution douteuse (citation sous secteur None) | 13 |
| Les Avirons | AUa | hauteur.faitage | m=15.0 | attribution douteuse (citation sous secteur None) | 13 |
| Les Avirons | AUa | pleine_terre.pct | pct=15.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | AUc | hauteur.egout | m=8.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | AUc | hauteur.faitage | m=11.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | AUd | hauteur.egout | m=7.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | AUd | hauteur.faitage | m=10.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | AUd | pleine_terre.pct | pct=40.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | Ua | hauteur.egout | m=12.0 | attribution douteuse (citation sous secteur None) | 13 |
| Les Avirons | Ua | hauteur.faitage | m=15.0 | attribution douteuse (citation sous secteur None) | 13 |
| Les Avirons | Ua | pleine_terre.pct | pct=15.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | Uc3 | pleine_terre.pct | pct=40.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | Ud | hauteur.egout | m=7.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud | hauteur.faitage | m=10.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud | pleine_terre.pct | pct=40.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | Ud1 | hauteur.egout | m=7.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud1 | hauteur.faitage | m=10.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud1 | pleine_terre.pct | pct=40.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | Ud2 | hauteur.egout | m=6.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud2 | hauteur.faitage | m=9.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud2 | pleine_terre.pct | pct=40.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Avirons | Ud3 | hauteur.egout | m=6.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud3 | hauteur.faitage | m=9.0 | attribution douteuse (citation sous secteur None) | 12 |
| Les Avirons | Ud3 | pleine_terre.pct | pct=40.0 | attribution douteuse (citation sous secteur None) | 18 |
| Bras-Panon | 1AUa | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 17 |
| Bras-Panon | 1AUb | hauteur.egout | m=8.0 | attribution douteuse (citation sous secteur None) | 31 |
| Bras-Panon | 1AUb | hauteur.faitage | m=11.0 | attribution douteuse (citation sous secteur None) | 31 |
| Bras-Panon | 1AUb | retraits.limites_separatives | min_m=4.0 | attribution douteuse (citation sous secteur None) | 30 |
| Bras-Panon | 1AUc | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 44 |
| Bras-Panon | 1AUd | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 57 |
| Bras-Panon | 1AUec | retraits.limites_separatives | min_m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 17 |
| Bras-Panon | 1AUt | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 17 |
| Bras-Panon | Ua | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 17 |
| Bras-Panon | Ub | hauteur.egout | m=8.0 | attribution douteuse (citation sous secteur None) | 31 |
| Bras-Panon | Ub | hauteur.faitage | m=11.0 | attribution douteuse (citation sous secteur None) | 31 |
| Bras-Panon | Ub | retraits.limites_separatives | min_m=4.0 | attribution douteuse (citation sous secteur None) | 30 |
| Bras-Panon | Uba | hauteur.egout | m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 31 |
| Bras-Panon | Uba | hauteur.faitage | m=11.0 | valeur 11 absente de la citation (harmonisation ≠ texte) | 31 |
| Bras-Panon | Uba | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 30 |
| Bras-Panon | Uc | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 44 |
| Bras-Panon | Ud | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 57 |
| Bras-Panon | Udu | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 57 |
| Entre-Deux | Ua | hauteur.egout | m=7.0 | attribution douteuse (citation sous secteur None) | 21 |
| Entre-Deux | Ua | hauteur.faitage | m=11.0 | attribution douteuse (citation sous secteur None) | 21 |
| L'Étang-Salé | AUa | emprise_sol.ces | pct=70.0 | attribution douteuse (citation sous secteur None) | 76 |
| L'Étang-Salé | AUb | emprise_sol.ces | pct=65.0 | attribution douteuse (citation sous secteur None) | 76 |
| L'Étang-Salé | AUc | emprise_sol.ces | pct=60.0 | attribution douteuse (citation sous secteur None) | 76 |
| L'Étang-Salé | AUt | emprise_sol.ces | pct=65.0 | attribution douteuse (citation sous secteur None) | 76 |
| Petite-Île | UZ | retraits.limites_separatives | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 83 |
| Petite-Île | UZ | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 83 |
| Le Port | 1AUa | emprise_sol.ces | pct=60.0 | valeur 60 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUa | hauteur.egout | m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUa | hauteur.faitage | m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUa | pleine_terre.pct | pct=15.0 | valeur 15 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUa | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUa | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 146 |
| Le Port | 1AUc | emprise_sol.ces | pct=80.0 | valeur 80 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUc | hauteur.egout | m=16.0 | valeur 16 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUc | hauteur.faitage | m=16.0 | valeur 16 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUc | pleine_terre.pct | pct=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUc | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUc | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUem | emprise_sol.ces | pct=60.0 | valeur 60 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUem | hauteur.faitage | m=18.0 | valeur 18 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUem | pleine_terre.pct | pct=20.0 | valeur 20 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUem | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUem | retraits.voie | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUm | pleine_terre.pct | pct=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 150 |
| Le Port | 1AUs | emprise_sol.ces | pct=60.0 | valeur 60 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUs | hauteur.faitage | m=18.0 | valeur 18 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUs | pleine_terre.pct | pct=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | 1AUs | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 145 |
| Le Port | Ua | pleine_terre.pct | pct=15.0 | valeur 15 absente de la citation (harmonisation ≠ texte) | 27 |
| Le Port | Uc | pleine_terre.pct | pct=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 58 |
| Le Port | Uca | pleine_terre.pct | pct=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 58 |
| Le Port | Ud | retraits.limites_separatives | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 68 |
| Le Port | Us | pleine_terre.pct | pct=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 125 |
| La Possession | AUAv | hauteur.egout | — | valeur non numérique ('a_verifier') | 17 |
| La Possession | AUAv | hauteur.faitage | — | valeur non numérique ('a_verifier') | 17 |
| La Possession | AUAv | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 22 |
| La Possession | AUB | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | AUBb | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | AUBm | hauteur.egout | — | valeur non numérique ('a_verifier') | 75 |
| La Possession | AUBm | hauteur.faitage | — | valeur non numérique ('a_verifier') | 75 |
| La Possession | AUBpsfr2 | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | AUEm | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 50 |
| La Possession | AUT | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 60 |
| La Possession | UA | retraits.limites_separatives | min_m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 15 |
| La Possession | UAa | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 15 |
| La Possession | UAm | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 22 |
| La Possession | UAm | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 15 |
| La Possession | UAm | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 14 |
| La Possession | UApsfr2 | hauteur.egout | — | valeur non numérique ('a_verifier') | 16 |
| La Possession | UApsfr2 | hauteur.faitage | — | valeur non numérique ('a_verifier') | 16 |
| La Possession | UAv | hauteur.egout | — | valeur non numérique ('a_verifier') | 17 |
| La Possession | UAv | hauteur.faitage | — | valeur non numérique ('a_verifier') | 17 |
| La Possession | UAv | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 22 |
| La Possession | UB | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | UBa | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | UBb | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | UBc | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | UBpsfr2 | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | UBpszc | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 30 |
| La Possession | UE | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 41 |
| La Possession | UEm | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 50 |
| La Possession | UT | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 60 |
| La Possession | UTfr2 | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 60 |
| Saint-Benoît | Ua | emprise_sol.ces | pct=80.0 | attribution douteuse (secteur None) | 10 |
| Saint-Benoît | Ua | pleine_terre.pct | pct=20.0 | attribution douteuse (secteur None) | 13 |
| Saint-Benoît | Ua | retraits.voie | — | attribution douteuse (secteur None) | 10 |
| Saint-Benoît | Ub | emprise_sol.ces | pct=80.0 | attribution douteuse (secteur None) | 10 |
| Saint-Benoît | Ub | pleine_terre.pct | pct=20.0 | attribution douteuse (secteur None) | 13 |
| Saint-Benoît | Ub | retraits.voie | — | valeur non numérique ('75 m axe RN hors agglomération (rues Pompidou/Montfleury/Brunet non concernées en Ub)') | 11 |
| Saint-Benoît | Ue | emprise_sol.ces | pct=80.0 | attribution douteuse (secteur None) | 10 |
| Saint-Benoît | Ue | pleine_terre.pct | pct=20.0 | attribution douteuse (secteur None) | 13 |
| Saint-Benoît | Ue | retraits.voie | — | valeur non numérique ('75 m axe RN hors agglomération') | 11 |
| Saint-Benoît | Up | emprise_sol.ces | pct=80.0 | attribution douteuse (secteur None) | 10 |
| Saint-Benoît | Up | pleine_terre.pct | pct=20.0 | attribution douteuse (secteur None) | 13 |
| Saint-Benoît | Up | retraits.voie | — | valeur non numérique ('75 m axe RN hors agglomération') | 11 |
| Saint-Benoît | Ut | emprise_sol.ces | pct=80.0 | attribution douteuse (secteur None) | 10 |
| Saint-Benoît | Ut | pleine_terre.pct | pct=20.0 | attribution douteuse (secteur None) | 13 |
| Saint-Benoît | Ut | retraits.voie | — | valeur non numérique ('75 m axe RN hors agglomération') | 11 |
| Saint-Joseph | 1AU3 | emprise_sol.ces | pct=70.0 | valeur 70 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3 | hauteur.egout | m=11.0 | valeur 11 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3 | hauteur.faitage | m=13.0 | valeur 13 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3 | pleine_terre.pct | pct=15.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU3 | retraits.limites_separatives | min_m=5.5 | valeur 5.5 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3 | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3 | stationnement.par_logement | places=2.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU3a | emprise_sol.ces | pct=70.0 | valeur 70 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3a | hauteur.egout | m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3a | hauteur.faitage | m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3a | pleine_terre.pct | pct=25.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU3a | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3a | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU3a | stationnement.par_logement | places=2.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU5 | emprise_sol.ces | pct=50.0 | valeur 50 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5 | hauteur.egout | m=7.0 | valeur 7 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5 | hauteur.faitage | m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5 | pleine_terre.pct | pct=35.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU5 | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5 | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5 | stationnement.par_logement | places=2.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU5ru | emprise_sol.ces | pct=40.0 | valeur 40 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5ru | hauteur.egout | m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5ru | hauteur.faitage | m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5ru | pleine_terre.pct | pct=35.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU5ru | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5ru | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5ru | stationnement.par_logement | places=2.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU5vi | emprise_sol.ces | pct=40.0 | valeur 40 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5vi | hauteur.egout | m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5vi | hauteur.faitage | m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5vi | pleine_terre.pct | pct=35.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU5vi | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5vi | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU5vi | stationnement.par_logement | places=2.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU6 | emprise_sol.ces | pct=50.0 | valeur 50 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6 | hauteur.egout | m=12.0 | valeur 12 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6 | hauteur.faitage | m=15.0 | valeur 15 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6 | pleine_terre.pct | pct=15.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU6 | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6 | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6c | emprise_sol.ces | pct=50.0 | valeur 50 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6c | hauteur.egout | m=15.0 | valeur 15 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6c | hauteur.faitage | m=18.0 | valeur 18 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6c | pleine_terre.pct | pct=15.0 | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AU6c | retraits.limites_separatives | min_m=7.5 | valeur 7.5 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AU6c | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 107 |
| Saint-Joseph | 1AUto | hauteur.egout | m=6.0 | attribution douteuse (citation sous secteur None) | 110 |
| Saint-Joseph | 1AUto | hauteur.faitage | m=9.0 | attribution douteuse (citation sous secteur None) | 110 |
| Saint-Joseph | 1AUto | pleine_terre.pct | — | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AUto | retraits.voie | — | valeur non numérique ('a_verifier') | 109 |
| Saint-Joseph | 1AUtok | hauteur.egout | m=9.0 | attribution douteuse (citation sous secteur None) | 110 |
| Saint-Joseph | 1AUtok | hauteur.faitage | m=12.0 | attribution douteuse (citation sous secteur None) | 110 |
| Saint-Joseph | 1AUtok | pleine_terre.pct | — | attribution douteuse (citation sous secteur None) | 108 |
| Saint-Joseph | 1AUtok | retraits.voie | — | valeur non numérique ('a_verifier') | 109 |
| Saint-Joseph | U1 | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 18 |
| Saint-Joseph | U2 | retraits.limites_separatives | min_m=5.5 | valeur 5.5 absente de la citation (harmonisation ≠ texte) | 33 |
| Saint-Joseph | U2a | retraits.limites_separatives | min_m=5.5 | valeur 5.5 absente de la citation (harmonisation ≠ texte) | 33 |
| Saint-Joseph | U2a | stationnement.par_logement | places=1.0 | valeur 1 absente de la citation (harmonisation ≠ texte) | 39 |
| Saint-Joseph | U3 | retraits.limites_separatives | min_m=5.5 | valeur 5.5 absente de la citation (harmonisation ≠ texte) | 49 |
| Saint-Joseph | U3a | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 49 |
| Saint-Joseph | U3ar | retraits.limites_separatives | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 49 |
| Saint-Joseph | U4 | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 63 |
| Saint-Joseph | U5 | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 78 |
| Saint-Joseph | U5cv | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 78 |
| Saint-Joseph | U5ma | retraits.limites_separatives | min_m=3.5 | valeur 3.5 absente de la citation (harmonisation ≠ texte) | 78 |
| Saint-Joseph | U6 | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 93 |
| Saint-Joseph | U6c | retraits.limites_separatives | min_m=7.5 | valeur 7.5 absente de la citation (harmonisation ≠ texte) | 93 |
| Saint-Louis | 1AUc1 | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 46 |
| Saint-Louis | 1AUe | hauteur.egout | m=12.0 | valeur 12 absente de la citation (harmonisation ≠ texte) | 110 |
| Saint-Louis | 1AUe | hauteur.faitage | m=15.0 | valeur 15 absente de la citation (harmonisation ≠ texte) | 110 |
| Saint-Louis | 1AUe | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 73 |
| Saint-Louis | 1AUe | retraits.voie | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 73 |
| Saint-Louis | UC1 | retraits.limites_separatives | min_m=4.5 | valeur 4.5 absente de la citation (harmonisation ≠ texte) | 46 |
| Saint-Louis | UE | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 73 |
| Saint-Louis | UE | retraits.voie | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 73 |
| Saint-Louis | US | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 85 |
| Saint-Louis | US | retraits.voie | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 85 |
| Saint-Paul | AU5e | emprise_sol.ces | — | valeur non numérique ('a_verifier') | 259 |
| Saint-Paul | AU5e | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 265 |
| Saint-Paul | AU5e | retraits.voie | — | valeur non numérique ('a_verifier') | 257 |
| Saint-Paul | U1a | retraits.voie | — | valeur non numérique ('a_verifier') | 18 |
| Saint-Paul | U1b | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U1c | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U1d | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 35 |
| Saint-Paul | U1d | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U1e | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 51 |
| Saint-Paul | U1e | retraits.voie | — | valeur non numérique ('a_verifier') | 41 |
| Saint-Paul | U1f | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U1g | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U1l | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 51 |
| Saint-Paul | U1l | retraits.voie | — | valeur non numérique ('a_verifier') | 41 |
| Saint-Paul | U1pru | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 35 |
| Saint-Paul | U1pru | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U1pso | retraits.voie | — | valeur non numérique ('a_verifier') | 19 |
| Saint-Paul | U2b | retraits.voie | — | valeur non numérique ('a_verifier') | 70 |
| Saint-Paul | U2c | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 72 |
| Saint-Paul | U2c | retraits.voie | — | valeur non numérique ('a_verifier') | 70 |
| Saint-Paul | U2d | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 72 |
| Saint-Paul | U2d | retraits.voie | — | valeur non numérique ('a_verifier') | 70 |
| Saint-Paul | U2e | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 100 |
| Saint-Paul | U2e | retraits.voie | — | valeur non numérique ('a_verifier') | 91 |
| Saint-Paul | U2h | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 72 |
| Saint-Paul | U3a | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 110 |
| Saint-Paul | U3e | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 156 |
| Saint-Paul | U3e | retraits.voie | — | valeur non numérique ('a_verifier') | 148 |
| Saint-Paul | U4a | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 172 |
| Saint-Paul | U5a | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 218 |
| Saint-Paul | U6a | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 278 |
| Saint-Paul | Usdu | emprise_sol.ces | — | valeur non numérique ('a_verifier') | 133 |
| Saint-Pierre | AUazc | hauteur.egout | m=13.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | AUazc | hauteur.faitage | m=18.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | AUazc | retraits.voie | min_m=4.0 | attribution douteuse (citation sous secteur None) | 176 |
| Saint-Pierre | AUazi | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | AUazi | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | AUazi | retraits.voie | min_m=4.0 | attribution douteuse (citation sous secteur None) | 176 |
| Saint-Pierre | AUdma | emprise_sol.ces | — | attribution douteuse (citation sous secteur None) | 80 |
| Saint-Pierre | AUdma | hauteur.egout | — | attribution douteuse (citation sous secteur None) | 80 |
| Saint-Pierre | AUdma | hauteur.faitage | — | attribution douteuse (citation sous secteur None) | 80 |
| Saint-Pierre | AUdma | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 91 |
| Saint-Pierre | AUdma | retraits.limites_separatives | — | attribution douteuse (citation sous secteur None) | 80 |
| Saint-Pierre | AUdma | retraits.voie | — | attribution douteuse (citation sous secteur None) | 80 |
| Saint-Pierre | AUf | hauteur.egout | m=6.0 | attribution douteuse (citation sous secteur None) | 119 |
| Saint-Pierre | AUf | hauteur.faitage | m=11.0 | attribution douteuse (citation sous secteur None) | 119 |
| Saint-Pierre | Uaza | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | Uaza | hauteur.faitage | m=21.0 | valeur 21 absente de la citation (harmonisation ≠ texte) | 178 |
| Saint-Pierre | Uaza | retraits.voie | min_m=4.0 | attribution douteuse (citation sous secteur None) | 176 |
| Saint-Pierre | Uazc | hauteur.egout | m=13.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | Uazc | hauteur.faitage | m=18.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | Uazi | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | Uazi | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 177 |
| Saint-Pierre | Uazi | retraits.voie | min_m=4.0 | attribution douteuse (citation sous secteur None) | 176 |
| Saint-Pierre | Uazp | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 178 |
| Saint-Pierre | Uazp | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 178 |
| Saint-Pierre | Uazp | retraits.voie | min_m=0.0 | attribution douteuse (citation sous secteur None) | 176 |
| Saint-Pierre | Uazpc | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 178 |
| Saint-Pierre | Uazpc | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 178 |
| Saint-Pierre | Uazpc | retraits.voie | min_m=0.0 | attribution douteuse (citation sous secteur None) | 176 |
| Saint-Pierre | Ucv | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 63 |
| Saint-Pierre | Ue | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 193 |
| Saint-Pierre | Ue | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 193 |
| Saint-Pierre | Uemi | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 193 |
| Saint-Pierre | Uemi | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 193 |
| Saint-Pierre | Uep | emprise_sol.ces | pct=0.2 | valeur 0.2 absente de la citation (harmonisation ≠ texte) | 192 |
| Saint-Pierre | Uep | hauteur.egout | m=16.0 | attribution douteuse (citation sous secteur None) | 193 |
| Saint-Pierre | Uep | hauteur.faitage | m=21.0 | attribution douteuse (citation sous secteur None) | 193 |
| Saint-Pierre | Up | retraits.voie | min_m=0.0 | valeur 0 absente de la citation (harmonisation ≠ texte) | 146 |
| Sainte-Marie | 1AUb | emprise_sol.ces | pct=70.0 | valeur 70 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUb | hauteur.egout | m=12.0 | valeur 12 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUb | hauteur.faitage | m=15.0 | valeur 15 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUb | pleine_terre.pct | pct=25.0 | valeur 25 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUb | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUb | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUb | stationnement.par_logement | places=1.5 | valeur 1.5 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | emprise_sol.ces | pct=60.0 | valeur 60 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | hauteur.egout | m=10.0 | valeur 10 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | hauteur.faitage | m=13.0 | valeur 13 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | pleine_terre.pct | pct=30.0 | valeur 30 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUc | stationnement.par_logement | places=1.5 | valeur 1.5 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUep | emprise_sol.ces | pct=75.0 | valeur 75 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUep | hauteur.faitage | m=16.0 | valeur 16 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUep | retraits.limites_separatives | min_m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | 1AUep | retraits.voie | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 41 |
| Sainte-Marie | UA | retraits.limites_separatives | min_m=7.5 | valeur 7.5 absente de la citation (harmonisation ≠ texte) | 20 |
| Sainte-Marie | UEa | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UEa | retraits.limites_separatives | min_m=12.0 | valeur 12 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Marie | UEc | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UEc | retraits.limites_separatives | min_m=7.0 | valeur 7 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Marie | UEm | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UEm | retraits.limites_separatives | min_m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Marie | UEp | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UEp | retraits.limites_separatives | min_m=8.0 | valeur 8 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Marie | UR | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UR | retraits.limites_separatives | min_m=12.0 | valeur 12 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Marie | UT | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UT | retraits.limites_separatives | min_m=5.5 | valeur 5.5 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Marie | UTp | pleine_terre.pct | — | valeur non numérique ('a_verifier') | 38 |
| Sainte-Marie | UTp | retraits.limites_separatives | min_m=5.5 | valeur 5.5 absente de la citation (harmonisation ≠ texte) | 33 |
| Sainte-Rose | 1AUa | emprise_sol.ces | pct=70.0 | valeur 70 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUa | hauteur.egout | m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUa | hauteur.faitage | m=12.0 | valeur 12 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUa | pleine_terre.pct | pct=25.0 | valeur 25 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUa | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUa | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUa | stationnement.par_logement | places=2.0 | valeur 2 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | emprise_sol.ces | pct=50.0 | valeur 50 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | hauteur.egout | m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | hauteur.faitage | m=9.0 | valeur 9 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | pleine_terre.pct | pct=30.0 | valeur 30 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUc | stationnement.par_logement | places=2.0 | valeur 2 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUe | emprise_sol.ces | pct=70.0 | valeur 70 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUe | hauteur.egout | m=11.0 | valeur 11 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUe | hauteur.faitage | m=14.0 | valeur 14 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUe | pleine_terre.pct | pct=25.0 | valeur 25 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUe | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | 1AUe | retraits.voie | min_m=4.0 | valeur 4 absente de la citation (harmonisation ≠ texte) | 55 |
| Sainte-Rose | Ua | stationnement.par_logement | places=2.0 | valeur 2 absente de la citation (harmonisation ≠ texte) | 17 |
| Sainte-Rose | Ub | stationnement.par_logement | places=2.0 | valeur 2 absente de la citation (harmonisation ≠ texte) | 26 |
| Sainte-Rose | Uc | stationnement.par_logement | places=2.0 | valeur 2 absente de la citation (harmonisation ≠ texte) | 35 |
| Sainte-Rose | Ud | stationnement.par_logement | places=2.0 | valeur 2 absente de la citation (harmonisation ≠ texte) | 43 |
| Sainte-Rose | Ue | retraits.limites_separatives | min_m=3.0 | valeur 3 absente de la citation (harmonisation ≠ texte) | 49 |
| Sainte-Suzanne | 1AUe | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 22 |
| Sainte-Suzanne | 1AUe | retraits.voie | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 22 |
| Sainte-Suzanne | UE | retraits.limites_separatives | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 22 |
| Sainte-Suzanne | UE | retraits.voie | min_m=6.0 | valeur 6 absente de la citation (harmonisation ≠ texte) | 22 |
| Les Trois-Bassins | Ua | hauteur.egout | m=10.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Trois-Bassins | Ua | hauteur.faitage | m=14.0 | attribution douteuse (citation sous secteur None) | 18 |
| Les Trois-Bassins | Ua | retraits.limites_separatives | min_m=3.0 | attribution douteuse (citation sous secteur None) | 15 |
| Les Trois-Bassins | Ue | retraits.limites_separatives | min_m=5.0 | valeur 5 absente de la citation (harmonisation ≠ texte) | 57 |

### Famille C — citation non retrouvée (41)

| commune | zone | rubrique | valeur proposée | pourquoi propose | p. |
| --- | --- | --- | --- | --- | --- |
| Entre-Deux | AUb | hauteur.egout | m=9.0 | citation INTROUVABLE à la re-lecture du PDF | 29 |
| Entre-Deux | AUb | hauteur.faitage | m=13.0 | citation INTROUVABLE à la re-lecture du PDF | 29 |
| Entre-Deux | AUb | retraits.limites_separatives | min_m=3.0 | citation INTROUVABLE à la re-lecture du PDF | 20 |
| Entre-Deux | AUb | retraits.voie | min_m=4.0 | citation INTROUVABLE à la re-lecture du PDF | 19 |
| Saint-Leu | UA | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 44%) | 13 |
| Saint-Leu | UB | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 33%) | 10 |
| Saint-Leu | UC | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 33%) | 10 |
| Saint-Leu | UD | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 33%) | 10 |
| Saint-Leu | UE | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 33%) | 10 |
| Saint-Leu | UF | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 33%) | 10 |
| Saint-Leu | UP | stationnement.par_logement | places=2.0 | citation non retrouvée (recouvrement 33%) | 10 |
| Saint-Louis | 1AUa | hauteur.egout | m=15.0 | citation non retrouvée autour de p.20 (recouvrement 47%) | 20 |
| Saint-Louis | 1AUa | hauteur.faitage | m=19.0 | citation non retrouvée autour de p.19 (recouvrement 31%) | 19 |
| Saint-Louis | 1AUa | stationnement.par_logement | places=2.0 | citation non retrouvée autour de p.23 (recouvrement 41%) | 23 |
| Saint-Louis | 1AUc | hauteur.egout | m=7.0 | citation non retrouvée autour de p.49 (recouvrement 47%) | 49 |
| Saint-Louis | 1AUc | hauteur.faitage | m=11.0 | citation non retrouvée autour de p.46 (recouvrement 25%) | 46 |
| Saint-Louis | 1AUc | retraits.limites_separatives | min_m=3.0 | citation non retrouvée autour de p.44 (recouvrement 44%) | 44 |
| Saint-Louis | 1AUc | stationnement.par_logement | places=2.0 | citation non retrouvée autour de p.52 (recouvrement 41%) | 52 |
| Saint-Louis | 1AUc1 | emprise_sol.ces | pct=60.0 | citation non retrouvée autour de p.48 (recouvrement 31%) | 48 |
| Saint-Louis | 1AUc1 | hauteur.faitage | m=13.0 | citation non retrouvée autour de p.49 (recouvrement 35%) | 49 |
| Saint-Louis | 1AUc1 | pleine_terre.pct | pct=25.0 | citation non retrouvée autour de p.53 (recouvrement 25%) | 53 |
| Saint-Louis | 1AUc1 | stationnement.par_logement | places=2.0 | citation non retrouvée autour de p.52 (recouvrement 41%) | 52 |
| Saint-Louis | 1AUc2 | emprise_sol.ces | pct=50.0 | citation non retrouvée autour de p.48 (recouvrement 36%) | 48 |
| Saint-Louis | 1AUc2 | hauteur.faitage | m=10.0 | citation non retrouvée autour de p.49 (recouvrement 35%) | 49 |
| Saint-Louis | 1AUc2 | pleine_terre.pct | pct=25.0 | citation non retrouvée autour de p.53 (recouvrement 31%) | 53 |
| Saint-Louis | 1AUc2 | retraits.limites_separatives | min_m=3.0 | citation non retrouvée autour de p.44 (recouvrement 40%) | 44 |
| Saint-Louis | 1AUc2 | stationnement.par_logement | places=2.0 | citation non retrouvée autour de p.52 (recouvrement 41%) | 52 |
| Saint-Louis | 1AUd | hauteur.egout | m=6.0 | citation non retrouvée autour de p.62 (recouvrement 47%) | 62 |
| Saint-Louis | 1AUd | hauteur.faitage | m=10.0 | citation non retrouvée autour de p.59 (recouvrement 25%) | 59 |
| Saint-Louis | 1AUd | stationnement.par_logement | places=2.0 | citation non retrouvée autour de p.66 (recouvrement 41%) | 66 |
| Saint-Louis | 1AUd1 | emprise_sol.ces | pct=40.0 | citation non retrouvée autour de p.62 (recouvrement 36%) | 62 |
| Saint-Louis | 1AUd1 | hauteur.egout | m=6.0 | citation non retrouvée autour de p.60 (recouvrement 32%) | 60 |
| Saint-Louis | 1AUd1 | hauteur.faitage | m=10.0 | citation non retrouvée autour de p.59 (recouvrement 29%) | 59 |
| Saint-Louis | 1AUd1 | pleine_terre.pct | pct=35.0 | citation non retrouvée autour de p.67 (recouvrement 33%) | 67 |
| Saint-Louis | 1AUd1 | retraits.limites_separatives | min_m=3.0 | citation non retrouvée autour de p.60 (recouvrement 47%) | 60 |
| Saint-Louis | 1AUd1 | stationnement.par_logement | places=2.0 | citation non retrouvée autour de p.66 (recouvrement 41%) | 66 |
| Saint-Louis | 1AUe | emprise_sol.ces | pct=70.0 | citation non retrouvée autour de p.76 (recouvrement 47%) | 76 |
| Saint-Louis | UA1 | hauteur.faitage | m=19.0 | citation non retrouvée autour de p.17 (recouvrement 29%) | 17 |
| Saint-Louis | UD1 | hauteur.egout | m=6.0 | citation non retrouvée autour de p.60 (recouvrement 44%) | 60 |
| Saint-Louis | UD1 | hauteur.faitage | m=10.0 | citation non retrouvée autour de p.59 (recouvrement 43%) | 59 |
| Les Trois-Bassins | 1AUt | pleine_terre.pct | pct=30.0 | citation non retrouvée autour de p.69 (recouvrement 41%) | 69 |
