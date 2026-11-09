'use strict';
// Tests du contrat pedagogique ; ne valident ni SIG, ni PLU, ni modele ML reel.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const api = require('./04_MOTEUR_REFERENCE.cjs');
const fixtures = JSON.parse(fs.readFileSync(path.join(__dirname,'05_CAS_FICTIFS.json'),'utf8'));
const byId = letter => fixtures.find(record => record.id === 'DEMO-' + letter);
const potential = (record, scenario='keep',extra={}) => api.evaluate(record,{mode:'potential',scenario,...extra});
const sale = (record,extra={}) => api.evaluate(record,{mode:'sale',...extra});
const clone = (letter,patch={}) => ({...byId(letter),...patch});
let count = 0;
function test(name,run) { run(); count++; process.stdout.write('✓ ' + name + '\n'); }

test('UMD navigateur sans require et API publique',()=>{
  const context = {Intl}; vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'04_MOTEUR_REFERENCE.cjs'),'utf8'),context);
  assert.equal(typeof context.LabuseV2.evaluate,'function');
  assert.equal(typeof context.LabuseV2.order,'function');
});
test('10 cas clairement fictifs et provenance de démonstration',()=>{
  assert.equal(fixtures.length,10);
  assert(fixtures.every(record=>record.demo && record.sources.every(source=>source.demo)));
});
test('identifiants conservés dans tous les modes et scénarios',()=>{
  for (const mode of ['sale','potential']) for (const scenario of ['keep','rebuild','divide'])
    assert.deepEqual(api.order(fixtures,{mode,scenario}).map(row=>row.id).sort(),fixtures.map(row=>row.id).sort());
});
test('bâti saturé : sans marge en conservation, Signal disponible en vente',()=>{
  assert.equal(potential(byId('A')).status,'NO_MARGIN');
  assert.equal(potential(byId('A')).quantities.additional,0);
  assert.equal(sale(byId('A')).status,'SIGNAL_AVAILABLE');
});
test('reconstruction cohérente à 2 099 puis 2 100 m² existants',()=>{
  const a=potential(clone('C',{capacity:2100,existing:2099}),'rebuild');
  const b=potential(clone('C',{capacity:2100,existing:2100}),'rebuild');
  assert.equal(a.status,'ESTIMATED');assert.equal(b.status,'ESTIMATED');
  assert.equal(a.rank_value,2100);assert.equal(b.rank_value,2100);
  assert.equal(a.quantities.net_signed,1);assert.equal(b.quantities.net_signed,0);
});
test('perte de SDP −500 conservée sans exclusion économique',()=>{
  const row=potential(byId('H'),'rebuild');assert.equal(row.status,'ESTIMATED');
  assert.equal(row.quantities.net_signed,-500);assert.equal(row.quantities.project_total,2500);
});
test('sol nu : aucune démolition inventée',()=>{
  const row=potential(byId('B'),'rebuild');assert.equal(row.quantities.existing,0);
  assert(row.warnings.some(text=>text.includes('aucune démolition')));
});
test('capacité absente distincte de zéro',()=>{
  const row=potential(clone('B',{capacity:null}));assert.equal(row.status,'TO_VERIFY');
  assert.equal(row.quantities.additional,null);assert.equal(row.rank_value,null);
});
test('hauteur manquante : bloque SDP mais pas division documentaire',()=>{
  assert.equal(potential(byId('E')).status,'TO_VERIFY');
  assert.equal(potential(byId('E'),'divide').status,'PRESTUDY');
  assert.equal(potential(byId('E'),'divide').quantities.project_total,null);
});
test('division n’exige ni SDP existante ni capacité',()=>{
  const row=potential(clone('B',{existing:null,capacity:null,height_status:'missing'}),'divide');
  assert.equal(row.status,'PRESTUDY');assert(!('lots' in row));
});
test('preuve d’incompatibilité vérifiée, pas simple étiquette de zone',()=>{
  assert.equal(potential(byId('D')).status,'OUTSIDE_OBJECTIVE');
  assert.equal(potential(clone('D',{proof_verified:false})).status,'TO_VERIFY');
  assert.equal(potential(clone('B',{zones:['N']})).status,'ESTIMATED');
});
test('géométrie suspecte : grandes et petites surfaces également à vérifier',()=>{
  assert.equal(potential(byId('I')).status,'TO_VERIFY');
  assert.equal(potential(clone('I',{area:30})).status,'TO_VERIFY');
});
test('AU fermée : 4 200 conditionnels, aucune capacité actuelle et aucun ×0,5',()=>{
  const row=potential(byId('G'));assert.equal(row.status,'DEFERRED');
  assert.equal(row.quantities.conditional_future,4200);assert.equal(row.quantities.additional,null);
});
test('différés : une capacité future ne remplace aucun gain ni résiduel de tri',()=>{
  const a=clone('G',{id:'Z',future_capacity:4200,existing:10000});
  const b=clone('G',{id:'A',future_capacity:3000,existing:0});
  for(const [scenario,sort] of [['keep','capacity'],['rebuild','capacity'],['rebuild','gain']]){
    const rows=api.order([a,b],{mode:'potential',scenario,sort});
    assert.deepEqual(rows.map(row=>row.id),['A','Z']);
    assert(rows.every(row=>row.rank_value===null));
  }
  assert.equal(api.order([a,b],{mode:'potential',scenario:'rebuild',sort:'area'})[0].rank_value,8000);
});
test('horizon différé conservé si la quantité future facultative est absente ou invalide',()=>{
  for(const future_capacity of [null,-1,NaN]) {
    const row=potential(clone('G',{future_capacity}));
    assert.equal(row.status,'DEFERRED');assert.equal(row.quantities.conditional_future,null);
  }
});
test('pente forte ou inconnue : aucun changement arithmétique',()=>{
  const a=potential(byId('F')),b=potential(clone('F',{slope:null}));
  assert.equal(a.quantities.additional,2400);assert.equal(a.rank_value,b.rank_value);
  assert(b.warnings.some(text=>text.includes('Pente non renseignée')));
});
test('zonage mixte : capacité portée par la portion autorisée',()=>{
  const row=potential(byId('J'));assert.equal(row.status,'ESTIMATED');
  assert.equal(row.quantities.additional,2000);assert.equal(row.record.zone_parts[0].area,4000);
});
test('seuils de Signal 0 / 0,10 / 0,20 / 1 exacts',()=>{
  for(const [p,level] of [[0,'weak'],[0.099999,'weak'],[0.1,'medium'],[0.199999,'medium'],[0.2,'strong'],[1,'strong']])
    assert.equal(sale(clone('A',{p})).signal.level,level);
});
test('probabilité absente distincte de probabilité nulle',()=>{
  assert.equal(sale(clone('A',{p:null})).status,'SIGNAL_NOT_AVAILABLE');
  assert.equal(sale(clone('A',{p:0})).status,'SIGNAL_AVAILABLE');
  assert.equal(sale(clone('A',{p:0})).signal.p,0);
});
test('probabilités hors [0,1] ou non finies refusées',()=>{
  for(const p of [-0.1,1.1,NaN,Infinity,'0.2']) {
    const row=sale(clone('A',{p}));assert.equal(row.status,'SIGNAL_TO_VERIFY');assert.equal(row.signal.p,null);
  }
});
test('domaine non validé ou hors champ sans extrapolation',()=>{
  assert.equal(sale(clone('A',{signal_domain_verified:false})).status,'SIGNAL_TO_VERIFY');
  const row=sale(clone('D',{p:0.9}));assert.equal(row.status,'SIGNAL_OUT_OF_SCOPE');assert.equal(row.signal.p,null);
});
test('politique DEMO ne réactive aucune politique de production',()=>{
  assert.equal(sale(byId('A'),{policy:'SERVED'}).status,'SIGNAL_TO_VERIFY');
  assert.equal(sale(clone('A',{demo:false})).status,'SIGNAL_TO_VERIFY');
  assert.equal(sale(clone('A',{signal_policy_allowed:true}),{policy:'SERVED'}).status,'SIGNAL_TO_VERIFY');
});
test('p_raw sans aucun effet sur probabilité ou classement',()=>{
  const a=sale(clone('A',{p_raw:0.001})),b=sale(clone('A',{p_raw:0.999}));
  assert.equal(a.rank_value,b.rank_value);assert.equal(a.signal.p,0.24);
});
test('la vue vente ne réapplique pas les exclusions logement à une prédiction fournie',()=>{
  const altered=clone('A',{existing:9000,capacity:null,slope:null,zones:['N'],eligibility:'incompatible',geometry_status:'suspect'});
  assert.equal(sale(altered).rank_value,sale(byId('A')).rank_value);
});
test('tri Signal explicite et type de valeur servie contrôlés',()=>{
  assert.equal(api.order(fixtures,{mode:'sale',sort:'signal'})[0].id,'DEMO-A');
  assert.equal(sale(clone('A',{signal_value_kind:'raw_probability'})).status,'SIGNAL_TO_VERIFY');
  assert.throws(()=>api.order(fixtures,{mode:'potential',sort:'signal'}),RangeError);
  assert.throws(()=>api.order(fixtures,{mode:'potential',scenario:'keep',sort:'gain'}),RangeError);
  assert.throws(()=>api.order(fixtures,{mode:'potential',scenario:'divide',sort:'capacity'}),RangeError);
});
test('bornes documentées calculées, traversée zéro à vérifier',()=>{
  const row=potential(clone('A',{capacity:180,existing:180,
    capacity_bounds:{min:170,max:200,documented:true,source:'Hypothèse fictive C'},
    existing_bounds:{min:175,max:185,documented:true,source:'Hypothèse fictive E'}}));
  assert.equal(row.status,'TO_VERIFY');assert.deepEqual(row.bounds.additional_interval,[0,25]);
  assert.deepEqual(row.bounds.gain_interval,[-15,25]);
});
test('en reconstruction, gain incertain autour de zéro ne supprime pas la capacité positive',()=>{
  const row=potential(clone('A',{capacity:180,existing:180,
    capacity_bounds:{min:170,max:200,documented:true,source:'Hypothèse fictive C'},
    existing_bounds:{min:175,max:185,documented:true,source:'Hypothèse fictive E'}}),'rebuild');
  assert.equal(row.status,'ESTIMATED');assert.equal(row.quantities.project_total,180);
  assert.deepEqual(row.bounds.gain_interval,[-15,25]);
});
test('bornes invalides, non sourcées ou contradictoires refusées',()=>{
  for(const bound of [{min:200,max:100,source:'x',documented:true},{min:0,max:1000},
    {min:0,max:50,source:'x',documented:true},{min:-1,max:1300,source:'x',documented:true}])
    assert.equal(potential(clone('B',{capacity_bounds:bound})).status,'TO_VERIFY');
});
test('bornes absentes ou une seule entrée bornée : aucune enveloppe fabriquée',()=>{
  assert.equal(potential(byId('B')).bounds,null);
  const row=potential(clone('B',{capacity_bounds:{min:1100,max:1300,source:'C',documented:true}}));
  assert.equal(row.status,'ESTIMATED');assert.equal(row.bounds,null);
});
test('capacités et existants négatifs, NaN et Infinity refusés',()=>{
  for(const field of ['capacity','existing']) for(const value of [-1,NaN,Infinity])
    assert.equal(potential(clone('B',{[field]:value})).status,'TO_VERIFY');
});
test('absence de plafonnement à 2 000 et tris nommés',()=>{
  const small=clone('B',{id:'SMALL',capacity:2100}),big=clone('B',{id:'BIG',capacity:20000});
  assert.deepEqual(api.order([small,big],{mode:'potential',scenario:'rebuild'}).map(x=>x.id),['BIG','SMALL']);
  assert.deepEqual(api.order([byId('H'),byId('C')],{mode:'potential',scenario:'rebuild',sort:'gain'}).map(x=>x.id),['DEMO-C','DEMO-H']);
});
test('ordre de groupes et valeurs nulles explicites',()=>{
  const rows=api.order(fixtures,{mode:'potential',scenario:'keep'});
  const groups={ESTIMATED:0,PRESTUDY:0,TO_VERIFY:1,DEFERRED:2,NO_MARGIN:3,OUTSIDE_OBJECTIVE:4};
  for(let i=1;i<rows.length;i++) assert(groups[rows[i-1].status]<=groups[rows[i].status]);
});
test('égalité exacte départagée par ID normalisé, sans arrondi',()=>{
  const a=clone('B',{id:' b ',capacity:1.0001}),b=clone('B',{id:'a',capacity:1.0001}),c=clone('B',{id:'c',capacity:1.0002});
  assert.deepEqual(api.order([a,b,c],{}).map(x=>x.id),['C','A','B']);
});
test('petite quantité positive ne s’affiche pas zéro',()=>{
  assert.equal(api.formatQuantity(0.2),'<1 m²');assert.notEqual(api.formatQuantity(null),api.formatQuantity(0));
});
test('moteur pur : aucune mutation des records ou de la sélection',()=>{
  const before=JSON.stringify(fixtures);api.order(fixtures,{scenario:'rebuild'});assert.equal(JSON.stringify(fixtures),before);
});
test('ordre stable entre appels et paramètres invalides refusés',()=>{
  assert.deepEqual(api.order(fixtures,{}).map(x=>x.id),api.order(fixtures.slice().reverse(),{}).map(x=>x.id));
  assert.throws(()=>api.evaluate(byId('A'),{mode:'other'}),RangeError);
  assert.throws(()=>api.order(null,{}),TypeError);
});
process.stdout.write('\n' + count + ' invariants validés. Données fictives ; aucune validation SIG/ML de production.\n');
