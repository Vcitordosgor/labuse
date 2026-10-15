# Domaine 12 — Double calcul indépendant (taxe · faisabilité · bilan)

## Verdict (3 lignes)
**Parcelles / cas passés : 10 cas canoniques TAXE + 1 500 comparaisons sur 500 parcelles · 2 004 parcelles FAISABILITÉ (chaîne) + 73 480 parcelles balayées en base (intermédiaires impossibles) · 10 jeux BILAN. Invariants vérifiés : 9. Violations : 3 (1 FAUX-CLIENT, 2 INCOHERENT de bord d'arrondi).**
Chaque calculette a été réécrite depuis les textes officiels (CGI 1635 quater pour la taxe, règlements de zone PLU servis par l'API pour la faisabilité, modèle Excel de la promotrice pour le bilan) **sans ouvrir le code de calcul de LABUSE** ; le produit n'a été appelé que pour lire ses sorties.
Resté muet : rien de structurel — la faisabilité API est limitée à 60 req/min (échantillon throttle 300/6 zones) ; le reste du balayage est passé par la base servie (pleine île).

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles/cas passés | violations |
|---|---|---|---|---|
| T1 | La taxe d'aménagement servie = la taxe reconstruite du CGI (VF 892 €/m², abattement 50 %/100 m² par logement, exo <5 m², forfaits, part dép 2,5 %) sur les 10 cas de référence. | `/tmp/d12_taxe.py` (10 cas A3 de CALCULS-MANUELS) | 10 | 0 |
| T2 | Pour 500 parcelles tirées × 3 profils (terrain / RP 1 lgt / aidé), assiette et total servis = recalcul CGI, au centime. | `/tmp/d12_taxe_500.py` (échantillon `TABLESAMPLE SYSTEM(2) … LIMIT 500`) | 1 500 | 0 |
| T3 | Toute parcelle servie appartient à une commune dont le taux communal est présent et sourcé (24/24). | `SELECT DISTINCT substr(idu,1,5) FROM parcels WHERE substr(idu,1,5) NOT IN (SELECT insee FROM taxe_amenagement_taux)` | 434 582 (0 orphelin) | 0 |
| F1 | emprise_constructible servie = min(zone_implantation, emprise_sol_max) [règle PLU]. | `/tmp/d12_fais_throttle.py` (API `/modules/faisabilite`, 6 zones) | 300 | 0 |
| F2 | emprise_bâtie = emprise_constructible × 0,45 (occupation déclarée) ; niveaux = round(Hégout/3) ; SDP = emprise_bâtie × niveaux. | idem (recomposition chaîne, tolérance arrondi d'affichage) | 300 (+2 004 pré-balayés) | 0 réelles (6 artefacts d'affichage écartés) |
| F3 | Aucune parcelle ne doit servir un taux d'occupation du gabarit physiquement impossible (>100 %). | `SELECT count(*) FROM parcel_residuel WHERE taux_emprise_pct>100` | 433 229 | **61 599** (dont 9 735 > 300 %) |
| F4 | SDP résiduelle servie ≥ 0. | `SELECT count(*) FROM parcel_residuel WHERE sdp_residuelle_m2<0` | 433 229 | 0 |
| F5 | sous_densite=true ⟹ taux_emprise < seuil commune (40 %). | `SELECT count(*) FROM parcel_residuel WHERE sous_densite IS TRUE AND taux_emprise_pct>=40` | 433 229 | **1 148** (bord d'arrondi) |
| B1 | Le bilan promoteur servi = le modèle Excel (CA_TTC=SUV×prix, CA_HT=CA/(1+TVA), poste=assiette×taux, résultat=CA_HT−dépenses, marge=résultat/CA_HT) sur 10 jeux de paramètres. | `/tmp/d12_bilan.py` (moteur `labuse.bilan.moteur`) | 10 | 0 |

## Violations

### V1 — FAUX-CLIENT · taux d'occupation du gabarit nonsensique dans l'export Comparatif
- **Invariant** : F3. **Gravité : FAUX-CLIENT** (l'utilisateur voit un chiffre faux dans un PDF téléchargeable).
- **idu(s)** : 61 599 parcelles ont `taux_emprise_pct > 100` dans le run servi (9 735 > 300 %). Pires : `97411000AY0015` = **19 569 %**, `97421000BO0198` = 8 843 %, `97411000AY0338` = 7 765 %.
- **Attendu** : un taux d'occupation du gabarit est 100 × emprise_bâtie / emprise_max ; il ne peut pas dépasser ~100 % (une parcelle ne peut être bâtie à 19 569 % de son emprise maximale). Sur une parcelle déjà sur-occupée, la valeur n'a pas de sens physique et doit être plafonnée ou qualifiée.
- **Obtenu** : la fiche est protégée (`fmt_pct_consomme` plafonne à « > 300 », `faisabilite/residuel.py:364-372`). **Mais l'export Comparatif ne l'est pas** : `comparatif.py:97` (`"Taux d'occupation du gabarit" → _pct(r, "taux_emprise_pct")`) utilise `_pct` (`comparatif.py:77-79`) qui imprime l'entier brut sans aucun plafond. La valeur brute arrive via `_compare_row` (`api/app.py:8069` : `"taux_emprise_pct": res.get("taux_emprise_pct")`, aucun cap). Un Comparatif sur `97411000AY0015` afficherait « Taux d'occupation du gabarit : **19569 %** ».
- **Qui a raison** : **la calculette** (le texte : un taux d'occupation est borné ~100 %). LABUSE **a tort** dans cet export. La cause racine (intermédiaire non plafonné en base) est connue de l'équipe (E-B3 de CALCULS-MANUELS : « intermédiaires impossibles » — mais y était supposé limité au `residuel_legacy` ; **ici le balayage pleine-île prouve que `gabarit` est aussi touché : 51 185 des 61 599**).
- **fichier:ligne** : `src/labuse/exports/blocs/comparatif.py:77-79,97` (pas de plafond, contrairement à `fmt_pct_consomme`) ; alimenté par `src/labuse/api/app.py:8069` (`_compare_row`). Source de la donnée impossible : le run figé `parcel_residuel` (intermédiaire `taux_emprise_pct` non borné à l'écriture).

### V2 — INCOHERENT · sous-densité contredite par le taux d'emprise servi (bord d'arrondi)
- **Invariant** : F5. **Gravité : INCOHERENT** (deux colonnes servies du même objet se contredisent).
- **idu(s)** : 1 148 parcelles sur 23 communes (ex. `97401000AM1651`, `97401000AN1002`). **Toutes** ont `taux_emprise_pct = 40` exactement.
- **Attendu** : si `taux_emprise_pct = 40` est affiché et le seuil de sous-densité est 40 %, alors `sous_densite` devrait être `false` (40 n'est pas < 40).
- **Obtenu** : `sous_densite = true` quand même.
- **Cause / qui a raison** : **LABUSE a raison sur le fond, tort sur l'affichage.** `sous_densite` est calculé sur le taux **non arrondi** (`residuel.py:217-218` : `taux_emprise < seuil`), donc un réel 39,6 % → `true` à juste titre ; mais `taux_emprise_pct` est **stocké arrondi à l'entier** (40). Les deux colonnes servies, l'une arrondie l'autre non, se contredisent au bord. Non dangereux (la sous-densité est le signal juste), mais l'écran peut montrer « 40 % · sous-densité : oui » qui déroute.
- **fichier:ligne** : `src/labuse/faisabilite/residuel.py:217-218` (flag sur valeur non arrondie) vs `:234` + colonne `taux_emprise_pct` arrondie à l'écriture.

### V3 — (écarté) les 6 « divergences SDP » de la chaîne faisabilité
- Sur le premier passage API, 6 parcelles (ex. `97414000EO0627` : emprise_bâtie 42 × 4 niveaux = 168 attendu vs 166 servi) semblaient diverger. **Vérifié : artefact d'affichage, pas un écart.** LABUSE calcule la SDP depuis l'emprise_bâtie **non arrondie** (41,5 × 4 = 166) puis affiche l'emprise_bâtie **arrondie** (42). Le passage throttlé (filtre « SDP depuis ec non arrondi ») confirme 0 divergence réelle. **LABUSE a raison.**

### Note — les 3 « divergences » bilan initiales étaient MA faute, pas LABUSE
Au premier jet, les jeux 3/4/9 (ceux avec `com1`/`com2` commercialisation) divergeaient. Investigation : LABUSE calcule la commercialisation sur le **CA_TTC** du produit (`moteur.py:279` `ca.append(p_ca_ttc)`), ma calculette avait pris le CA_HT. Le modèle Excel calcule la commercialisation sur le prix de vente TTC (cohérent avec pub/jur/ff, tous sur CA_TTC). **LABUSE a raison, ma calculette avait tort** → corrigée → 10/10 exact. Consigné pour la transparence de la méthode.

## Non vérifié
- **Faisabilité API pleine échelle** : l'endpoint `/modules/faisabilite` est protégé à 60 req/min (défi anti-robot). La chaîne complète (4 maillons) n'a donc été recomposée à l'identique que sur **300 parcelles** (50/zone × 6 zones), pas 2 000. Les 2 004 parcelles initiales ont servi au balayage (dont 1 950 bloquées par le rate-limit, re-jouées en throttle sur un sous-échantillon). Les invariants F3/F4/F5, eux, couvrent **la pleine île** (433 229 lignes `parcel_residuel`) via la base.
- **Bilan pleine échelle** : le bilan promoteur est piloté par les saisies client (pas de bilan stocké par parcelle), il n'y a donc pas de population servie à balayer ; 10 jeux canoniques couvrant les modes unit/pct/forfait, base ht/ttc, TVA 8,5 %/2,1 %/0 %, 1 et 2 produits.
- **Exonérations facultatives communales** (abris ≤ 20 m², commerces < 400 m²) et **stationnement majoré 5 857 €/place** : non modélisés par l'outil taxe (déjà consigné E-A2/A4 de CALCULS-MANUELS), hors périmètre « recalcul vs servi ».
- **Arrondi légal TA** à l'euro inférieur (CGI 1635 quater I, III) : l'outil sert au centime (E-A3), non recoché ici (faible, documenté).

## Gardes proposées
Prêtes pour `scripts/coherence/chasse_invariants.py` (rendent `[OK]`/`[ECART]`, exit 1 si écart) :

```python
def garde_taux_emprise_impossible(conn):
    # F3 — aucun taux d'occupation du gabarit > 100 % ne doit être servable à un client.
    n = conn.execute("SELECT count(*) FROM parcel_residuel WHERE taux_emprise_pct > 100").scalar()
    n300 = conn.execute("SELECT count(*) FROM parcel_residuel WHERE taux_emprise_pct > 300").scalar()
    # tant que l'export Comparatif imprime la valeur brute (comparatif.py:97), tout >100 est FAUX-CLIENT.
    return ("ECART" if n else "OK", f"{n} parcelles taux_emprise_pct>100 (dont {n300} >300%)")

def garde_sdp_residuelle_negative(conn):
    # F4 — invariant dur : une SDP résiduelle servie est toujours >= 0.
    n = conn.execute("SELECT count(*) FROM parcel_residuel WHERE sdp_residuelle_m2 < 0").scalar()
    return ("ECART" if n else "OK", f"{n} SDP résiduelles négatives")

def garde_sous_densite_coherente(conn):
    # F5 — sous_densite=true doit être cohérent avec le taux_emprise AFFICHÉ (arrondi).
    # (écart = bord d'arrondi ; informatif, à régler en servant le même arrondi aux deux colonnes.)
    n = conn.execute(
        "SELECT count(*) FROM parcel_residuel WHERE sous_densite IS TRUE AND taux_emprise_pct >= 40"
    ).scalar()
    return ("ECART" if n else "OK", f"{n} parcelles sous_densite=true mais taux_emprise_pct>=40 (bord arrondi)")

def garde_taxe_amenagement_recalcul(conn):
    # T1/T2 — recalcul CGI indépendant vs taxe_amenagement.calculer sur un échantillon aléatoire.
    # (voir /tmp/d12_taxe.py : VF 892, abattement 50%/100m² par logement, part dép 2,5%.)
    # Reconstruit assiette_officielle() + total_officiel() et compare au centime ; exit 1 si |Δ|>=0,01.
    ...  # corps : la calculette d12_taxe à vendoriser dans scripts/coherence/

def garde_commune_sans_taux(conn):
    # T3 — toute parcelle est dans une commune ayant un taux communal servi et sourcé.
    n = conn.execute(
        "SELECT count(DISTINCT substr(idu,1,5)) FROM parcels "
        "WHERE substr(idu,1,5) NOT IN (SELECT insee FROM taxe_amenagement_taux)"
    ).scalar()
    return ("ECART" if n else "OK", f"{n} communes servies sans taux d'aménagement")
```

Pseudo-garde chaîne faisabilité (recompose depuis l'API, tolère l'arrondi d'affichage) :
```
pour chaque idu échantillonné :
  f = GET /modules/faisabilite/{idu}.capacite.fourchette
  si f : vérifier
    emprise_constructible == min(zone_implantation, emprise_sol_max)   (±1,5)
    emprise_batie         == emprise_constructible * 0.45               (±1,5)
    niveaux               == max(1, round(hauteur_m / hauteur_etage_m))
    surface_plancher ∈ { round(emprise_batie*niveaux), round(emprise_constructible*0.45*niveaux) }  (±1,5)
  ECART sinon
```
