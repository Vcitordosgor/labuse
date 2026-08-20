// M135 P3 — MIROIR TS de src/labuse/scoring/p_v2/libelles_client._RAISON_COURTE / raison_dominante.
// Le geojson (carte, assemblé et caché en SQL) ne peut pas appeler le Python ; il sert `top5`,
// le front en dérive la raison dominante. La LISTE île, la fiche et le PDF utilisent la version
// PYTHON servie (`raison`) ; ce miroir ne sert QU'AU geojson commune. Un test anti-dérive
// (test_front_reliquats) garantit que les deux tables ont les mêmes clés/valeurs.
type Contrib = { signe?: string; feature?: string; bin?: string }

const COURTE: Record<string, (b: string) => string | null> = {
  tenure_bin: (b) => (b === '3+' ? 'détenu 3 ans et +' : (['<1', '1-2'].includes(b) ? 'mutation récente' : null)),
  permis_bin: (b) => (['<2a', '2-5a'].includes(b) ? 'permis récent' : null),
  permis_etat: () => 'permis en cours',
  pc_accorde_jamais_commence: (b) => (b === 'true' ? 'permis jamais lancé' : null),
  proc_collective: (b) => (b === 'true' ? 'procédure en cours' : null),
  succession_indivision: (b) => (b === 'true' ? 'succession / indivision' : null),
  age_dirigeant_bin: () => 'dirigeant âgé',
  contagion_voisinage: () => 'secteur qui bouge',
  vente_tab_proximite: (b) => (b === 'true' ? 'ventes juste à côté' : null),
  rot_nu: () => 'secteur qui bouge',
  rot_bati: () => 'secteur qui bouge',
  nu_constructible: (b) => (b === 'true' ? 'terrain nu constructible' : null),
  friche: (b) => (b === 'true' ? 'friche recensée' : null),
  piscine: (b) => (b === 'true' ? 'piscine détectée' : null),
  pm_nue_dormante: (b) => (b === 'true' ? 'société, terrain nu' : null),
  zone_plu: (b) => (({ U: 'zone urbaine', AU: 'zone à urbaniser' } as Record<string, string>)[b] ?? null),
  sous_densite: (b) => (b === 'true' ? 'sous-densité (bâti léger)' : null),
}

export function raisonDominante(top5: Contrib[] | null | undefined): string | null {
  for (const c of top5 ?? []) {
    if (c.signe !== '+') continue
    const feat = (c.feature ?? '').split('*')[0]   // interactions ignorées
    const fn = COURTE[feat]
    if (fn) { const r = fn((c.bin ?? '').trim()); if (r) return r }
  }
  return null
}
