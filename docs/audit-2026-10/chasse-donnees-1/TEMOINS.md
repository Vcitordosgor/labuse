# CHASSE-DONNEES-1 — Lot B : 40 parcelles témoins

Base : `labuse` locale (lecture seule), run servi **q_v18** (scoring) / **q_v18_sources** (cascade) / **run_seq 15** (résiduel). Requêtes rejouables en fin de document (section « Requêtes », numérotées Q1…Q24). Date : 2026-10-12.

Chaque témoin est choisi **pour mettre la donnée en difficulté** ; la colonne « raison/preuve » cite la requête (Qn) qui l'a trouvé et le résultat court.

## Les 40 témoins

| # | IDU | commune | cas | raison/preuve courte |
|---|-----|---------|-----|----------------------|
| 1 | 97409000AB0993 | Saint-André | 1. nouvelle parcelle (cadastre octobre) | Q1 : dans `_cad_sm1_nouvelles` (2 919 nouvelles), `parcels.created_at=2026-10-11` ; la plus grosse : contenance 664 663 m² |
| 2 | 97411000CR0650 | Saint-Denis | 1. nouvelle parcelle (cadastre octobre) | Q1 : `_cad_sm1_nouvelles`, created_at 2026-10-11, contenance 459 920 m² |
| 3 | 97418000AV2114 | Sainte-Marie | 2. disparue mais encore référencée | Q2 : `cadastre_disparue_le=2026-09-01` ET présente dans `pipeline_entries` (CRM) — la fiche doit l'ouvrir sans mentir |
| 4 | 97411000AE0013 | Saint-Denis | 2. disparue mais encore référencée | Q2 : disparue 2026-09-01 ET référencée 2 fois dans `projet_parcelles` |
| 5 | 97416000DV0285 | Saint-Pierre | 3. surface incertaine (DV0285) **+ 18. ORT** | Q3 : contenance_m2=**1** vs dessin ST_Area=**117 505 m²** (acte absurde, le dessin fait foi ?) ; Q14 : Saint-Pierre = ORT ACV signée 2021-11-19 |
| 6 | 97415000CW0658 | Saint-Paul | 4. contenance ≠ dessin > 5 % | Q3 : contenance 25 633 vs dessin 27 156 m² = écart **+5,9 %** |
| 7 | 97420000BC9999 | Sainte-Suzanne | 5. sans contenance | Q4 : `contenance_m2 IS NULL`, numéro 9999 (parcelle fictive/arpentage ?), dessin 600 m² |
| 8 | 97416000DX8001 | Saint-Pierre | 5. sans contenance | Q4 : `contenance_m2 IS NULL`, dessin 49 m² (numéro 8001 = domaine non cadastré ?) |
| 9 | 97415000BZ0007 | Saint-Paul | 6. à cheval sur deux zones PLU | Q5 : intersections pondérées `plu_gpu_zone` → **Usdu 73 % / N 27 %** — quelle zone servie ? |
| 10 | 97415000BZ0005 | Saint-Paul | 6. à cheval sur deux zones PLU | Q5 : **A 70 % / N 28 %** — deux zones non constructibles différentes |
| 11 | 97410000AB0212 | Saint-Benoît | 7. zone AU fermée | Q6 : `parcel_au_statut.classe='declasse_au_fermee'`, zone AUp1 (456 parcelles dans ce cas) |
| 12 | 97409000AK0804 | Saint-André | 8. zone rouge partielle PPR (AK0804) | Q7 : 5 homonymes AK0804 ; celle-ci touche PPR INTERDICTION sur 3 362/28 258 m² (12 %) ; q_v18 la sert **bande A, SDP 34 223 m²** (recalcul PPR-PARTIEL-A) |
| 13 | 97409000AY0786 | Saint-André | 8bis. zone rouge partielle (témoin PPR-PARTIEL-1) | Q7 : rouge 145/4 877 m² (3 %) ; était servie à 0 avant q_v18, maintenant bande A SDP 2 302 — vérifier la cohérence du badge |
| 14 | 97415000AB0001 | Saint-Paul | 9. PPR multiple | Q8 : touche **2 plans** (PPR inondation/mvt de terrain B2+B3 **et** PPRL littoral B+R+Rrtc) |
| 15 | 97415000AB0899 | Saint-Paul | 9. PPR multiple | Q8 : 6 zonages superposés dont R1/Rg (interdiction) + PPRL R/Rrtc |
| 16 | 97417000BN0002 | Saint-Philippe | 10. RNU | Q9 : `sudocuh_procedures` insee **97417** (pas 97424=Cilaos) : du_opposable=RNU, code_etat 93 ; zones GPU seulement en `plu_gpu_zone__archive_m40` |
| 17 | 97409000AB0521 | Saint-André | 11. GPU dépublié | Q10 : Saint-André listée dans `config/plu_depublies.yaml` (CHASSE-FIX-1 C27) ; zone UB servie = dernier état connu, note dépublication attendue |
| 18 | 97413000AC0009 | Saint-Leu | 11. GPU dépublié | Q10 : Saint-Leu dans `plu_depublies.yaml` ; zone UD servie du dernier état connu |
| 19 | 97411000AW0692 | Saint-Denis | 12. propriétaire SCI avec dirigeant connu | Q11 : `parcelle_personne_morale` SCI ALOE (siren 913037362) → `pm_dirigeants` TECHER Christian Philippe (rôle 30) |
| 20 | 97411000DR0219 | Saint-Denis | 12. propriétaire SCI avec dirigeant connu | Q11 : SCI HOSSEIN ROY (414234526), **2 dirigeants** (HOSSEIN ZADEH Gilles, ROY Jean-Philippe) |
| 21 | 97424000AL1244 | Cilaos | 13. propriétaire absent | Q12 : aucune ligne `parcelle_personne_morale` (propriétaire physique non diffusé = aucune info servie) |
| 22 | 97411000ID0002 | Saint-Denis | 14. copropriété | Q13 : `rnic_coproprietes` « LES JARDINS DE LA ROSERAIE », **363 lots habitation** |
| 23 | 97409000AS1381 | Saint-André | 14. copropriété | Q13 : RNIC « LE DOMAINE DE CHAMP BORNE », 80 lots |
| 24 | 97402000AE0513 | Bras-Panon | 15. permis annulé **+ 18. ORT** | Q15 : PC 97440212A0057, `raw->>'etat'='4'` (ETAT_DAU=4 = annulé, cf. zone.py:664) ; Q14 : Bras-Panon = ORT PVD signée 2021-10-05 |
| 25 | 97408000AP1582 | La Possession | 16. DVF récente ET multi-parcelles | Q16 : mutation 2025-1273171 du **2025-12-31** (<12 mois), 482 000 €, **2 parcelles** (AP1582+AP1584) |
| 26 | 97414000CH1970 | Saint-Louis | 16. DVF récente ET multi-parcelles | Q16 : mutation 2025-1273179 du 2025-12-31, 123 000 €, 2 parcelles (CH1970+CH1971) — ventilation du prix impossible |
| 27 | 97411000HM0136 | Saint-Denis | 17. QPV | Q17 : `ST_Within` du QPV `spatial_layers kind='qpv'` « Moufia Les Hauts » |
| 28 | 97411000AC0069 | Saint-Denis | 19. littoral | Q18 : intersecte `kind='cinquante_pas'` « Limite haute des 50 pas (historique) » |
| 29 | 97407000AO1886 | Le Port | 20. sans adresse BAN | Q19 : aucune ligne dans `adresse_parcelles` NI `parcel_adresse` |
| 30 | 97411000AB0318 | Saint-Denis | 21. bâti dense (>70 %) | Q20 : emprise bâtie (kind='batiment') = **91 %** de la parcelle (271 m²) |
| 31 | 97411000AB0061 | Saint-Denis | 21. bâti dense (>70 %) | Q20 : emprise bâtie **93 %** (792 m²) — SDP résiduelle attendue ~0 |
| 32 | 97411000BK0101 | Saint-Denis | 22. terrain nu en zone U | Q21 : zone_filtre UD, contenance 574 m², **aucun** bâtiment (`batiment` + `batiment_cosia`) n'intersecte |
| 33 | 97411000BZ1065 | Saint-Denis | 23. suivie par une veille | Q22 : présente dans `watched_parcels` (2026-07-22) — aussi témoin prix connu (PRIX-SORTIE-1 : 4 275 €/m²) |
| 34 | 97414000CV0938 | Saint-Louis | 24. dans un projet/CRM | Q22 : `pipeline_entries` status=reperee (2026-07-12), parcelle vivante |
| 35 | 97423000AB1908 | Les Trois-Bassins | 25. Flash test | Q23 : **4 commandes** `flash_commandes` (en_attente + 3 generee, juillet 2026) |
| 36 | 97415000CW1073 | Saint-Paul | 25. Flash test | Q23 : flash generee 2026-08-23 |
| 37 | 97410000AC0157 | Saint-Benoît | 26. servie à 0 terrain_exigu + PPR rouge | Q24 : `parcel_residuel.cause='terrain_exigu'`, bande 0 q_v18, 31 572 m² dont seulement 1 518 m² en PPR INTERDICTION → candidat badge « hors zone rouge » / vérifier pourquoi exigu |
| 38 | 97413000CA0243 | Saint-Leu | 27. bande A (top score) | Q25 : q_v18 bande **A**, score **100** — et dans une commune GPU dépublié (stress combiné) |
| 39 | 97413000CX0730 | Saint-Leu | 27. bande D | Q25 : q_v18 bande **D**, score 10 |
| 40 | 97416000ES2238 | Saint-Pierre | 28. DPE récent rattaché | Q26 : `dpe_records.parcelle_idu` renseigné, étiquette E, `date_etablissement=2026-09-02` (le plus frais de la base) |
| 41* | 97409000BO0383 | Saint-André | 28bis. procédure BODACC sur le propriétaire | Q27 : `parcelle_personne_morale` SCI FREYNEAU (820034122) → `bodacc_procedures` « Autre jugement et ordonnance » du **2026-08-21** |

\* 41 lignes pour 40 parcelles exigées : les doubles emplois (#5 = DV0285+ORT, #24 = permis annulé+ORT) couvrent 2 cas chacun ; le mandat demande 1-2 parcelles par cas, tous les 28 cas sont couverts.

### Notes de chasse (ce que les témoins ont déjà révélé)

- **#5 (97416000DV0285)** : contenance cadastrale = 1 m² pour un dessin de 117 505 m². CONTENANCE-1 fait foi à la contenance → l'écran dirait 1 m². À surveiller en lot C.
- **#12/#13 (AK0804/AY0786)** : les deux témoins PPR-partiel historiques sont passés de bande 0 à **bande A** en q_v18 (recalcul PPR-PARTIEL-A visiblement actif) ; la cause/le badge doivent suivre.
- **Permis annulés orphelins** : les premiers PC etat=4 trouvés (97411000IC0047, 97402000AB0309) référencent des IDU **absents de `parcels`** — un angle mort supplémentaire (permis → parcelle disparue).
- **Saint-Philippe** : 4 164 parcelles sans `parcel_zone_plu` (RNU, zones seulement en archive `plu_gpu_zone__archive_m40`) — le plus gros trou zonage de l'île, cohérent avec le RNU.
- `parcel_filtre_bati.ratio_pct` plafonne à 300 (ce n'est PAS une emprise %) ; l'emprise bâtie réelle a été recalculée spatialement (Q20).

## Les 24 communes témoins (code INSEE + nom)

| INSEE | Commune | | INSEE | Commune |
|-------|---------|-|-------|---------|
| 97401 | Les Avirons | | 97413 | Saint-Leu |
| 97402 | Bras-Panon | | 97414 | Saint-Louis |
| 97403 | Entre-Deux | | 97415 | Saint-Paul |
| 97404 | L'Étang-Salé | | 97416 | Saint-Pierre |
| 97405 | Petite-Île | | 97417 | Saint-Philippe |
| 97406 | La Plaine-des-Palmistes | | 97418 | Sainte-Marie |
| 97407 | Le Port | | 97419 | Sainte-Rose |
| 97408 | La Possession | | 97420 | Sainte-Suzanne |
| 97409 | Saint-André | | 97421 | Salazie |
| 97410 | Saint-Benoît | | 97422 | Le Tampon |
| 97411 | Saint-Denis | | 97423 | Les Trois-Bassins |
| 97412 | Saint-Joseph | | 97424 | Cilaos |

(Q9 : `SELECT insee, nom FROM communes_referentiel ORDER BY insee;` — ⚠ Saint-Philippe = **97417**, 97424 = Cilaos.)

## Requêtes

Toutes précédées de `SET statement_timeout='15s';` — base `labuse`, lecture seule.

```sql
-- Q1 — nouvelles parcelles d'octobre (2 919)
SELECT p.idu, p.commune, p.created_at::date, p.contenance_m2
FROM parcels p JOIN _cad_sm1_nouvelles n USING(idu)
ORDER BY p.contenance_m2 DESC NULLS LAST LIMIT 3;

-- Q2 — disparues encore référencées (pipeline / projets)
SELECT p.idu, p.commune, p.cadastre_disparue_le, 'pipeline' AS ref
FROM parcels p JOIN pipeline_entries pe ON pe.parcel_id = p.id
WHERE p.cadastre_disparue_le IS NOT NULL LIMIT 3;
SELECT p.idu, p.commune, p.cadastre_disparue_le, 'projet'
FROM parcels p JOIN projet_parcelles pp ON pp.parcel_id = p.id
WHERE p.cadastre_disparue_le IS NOT NULL LIMIT 3;
-- (watched_parcels : 0 disparue suivie)

-- Q3 — contenance vs dessin (DV0285 homonymes + CW0658)
SELECT idu, commune, contenance_m2, round(ST_Area(geom_2975)) AS dessin
FROM parcels
WHERE idu IN ('97414000DV0285','97415000DV0285','97416000DV0285','97415000CW0658');

-- Q4 — sans contenance
SELECT idu, commune, round(ST_Area(geom_2975)) dessin FROM parcels
WHERE contenance_m2 IS NULL AND cadastre_disparue_le IS NULL LIMIT 3;

-- Q5 — à cheval sur deux zones PLU (parts 20-80 %)
WITH z AS (SELECT id, name, geom_2975 FROM spatial_layers
           WHERE kind='plu_gpu_zone' AND commune='Saint-Paul'),
cand AS (SELECT p.id, p.idu, p.geom_2975, ST_Area(p.geom_2975) a
         FROM parcels p
         WHERE p.commune='Saint-Paul' AND p.section IN ('BZ','CK') AND p.contenance_m2>500)
SELECT c.idu, z.name,
       round(100*ST_Area(ST_Intersection(c.geom_2975,z.geom_2975))/c.a) part_pct
FROM cand c JOIN z ON ST_Intersects(c.geom_2975, z.geom_2975)
WHERE ST_Area(ST_Intersection(c.geom_2975,z.geom_2975))/c.a BETWEEN 0.2 AND 0.8
ORDER BY c.idu LIMIT 12;

-- Q6 — AU fermée
SELECT s.idu, p.commune, s.zone_lib, s.classe
FROM parcel_au_statut s JOIN parcels p ON p.id = s.parcel_id
WHERE s.classe='declasse_au_fermee' LIMIT 3;

-- Q7 — AK0804/AY0786 : part en PPR INTERDICTION + état servi q_v18
SELECT p.idu, p.commune, round(ST_Area(p.geom_2975)) m2,
 (SELECT round(sum(ST_Area(ST_Intersection(p.geom_2975, s.geom_2975))))
  FROM spatial_layers s
  WHERE s.kind='ppr' AND s.subtype='INTERDICTION'
    AND ST_Intersects(p.geom_2975, s.geom_2975)) rouge_m2
FROM parcels p WHERE p.idu LIKE '%AK0804' OR p.idu LIKE '%AY0786';
SELECT idu, bande, score, sdp_residuelle_m2 FROM score_labuse
WHERE run_label='q_v18' AND idu IN ('97409000AY0786','97409000AK0804');

-- Q8 — PPR multiple (2 plans superposés)
WITH ppr AS (SELECT id, name, geom_2975 FROM spatial_layers
             WHERE kind='ppr' AND commune='Saint-Paul')
SELECT p.idu, p.commune,
       count(DISTINCT split_part(ppr.name,' — ',1)) nb_plans,
       array_agg(DISTINCT ppr.name) aleas
FROM parcels p JOIN ppr ON ST_Intersects(p.geom_2975, ppr.geom_2975)
WHERE p.commune='Saint-Paul' AND p.section='AB'
GROUP BY 1,2 HAVING count(DISTINCT split_part(ppr.name,' — ',1))>=2 LIMIT 3;

-- Q9 — communes + RNU / révisions
SELECT insee, nom FROM communes_referentiel ORDER BY insee;
SELECT insee, commune, du_opposable, etat_commune, code_etat
FROM sudocuh_procedures WHERE insee IN ('97417','97409','97413');
SELECT idu, commune FROM parcels
WHERE commune='Saint-Philippe' AND contenance_m2 > 500 LIMIT 2;

-- Q10 — GPU dépublié (liste config/plu_depublies.yaml : Saint-Leu, Saint-André)
(SELECT p.idu, p.commune, z.zone_lib FROM parcels p
 JOIN parcel_zone_plu z ON z.idu=p.idu
 WHERE p.commune='Saint-André' AND z.zone_lib='UB' LIMIT 1)
UNION ALL
(SELECT p.idu, p.commune, z.zone_lib FROM parcels p
 JOIN parcel_zone_plu z ON z.idu=p.idu
 WHERE p.commune='Saint-Leu' AND z.zone_lib LIKE 'U%' LIMIT 1);

-- Q11 — SCI avec dirigeant connu
SELECT ppm.idu, ppm.denomination, ppm.siren, d.nom, d.prenoms, d.role_entreprise
FROM parcelle_personne_morale ppm JOIN pm_dirigeants d ON d.siren=ppm.siren
WHERE ppm.forme_juridique='SCI' AND d.type_personne IS NOT NULL LIMIT 3;

-- Q12 — propriétaire absent
SELECT p.idu, p.commune FROM parcels p
WHERE p.commune='Cilaos' AND p.cadastre_disparue_le IS NULL
AND NOT EXISTS (SELECT 1 FROM parcelle_personne_morale m WHERE m.idu=p.idu)
LIMIT 3;

-- Q13 — copropriétés RNIC
SELECT parcelle_idu, commune, nom_usage, nb_lots_habitation
FROM rnic_coproprietes
WHERE parcelle_idu IS NOT NULL AND nb_lots_habitation>10 LIMIT 3;

-- Q14 — ORT signées
SELECT insee, commune, statut, ort_signee, date_signature
FROM commune_ort WHERE ort_signee LIMIT 5;

-- Q15 — permis annulé (ETAT_DAU=4) rattaché à une parcelle vivante
SELECT t.permit_id, t.type, t.commune, x.idu
FROM (SELECT * FROM sitadel_permits WHERE raw IS NOT NULL OFFSET 0) t
CROSS JOIN LATERAL jsonb_array_elements_text(t.idu_codes::jsonb) x(idu)
JOIN parcels p ON p.idu=x.idu AND p.cadastre_disparue_le IS NULL
WHERE left(t.raw::text,1)='{' AND t.raw->>'etat'='4' LIMIT 3;

-- Q16 — DVF < 12 mois ET multi-parcelles
SELECT id_mutation, date_mutation, count(DISTINCT id_parcelle) np,
       max(valeur_fonciere) vf, array_agg(DISTINCT id_parcelle) parcelles
FROM dvf_mutations_parcelle WHERE date_mutation >= '2025-10-12'
GROUP BY 1,2 HAVING count(DISTINCT id_parcelle)>1
ORDER BY date_mutation DESC LIMIT 3;

-- Q17 — QPV
WITH q AS (SELECT id, name, geom_2975 FROM spatial_layers WHERE kind='qpv' LIMIT 3)
SELECT p.idu, p.commune, q.name FROM parcels p
JOIN q ON ST_Within(p.geom_2975, q.geom_2975) LIMIT 3;

-- Q18 — littoral (50 pas géométriques)
WITH c AS (SELECT id, name, geom_2975 FROM spatial_layers
           WHERE kind='cinquante_pas' LIMIT 5)
SELECT p.idu, p.commune, c.name FROM parcels p
JOIN c ON ST_Intersects(p.geom_2975, c.geom_2975)
WHERE p.contenance_m2>300 LIMIT 3;

-- Q19 — sans adresse BAN
SELECT p.idu, p.commune FROM parcels p
WHERE p.commune='Le Port' AND p.cadastre_disparue_le IS NULL
AND NOT EXISTS (SELECT 1 FROM adresse_parcelles a WHERE a.idu=p.idu)
AND NOT EXISTS (SELECT 1 FROM parcel_adresse pa WHERE pa.idu=p.idu)
LIMIT 3;

-- Q20 — emprise bâtie > 70 % (calcul spatial direct)
SELECT p.idu, p.commune, round(ST_Area(p.geom_2975)) m2,
       round(100*b.bati/ST_Area(p.geom_2975)) pct_bati
FROM parcels p,
LATERAL (SELECT sum(ST_Area(ST_Intersection(s.geom_2975,p.geom_2975))) bati
         FROM spatial_layers s
         WHERE s.kind='batiment' AND ST_Intersects(s.geom_2975,p.geom_2975)) b
WHERE p.commune='Saint-Denis' AND p.section='AB' AND p.contenance_m2>200
  AND b.bati/ST_Area(p.geom_2975)>0.7 LIMIT 3;

-- Q21 — terrain nu en zone U
SELECT p.idu, p.commune, z.zone_filtre, p.contenance_m2
FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
WHERE p.commune='Saint-Denis' AND p.section='BK'
  AND z.zone_filtre IN ('UA','UB','UC','UD')
  AND p.contenance_m2 BETWEEN 300 AND 3000
  AND NOT EXISTS (SELECT 1 FROM spatial_layers b
                  WHERE b.kind IN ('batiment','batiment_cosia')
                    AND ST_Intersects(b.geom_2975, p.geom_2975))
LIMIT 3;

-- Q22 — veille + CRM (parcelles vivantes)
SELECT w.idu, p.commune, w.created_at::date FROM watched_parcels w
JOIN parcels p ON p.idu=w.idu WHERE p.cadastre_disparue_le IS NULL LIMIT 3;
SELECT p.idu, p.commune, pe.status, pe.created_at::date
FROM pipeline_entries pe JOIN parcels p ON p.id=pe.parcel_id
WHERE p.cadastre_disparue_le IS NULL LIMIT 3;

-- Q23 — Flash test
SELECT idu, statut, created_at::date FROM flash_commandes LIMIT 5;

-- Q24 — servie 0 pour terrain_exigu en zone PPR rouge
SELECT p.idu, p.commune, round(ST_Area(p.geom_2975)) m2, r.cause, sl.bande,
 (SELECT round(sum(ST_Area(ST_Intersection(p.geom_2975,s.geom_2975))))
  FROM spatial_layers s WHERE s.kind='ppr' AND s.subtype='INTERDICTION'
    AND ST_Intersects(p.geom_2975,s.geom_2975)) rouge_m2
FROM parcels p
JOIN parcel_residuel r ON r.parcel_id=p.id
JOIN score_labuse sl ON sl.idu=p.idu AND sl.run_label='q_v18'
WHERE r.cause='terrain_exigu' AND sl.bande='0'
  AND p.commune='Saint-Benoît' AND ST_Area(p.geom_2975)>2000
  AND EXISTS (SELECT 1 FROM spatial_layers s WHERE s.kind='ppr'
              AND s.subtype='INTERDICTION' AND ST_Intersects(p.geom_2975,s.geom_2975))
LIMIT 3;

-- Q25 — bandes A et D du run servi
(SELECT idu, commune, bande, score FROM score_labuse
 WHERE run_label='q_v18' AND bande='A' ORDER BY score DESC LIMIT 2)
UNION ALL
(SELECT idu, commune, bande, score FROM score_labuse
 WHERE run_label='q_v18' AND bande='D' LIMIT 2);

-- Q26 — DPE récent rattaché
SELECT parcelle_idu, etiquette_dpe, date_etablissement, code_insee
FROM dpe_records WHERE parcelle_idu IS NOT NULL
ORDER BY date_etablissement DESC LIMIT 3;

-- Q27 — procédure BODACC sur le propriétaire
SELECT DISTINCT ppm.idu, ppm.denomination, ppm.siren, b.type_procedure, b.date_annonce
FROM parcelle_personne_morale ppm
JOIN bodacc_procedures b ON b.siren=ppm.siren
ORDER BY b.date_annonce DESC LIMIT 3;
```
