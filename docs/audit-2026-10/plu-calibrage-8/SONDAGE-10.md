# PLU-CALIBRAGE-8 (oct.) — Sondage de 10 règles pour Vic

10 feuilles calibrées/validées dans ce mandat, tirées à travers les 5 communes touchées et les
4 familles (hauteur, emprise, reculs). Pour chacune : **valeur servie**, **article + page PDF**,
**citation** (du YAML) et **extrait relu à la page du règlement en vigueur** (PDF md5 vérifié =
`meta` du YAML). Objectif : vérifier d'un coup d'œil que la valeur servie = le texte du règlement.

---

**1. Saint-Denis — zone AUm — hauteur au faîtage = 10 m** · Art. AUm.10 · p.98 (md5 `43426a8f…`)
- Valeur servie : `hauteur.faitage.m = 10.0` (+ égout 7 m).
- Extrait relu p.98 : « La hauteur des constructions n'excèdera pas : - 10 m pour la hauteur maximale H - 7 m pour la hauteur d'égout he ».

**2. Saint-Denis — zone AUh — emprise au sol (CES) = 30 %** · Art. AUh.9 · p.103
- Valeur servie : `emprise_sol.ces.pct = 30.0`.
- Extrait relu p.103 : « L'emprise au sol des constructions est limitée à 30% de la superficie de l'unité foncière. »

**3. Saint-Denis — zone AUj — hauteur à l'égout = 10 m** · Art. AUj.10 · p.93
- Valeur servie : `hauteur.egout.m = 10.0` (+ faîtage 13 m).
- Extrait relu p.93 : « La hauteur des constructions n'excèdera pas : - 13 m pour la hauteur maximale H - 10 m pour la hauteur d'égout he ».

**4. Saint-Leu — secteur AUa — emprise au sol (CES) = 80 %** · Art. AU 9 · p.90 (md5 `d74416f9…`)
- Valeur servie : `emprise_sol.ces.pct = 80.0`.
- Extrait relu p.90 : « Dans le secteur AUa et AUa-rc, l'emprise au sol maximale autorisée de l'ensemble des constructions ne doit pas excéder 80% de l'unité foncière. »

**5. Saint-Leu — secteur AUc — hauteur au faîtage = 9 m** · Art. AU 10 · p.91
- Valeur servie : `hauteur.faitage.m = 9.0` (+ égout 6 m).
- Extrait relu p.91 : « Dans les secteurs AUc , la hauteur maximale des constructions est limitée à : - 6,00m à l'égout du toit - 9,00m au faîtage - R+1+combles ».

**6. Saint-Leu — secteur AUe — hauteur à l'égout = 10 m, faîtage ABSENT (silence prouvé)** · Art. AU 10 · p.91
- Valeur servie : `hauteur.egout.m = 10.0` ; **faîtage `absent: true`** — l'Art. AU 10 ne fixe QUE l'égout pour AUe, et le règlement **ne contient aucun renvoi écrit vers la zone UE** (vérifié). Le moteur s'en tient donc à l'égout (gabarit « Hauteur réglementaire — à l'égout : 10 m »), **aucun faîtage emprunté**. Les 12 m cités visent la seule ZAC du Portail (hauteur totale), écartés.
- Extrait relu p.91 : « Dans le secteur AUe, la hauteur maximale des constructions (…) est limitée à 10,00m à l'égout du toit. Pour la zone AUe de la ZAC du Portail, la hauteur totale maximale des bâtiments est portée à 12,00m. »

**7. Saint-Leu — secteur AUd — recul voie = 4 m** · Art. AU 6 · p.87
- Valeur servie : `retraits.voie.min_m = 4.0`.
- Extrait relu p.87 : « Dans le secteur AUc et AUd, les constructions doivent s'implanter avec un recul minimum de 4,00m par rapport à l'alignement. »

**8. Saint-Paul — zone U1pru — limites séparatives : implantation EN LIMITE (recul 0, « alignement »)** · Art. 7 · p.21 (md5 `0aee7298…`) — *Lot C*
- Valeur servie : `retraits.limites_separatives.forme = alignement` (recul 0). Remplace un `min_m 3 m` inventé (passé `propose` par PLU-VERIF-1).
- Extrait relu p.21 : « en zone U1pru — Chaque construction pourra s'implanter sur une limite séparative sans limitation de longueur. En cas de retrait, celui-ci ne pourra excéder 5 mètres ». (Le « retrait ≤ 5 m » est un plafond permissif, pas un minimum.)

**9. Saint-Joseph — zone U5cvd — limites séparatives = 3 m minimum (H/2)** · Art. U5 7.2 · p.78 (md5 `f7f3e047…`)
- Valeur servie : `retraits.limites_separatives.min_m = 3.0` + formule « H/2, minimum 3 m (ou sur limites) ». Remplace un `5 m` inventé (passé `propose`). Identique à la zone sœur U5cv (même phrase).
- Extrait relu p.78 : « Dans les secteurs U5cv et U5cvd, les constructions peuvent être implantées sur deux limites séparatives. En cas de retrait (…) au moins égale à la moitié de la hauteur (H) (…) avec un minimum de 3 mètres. »

**10. Saint-Pierre — zone Uep — emprise au sol = 0,2 % (= 20 m²/ha)** · Art. Ue3.4 · p.192 (md5 `8d65c791…`)
- Valeur servie : `emprise_sol.ces.pct = 0.2` (conversion d'unité exacte de « 20 m² par ha »). Zone d'équipement très restrictive.
- Extrait relu p.192 : « En zone Uep, l'emprise au sol est limitée au maximum à 20 m² par ha (calculée au prorata de la superficie de l'unité foncière). »

---

**Concordance : 10/10** — chaque valeur servie correspond au texte du règlement en vigueur (PDF md5
vérifié). Les reculs « alignement » (U1pru, limites AU Saint-Denis/Saint-Leu) traduisent un droit
d'implanter EN LIMITE / À L'ALIGNEMENT (recul 0) ; les plafonds de retrait permissifs (« ≤ 5 m »,
« ≤ 6 m ») ne sont volontairement pas modélisés (ils ne réduisent pas l'enveloppe).
