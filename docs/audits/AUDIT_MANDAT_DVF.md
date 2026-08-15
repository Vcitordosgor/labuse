# AUDIT MANDAT_DVF — Quelle lecture DVF pour quel usage (Phase 1, mesure)

**Branche `feat/mandat-dvf`. Aucune écriture de doctrine. Mesuré le 15/08/2026. STOP arbitrage.**

## Verdict en une phrase
Les 4 profils DVF de `marche_service` servent **4 grandeurs différentes** pour **4 questions
différentes** — ce sont des lectures légitimes, pas des variantes d'un même chiffre. La sensibilité
mesurée JUSTIFIE les rayons : **100 m = 0 vente en dense**, **rural = 1 vente même à 500 m/5 ans**,
**500 m/3 ans stabilise** (n ≥ 20, ±8 %). Ce qui manque : les paramètres et l'effectif ne sont pas
affichés à côté du chiffre, et le seuil « effectif trop faible » n'est pas dit.

## 1 — Inventaire des lectures servies (profil · grandeur · question)
| Usage servi | Profil `marche_service` | Rayon / Fenêtre | GRANDEUR | Question de l'utilisateur |
|---|---|---|---|---|
| Dossier (bloc Marché secteur) | `DVF_SECTEUR_DOSSIER` (flash/_marche) | 500 m / 3 ans | **médiane €/m² BÂTI ET €/m² TERRAIN NU** (deux) | « Quel niveau de prix dans le secteur ? » |
| Banquier + Argumentaire | `DVF_BANQUIER_ADAPTATIF` (sector_price) | adaptatif 500→1500→commune | **€/m² HABITABLE** (prix de sortie neuf, appart/maison, Q1/méd/Q3) | « À quel prix revendre le programme neuf ? » |
| One-pager (voisinage) | `DVF_VOISINAGE_100M` (site_voisinage) | 100 m / 36 mois | **médiane BRUTE de valeur_foncière** (pas un €/m²) | « Qu'est-ce qui s'est vendu au pied de la parcelle ? » |
| Premium (table comparables) | `COMPARABLES_PREMIUM` | < 500 m / 3 ans | **€/m² BÂTI par vente** (date/dist/surface/prix) | « Quelles ventes comparables montrer au financeur ? » |
| Fiche écran + premium (bloc Marché commune, M-U) | `marche_bloc.bloc_condense` (**hors marche_service**) | commune | prix ancien médian commune, tendance | « Comment va le marché de la commune ? » |

## 2 — La question avant le paramètre (à figer)
- **Voisinage (100 m)** = un SIGNAL DE PROXIMITÉ, pas une référence de marché. Par nature rare (cf. §3 :
  dense = 0 vente à 100 m). La bonne lecture est « ce qui s'est vendu tout près » AVEC son effectif, pas
  un prix qu'on présente comme fiable. Grandeur = transaction brute (M38).
- **Secteur / comparables (500 m / 3 ans)** = une RÉFÉRENCE DE MARCHÉ. Le rayon 500 m et la fenêtre 3 ans
  sont ce qui donne un effectif suffisant pour une médiane stable (§3). Grandeur = €/m² bâti.
- **Banquier (adaptatif)** = un PRIX DE SORTIE NEUF (habitable), rayon croissant jusqu'à atteindre
  l'effectif minimal (fiabilité). Grandeur ≠ des autres (habitable, pas bâti existant).

## 3 — Sensibilité mesurée (médiane €/m² bâti · n) — le rayon a une raison
| parcelle | 100 m | 300 m | 500 m |
|---|---|---|---|
| **DENSE** (Saint-Denis) | **0 vente** | 1 an n=8 (2198) · 3 ans n=21 (2195) · 5 ans n=42 (2029) | 1 an n=40 (2381) · 3 ans **n=226 (2336)** · 5 ans n=436 (2258) |
| **RURAL** (Cilaos) | 0 | 5 ans **n=1** (1300) | 5 ans **n=1** (1300) |
| **LITTORAL** (Saint-Leu) | 3 ans n=3 (4156) · 5 ans n=6 (4863) | 1 an n=3 (**6000**) · 3 ans n=50 (5029) · 5 ans n=98 (4892) | 1 an n=8 (4955) · 3 ans **n=74 (5094)** · 5 ans n=164 (4907) |

**Lecture :**
- **100 m est inexploitable comme référence** : 0 vente en dense, ≤ 6 en littoral. C'est un signal de
  proximité (M38), pas un prix — d'où l'obligation d'afficher n et de le dire.
- **Rural = instabilité structurelle** : 1 seule vente même à 500 m/5 ans → une médiane à n=1 (1 300)
  n'est PAS une référence. Le document doit dire « échantillon insuffisant », pas montrer un tableau.
- **500 m / 3 ans est le point stable** (dense n=226, littoral n=74 ; médiane ±8 % entre fenêtres). En
  deçà (n=3) la médiane oscille de **±44 %** (littoral 300 m : 6000 à n=3 vs 5029 à n=50) → seuil de
  fiabilité ≈ **n ≥ 8** ; en dessous, la lecture n'a pas de sens.

## 4 — Sémantique : quatre grandeurs, pas quatre variantes (le défaut du 2×)
Ordres de grandeur mesurés, **distincts par nature** :
- **€/m² bâti existant** (comparables/dossier) : ~2 200 (dense) à ~5 000 (littoral) ;
- **€/m² habitable prix de sortie NEUF** (banquier) : supérieur au bâti existant (VEFA) ;
- **€/m² terrain nu** (dossier, M79) : ~150–325 (secteur) — **un ordre de grandeur en dessous** ;
- **valeur_foncière brute** (voisinage) : un montant de transaction, pas un €/m².
→ Présenter un €/m² habitable sous le libellé « prix du secteur » (bâti), ou un terrain nu à côté d'un
bâti sans distinction, produit un écart de 2× à 10× qui fait douter le client. **Aucun mislabel trouvé
dans les profils actuels** (chaque profil sert sa grandeur), MAIS les libellés servis ne DISENT pas
toujours la grandeur (« prix » nu). À figer : chaque chiffre dit SA grandeur.

## 5 — Appels DVF résiduels hors `marche_service` (à router en Phase 2)
- `app.py:2946` `sector_price(...)` DIRECT (dans `_calculette_for_pdf`) — mais le prix est **overridé**
  par `resolve_prix_sortie_servi` (point partagé) : la structure vient de sector_price, le prix du point
  unique. À router par propreté.
- `app.py:1417` `SELECT count(*) FROM dvf_mutations WHERE commune…` — un COMPTE commune (signal
  d'activité, pas un prix). Direct. À décider : dans marche_service ou hors périmètre (signal ≠ prix).
- `marche_bloc.bloc_condense` (bloc Marché commune M-U) — lecture commune, hors marche_service. Grandeur
  = prix ancien médian commune. À décider si elle entre dans les profils ou reste un bloc commune distinct.

## Décision demandée à Vic (STOP)
1. **Figer les 4 profils sur leur raison** (§2-3) : voisinage_100m = signal proximité (n affiché, jamais
   « référence ») ; secteur/comparables 500 m/3 ans = référence marché (raison : effectif stable) ;
   banquier adaptatif = prix sortie habitable. Fenêtre 3 ans = équilibre effectif/récence.
2. **Seuil d'effectif** : sous **n ≈ 8**, la sortie dit « échantillon insuffisant » et ne montre pas un
   tableau qui paraît solide (le rural n=1 le rend obligatoire). Valider le seuil.
3. **Le garde-fou du 2×** (projection arithmétique > 2× référence → information manquante) : à câbler.
4. **Résiduels §5** : router sector_price, décider du compte commune et du bloc M-U.
