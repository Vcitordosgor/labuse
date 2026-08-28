-- RADAR-CATÉGORIE (T6) — jeu de recette [RADAR-TEST], PURGEABLE (bien_id >= 900000).
-- Exerce tous les cas de T2/T3 : rattaché Sourcé, Estimé (candidate), non rattaché, 4 types,
-- baisse de prix, en_vente_longue, particulier/pro, DEUX communes (filtre commune réel).
-- Les url_sortante portent 'radar-test' — aucune requête portail (constantes d'affichage seules).
-- IDU réels (parcels.centroid non nul) : Saint-Paul 97415*, Les Avirons 97401*.
-- Purge : voir qa/radar/purge_recette.sql (DELETE ... WHERE bien_id >= 900000).

BEGIN;

INSERT INTO pige_biens (bien_id, commune, type_bien, est_copro, idu, rattachement_niveau, rattachement_confiance, statut, date_publication, date_premiere_saisie, date_derniere_confirmation) VALUES
  (900001, 'Saint-Paul', 'terrain',     false, '97415000BH0283', 'source', 0.95, 'active',          CURRENT_DATE - 2,  now() - interval '2 day',  now()),
  (900002, 'Saint-Paul', 'maison',      false, '97415000BL0014', 'source', 0.92, 'active',          CURRENT_DATE - 5,  now() - interval '5 day',  now()),
  (900003, 'Saint-Paul', 'appartement', true,  NULL,             'absent', NULL, 'active',          CURRENT_DATE - 1,  now() - interval '1 day',  now()),
  (900004, 'Saint-Paul', 'terrain',     false, '97415000BL0023', 'source', 0.90, 'en_vente_longue', CURRENT_DATE - 97, now() - interval '97 day', now()),
  (900005, 'Saint-Paul', 'immeuble',    false, NULL,             'absent', NULL, 'active',          CURRENT_DATE - 12, now() - interval '12 day', now()),
  (900006, 'Les Avirons','maison',      false, '97401000AB0001', 'source', 0.93, 'active',          CURRENT_DATE - 8,  now() - interval '8 day',  now()),
  (900007, 'Les Avirons','maison',      false, '97401000AB0002', 'estime', 0.60, 'active',          CURRENT_DATE - 3,  now() - interval '3 day',  now());

INSERT INTO pige_faits (bien_id, prix, pieces, surface_hab, surface_terrain, dpe_classe, particulier_pro, fraicheur_source, etiquettes, valide_at) VALUES
  (900001, 295000, NULL, NULL, 620,  NULL, 'particulier', 'publication', '{"prix":"source","surface_terrain":"source","particulier_pro":"source"}',                                'now'::timestamptz),
  (900002, 415000, 4,    96,   410,  NULL, 'particulier', 'publication', '{"prix":"source","pieces":"source","surface_hab":"source","surface_terrain":"source","particulier_pro":"source"}', 'now'::timestamptz),
  (900003, 189000, 3,    64,   NULL, 'C',  'pro',         'publication', '{"prix":"source","pieces":"source","surface_hab":"source","dpe_classe":"source","particulier_pro":"source"}',       'now'::timestamptz),
  (900004, 138000, NULL, NULL, 1240, NULL, 'particulier', 'publication', '{"prix":"source","surface_terrain":"source","particulier_pro":"source"}',                                'now'::timestamptz),
  (900005, 780000, NULL, 512,  NULL, NULL, 'pro',         'publication', '{"prix":"source","surface_hab":"source","particulier_pro":"source"}',                                    'now'::timestamptz),
  (900006, 342000, 5,    118,  520,  'D',  'particulier', 'publication', '{"prix":"source","pieces":"source","surface_hab":"source","surface_terrain":"source","dpe_classe":"source","particulier_pro":"source"}', 'now'::timestamptz),
  (900007, 258000, 3,    78,   NULL, NULL, 'particulier', 'publication', '{"prix":"source","pieces":"source","surface_hab":"source","particulier_pro":"source"}',                    'now'::timestamptz);

INSERT INTO pige_annonces (bien_id, portail, url_sortante) VALUES
  (900001, 'leboncoin', 'https://www.leboncoin.fr/radar-test/900001'),
  (900002, 'leboncoin', 'https://www.leboncoin.fr/radar-test/900002'),
  (900003, 'seloger',   'https://www.seloger.com/radar-test/900003'),
  (900004, 'leboncoin', 'https://www.leboncoin.fr/radar-test/900004'),
  (900005, 'seloger',   'https://www.seloger.com/radar-test/900005'),
  (900006, 'leboncoin', 'https://www.leboncoin.fr/radar-test/900006'),
  (900007, 'leboncoin', 'https://www.leboncoin.fr/radar-test/900007');

-- baisse de prix sur 900001 (320 000 → 295 000) : alimente le badge « baisse » + la sparkline
INSERT INTO pige_prix_historique (bien_id, date_constat, ancien_prix, nouveau_prix) VALUES
  (900001, CURRENT_DATE - 10, 320000, 295000);

COMMIT;
