# PLU-SÉRIE-NUIT — ANALYSES DU MATIN (session B, 28/07/2026)

> Quatre livrables d'analyse demandés par Vic après les arbitrages du matin.
> **AUCUNE modification appliquée aux YAML** — Vic tranche sur pièces.
> Périmètre : les 21 `config/plu_*.yaml` de l'île (état de la branche après merge de main).
> Base applicative jamais touchée ; verbatims lus dans les caches de nuit
> (`/tmp/plu_nuit/reglements/`) — les PDF des communes pilotes (Saint-Denis, Saint-Paul)
> ne sont PAS en cache : leurs verbatims sont cités depuis les `_src`/notes des YAML et
> marqués « à confirmer sur pièce ».

## A · LES 18 ZONES « PLAFOND UNIQUE » — verbatims classés pour arbitrage

Classe analysée : zones dont la clause de hauteur donne UNE valeur sans couple
égout/faîtage. Deux catégories selon la formulation (arbitrage Vic sur les libellés).
Hors périmètre : les zones où le faîtage est explicitement nommé (forme `hf`-seul
correcte — 25 zones, liste en fin de section) et les renvois/dérivées (règles de leur
zone support).

### CAT 1 — « hauteur absolue / totale / en tout point » (règle 8 : he = hf)

| Commune | Zone | Valeur | Verbatim |
|---|---|---|---|
| Bras-Panon | AUec | 18 | « Pour la zone AUec, la hauteur absolue (hors équipements techniques) des constructions ne doit pas excéder 18 mètres dans un plan parallèle au sol naturel » (Art. AUINDICEE 10, p.78) — **DÉJÀ réalignée he = hf = 18** (arbitrage explicite du matin). |
| Petite-Île | UZ | 12 | « La hauteur totale d'une construction ne doit pas excéder 12 mètres » (Art. UZ.10, p.84). Gravée `hf: 12, he: null`. |
| Saint-Louis | UZ | 9 (tranche) | Hauteurs « en tout point » PAR AFFECTATION du schéma d'annexe ZAC : 17 m collectifs / 9 m individuels / 12 m tertiaires + plafond NGR (Art. UZ 10.2, p.96-97). Cas particulier : tiroir dépendant d'un schéma non parcellisable, tranche conservatrice 9 gravée en `hf`. |

### CAT 2 — « hauteur maximale fixée à N mètres », sans précision de référence (18 zones)

Gravées `hf`-seul par prudence pendant la nuit ; la règle 8 restaurée (`he = hf`) les
concernerait — mais la vérification A/C a montré que la forme `hf`-seul est PLUS
conservatrice au calcul des niveaux (`engine.py:236-242`) : realignement = hausse de
capacité mesurable. Décision sur formulations, rien appliqué.

| # | Commune | Zone | Valeur | Verbatim |
|---|---|---|---|---|
| 1 | La Possession | UAa | 9 | « Dans le secteur UAa, la hauteur maximale des constructions est fixée à 9 mètres. » (Art. UA 10.2, PDF p.16) |
| 2 | La Possession | UApsfr2 | 12 | « Dans le secteur UApsfr2, la hauteur maximale des constructions est fixée à 12 mètres » (Art. UA 10.2, PDF p.16). ⚠ La MÊME page porte aussi : « …UApsfr2, UAm et UAv, la hauteur maximale des constructions est fixée à 16 mètres au faitage » — deux clauses concurrentes sur la même page, à trancher sur pièce (la session A a gravé 12 sans précision). |
| 3 | La Possession | UBpszc | 7 | « Dans le secteur UBpszc, la hauteur maximale des constructions est fixée à 7 mètres. » (Art. UB 10.2, PDF p.31 — la clause générale UB juste avant donne, elle, le couple 7 égout / 10 faîtage) |
| 4 | La Possession | UT | 10 | « La hauteur maximale des constructions est fixée à 10 mètres » (Art. UT 10.2, PDF p.61 ; annexes 3,50 m) |
| 5 | Le Port | Uem | 18 | « En secteur Uem, la hauteur maximale des constructions est fixée 18 mètres » (Art. Ue 8, p.82 — seule règle de hauteur du chapitre Ue) |
| 6 | Le Port | Us | 18 | « La hauteur maximale des constructions est fixée 18 mètres » (Art. Us 8, p.122) |
| 7 | Le Port | 1AUm | 18 | « Dans les zones 1AUm et 1AUmut, la hauteur maximale des constructions est fixée 18 mètres » (Art. 1AU 8, p.146) |
| 8 | Sainte-Rose | Ud | 7 | « 10.2 - Règle générale. La hauteur maximale des constructions est fixée à 7 mètres. » (Art. UD 10, PDF p.41) |
| 9 | Sainte-Rose | 1AUto | 6 | « 10.2 - Règle générale. La hauteur maximale des constructions est fixée à 6 mètres. » (Art. AUto 10, PDF p.62) |
| 10 | Saint-Denis | Ui | 18 | « Seul H (18 m) donné ; hé non précisé » (Art. Ui.10, p.56) — *PDF hors cache, à confirmer sur pièce* |
| 11 | Saint-Denis | Uicm | 12 | idem, secteur Uicm (Art. Ui.10, p.56) — *à confirmer sur pièce* |
| 12 | Saint-Denis | Ua | 18 | « Seul H (18 m) donné » (Art. Ua.10, p.79) — *à confirmer sur pièce* |
| 13 | Saint-Denis | Uac | 18 | idem, secteur Uac (Art. Ua.10, p.79) — *à confirmer sur pièce* |
| 14 | Saint-Denis | Uad | 28 | idem, secteur Uad, le long du boulevard Sud (Art. Ua.10, p.79) — *à confirmer sur pièce* |
| 15 | Saint-Denis | Uva | 4 | « Seul H (4 m) donné » (Art. Uv.10, p.84) — *à confirmer sur pièce* |
| 16 | Saint-Denis | Uvl | 10 | idem (Art. Uv.10, p.84) — *à confirmer sur pièce* |
| 17 | Saint-Denis | Uvac | 10 | idem (Art. Uv.10, p.84) — *à confirmer sur pièce* |
| 18 | Saint-Denis | AUa | 10 | « Seul H (10 m) donné » (Art. AUa.10, p.108) — *à confirmer sur pièce* |

Dérivées/renvois qui suivront mécaniquement la décision de leur zone support :
Possession UTfr2, AUT (→ UT) ; Le Port 1AUem (→ Uem), 1AUs (→ Us) ; les zones AU de
Saint-Denis en renvoi le cas échéant.

Hors périmètre — faîtage explicitement nommé, forme `hf`-seul correcte (25) :
Étang-Salé AUt · PdP Ue, AUe · Possession UA (16 m au faîtage), UEm, AUEm ·
Petite-Île UCe, UDe · Saint-Pierre AUfGB, AUt1, AUt2 · Sainte-Marie UEa, UEc, UEm,
UEp, UR, UT, UTp, 1AUep · Sainte-Suzanne UE, 1AUe · Saint-Paul U1e, U1l, U1ec, U2e,
U3e, AU5e (« au faîtage » dans les notes ; PDF hors cache) · Saint-Denis Uip, Udop
(R+n = N m « au faîtage/acrotère »).

## B · LES 15 ZONES `a_verifier` (he ET hf) — dette de calibrage

**Pool servi (parcelles) : NON MESURABLE sans la base (interdite) — mesure en phase 4.**
Proxy fourni : polygones et surface (matrice m6 `reports/m6-audit/sections/1-3a-matrice-plu.csv`
et manifestes de zonage).

| Commune | Zone | Polygones | Surface (ha) | Motif du a_verifier (note YAML) |
|---|---|---|---|---|
| La Possession | UAv | 2 | 13 | Hauteur PAR ÎLOT (repérage graphique) |
| La Possession | AUAv | 2 | 16 | Renvoi → UAv (hauteur par îlot) |
| La Possession | AUBm | — | — | Hauteur « R+3 » en niveaux (friction v1 ; repli R+2 < R+3 réel : prudent) |
| Saint-Denis | Ud | — | — | AVAP/patrimoine — hauteur non exploitable en l'état |
| Saint-Denis | Udp | — | — | idem |
| Saint-Denis | Udo | — | — | idem |
| Saint-Denis | Uavap | 2 | 250 | AVAP — règlement propre hors PLU |
| Saint-Denis | Uat | — | — | idem famille patrimoine |
| Saint-Denis | Uu | — | — | idem |
| Saint-Denis | Uma | — | — | idem |
| Saint-Denis | Upi | — | — | idem |
| Saint-Denis | Upr | — | — | idem |
| Saint-Denis | AUx | — | — | idem |
| Saint-Paul | U1lec | — | — | Tout `a_verifier` (audit SP/SD : « calibré sans hauteur exploitable ») |
| Saint-Pierre | AUdma | — | — | idem |

(— : zone absente de la matrice m6 ou non extraite sans base ; à compléter en phase 4
avec les pools. Comportement moteur pour ces 15 : `a_verifier` n'est pas exploitable →
mode progressif = estimation générique, mode strict (Saint-Paul, Saint-Denis si strict) =
règles rendues telles quelles → capacité non calculable. Vérifier le mode par fichier au
moment de résorber la dette.)

## C · ZONES HABITAT-INTERDIT LOGÉES EN `zones_au_st` « pour la même raison que Petite-Île UF »

Inventaire des 19 st-listes de l'île. **14 zones** y sont pour la raison mesurée ce matin
(habitat interdit textuel + AUCUNE hauteur chiffrée → l'entrée calibrée retomberait en
générique constructible, mode progressif) :

| Commune | Zones | Fondement habitat-interdit |
|---|---|---|
| Le Port | Ue, Up, Uppp, Uv, 1AUe, 1AUv (6) | Art. Ue 1/2 p.79-80, Up 2 p.109, Uv 2 p.132 ; hauteurs non fixées (Ue 8 ne fixe que Uem ; Up/Uv « Non réglementé ») |
| Saint-Benoît | Ue, Up, Ut, AUe3, AUp1 (5) | Art. U 2 (5°-6°) p.5-7, AU 2 (2°) p.21 ; hauteurs par secteurs graphiques (non portables — arbitrage du matin) |
| Petite-Île | UF, UFcim, AUF (3) | Art. UF.1/2 p.66-68, AUF.1/2 p.116-118 ; Art. 10 sans aucun chiffre (schéma) — REVENUES en st ce matin sur mesure |

Cas limite NON compté : Les Avirons Ub5 (non aedificandi ravines/talweg — interdiction de
TOUTE construction, pas seulement l'habitat : le gel est la représentation exacte).
Toutes les autres entrées st de l'île sont de VRAIS gels juridiques (2AU/3AU à condition
d'ouverture, AUst/AUs à modification du PLU, AU0 fermées, Us Saint-Pierre gelée SCoT,
2AU à horizon 2031 Sainte-Marie/Sainte-Suzanne).

**Ces 14 zones sont le périmètre exact de migration si le v2 apporte le type « gel »
distinct + la priorité `habitat: interdit` sur le gate hauteur** (exception à la règle 10
du §4 du mandat-cadre, vérifiée sur pièces ce matin).

## D · LES 89 ZONES « EMPRISE NULL + % SOUSTRAIT GRAVÉ » — emprise implicite (100 − % soustrait)

Demande Vic : documenter, NE PAS APPLIQUER (décision produit touchant le moteur,
arbitrage séparé). Le % soustrait retenu est celui du TEXTE (le % perméable/espace
vert total), qui peut être supérieur au sous-minimum de pleine terre gravé dans
`pleine_terre_pct` (cas « X % perméable dont Y % pleine terre » du Tampon et de
Saint-Paul — la contrainte d'emprise vient de X, pas de Y).

| Commune | Zone | pleine_terre_pct gravé | % soustrait (texte) | Emprise implicite | Note |
|---|---|---|---|---|---|
| entre_deux | Ub | 40 | 40 | **60 %** | |
| entre_deux | Ub1 | 40 | 40 | **60 %** | |
| entre_deux | Ub2 | 40 | 40 | **60 %** | |
| entre_deux | AUb | 40 | 40 | **60 %** | |
| la_possession | UA | 35 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| la_possession | UAa | 35 | 35 | **65 %** | |
| la_possession | UApsfr2 | 40 | 40 | **60 %** | |
| la_possession | UB | 35 | 35 | **65 %** | |
| la_possession | UBa | 50 | 50 | **50 %** | |
| la_possession | UBb | 40 | 40 | **60 %** | |
| la_possession | UBc | 40 | 40 | **60 %** | |
| la_possession | UBpszc | 40 | 40 | **60 %** | |
| la_possession | UBpsfr2 | 40 | 40 | **60 %** | |
| la_possession | UT | 30 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| la_possession | UTfr2 | 40 | 40 | **60 %** | |
| la_possession | AUB | 35 | 35 | **65 %** | |
| la_possession | AUBb | 40 | 40 | **60 %** | |
| la_possession | AUBpsfr2 | 40 | 40 | **60 %** | |
| la_possession | AUT | 30 | 30 | **70 %** | |
| le_tampon | Ua | 15 | 20 | **80 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| le_tampon | Uav | 20 | 30 | **70 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| le_tampon | Ub | 25 | 35 | **65 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| le_tampon | Uc | 30 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| le_tampon | Ucm | 30 | 30 | **70 %** | |
| le_tampon | UCto | 30 | 30 | **70 %** | |
| le_tampon | UCtom | 30 | 30 | **70 %** | |
| le_tampon | Ud | 30 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| le_tampon | 1AUa | 15 | 15 | **85 %** | |
| le_tampon | 1AUb | 25 | 25 | **75 %** | |
| le_tampon | 1AUc | 30 | 30 | **70 %** | |
| le_tampon | 1AUto | 30 | 30 | **70 %** | |
| le_tampon | 1AUcto | 30 | 30 | **70 %** | |
| les_avirons | Ub | 30 | 30 | **70 %** | |
| les_avirons | Ub1 | 30 | 30 | **70 %** | |
| les_avirons | Ub2 | 30 | 30 | **70 %** | |
| les_avirons | Ub3 | 30 | 30 | **70 %** | |
| les_avirons | Ub4 | 30 | 30 | **70 %** | |
| les_avirons | Ue | 30 | 30 | **70 %** | |
| les_avirons | AUec | 30 | 30 | **70 %** | |
| les_avirons | AUt | 30 | 30 | **70 %** | |
| petite_ile | UB | 25 | 25 | **75 %** | |
| petite_ile | UZ | 10 | 10 | **90 %** | |
| saint_paul | U1a | 10 | 50 | **50 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| saint_paul | U1b | 30 | 30 | **70 %** | |
| saint_paul | U1c | 30 | 30 | **70 %** | |
| saint_paul | U1f | 30 | 30 | **70 %** | |
| saint_paul | U1g | 30 | 30 | **70 %** | |
| saint_paul | U1pso | 30 | 30 | **70 %** | |
| saint_paul | U2a | 30 | 50 | **50 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| saint_paul | U2b | 30 | 50 | **50 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| saint_paul | U2c | 50 | 50 | **50 %** | |
| saint_paul | U2d | 90 | 90 | **10 %** | |
| saint_paul | U2h | 40 | 50 | **50 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| saint_paul | U3a | 20 | 20 | **80 %** | |
| saint_paul | U3b | 30 | 30 | **70 %** | |
| saint_paul | U3c | 40 | 40 | **60 %** | |
| saint_paul | U3h | 40 | 40 | **60 %** | |
| saint_paul | U4a | 20 | 20 | **80 %** | |
| saint_paul | U4b | 30 | 30 | **70 %** | |
| saint_paul | U4c | 40 | 40 | **60 %** | |
| saint_paul | U5a | 20 | 20 | **80 %** | |
| saint_paul | U5b | 30 | 30 | **70 %** | |
| saint_paul | U5c | 40 | 40 | **60 %** | |
| saint_paul | U6a | 20 | 20 | **80 %** | |
| saint_paul | U6b | 30 | 30 | **70 %** | |
| saint_paul | U6c | 40 | 40 | **60 %** | |
| sainte_marie | UA | 20 | 20 | **80 %** | |
| sainte_marie | UAb | 20 | 30 | **70 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_marie | UAz | 20 | 30 | **70 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | UA | 20 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | UAv | 20 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | UAc | 20 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | UB | 30 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | UC | 40 | 40 | **60 %** | |
| sainte_suzanne | UC1 | 40 | 40 | **60 %** | |
| sainte_suzanne | 1AUa | 20 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | 1AUac | 20 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | 1AUb | 30 | 40 | **60 %** | (soustrait = % perméable total du texte, > sous-minimum pleine terre gravé) |
| sainte_suzanne | 1AUc | 40 | 40 | **60 %** | |
| salazie | UA | 10 | 10 | **90 %** | |
| salazie | UA1 | 10 | 10 | **90 %** | |
| salazie | UB | 20 | 20 | **80 %** | |
| salazie | UC | 25 | 25 | **75 %** | |
| salazie | UT | 25 | 25 | **75 %** | |
| salazie | AUa1 | 10 | 10 | **90 %** | |
| salazie | AUb | 20 | 20 | **80 %** | |
| salazie | AUc | 25 | 25 | **75 %** | |
| salazie | AUt | 25 | 25 | **75 %** | |
| salazie | AUe | 25 | 25 | **75 %** | |

Total : 89 zones.

Lecture : dans ces 89 zones, l'article « espaces libres » borne l'emprise bâtie à
l'emprise implicite ci-dessus alors que l'article « emprise » dit « non réglementée »
(null gravé, sourcé). Aujourd'hui le moteur ne consomme pas cette borne (l'emprise
effective vient des reculs + hypothèses). L'appliquer = décision produit (elle
durcirait la capacité sur les 89), arbitrage Vic séparé.
