# Calibration DESTINATIONS par commune (DESTINATIONS-1)

Un YAML par commune : `<insee>_<slug>.yaml` (ex. `97411_saint_denis.yaml`), lu par le
module unique `src/labuse/plu/destinations.py`. Une commune sans fichier ici est
« non calibrée » (les surfaces l'affichent, jamais un silence). `rnu.yaml` porte la
calibration du règlement national d'urbanisme (Saint-Philippe).

Référentiel : art. R151-27 / R151-28 du code de l'urbanisme, version en vigueur depuis
le 01/07/2023 (décret n° 2023-195) — 5 destinations, 23 sous-destinations (slugs dans
`destinations.py`).

## Schéma

```yaml
meta:
  insee: "97411"
  commune: "Saint-Denis"
  document: "97411_reglement_20260805.pdf"      # pièce écrite lue (nom GPU)
  document_gpu: "97411_PLU_20260805"            # idurba du document GPU au calibrage
  gpu_doc_id: "…"                               # id API GPU (retélécharger la pièce)
  url: "https://data.geopf.fr/annexes/gpu/documents/DU_97411/…/97411_reglement_20260805.pdf"
  md5: "…"                                      # empreinte du PDF lu (garde-fou)
  millesime: "2026-08-05"
  pages_total: 154
  lu_le: "2026-09-03"
  structure: "texte court : comment le règlement organise interdits/autorisés"

zones:
  UA:
    silence: autorise            # ce que vaut le SILENCE dans cette zone :
    silence_src: "Art. UA1…"     #   lu dans la STRUCTURE du règlement, cité (jamais déduit)
    sous_destinations:
      industrie:
        statut: interdit                    # autorise | interdit | sous_condition
        article: "UA1"
        page_pdf: 10                        # page du PDF cité (lien vérifiable #page=N)
        citation: "« … » (mot à mot si utile)"
      artisanat_commerce_detail:
        statut: sous_condition
        condition: "surface de vente limitée à 300 m²"
        seuil_m2: 300
        seuil_type: surface_vente           # surface_vente | surface_plancher | emprise_sol
        article: "UA2"
        page_pdf: 11
  1AUa:
    renvoi: UA                              # seulement si le règlement le DIT
    renvoi_src: "caractère de zone, p. 60 : « se reporter au règlement de la zone UA »"
  N:
    etat: non_lu                            # zone identifiée mais pas encore lue
```

Doctrine (identique aux `plu_<slug>.yaml` de constructibilité) :

- chaque valeur cite **article + page_pdf** du document `meta.document` ; rien de déduit ;
- une sous-destination absente de `sous_destinations:` = **non mentionnée** par le
  règlement → le verdict effectif découle de `silence:` (autorisé/interdit), lui-même
  cité ; distinct de `non_lu` (pas encore lu) ;
- les règlements antérieurs à la nomenclature R151-28 parlent en « occupations et
  utilisations du sol » : on mappe UNIQUEMENT ce que le texte porte (citation à l'appui),
  le reste demeure non mentionné ;
- verrou CDAC (L752-1 code de commerce, > 1 000 m² de surface de vente) : règle statique
  portée par le module, PAS par ces fichiers.
