# Domaine 6 — Propriétaires et sociétés (SIRENE / BODACC / owner_enrichment)

## Verdict (3 lignes)
Passées au crible : 82 701 liens parcelle↔PM (12 605 SIREN distincts) + 461 570 lignes millésimées + 158 515 établissements SIRENE + 27 146 dirigeants + 674 procédures BODACC + 9 730 lignes owner_enrichment.
9 invariants vérifiés sur tout le stock. **2 violations FAUX-CLIENT** issues d'une MÊME cause (âge de dirigeant hors bornes servi tel quel) : 5 fiches §Identité affichent un âge aberrant (0, 4, 13, 114, **117 ans — prouvé live sur `/parcels/97411000BL0284`**) et 1 parcelle (97416000DW0432) entre dans l'outil « Successions à venir » avec `dirigeant_age=114`.
Resté muet : rien de structurel — toutes les requêtes ont tourné sur l'île entière sous `statement_timeout='120s'`.

## Invariants
| # | règle (une phrase FR) | requête/script | parcelles/lignes passées | violations |
|---|---|---|---|---|
| I1 | Tout SIREN servi à 9 chiffres respecte la clé de Luhn | script Python Luhn sur `parcelle_personne_morale`, `pm_proprietaires_millesimes`, `sirene_etablissements`, `pm_dirigeants`, `pm_dirigeant_gigogne.(siren,gerant_siren)`, `bodacc_procedures`, `owner_enrichment` (voir « Gardes ») | 9 733 + 10 536 + 143 897 + 9 337 + 586 + 511 + 193 + 9 730 SIREN distincts à 9 chiffres | **0** |
| I2 | Les seuls SIREN non-canoniques sont les pseudo-SIREN DGFiP « U… » (connus, jamais affichés comme identité) | même script, catégorie « autres formats » | 0 autre format ; pseudo-U = 2 871 / 3 980 distincts | 0 (attendu) |
| I3 | Une société `etat_administratif=C` n'est jamais servie « active » | `_pm_identite` force `actif=False` si C ; vérif croisée BODACC « radiation » vs owner `A` (SQL ci-dessous) | 551 SIREN état C ; 193 SIREN BODACC | **0** (déjà couvert par g10 de `chasse_donnees.py`) |
| I4 | `owner_enrichment.payload.etat_administratif` ∈ {A, C, NULL} et `date_mise_a_jour` jamais dans le futur | `SELECT etat GROUP BY` + filtre `>current_date` | 9 730 lignes | 0 |
| I5 | L'âge du dirigeant AÎNÉ servi en fiche (`_pm_dirigeant`) est cohérent : 18 ≤ âge ≤ 110 | SQL `DISTINCT ON (siren) … date_naissance ASC` + `age()` (voir « Gardes ») | 7 725 aînés servis | **5** (ages 0, 4, 13, 114, 117) |
| I6 | L'âge MAX servi dans `v_pm_propension_vendre` (filtre « 70+ » + bandes propension) est cohérent 18..110 | `SELECT … FROM v_pm_propension_vendre` | 8 311 SIREN avec âge | **5** (mêmes bogues : 3×<18, 2×>110) |
| I7 | Une parcelle en « Succession à venir » a dirigeant_age ≥ 70 OU sci_dormante=true | `parcel_veille_succession WHERE NOT sci_dormante AND (age IS NULL OR age<70)` | 6 256 parcelles | 0 (sens seuil OK) |
| I8 | …et le `dirigeant_age` stocké dans la veille succession est cohérent 18..110 | `parcel_veille_succession` bornes | 6 249 avec âge | **1** (age 114, parcelle 97416000DW0432) |
| I9 | Le lien idu↔PM est unique (PK), la PM a toujours source+url+millésime+date, pas de PM « fantôme » servie | SQL ci-dessous | 82 701 liens | 0 doublon / 0 sans source / **601 idu hors `parcels`** (non servis — voir Non vérifié) |

Requêtes rejouables clés :
```sql
SET statement_timeout='120s';
-- I5 : âge de l'aîné servi (requête EXACTE de app.py:_pm_dirigeant)
WITH aine AS (
  SELECT DISTINCT ON (siren) siren, date_naissance,
    date_part('year', age(to_date(date_naissance,'YYYY-MM')))::int AS age
  FROM pm_dirigeants
  WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL
  ORDER BY siren, date_naissance ASC)
SELECT siren, date_naissance, age FROM aine WHERE age<18 OR age>110;
-- I6
SELECT count(*) FILTER (WHERE age_max_dirigeant<18 OR age_max_dirigeant>110)
FROM v_pm_propension_vendre;
-- I8
SELECT parcelle_id, siren, dirigeant_age FROM parcel_veille_succession
WHERE dirigeant_age<18 OR dirigeant_age>110;
-- I9
SELECT count(*) FROM (SELECT idu FROM parcelle_personne_morale GROUP BY idu HAVING count(*)>1) t;  -- doublons
SELECT count(*) FROM parcelle_personne_morale
WHERE source IS NULL OR url_source IS NULL OR millesime IS NULL OR date_import IS NULL;             -- sans source
SELECT count(*) FROM parcelle_personne_morale pm
WHERE NOT EXISTS (SELECT 1 FROM parcels p WHERE p.idu = pm.idu);                                     -- fantômes
```

## Violations

### V1 — FAUX-CLIENT : âge de dirigeant aberrant servi en fiche §Identité
- **Gravité** : FAUX-CLIENT (l'utilisateur lit un chiffre faux).
- **idu(s) visibles** (parcelles servies, propriétaire PM) :
  - `97411000BL0284` + `97411000BL0392` (2 parcelles) — CAZAL SA, SIREN 310851209 → **« Dirigeant : GABRIEL BECHIR BALOUKY, 117 ans »** (né 1909-03). **Prouvé live** : `GET /parcels/97411000BL0284` renvoie `"dirigeant":{"nom":"GABRIEL BECHIR BALOUKY","age":117}`.
  - `97416000DW0432` — SCI MAKBOULE, SIREN 319252557 → « …IBRAHIM USUF MOHAMED, 114 ans » (né 1911-11).
  - `97401000AI1157` — LE TEVELAVE, SIREN 443982939 → âge **0** (né 2026-11, date dans le futur).
  - `97422000BX0880` — IMMO INVEST, SIREN 753659317 → âge **13** (né 2013-08).
  - `97422000CS0612` — ABA REAL ESTATE, SIREN 809309073 → âge **4** (né 2022-04).
- **Attendu** : un âge de dirigeant personne physique dans 18..110, ou aucune ligne « Dirigeant » si la donnée est manifestement fausse.
- **Obtenu** : 0, 4, 13, 114, 117 ans servis tels quels.
- **Cause probable** : `_pm_dirigeant` prend l'aîné par `ORDER BY date_naissance ASC LIMIT 1` et renvoie `int(r["age"])` **sans aucun garde-fou de bornes**. Les `date_naissance` INPI RNE contiennent des saisies erronées (1909, 1911) et des dates futures (2026-11) ; l'ordre ASC sélectionne justement la plus ancienne → l'aberration remonte systématiquement.
- **fichier:ligne** : `src/labuse/api/app.py:5787-5800` (`_pm_dirigeant`), rendu via `_pm_block` `src/labuse/api/app.py:5879`.

### V2 — FAUX-CLIENT : outil « Successions à venir » affiche un âge aberrant
- **Gravité** : FAUX-CLIENT.
- **idu** : `97416000DW0432` (SCI MAKBOULE) listée dans l'outil « Successions à venir » avec `dirigeant_age=114`.
- **Attendu** : âge cohérent ≤ 110 ; un dirigeant « 114 ans » ne devrait pas servir de justification « succession à venir » crédible.
- **Obtenu** : `parcel_veille_succession.dirigeant_age = 114`.
- **Cause probable** : MÊME racine que V1. La vue `v_pm_propension_vendre` fait `max(age …)` sans borne (`\sv v_pm_propension_vendre`) → `age_max_dirigeant=114` → `propension_band='tres_eleve'` ; le moteur Score V (`src/labuse/scoring/score_v.py:104-110`, `_load_dirigeant_ages`) lit cet âge sans clamp (le clamp `0<=age<=130` existe uniquement dans le FALLBACK `_age_from_enrichment` `score_v.py:129`, pas sur la source principale) puis l'écrit dans `parcel_veille_succession`.
- **fichier:ligne** : définition vue `v_pm_propension_vendre` (CASE sur `max(age)`, non borné) ; `src/labuse/scoring/score_v.py:104-110` (lecture sans clamp) ; filtre `70plus` servi en direct `src/labuse/api/app.py:1831-1839`.

Note : SIREN 310851209 (âge 117) N'entre PAS dans la veille succession (CAZAL = SA, exclue par la restriction de forme juridique de `veille_succession_eligible`, `score_v.py:371-385`) — l'exclusion de forme limite le dégât côté succession, mais PAS côté §Identité (V1) où toute PM affiche son dirigeant.

## Non vérifié
- **601 lignes `parcelle_personne_morale` dont l'idu est absent de `parcels`** : non servies en fiche (la fiche lit par idu depuis `parcels`), donc hors FAUX-CLIENT direct — je n'ai pas vérifié si un lecteur secondaire (export de liste par commune, acquisitions_recentes) les expose ; probable résidu de recadastrage q_v18. À confirmer par le domaine « parcelles disparues ».
- **Exactitude amont des `date_naissance` INPI** : je constate l'incohérence des bornes, je n'ai pas pu vérifier si 1909/1911 sont de vraies saisies INPI ou un défaut d'ingestion (source externe, non rejouable en lecture seule).
- **`pm_dirigeant_gigogne` âges (chaîne de gérance)** : les bornes ont été vérifiées sur la vue agrégée (I6) qui COALESCE direct+gigogne ; je n'ai pas isolé un décompte gigogne-seul.

## Gardes proposées
Prêtes pour `scripts/coherence/chasse_invariants.py` (fonction → `("OK"|"ECART", message)`, exit 1 si ECART) :

```python
def g_siren_luhn():
    """I1/I2 — tout SIREN servi à 9 chiffres respecte la clé de Luhn ; seul le pseudo-SIREN « U… » échappe."""
    def luhn9(s):
        tot = 0
        for i, ch in enumerate(s):
            d = int(ch)
            if i % 2 == 1:
                d *= 2
                if d > 9: d -= 9
            tot += d
        return tot % 10 == 0
    tables = [("parcelle_personne_morale","siren"),("pm_proprietaires_millesimes","siren"),
              ("sirene_etablissements","siren"),("pm_dirigeants","siren"),
              ("bodacc_procedures","siren"),("owner_enrichment","siren"),
              ("pm_dirigeant_gigogne","siren"),("pm_dirigeant_gigogne","gerant_siren")]
    bad = 0
    with _db() as cx:
        for t, c in tables:
            for (v,) in cx.execute(f"SELECT DISTINCT {c} FROM {t} WHERE {c} IS NOT NULL"):
                v = v.strip()
                if v.upper().startswith("U"):          # pseudo-SIREN DGFiP, jamais affiché comme identité
                    continue
                if not (len(v) == 9 and v.isdigit() and luhn9(v)):
                    bad += 1
    return ("OK", "tout SIREN 9c respecte Luhn") if not bad else ("ECART", f"{bad} SIREN invalides (Luhn/format)")

def g_age_dirigeant_borne():
    """I5/I6/I8 — aucun âge de dirigeant servi hors 18..110 (fiche §Identité, filtre 70+, veille succession)."""
    with _db() as cx:
        aine = cx.execute("""
            WITH aine AS (SELECT DISTINCT ON (siren) siren,
              date_part('year', age(to_date(date_naissance,'YYYY-MM')))::int AS age
              FROM pm_dirigeants WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL
              ORDER BY siren, date_naissance ASC)
            SELECT count(*) FROM aine WHERE age<18 OR age>110""").fetchone()[0]
        vue = cx.execute("SELECT count(*) FROM v_pm_propension_vendre "
                         "WHERE age_max_dirigeant<18 OR age_max_dirigeant>110").fetchone()[0]
        vs = cx.execute("SELECT count(*) FROM parcel_veille_succession "
                        "WHERE dirigeant_age<18 OR dirigeant_age>110").fetchone()[0]
    if aine or vue or vs:
        return "ECART", f"âges hors bornes — aîné fiche:{aine}, propension:{vue}, succession:{vs}"
    return "OK", "aucun âge de dirigeant servi hors 18..110"

def g_succession_seuil():
    """I7 — toute parcelle en « succession à venir » a dirigeant_age>=70 OU sci_dormante."""
    with _db() as cx:
        n = cx.execute("SELECT count(*) FROM parcel_veille_succession "
                       "WHERE sci_dormante=false AND (dirigeant_age IS NULL OR dirigeant_age<70)").fetchone()[0]
    return ("OK", "succession ⇒ (âge≥70 ∨ SCI dormante)") if not n else ("ECART", f"{n} succession sous seuil sans SCI dormante")

def g_pm_source_unique():
    """I9 — lien idu↔PM unique, toujours sourcé/daté (pas de PM servie sans source)."""
    with _db() as cx:
        dbl = cx.execute("SELECT count(*) FROM (SELECT idu FROM parcelle_personne_morale "
                         "GROUP BY idu HAVING count(*)>1) t").fetchone()[0]
        nos = cx.execute("SELECT count(*) FROM parcelle_personne_morale "
                         "WHERE source IS NULL OR url_source IS NULL OR millesime IS NULL OR date_import IS NULL").fetchone()[0]
    if dbl or nos:
        return "ECART", f"PM : doublons idu={dbl}, sans source/date={nos}"
    return "OK", "PM : idu unique, toujours sourcée+datée"
```
Note : la cessée↔active (I3) et la fraîcheur BODACC sont déjà couvertes par `g10_sirene_etat` et `g11_bodacc_fraicheur` de `scripts/coherence/chasse_donnees.py` — ne pas dupliquer.
