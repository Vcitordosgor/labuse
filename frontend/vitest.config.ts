// M26-B — config Vitest SÉPARÉE de vite.config.ts : le build de production n'est pas
// touché (borne du GO). Vitest la choisit d'office avant vite.config.ts.
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
