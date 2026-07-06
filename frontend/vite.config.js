import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
// API FastAPI (labuse api) proxifiée en dev. En prod, FastAPI sert dist/ à la même origine.
const API = 'http://127.0.0.1:8000';
const apiPaths = ['/map', '/parcels', '/stats', '/sources', '/filters', '/discover',
    '/health', '/coverage', '/assemblage', '/compare', '/mutation', '/communes'];
export default defineConfig({
    base: '/socle/', // servi par FastAPI sous /socle (cf. app.py). Dev vite = racine.
    plugins: [react()],
    build: { outDir: 'dist', emptyOutDir: true },
    server: {
        port: 5173,
        proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
    },
});
