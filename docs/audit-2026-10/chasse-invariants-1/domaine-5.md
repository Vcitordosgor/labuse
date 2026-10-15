# Domaine 5 — Marché, prix DVF et estimations

## Verdict (3 lignes)
Passées : **282 287 lignes `score_e`** (150 179 estimables) + **29 566 mutations DVF** + 2 359 médianes sectorielles, île entière.
Invariants vérifiés : 8. Violations : **2** (1 FAUX-CLIENT fenêtre non ancrée partout · 1 ROBUSTESSE marges en M€ sur grandes parcelles). L'identité comptable `marge = charge − prix` tient **à l'euro près sur 150 179 lignes, 0 écart**.
Resté muet : prix servis par l'`obsimmo`/`pige_prix_historique` (chemins Radar hors fiche, non échantillonnés), et la plausibilité par-commune fine des médianes neuf live (`neuf_vefa_commune`, recalcul live non rejoué).

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
|---|---|---|---|---|
| I1 | Pour toute estimation estimable, `marge_estimee = charge_supportable − prix_probable` (identité comptable exacte). | `SELECT count(*) FILTER (WHERE marge_estimee IS DISTINCT FROM (charge_supportable - prix_probable)) FROM score_e WHERE estimable;` | 150 179 | **0** |
| I2 | Une ligne NON estimable ne porte aucun chiffre (marge/charge/prix NULL). | `SELECT count(*) FILTER (WHERE marge_estimee IS NOT NULL OR charge_supportable IS NOT NULL OR prix_probable IS NOT NULL) FROM score_e WHERE NOT estimable;` | 132 108 | **0** |
| I3 | Une ligne estimable a tous ses champs renseignés (marge/charge/prix/niveau non NULL). | `SELECT count(*) FILTER (WHERE marge_estimee IS NULL OR charge_supportable IS NULL OR prix_probable IS NULL OR niveau_prix IS NULL) FROM score_e WHERE estimable;` | 150 179 | **0** |
| I4 | Toute estimation servie porte la mention « estim » (libellé court + détail). | `SELECT count(*) FILTER (WHERE estimable AND libelle_court NOT ILIKE '%estim%'), count(*) FILTER (WHERE detail NOT ILIKE '%estim%') FROM score_e;` | 282 287 | **0** |
| I5 | Toutes les lignes `score_e` portent le run servi (`q_v18`). | `SELECT run_label, count(*) FROM score_e GROUP BY run_label;` | 282 287 | **0** (tout `q_v18`) |
| I6 | Prix terrain implicite servi (`prix_probable / surface`) dans une fourchette plausible €/m². | `SELECT min, p01, p99, max de prix_probable/surface_m2 FROM score_e JOIN parcels WHERE estimable;` | 150 179 | **0** (64 → 5 290 €/m², p01=85 / p99=909) |
| I7 | Médianes DVF sectorielles servies dans une fourchette plausible par type. | `SELECT type_bien, min, med, max(mediane_prix_m2) FROM dvf_secteur_medianes GROUP BY type_bien;` | 2 359 | **0** (terrain 50–5 290, maison 64–9 882, appt 86–8 101) |
| I8 | La fenêtre DVF « N ans / 12 mois » est ancrée sur la DERNIÈRE date DVF réelle, pas sur `CURRENT_DATE` (L7 / VEFA-1). | voir Violation V1 (comparaison `CURRENT_DATE` vs `max(date_mutation)`) | 29 566 mutations | **V1 : 2 lecteurs non ancrés** |

Requêtes rejouables — toutes précédées de `SET statement_timeout='120s';` sur `psql -h localhost -U openclaw -d labuse`.

## Violations

### V1 — Fenêtre DVF du secteur/comparables fiche+dossier NON ancrée sur la dernière date réelle
- **Gravité : FAUX-CLIENT** (le client voit *moins* de ventes que la réalité ; le chiffre de volume est faux par défaut).
- **Attendu** : fenêtre bornée par `max(date_mutation) − N ans` (doctrine CHASSE-DONNEES-FIX-1 L7 et VEFA-1 : « calé sur la DERNIÈRE vente observée, pas sur l'horloge système »). La dernière vente DVF est le **2026-08-10** ; `CURRENT_DATE` = 2026-10-14 → **65 jours** d'avance de l'horloge sur les données.
- **Obtenu** : deux lecteurs servis utilisent encore `CURRENT_DATE - make_interval(...)`, donc leur bord ancien dérive et jette des ventes réelles du vieux bord de la fenêtre :
  - `src/labuse/flash/data.py:489` et `:515` — `_marche` (profil `DVF_SECTEUR_DOSSIER`, servi au bloc « Marché secteur » de la fiche, du Flash et du Dossier) : fenêtre 3 ans + rayon 500 m.
  - `src/labuse/marche_service.py:255` — `comparables` (profil `COMPARABLES_PREMIUM`, liste de comparables de la fiche/PDF) : même motif `CURRENT_DATE - make_interval(years => :ans)`.
  - idem `flash/data.py:602` et `:625` (`sp.date >= CURRENT_DATE - make_interval(months => :mois)`).
- **Mesure île entière (ventes Vente, 3 ans)** :
  ```
  n_current = 10 962   (CURRENT_DATE - 3 ans)
  n_ancre   = 12 030   (max(date_mutation) - 3 ans)
  → 1 068 ventes réelles (−8,9 %) jetées silencieusement du vieux bord.
  ```
  Exemple parcelle `97411000AK0182`, rayon 500 m / 3 ans, bâti ≥ 20 m² : **121 comparables servis** vs **129 réels** = 8 ventes perdues sur une seule fiche.
- **Cause probable** : la correction L7 n'a été appliquée qu'à l'Étude de zone (`ventes_12m`, couverte par `scripts/coherence/chasse_donnees.py:486 g24_ventes_12m_ancree`) et à la VEFA (`ingestion/dvf_marche.py:175 vefa_fenetre_predicat`, correctement ancré). Les lecteurs DVF génériques du bloc « marché secteur » et de la liste de comparables sont restés sur `CURRENT_DATE`. Le motif correct existe déjà dans la base (`vefa_fenetre_predicat` ancre sur `max(date_mutation)`) — il faut l'appliquer ici aussi.
- **Note** : le nombre affiché `n` est *interne-cohérent* (il vaut bien ce que la requête rend), mais la REQUÊTE sous-estime la réalité → invariant « n affiché = n réel dans la fenêtre annoncée » faux par l'ancrage, pas par un double comptage.

### V2 — Marges estimées en dizaines de M€ servies sur de très grandes parcelles
- **Gravité : ROBUSTESSE** (calcul arithmétiquement correct, mais chiffre servi non signifiant pour un promoteur ; aucune donnée fausse, aucune contradiction entre lecteurs).
- **Attendu** : une « marge estimée » lisible par un promoteur (ordre de grandeur d'une opération).
- **Obtenu** : `charge_supportable` va jusqu'à **183,9 M€** et `marge_estimee` de **−115,1 M€** à **+85,1 M€**. Ex. `97415000DK1169` (34,8 ha, SDP résiduelle 259 157 m²) → charge 183,9 M€, prix probable 249,2 M€, marge −65,3 M€. `97411000EI0085` (19,9 ha) → marge −115,1 M€.
- **Vérification** : l'identité I1 tient sur ces extrêmes (marge = charge − prix exact), et le €/m² terrain implicite reste plausible (623–1 022 €/m²). Ce sont de vraies parcelles agricoles/très grandes avec SDP résiduelle proportionnelle — pas un artefact de donnée. Le chiffre est honnête et porte « Estimé », mais sert une estimation économiquement vide (une opération de 35 ha n'est pas une promotion unique).
- **Cause probable** : `src/labuse/ingestion/score_e.py:152-155` applique le bilan à rebours sans garde-fou de surface/SDP maximale ni repli « échantillon de bilan générique inadapté » pour les parcelles hors domaine de promotion. Non bloquant, non trompeur, mais salissant.

## Non vérifié
- **Prix `obsimmo` / `pige_prix_historique`** (chemins Radar « Mon secteur » hors fiche) : non échantillonnés faute de budget ; les lecteurs fiche (score_e, sector_price, comparables, _marche) ont été couverts.
- **Plausibilité fine par commune des médianes NEUF live** (`neuf_vefa_commune`, recalculé live au build) : non rejoué commune par commune (recalcul live ~communes × requêtes). Seules les médianes terrain/bâti précalculées (`dvf_secteur_medianes`) ont été balayées (I7, OK).
- **`sector_price` « récente 5 ans »** : ancrée sur `ANNEE_REF = date.today().year` (`faisabilite/bilan.py:29`). Aujourd'hui sans perte (2026 présent en DVF), mais ancrage sur l'ANNÉE système, pas sur `max(annee DVF)` — même famille que V1, dormant tant que l'année courante a des ventes. Noté, non chiffré comme violation car perte = 0 au 2026-10-14.

## Gardes proposées
À ajouter dans `scripts/coherence/chasse_invariants.py`. G-I1 est la garde reine (identité comptable, zéro dépendance réseau) ; G-I8 attrape V1 et complète `g24` (qui ne teste que l'Étude de zone).

```python
import os, psycopg
PG = os.environ.get("PG_DSN", "host=localhost user=openclaw dbname=labuse")

def _q(sql, params=None):
    with psycopg.connect(PG) as c, c.cursor() as cur:
        cur.execute("SET statement_timeout='120s'")
        cur.execute(sql, params or ())
        return cur.fetchall()

def g_e_identite_comptable():
    """I1 — marge_estimee = charge_supportable - prix_probable à l'euro près (estimables)."""
    (n,), = _q("SELECT count(*) FROM score_e "
               "WHERE estimable AND marge_estimee IS DISTINCT FROM (charge_supportable - prix_probable)")
    return ("OK", "identité marge=charge-prix vérifiée sur tous les estimables") if n == 0 \
        else ("ECART", f"{n} lignes score_e violent marge=charge-prix")

def g_e_non_estimable_sans_chiffre():
    """I2 — une ligne non estimable ne porte aucun chiffre."""
    (n,), = _q("SELECT count(*) FROM score_e WHERE NOT estimable "
               "AND (marge_estimee IS NOT NULL OR charge_supportable IS NOT NULL OR prix_probable IS NOT NULL)")
    return ("OK", "aucune estimation chiffrée sur non-estimable") if n == 0 \
        else ("ECART", f"{n} non-estimables portent pourtant un chiffre")

def g_e_mention_estime():
    """I4 — toute estimation servie porte « estim » (libellé + détail)."""
    (c, d), = _q("SELECT count(*) FILTER (WHERE estimable AND libelle_court NOT ILIKE '%estim%'), "
                 "count(*) FILTER (WHERE detail NOT ILIKE '%estim%') FROM score_e")
    return ("OK", "mention Estimé présente partout") if c == 0 and d == 0 \
        else ("ECART", f"{c} libellés / {d} détails sans mention « estim »")

def g_dvf_medianes_plausibles():
    """I7 — médianes DVF sectorielles servies dans une fourchette de bon sens par type."""
    rows = _q("SELECT type_bien, min(mediane_prix_m2), max(mediane_prix_m2) FROM dvf_secteur_medianes "
              "WHERE mediane_prix_m2 IS NOT NULL GROUP BY type_bien")
    bornes = {"terrain": (20, 6000), "maison": (300, 12000), "appartement": (300, 12000)}
    mauvais = [(t, lo, hi) for (t, lo, hi) in rows
               if t in bornes and (lo < bornes[t][0] or hi > bornes[t][1])]
    return ("OK", "médianes DVF dans les fourchettes") if not mauvais \
        else ("ECART", f"médianes hors fourchette : {mauvais}")

def g_dvf_fenetre_ancree():
    """I8 (V1) — le bord ancien de la fenêtre DVF doit être ancré sur max(date_mutation), pas CURRENT_DATE.
    On compte les ventes jetées par l'horloge qui avance : si > 0, un lecteur sert moins que la réalité."""
    (n_cur, n_anc), = _q(
        "WITH mx AS (SELECT max(date_mutation) m FROM dvf_mutations) "
        "SELECT count(*) FILTER (WHERE date_mutation >= CURRENT_DATE - interval '3 years'), "
        "       count(*) FILTER (WHERE date_mutation >= (SELECT m FROM mx) - interval '3 years') "
        "FROM dvf_mutations WHERE nature_mutation ILIKE 'vente%%'")
    perdues = n_anc - n_cur
    return ("OK", "fenêtre DVF 3 ans calendaire == ancrée (horloge à jour)") if perdues == 0 \
        else ("ECART", f"{perdues} ventes jetées par la fenêtre CURRENT_DATE "
                       f"(flash/data.py:489,515 · marche_service.py:255) — ancrer sur max(date_mutation)")
```
