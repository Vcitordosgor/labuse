# VERITE-TERRAIN-1 — ÉCHANTILLON

**500 parcelles**, tirées au hasard mais stratifiées et reproductibles (graine `20261015`, base figée q_v18).

Reproduire : `python -m labuse.verite_terrain echantillon`. Le tirage est déterministe (même graine + même contenu de base = même échantillon).

## Répartition par commune (prorata)

| Commune | Parcelles |
|---|---|
| Saint-Paul | 54 |
| Le Tampon | 45 |
| Saint-Pierre | 44 |
| Saint-Denis | 41 |
| Les Avirons | 35 |
| Saint-Joseph | 30 |
| Saint-Louis | 30 |
| Saint-Leu | 24 |
| Saint-André | 23 |
| Cilaos | 22 |
| Saint-Benoît | 21 |
| Sainte-Marie | 17 |
| La Possession | 14 |
| Salazie | 14 |
| Petite-Île | 13 |
| Sainte-Suzanne | 13 |
| Le Port | 11 |
| Les Trois-Bassins | 10 |
| L'Étang-Salé | 9 |
| Entre-Deux | 7 |
| La Plaine-des-Palmistes | 7 |
| Bras-Panon | 6 |
| Sainte-Rose | 6 |
| Saint-Philippe | 4 |

## Minimum garanti par cas difficile

| Cas difficile | Parcelles |
|---|---|
| prorata | 261 |
| bizone | 20 |
| ppr_rouge_partiel | 20 |
| surface_incertaine | 20 |
| permis | 20 |
| littoral | 20 |
| contenance_vs_dessin | 20 |
| ventes_recentes | 20 |
| les_Hauts | 20 |
| bande_A | 20 |
| proprietaire_societe | 20 |
| cadastre_octobre | 20 |
| zones_calibrees_plu8 | 20 |

## Les 500 parcelles

| # | IDU | Commune | Cas |
|---|---|---|---|
| 1 | 97401000AB0001 | Les Avirons | bizone |
| 2 | 97401000AB0005 | Les Avirons | ppr_rouge_partiel |
| 3 | 97401000AB0007 | Les Avirons | bizone |
| 4 | 97401000AB0008 | Les Avirons | ppr_rouge_partiel |
| 5 | 97401000AB0009 | Les Avirons | bizone |
| 6 | 97401000AB0015 | Les Avirons | ppr_rouge_partiel |
| 7 | 97401000AC0005 | Les Avirons | bizone |
| 8 | 97401000AC0007 | Les Avirons | ppr_rouge_partiel |
| 9 | 97401000AC0016 | Les Avirons | bizone |
| 10 | 97401000AC0023 | Les Avirons | ppr_rouge_partiel |
| 11 | 97401000AC0026 | Les Avirons | ppr_rouge_partiel |
| 12 | 97401000AC0040 | Les Avirons | ppr_rouge_partiel |
| 13 | 97401000AC0064 | Les Avirons | ppr_rouge_partiel |
| 14 | 97401000AC0068 | Les Avirons | ppr_rouge_partiel |
| 15 | 97401000AC0103 | Les Avirons | ppr_rouge_partiel |
| 16 | 97401000AC0106 | Les Avirons | bizone, ppr_rouge_partiel |
| 17 | 97401000AC0116 | Les Avirons | ppr_rouge_partiel |
| 18 | 97401000AC0117 | Les Avirons | bizone |
| 19 | 97401000AC0160 | Les Avirons | bizone |
| 20 | 97401000AC0196 | Les Avirons | bizone |
| 21 | 97401000AC0553 | Les Avirons | bizone |
| 22 | 97401000AC0569 | Les Avirons | bizone |
| 23 | 97401000AP0011 | Les Avirons | surface_incertaine |
| 24 | 97401000AS0401 | Les Avirons | permis |
| 25 | 97401000AT0016 | Les Avirons | littoral |
| 26 | 97401000AT0404 | Les Avirons | littoral |
| 27 | 97401000AT0412 | Les Avirons | littoral |
| 28 | 97401000AT0447 | Les Avirons | littoral |
| 29 | 97401000AT0536 | Les Avirons | littoral |
| 30 | 97401000AT0538 | Les Avirons | littoral |
| 31 | 97401000AT0572 | Les Avirons | littoral |
| 32 | 97401000AT0628 | Les Avirons | littoral |
| 33 | 97401000AT0680 | Les Avirons | littoral |
| 34 | 97401000AT0681 | Les Avirons | littoral |
| 35 | 97401000AT0691 | Les Avirons | littoral |
| 36 | 97402000AB1017 | Bras-Panon | prorata |
| 37 | 97402000AC0445 | Bras-Panon | prorata |
| 38 | 97402000AI0716 | Bras-Panon | contenance_vs_dessin |
| 39 | 97402000AK1914 | Bras-Panon | prorata |
| 40 | 97402000AL0073 | Bras-Panon | prorata |
| 41 | 97402000AN0241 | Bras-Panon | ventes_recentes |
| 42 | 97403000AO0629 | Entre-Deux | prorata |
| 43 | 97403000AP1847 | Entre-Deux | les_Hauts |
| 44 | 97403000AP2323 | Entre-Deux | prorata |
| 45 | 97403000AS0238 | Entre-Deux | les_Hauts |
| 46 | 97403000AS0907 | Entre-Deux | les_Hauts |
| 47 | 97403000AS1233 | Entre-Deux | prorata |
| 48 | 97403000AS1794 | Entre-Deux | les_Hauts |
| 49 | 97404000AC0508 | L'Étang-Salé | prorata |
| 50 | 97404000AC1083 | L'Étang-Salé | prorata |
| 51 | 97404000AL0940 | L'Étang-Salé | prorata |
| 52 | 97404000AL1630 | L'Étang-Salé | prorata |
| 53 | 97404000AM0708 | L'Étang-Salé | prorata |
| 54 | 97404000AV0342 | L'Étang-Salé | prorata |
| 55 | 97404000AV0443 | L'Étang-Salé | prorata |
| 56 | 97404000AW0178 | L'Étang-Salé | prorata |
| 57 | 97404000AX0623 | L'Étang-Salé | bande_A |
| 58 | 97405000AE0590 | Petite-Île | ventes_recentes |
| 59 | 97405000AI1209 | Petite-Île | ventes_recentes |
| 60 | 97405000AK0910 | Petite-Île | prorata |
| 61 | 97405000AK1010 | Petite-Île | prorata |
| 62 | 97405000AK1439 | Petite-Île | prorata |
| 63 | 97405000AM0819 | Petite-Île | prorata |
| 64 | 97405000AO0400 | Petite-Île | prorata |
| 65 | 97405000AZ0434 | Petite-Île | prorata |
| 66 | 97405000AZ0609 | Petite-Île | prorata |
| 67 | 97405000AZ0700 | Petite-Île | prorata |
| 68 | 97405000BC0174 | Petite-Île | prorata |
| 69 | 97405000BE0839 | Petite-Île | prorata |
| 70 | 97405000BE1392 | Petite-Île | contenance_vs_dessin |
| 71 | 97406000AD0337 | La Plaine-des-Palmistes | les_Hauts |
| 72 | 97406000AD0554 | La Plaine-des-Palmistes | bande_A |
| 73 | 97406000AK0079 | La Plaine-des-Palmistes | permis |
| 74 | 97406000AM0227 | La Plaine-des-Palmistes | les_Hauts |
| 75 | 97406000AS0280 | La Plaine-des-Palmistes | les_Hauts |
| 76 | 97406000AT0796 | La Plaine-des-Palmistes | prorata |
| 77 | 97406000AV1019 | La Plaine-des-Palmistes | ventes_recentes |
| 78 | 97407000AD0087 | Le Port | prorata |
| 79 | 97407000AH8017 | Le Port | surface_incertaine |
| 80 | 97407000AI1282 | Le Port | prorata |
| 81 | 97407000AI1549 | Le Port | ventes_recentes |
| 82 | 97407000AK1227 | Le Port | contenance_vs_dessin |
| 83 | 97407000AK1781 | Le Port | prorata |
| 84 | 97407000AL0616 | Le Port | proprietaire_societe |
| 85 | 97407000AO0644 | Le Port | proprietaire_societe |
| 86 | 97407000AS0763 | Le Port | prorata |
| 87 | 97407000BA0183 | Le Port | ventes_recentes |
| 88 | 97407000BE0248 | Le Port | prorata |
| 89 | 97408000AB0390 | La Possession | permis |
| 90 | 97408000AC0253 | La Possession | prorata |
| 91 | 97408000AC3249 | La Possession | prorata |
| 92 | 97408000AH0250 | La Possession | prorata |
| 93 | 97408000AM1363 | La Possession | prorata |
| 94 | 97408000AR8001 | La Possession | surface_incertaine |
| 95 | 97408000AV1432 | La Possession | prorata |
| 96 | 97408000AW0043 | La Possession | ventes_recentes |
| 97 | 97408000AW0164 | La Possession | prorata |
| 98 | 97408000BD0074 | La Possession | surface_incertaine |
| 99 | 97408000BL0110 | La Possession | proprietaire_societe |
| 100 | 97408000BM0222 | La Possession | prorata |
| 101 | 97408000BN0142 | La Possession | prorata |
| 102 | 97408000BO0281 | La Possession | proprietaire_societe |
| 103 | 97409000AB0188 | Saint-André | prorata |
| 104 | 97409000AI0417 | Saint-André | prorata |
| 105 | 97409000AI0538 | Saint-André | prorata |
| 106 | 97409000AI1204 | Saint-André | prorata |
| 107 | 97409000AI1631 | Saint-André | prorata |
| 108 | 97409000AK0195 | Saint-André | prorata |
| 109 | 97409000AK0804 | Saint-André | bande_A |
| 110 | 97409000AL0211 | Saint-André | prorata |
| 111 | 97409000AM0602 | Saint-André | prorata |
| 112 | 97409000AO0158 | Saint-André | prorata |
| 113 | 97409000AO0285 | Saint-André | prorata |
| 114 | 97409000AP0982 | Saint-André | contenance_vs_dessin |
| 115 | 97409000AP1192 | Saint-André | prorata |
| 116 | 97409000AP1637 | Saint-André | permis |
| 117 | 97409000AS0337 | Saint-André | prorata |
| 118 | 97409000AT0307 | Saint-André | prorata |
| 119 | 97409000AT1410 | Saint-André | prorata |
| 120 | 97409000AV0417 | Saint-André | prorata |
| 121 | 97409000AX0835 | Saint-André | bande_A |
| 122 | 97409000BH0545 | Saint-André | prorata |
| 123 | 97409000BK0287 | Saint-André | prorata |
| 124 | 97409000BM0535 | Saint-André | prorata |
| 125 | 97409000BR0194 | Saint-André | prorata |
| 126 | 97410000AB0339 | Saint-Benoît | prorata |
| 127 | 97410000AC0436 | Saint-Benoît | prorata |
| 128 | 97410000AD0654 | Saint-Benoît | bande_A |
| 129 | 97410000AD0701 | Saint-Benoît | prorata |
| 130 | 97410000AH0274 | Saint-Benoît | prorata |
| 131 | 97410000AH0480 | Saint-Benoît | prorata |
| 132 | 97410000AI0666 | Saint-Benoît | prorata |
| 133 | 97410000AO0642 | Saint-Benoît | prorata |
| 134 | 97410000AR0634 | Saint-Benoît | prorata |
| 135 | 97410000AR0727 | Saint-Benoît | prorata |
| 136 | 97410000AR1650 | Saint-Benoît | prorata |
| 137 | 97410000AW0019 | Saint-Benoît | prorata |
| 138 | 97410000AW0954 | Saint-Benoît | prorata |
| 139 | 97410000BE0451 | Saint-Benoît | prorata |
| 140 | 97410000BI0590 | Saint-Benoît | prorata |
| 141 | 97410000BK0323 | Saint-Benoît | prorata |
| 142 | 97410000BT0073 | Saint-Benoît | prorata |
| 143 | 97410000BX0299 | Saint-Benoît | prorata |
| 144 | 97410000BX1260 | Saint-Benoît | prorata |
| 145 | 97410000BZ0294 | Saint-Benoît | prorata |
| 146 | 97410000CL0525 | Saint-Benoît | prorata |
| 147 | 97411000AB0565 | Saint-Denis | prorata |
| 148 | 97411000AE0356 | Saint-Denis | proprietaire_societe |
| 149 | 97411000AI0154 | Saint-Denis | prorata |
| 150 | 97411000AK0082 | Saint-Denis | prorata |
| 151 | 97411000AZ0522 | Saint-Denis | prorata |
| 152 | 97411000BD1455 | Saint-Denis | cadastre_octobre |
| 153 | 97411000BK0430 | Saint-Denis | contenance_vs_dessin |
| 154 | 97411000BN0509 | Saint-Denis | cadastre_octobre |
| 155 | 97411000BP0620 | Saint-Denis | ventes_recentes |
| 156 | 97411000BZ0895 | Saint-Denis | cadastre_octobre |
| 157 | 97411000CD0701 | Saint-Denis | contenance_vs_dessin |
| 158 | 97411000CM0220 | Saint-Denis | cadastre_octobre |
| 159 | 97411000CV0511 | Saint-Denis | prorata |
| 160 | 97411000CX1762 | Saint-Denis | prorata |
| 161 | 97411000DL0077 | Saint-Denis | prorata |
| 162 | 97411000DL0142 | Saint-Denis | cadastre_octobre |
| 163 | 97411000DM0639 | Saint-Denis | prorata |
| 164 | 97411000DM0744 | Saint-Denis | cadastre_octobre |
| 165 | 97411000DR0878 | Saint-Denis | prorata |
| 166 | 97411000DS0410 | Saint-Denis | proprietaire_societe |
| 167 | 97411000EO0135 | Saint-Denis | prorata |
| 168 | 97411000ER0022 | Saint-Denis | prorata |
| 169 | 97411000EY0145 | Saint-Denis | permis |
| 170 | 97411000HD0070 | Saint-Denis | cadastre_octobre |
| 171 | 97411000HI0541 | Saint-Denis | cadastre_octobre |
| 172 | 97411000HI0592 | Saint-Denis | prorata |
| 173 | 97411000HS0322 | Saint-Denis | bande_A |
| 174 | 97411000HT0045 | Saint-Denis | ventes_recentes |
| 175 | 97411000HT0116 | Saint-Denis | surface_incertaine |
| 176 | 97411000HW0179 | Saint-Denis | cadastre_octobre |
| 177 | 97411000HZ0349 | Saint-Denis | prorata |
| 178 | 97411000HZ0391 | Saint-Denis | permis |
| 179 | 97411000IB0339 | Saint-Denis | ventes_recentes |
| 180 | 97411000IE0157 | Saint-Denis | prorata |
| 181 | 97411000IK0289 | Saint-Denis | prorata |
| 182 | 97411000IR0063 | Saint-Denis | prorata |
| 183 | 97411000IR0418 | Saint-Denis | contenance_vs_dessin |
| 184 | 97411000IS0284 | Saint-Denis | prorata |
| 185 | 97411000IZ0157 | Saint-Denis | prorata |
| 186 | 97411000IZ0349 | Saint-Denis | permis |
| 187 | 97411000KC0030 | Saint-Denis | bande_A |
| 188 | 97412000AH1018 | Saint-Joseph | prorata |
| 189 | 97412000AM0093 | Saint-Joseph | bande_A |
| 190 | 97412000AM1460 | Saint-Joseph | prorata |
| 191 | 97412000AN0186 | Saint-Joseph | prorata |
| 192 | 97412000AO0395 | Saint-Joseph | zones_calibrees_plu8 |
| 193 | 97412000AP0354 | Saint-Joseph | prorata |
| 194 | 97412000AR8002 | Saint-Joseph | surface_incertaine |
| 195 | 97412000AT0558 | Saint-Joseph | surface_incertaine |
| 196 | 97412000AV0315 | Saint-Joseph | prorata |
| 197 | 97412000AV0401 | Saint-Joseph | prorata |
| 198 | 97412000AV0779 | Saint-Joseph | prorata |
| 199 | 97412000AZ0324 | Saint-Joseph | proprietaire_societe |
| 200 | 97412000AZ0765 | Saint-Joseph | zones_calibrees_plu8 |
| 201 | 97412000BH0363 | Saint-Joseph | prorata |
| 202 | 97412000BH0744 | Saint-Joseph | prorata |
| 203 | 97412000BN1117 | Saint-Joseph | contenance_vs_dessin |
| 204 | 97412000BO0144 | Saint-Joseph | prorata |
| 205 | 97412000BY0117 | Saint-Joseph | surface_incertaine |
| 206 | 97412000CD0500 | Saint-Joseph | ventes_recentes |
| 207 | 97412000CE2316 | Saint-Joseph | ventes_recentes |
| 208 | 97412000CE2686 | Saint-Joseph | ventes_recentes |
| 209 | 97412000CI0083 | Saint-Joseph | surface_incertaine |
| 210 | 97412000CM0014 | Saint-Joseph | surface_incertaine |
| 211 | 97412000CM0015 | Saint-Joseph | surface_incertaine |
| 212 | 97412000CN0144 | Saint-Joseph | prorata |
| 213 | 97412000CV0413 | Saint-Joseph | prorata |
| 214 | 97412000CW0987 | Saint-Joseph | prorata |
| 215 | 97412000CW1154 | Saint-Joseph | prorata |
| 216 | 97412000CY1092 | Saint-Joseph | prorata |
| 217 | 97412000CZ0965 | Saint-Joseph | prorata |
| 218 | 97413000AC0521 | Saint-Leu | contenance_vs_dessin |
| 219 | 97413000AC0892 | Saint-Leu | prorata |
| 220 | 97413000AV0080 | Saint-Leu | prorata |
| 221 | 97413000CC0897 | Saint-Leu | prorata |
| 222 | 97413000CD0313 | Saint-Leu | prorata |
| 223 | 97413000CD0387 | Saint-Leu | contenance_vs_dessin |
| 224 | 97413000CF0445 | Saint-Leu | prorata |
| 225 | 97413000CL0049 | Saint-Leu | prorata |
| 226 | 97413000CN0142 | Saint-Leu | permis |
| 227 | 97413000CO0040 | Saint-Leu | prorata |
| 228 | 97413000CO0349 | Saint-Leu | prorata |
| 229 | 97413000CQ0708 | Saint-Leu | prorata |
| 230 | 97413000CU0448 | Saint-Leu | prorata |
| 231 | 97413000CU1014 | Saint-Leu | prorata |
| 232 | 97413000CX0267 | Saint-Leu | contenance_vs_dessin |
| 233 | 97413000CX1218 | Saint-Leu | prorata |
| 234 | 97413000CX1920 | Saint-Leu | cadastre_octobre |
| 235 | 97413000CX2174 | Saint-Leu | prorata |
| 236 | 97413000DB0040 | Saint-Leu | cadastre_octobre |
| 237 | 97413000DD1288 | Saint-Leu | prorata |
| 238 | 97413000DE0341 | Saint-Leu | prorata |
| 239 | 97413000DE1308 | Saint-Leu | ventes_recentes |
| 240 | 97413000DE1540 | Saint-Leu | prorata |
| 241 | 97413000DM0224 | Saint-Leu | proprietaire_societe |
| 242 | 97414000CH1250 | Saint-Louis | prorata |
| 243 | 97414000CI0752 | Saint-Louis | prorata |
| 244 | 97414000CN0740 | Saint-Louis | contenance_vs_dessin |
| 245 | 97414000CV0028 | Saint-Louis | prorata |
| 246 | 97414000CV0743 | Saint-Louis | prorata |
| 247 | 97414000CW0487 | Saint-Louis | zones_calibrees_plu8 |
| 248 | 97414000DE1475 | Saint-Louis | prorata |
| 249 | 97414000DH0913 | Saint-Louis | prorata |
| 250 | 97414000DS0897 | Saint-Louis | cadastre_octobre |
| 251 | 97414000DT0102 | Saint-Louis | prorata |
| 252 | 97414000DY0500 | Saint-Louis | prorata |
| 253 | 97414000EL0959 | Saint-Louis | prorata |
| 254 | 97414000EL1365 | Saint-Louis | zones_calibrees_plu8 |
| 255 | 97414000EL2601 | Saint-Louis | prorata |
| 256 | 97414000EM0566 | Saint-Louis | zones_calibrees_plu8 |
| 257 | 97414000EN0578 | Saint-Louis | prorata |
| 258 | 97414000EN2004 | Saint-Louis | prorata |
| 259 | 97414000EN2442 | Saint-Louis | prorata |
| 260 | 97414000EN3268 | Saint-Louis | zones_calibrees_plu8 |
| 261 | 97414000EN3630 | Saint-Louis | prorata |
| 262 | 97414000EN3639 | Saint-Louis | prorata |
| 263 | 97414000EN4183 | Saint-Louis | prorata |
| 264 | 97414000EO0103 | Saint-Louis | bande_A |
| 265 | 97414000ER0541 | Saint-Louis | prorata |
| 266 | 97414000ET0484 | Saint-Louis | prorata |
| 267 | 97414000EX0548 | Saint-Louis | proprietaire_societe |
| 268 | 97414000EX0755 | Saint-Louis | prorata |
| 269 | 97414000EZ0044 | Saint-Louis | prorata |
| 270 | 97414000EZ0443 | Saint-Louis | prorata |
| 271 | 97414000HI0735 | Saint-Louis | prorata |
| 272 | 97415000AV8002 | Saint-Paul | surface_incertaine |
| 273 | 97415000AW0061 | Saint-Paul | prorata |
| 274 | 97415000AW0763 | Saint-Paul | contenance_vs_dessin |
| 275 | 97415000AX0316 | Saint-Paul | prorata |
| 276 | 97415000AX0960 | Saint-Paul | proprietaire_societe |
| 277 | 97415000BI0633 | Saint-Paul | ventes_recentes |
| 278 | 97415000BO0025 | Saint-Paul | prorata |
| 279 | 97415000BO0828 | Saint-Paul | permis |
| 280 | 97415000BS0019 | Saint-Paul | prorata |
| 281 | 97415000BS0165 | Saint-Paul | bande_A |
| 282 | 97415000BV1410 | Saint-Paul | prorata |
| 283 | 97415000BX0025 | Saint-Paul | prorata |
| 284 | 97415000BY0330 | Saint-Paul | prorata |
| 285 | 97415000BY0409 | Saint-Paul | zones_calibrees_plu8 |
| 286 | 97415000BZ0169 | Saint-Paul | cadastre_octobre |
| 287 | 97415000CK0785 | Saint-Paul | prorata |
| 288 | 97415000CL0700 | Saint-Paul | zones_calibrees_plu8 |
| 289 | 97415000CM0582 | Saint-Paul | surface_incertaine |
| 290 | 97415000CR0069 | Saint-Paul | prorata |
| 291 | 97415000CR0445 | Saint-Paul | prorata |
| 292 | 97415000CR1272 | Saint-Paul | prorata |
| 293 | 97415000CS0590 | Saint-Paul | contenance_vs_dessin |
| 294 | 97415000CT3018 | Saint-Paul | prorata |
| 295 | 97415000CV0270 | Saint-Paul | prorata |
| 296 | 97415000CV0451 | Saint-Paul | prorata |
| 297 | 97415000CW0603 | Saint-Paul | cadastre_octobre |
| 298 | 97415000CW1051 | Saint-Paul | proprietaire_societe |
| 299 | 97415000CZ1234 | Saint-Paul | prorata |
| 300 | 97415000CZ1292 | Saint-Paul | permis |
| 301 | 97415000DE0943 | Saint-Paul | bande_A |
| 302 | 97415000DI0143 | Saint-Paul | prorata |
| 303 | 97415000DM0933 | Saint-Paul | prorata |
| 304 | 97415000DM1338 | Saint-Paul | proprietaire_societe |
| 305 | 97415000DT0773 | Saint-Paul | permis |
| 306 | 97415000DT0867 | Saint-Paul | prorata |
| 307 | 97415000DV0348 | Saint-Paul | prorata |
| 308 | 97415000DV0537 | Saint-Paul | prorata |
| 309 | 97415000DY0119 | Saint-Paul | surface_incertaine |
| 310 | 97415000DZ0119 | Saint-Paul | contenance_vs_dessin |
| 311 | 97415000EK0228 | Saint-Paul | contenance_vs_dessin |
| 312 | 97415000EM0041 | Saint-Paul | zones_calibrees_plu8 |
| 313 | 97415000EM0459 | Saint-Paul | cadastre_octobre |
| 314 | 97415000EO0928 | Saint-Paul | permis |
| 315 | 97415000ER0318 | Saint-Paul | prorata |
| 316 | 97415000EV0814 | Saint-Paul | proprietaire_societe |
| 317 | 97415000EW0263 | Saint-Paul | prorata |
| 318 | 97415000EW0949 | Saint-Paul | prorata |
| 319 | 97415000EX0416 | Saint-Paul | prorata |
| 320 | 97415000EY1769 | Saint-Paul | permis |
| 321 | 97415000HI0539 | Saint-Paul | ventes_recentes |
| 322 | 97415000HM0151 | Saint-Paul | prorata |
| 323 | 97415000HO1036 | Saint-Paul | permis |
| 324 | 97415000HP0221 | Saint-Paul | prorata |
| 325 | 97415000HP0363 | Saint-Paul | prorata |
| 326 | 97416000CV1189 | Saint-Pierre | prorata |
| 327 | 97416000CV1270 | Saint-Pierre | prorata |
| 328 | 97416000CV1578 | Saint-Pierre | zones_calibrees_plu8 |
| 329 | 97416000CV2315 | Saint-Pierre | prorata |
| 330 | 97416000CW1220 | Saint-Pierre | prorata |
| 331 | 97416000CY0116 | Saint-Pierre | prorata |
| 332 | 97416000CZ0204 | Saint-Pierre | surface_incertaine |
| 333 | 97416000CZ1597 | Saint-Pierre | proprietaire_societe |
| 334 | 97416000DE1279 | Saint-Pierre | prorata |
| 335 | 97416000DE1672 | Saint-Pierre | permis |
| 336 | 97416000DE1762 | Saint-Pierre | prorata |
| 337 | 97416000DH1928 | Saint-Pierre | prorata |
| 338 | 97416000DM0500 | Saint-Pierre | prorata |
| 339 | 97416000DM0785 | Saint-Pierre | prorata |
| 340 | 97416000DT0190 | Saint-Pierre | prorata |
| 341 | 97416000DW0102 | Saint-Pierre | prorata |
| 342 | 97416000DX0271 | Saint-Pierre | prorata |
| 343 | 97416000DX8001 | Saint-Pierre | surface_incertaine |
| 344 | 97416000DX8002 | Saint-Pierre | surface_incertaine |
| 345 | 97416000DZ0853 | Saint-Pierre | prorata |
| 346 | 97416000EH0727 | Saint-Pierre | prorata |
| 347 | 97416000EK0496 | Saint-Pierre | prorata |
| 348 | 97416000EL0327 | Saint-Pierre | permis |
| 349 | 97416000EM0018 | Saint-Pierre | prorata |
| 350 | 97416000EO0022 | Saint-Pierre | cadastre_octobre |
| 351 | 97416000ER0306 | Saint-Pierre | zones_calibrees_plu8 |
| 352 | 97416000ET0021 | Saint-Pierre | prorata |
| 353 | 97416000ET0700 | Saint-Pierre | prorata |
| 354 | 97416000EV1102 | Saint-Pierre | cadastre_octobre |
| 355 | 97416000EW1130 | Saint-Pierre | prorata |
| 356 | 97416000EX0314 | Saint-Pierre | zones_calibrees_plu8 |
| 357 | 97416000EZ0676 | Saint-Pierre | prorata |
| 358 | 97416000HN0211 | Saint-Pierre | zones_calibrees_plu8 |
| 359 | 97416000HN1233 | Saint-Pierre | prorata |
| 360 | 97416000HO0545 | Saint-Pierre | prorata |
| 361 | 97416000HP0016 | Saint-Pierre | prorata |
| 362 | 97416000HW0156 | Saint-Pierre | prorata |
| 363 | 97416000HX0334 | Saint-Pierre | contenance_vs_dessin |
| 364 | 97416000IA1447 | Saint-Pierre | zones_calibrees_plu8 |
| 365 | 97416000IB0278 | Saint-Pierre | prorata |
| 366 | 97416000IC0174 | Saint-Pierre | prorata |
| 367 | 97416000IE0838 | Saint-Pierre | ventes_recentes |
| 368 | 97416000IM0125 | Saint-Pierre | prorata |
| 369 | 97416000IM0285 | Saint-Pierre | prorata |
| 370 | 97417000AN0137 | Saint-Philippe | prorata |
| 371 | 97417000AS0129 | Saint-Philippe | prorata |
| 372 | 97417000AS0294 | Saint-Philippe | permis |
| 373 | 97417000BN0002 | Saint-Philippe | prorata |
| 374 | 97418000AC0733 | Sainte-Marie | prorata |
| 375 | 97418000AC1332 | Sainte-Marie | permis |
| 376 | 97418000AE0256 | Sainte-Marie | prorata |
| 377 | 97418000AE0502 | Sainte-Marie | prorata |
| 378 | 97418000AP2264 | Sainte-Marie | zones_calibrees_plu8 |
| 379 | 97418000AR2073 | Sainte-Marie | prorata |
| 380 | 97418000AR2589 | Sainte-Marie | ventes_recentes |
| 381 | 97418000AS0338 | Sainte-Marie | prorata |
| 382 | 97418000AT1832 | Sainte-Marie | prorata |
| 383 | 97418000AT2033 | Sainte-Marie | prorata |
| 384 | 97418000AX0278 | Sainte-Marie | prorata |
| 385 | 97418000AX0451 | Sainte-Marie | permis |
| 386 | 97418000AY0519 | Sainte-Marie | bande_A |
| 387 | 97418000BH0637 | Sainte-Marie | prorata |
| 388 | 97418000BH0755 | Sainte-Marie | prorata |
| 389 | 97418000BP0036 | Sainte-Marie | prorata |
| 390 | 97418000BT0865 | Sainte-Marie | prorata |
| 391 | 97419000AC0362 | Sainte-Rose | prorata |
| 392 | 97419000AN0292 | Sainte-Rose | prorata |
| 393 | 97419000AO0131 | Sainte-Rose | prorata |
| 394 | 97419000AR0146 | Sainte-Rose | prorata |
| 395 | 97419000AW0148 | Sainte-Rose | prorata |
| 396 | 97419000AZ0031 | Sainte-Rose | prorata |
| 397 | 97420000AB0822 | Sainte-Suzanne | prorata |
| 398 | 97420000AC1075 | Sainte-Suzanne | bande_A |
| 399 | 97420000AH0134 | Sainte-Suzanne | proprietaire_societe |
| 400 | 97420000AM0218 | Sainte-Suzanne | proprietaire_societe |
| 401 | 97420000AR0683 | Sainte-Suzanne | prorata |
| 402 | 97420000AS0646 | Sainte-Suzanne | prorata |
| 403 | 97420000AZ0385 | Sainte-Suzanne | prorata |
| 404 | 97420000BC0899 | Sainte-Suzanne | prorata |
| 405 | 97420000BC1198 | Sainte-Suzanne | prorata |
| 406 | 97420000BC9999 | Sainte-Suzanne | surface_incertaine |
| 407 | 97420000BD0961 | Sainte-Suzanne | zones_calibrees_plu8 |
| 408 | 97420000BH0346 | Sainte-Suzanne | ventes_recentes |
| 409 | 97420000BH1606 | Sainte-Suzanne | cadastre_octobre |
| 410 | 97421000AC0269 | Salazie | les_Hauts |
| 411 | 97421000AC0308 | Salazie | les_Hauts |
| 412 | 97421000AH0557 | Salazie | les_Hauts |
| 413 | 97421000AL0321 | Salazie | cadastre_octobre |
| 414 | 97421000AP0068 | Salazie | bande_A |
| 415 | 97421000AP0147 | Salazie | les_Hauts |
| 416 | 97421000AV0372 | Salazie | les_Hauts |
| 417 | 97421000AV0536 | Salazie | cadastre_octobre |
| 418 | 97421000BD0331 | Salazie | bande_A |
| 419 | 97421000BL0089 | Salazie | surface_incertaine |
| 420 | 97421000BM0064 | Salazie | les_Hauts |
| 421 | 97421000BN0042 | Salazie | les_Hauts |
| 422 | 97421000BO0266 | Salazie | bande_A |
| 423 | 97421000BO0430 | Salazie | les_Hauts |
| 424 | 97422000AB0049 | Le Tampon | proprietaire_societe |
| 425 | 97422000AD0661 | Le Tampon | prorata |
| 426 | 97422000AD1061 | Le Tampon | prorata |
| 427 | 97422000AE8001 | Le Tampon | surface_incertaine |
| 428 | 97422000AK0991 | Le Tampon | contenance_vs_dessin |
| 429 | 97422000AX0956 | Le Tampon | contenance_vs_dessin |
| 430 | 97422000AX1448 | Le Tampon | prorata |
| 431 | 97422000AY0017 | Le Tampon | proprietaire_societe |
| 432 | 97422000BD1172 | Le Tampon | prorata |
| 433 | 97422000BD3213 | Le Tampon | bande_A |
| 434 | 97422000BH0078 | Le Tampon | bande_A |
| 435 | 97422000BH1561 | Le Tampon | contenance_vs_dessin |
| 436 | 97422000BI1005 | Le Tampon | prorata |
| 437 | 97422000BL0028 | Le Tampon | zones_calibrees_plu8 |
| 438 | 97422000BL1219 | Le Tampon | prorata |
| 439 | 97422000BM0501 | Le Tampon | prorata |
| 440 | 97422000BN2291 | Le Tampon | bande_A |
| 441 | 97422000BN2704 | Le Tampon | prorata |
| 442 | 97422000BO1094 | Le Tampon | zones_calibrees_plu8 |
| 443 | 97422000BP1864 | Le Tampon | prorata |
| 444 | 97422000BP2028 | Le Tampon | prorata |
| 445 | 97422000BR1554 | Le Tampon | prorata |
| 446 | 97422000BV0523 | Le Tampon | prorata |
| 447 | 97422000BV1983 | Le Tampon | prorata |
| 448 | 97422000BW0709 | Le Tampon | bande_A |
| 449 | 97422000BW1117 | Le Tampon | proprietaire_societe |
| 450 | 97422000BW3474 | Le Tampon | prorata |
| 451 | 97422000BX0497 | Le Tampon | prorata |
| 452 | 97422000CD0352 | Le Tampon | permis |
| 453 | 97422000CL1438 | Le Tampon | prorata |
| 454 | 97422000CM0181 | Le Tampon | prorata |
| 455 | 97422000CM0592 | Le Tampon | prorata |
| 456 | 97422000CO0386 | Le Tampon | ventes_recentes |
| 457 | 97422000CR0409 | Le Tampon | zones_calibrees_plu8 |
| 458 | 97422000CS0365 | Le Tampon | prorata |
| 459 | 97422000CS0690 | Le Tampon | prorata |
| 460 | 97422000DE0532 | Le Tampon | prorata |
| 461 | 97422000DE0563 | Le Tampon | prorata |
| 462 | 97422000DH0793 | Le Tampon | prorata |
| 463 | 97422000DI0036 | Le Tampon | prorata |
| 464 | 97422000DM0562 | Le Tampon | prorata |
| 465 | 97422000EH0118 | Le Tampon | prorata |
| 466 | 97422000EI0240 | Le Tampon | prorata |
| 467 | 97422000EI0316 | Le Tampon | prorata |
| 468 | 97422000EM0178 | Le Tampon | proprietaire_societe |
| 469 | 97423000AE0142 | Les Trois-Bassins | littoral |
| 470 | 97423000AE0220 | Les Trois-Bassins | littoral |
| 471 | 97423000AE0238 | Les Trois-Bassins | littoral |
| 472 | 97423000AE0261 | Les Trois-Bassins | littoral |
| 473 | 97423000AE0275 | Les Trois-Bassins | littoral |
| 474 | 97423000AE0289 | Les Trois-Bassins | littoral |
| 475 | 97423000AE0561 | Les Trois-Bassins | littoral |
| 476 | 97423000AE1118 | Les Trois-Bassins | littoral |
| 477 | 97423000AE1119 | Les Trois-Bassins | littoral |
| 478 | 97423000AK1937 | Les Trois-Bassins | zones_calibrees_plu8 |
| 479 | 97424000AE0468 | Cilaos | les_Hauts |
| 480 | 97424000AE2248 | Cilaos | les_Hauts |
| 481 | 97424000AH0251 | Cilaos | les_Hauts |
| 482 | 97424000AI2357 | Cilaos | les_Hauts |
| 483 | 97424000AP0456 | Cilaos | ppr_rouge_partiel |
| 484 | 97424000AP0464 | Cilaos | ppr_rouge_partiel |
| 485 | 97424000AP0468 | Cilaos | ppr_rouge_partiel |
| 486 | 97424000AP0483 | Cilaos | ppr_rouge_partiel |
| 487 | 97424000AP0495 | Cilaos | ppr_rouge_partiel |
| 488 | 97424000AP0522 | Cilaos | ppr_rouge_partiel |
| 489 | 97424000AP0528 | Cilaos | ppr_rouge_partiel |
| 490 | 97424000AR0036 | Cilaos | les_Hauts |
| 491 | 97424000AR0040 | Cilaos | bizone |
| 492 | 97424000AR0041 | Cilaos | bizone |
| 493 | 97424000AR0045 | Cilaos | bizone |
| 494 | 97424000AR0075 | Cilaos | bizone |
| 495 | 97424000AR0076 | Cilaos | bizone |
| 496 | 97424000AR0078 | Cilaos | bizone |
| 497 | 97424000AR0085 | Cilaos | bizone |
| 498 | 97424000AR0086 | Cilaos | bizone |
| 499 | 97424000AR0101 | Cilaos | bizone |
| 500 | 97424000AR0111 | Cilaos | ppr_rouge_partiel |
