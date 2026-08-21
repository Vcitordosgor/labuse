# M129 — DETTE : contenance cadastrale non persistée

> **Créée le** 2026-08-21 (mandat M129 bis, arbitrage Vic §1).
> **Statut : OUVERTE — relève d'un mandat ingestion + migration séparé, hors périmètre M129.**

## Le fait

La table `parcels` ne stocke que `surface_m2 = ST_Area(ST_Transform(geom, 2975))` — l'**aire
géométrique** du polygone ingéré (`src/labuse/ingestion/cadastre_ingest.py:36-46`). Ce n'est **pas**
la **contenance cadastrale** officielle (la superficie certifiée du relevé de propriété / de l'acte).

Or la contenance officielle **est disponible dans la source** Etalab et déjà extraite au parsing :

    src/labuse/ingestion/cadastre_bulk.py:54   "contenance": p.get("contenance"),

…mais elle n'est **pas persistée** (aucune colonne `contenance` dans `parcels` ; grep
`information_schema` → 0).

## Conséquence traitée en M129

Le CERFA du pré-dossier PC ne remplit **plus** la superficie (`T2T_superficie`, `D5T_total`) —
arbitrage Vic : un champ faux est pire qu'un champ vide sur un formulaire qui fait *certifier* la
superficie par le déposant. Le LISEZMOI renvoie le pétitionnaire au relevé de propriété /
cadastre.gouv.fr.

## Résolution attendue (mandat séparé)

Persister la `contenance` de la source (colonne `parcels.contenance int`, migration + reprise
d'ingestion `cadastre_ingest` / `cadastre_bulk`), puis servir cette valeur officielle au CERFA
(`T2T_superficie` = contenance, **Sourcé**). Tant que ce mandat n'est pas fait, la superficie reste
**non servie** — pas estimée.
