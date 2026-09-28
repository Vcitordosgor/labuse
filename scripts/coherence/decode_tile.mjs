// COHERENCE-1 — décodeur de tuiles MVT pour le banc (lecture seule).
// Usage : node decode_tile.mjs <fichier.pbf>  → JSON {layer: [{props…}]}
// S'appuie sur les node_modules du front (symlink) : @mapbox/vector-tile + pbf.
import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(here, '..', '..', 'frontend', 'package.json'));
const { VectorTile } = require('@mapbox/vector-tile');
const Protobuf = require('pbf');

const buf = readFileSync(process.argv[2]);
const tile = new VectorTile(new Protobuf(buf));
const out = {};
for (const name of Object.keys(tile.layers)) {
  const layer = tile.layers[name];
  out[name] = [];
  for (let i = 0; i < layer.length; i++) out[name].push(layer.feature(i).properties);
}
process.stdout.write(JSON.stringify(out));
