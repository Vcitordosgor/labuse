# RADAR-FIX-3 — la page Radar cohérente

Branche `fix/radar-3` (base `52f97272`). Exécute les corrections issues de **RADAR-AUDIT-3**
(`docs/RADAR/RADAR-AUDIT-3.md`, sur `origin/audit/radar-3`). Aucune donnée modifiée en base ; le corpus
de vérification = 241 biens (StBenoît, St-Denis, île). Captures avant/après 1440 px dans `avant/` et `apres/`.

## 1 · Un seul périmètre « en vente »
Statut `active`/`en_vente_longue`, annonce **qualifiée**, hors copro. Les « à qualifier » **et** les
retirées n'y entrent jamais. Même prédicat pour le compteur de la liste, les 4 chiffres, le tableau, la
porte Radar, et **le `n` de la médiane demandée**.
- `client._where` : les à-qualifier sortent du flux par défaut (escapes `a_qualifier=oui|tous`).
- `marche.radar_stats` : la médiane demandée filtre désormais `statut IN (active, en_vente_longue)` → son
  `n` = les annonces en vente du type (plus les retirées).

**Résultat (biens « en vente ») :** Toute l'île **92**, Saint-Denis **13**, Saint-Benoît **3** — identiques
à la liste, à la porte, aux 4 chiffres et au `n` de la médiane, sur les trois périmètres. (Avant : 103 / 13 / 5,
et la médiane comptait 132/…/4 annonces dont des retirées.)

## 2 · Écart par commune : maison contre maison
`marche.tableau` — la barre par commune réutilise **exactement** `_demande_acte("maison", c)` (le calcul de
la ligne « maison » du tableau), plus jamais un bâti mélangé (maison+appt+immeuble) opposé à un acté « tous
types ». **Saint-Denis affiche le même écart dans la barre et dans le tableau** (+5,3 % · indicatif · n=10).
(Avant : −4,7 % au tableau contre +23,9 % à la barre.)

## 3 · Seuil à trois paliers
`marche._ecart_niveau(dn, an, 30)` : **≥ 30** annonces → écart *normal* (coloré) ; **5–29** → *indicatif*
(gris, « +X % · indicatif · n = N ») ; **< 5** → « sous le seuil ». L'acté DVF doit aussi tenir ≥ 5. Même
règle dans les 4 chiffres, le tableau, la barre par commune et le bloc « Ce bien ». Le pied de colonne le dit.

## 4 · Colonnes
- **> 90 j** : calculé sur `COALESCE(date_publication, date_premiere_saisie)` (comme le badge de la liste),
  plus sur `statut='en_vente_longue'` (jamais posé tant que le cycle ne tourne pas). `client.compter(sup90)`
  et le tableau alignés. Île : 3 biens > 90 j (avant : 0).
- **Retirées 30 j** : exclut l'import initial « en bloc ». Ne comptent que les retraits d'un **passage
  quotidien** — datés *après* le jour de la toute première passe de confirmation. Île **1** (avant : 101).
- **Baisses** et **De retour** : inchangés.

## 5 · Sélection visible
`RadarEcran` — l'annonce ouverte dans « Ce bien » porte l'**état actif de la charte** (fond vert `bg-mint`,
encre sombre `mint-on`, puces assombries) et **la liste défile jusqu'à elle** (`scrollIntoView`). (Avant :
simple filet menthe à 6 % d'opacité, sans défilement.)

## Vérifs
- `tsc` 0 · `vite build` 0 · **vitest 225** · pytest ciblé pige/radar/marché **verts** (dont 4 nouveaux
  tests RADAR-FIX-3 : périmètre unique, paliers `_ecart_niveau`, barre = tableau, > 90 j par date).
- 2 échecs pré-existants hors périmètre (prouvés sur la base : `test_pige_digests::test_jamais_de_mail_vide`,
  `test_pige_socle::test_aucune_requete_portail`) ; un 3ᵉ (`test_marche_commune::test_commune_riche`) est un
  artefact d'ordre/données de `labuse_test` (identique base/branche en paire minimale, il *skip*).

## Fichiers
- back : `src/labuse/pige/marche.py`, `src/labuse/pige/client.py`
- front : `frontend/src/lib/api.ts`, `components/radar/RadarMarcheColonne.tsx`, `components/radar/RadarEcran.tsx`
- tests : `tests/test_pige_marche.py` (+4), `tests/test_pige_depot2.py` (doctrine à-qualifier hors flux)
