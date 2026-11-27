// Recette navigateur des audits 3.10, 4.10 et 5.10 sur l'origine explicitement fournie.
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const baseURL = process.argv[2]
if (!baseURL || new URL(baseURL).protocol !== 'https:') throw Error('Indiquer une origine HTTPS.')
const identifiant = process.env.LABUSE_RECETTE_EMAIL
const password = process.env.LABUSE_RECETTE_PASSWORD
if (!identifiant || !password) throw Error('Configurer le compte de recette LABUSE_RECETTE_EMAIL et LABUSE_RECETTE_PASSWORD.')
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined })
const ids = new Set()
try {
  const ctx = await browser.newContext({ baseURL, viewport: { width: 1440, height: 820 } })
  try {
    await ctx.request.post('/login', { data: { identifiant, password } })
    const p = await ctx.newPage()
    await p.goto('/socle/')
    console.log('Bundle', await p.locator('script[type=module][src]').first().getAttribute('src'))
    const consent = p.getByText('Refuser les tiers', { exact: true })
    if (await consent.isVisible()) await consent.click()
    await p.locator('[data-rail="copilote"]').click()
    for (const width of [1440, 390, 320]) {
      await p.setViewportSize({ width, height: 820 })
      const input = p.locator('[data-copilote-saisie]:visible')
      if (width < 768) {
        await p.locator('[data-conv-menu]:visible').click()
        await p.locator('[data-conv-nouvelle]:visible').click()
        const rect = await input.boundingBox()
        const send = await p.locator('[data-copilote-envoyer]:visible').boundingBox()
        assert.ok(rect.width >= 120 && send.y + send.height <= 820)
        console.log('3.10 OK', width, 'px')
        await input.fill('Brouillon de recette')
        const menu = p.locator('[data-conv-menu]:visible')
        await menu.click()
        const drawer = p.getByRole('dialog', { name: 'Conversations' })
        for (const key of ['Tab', 'Shift+Tab']) {
          for (let i = 0; i < 15; i++) {
            await p.keyboard.press(key)
            assert.ok(await drawer.evaluate(el => el.contains(document.activeElement)))
          }
        }
        await p.keyboard.type('X')
        assert.equal(await input.inputValue(), 'Brouillon de recette')
        await p.keyboard.press('Escape')
        assert.ok(await menu.evaluate(el => el === document.activeElement))
        console.log('4.10 OK', width, 'px')
      }
      await input.fill('Quelle est la surface moyenne des parcelles 97415000BY0083 et 97411000BZ1281 ?')
      const done = p.waitForResponse(r => r.url().endsWith('/api/copilote-v2/ask') && r.request().method() === 'POST', { timeout: 70000 })
      await input.press('Enter')
      const rep = await (await done).json()
      if (rep.conversation_id) ids.add(rep.conversation_id)
      assert.ok(rep.conversation_id && !rep.erreur)
      await p.getByText(rep.text, { exact: true }).first().waitFor()
      await p.keyboard.type('suite de recette')
      assert.equal(await input.inputValue(), 'suite de recette')
      console.log('5.10 OK', width, 'px')
    }
  } finally {
    for (const id of ids) assert.ok((await (await ctx.request.delete('/api/copilote-v2/missions/' + id)).json()).ok)
  }
} finally {
  await browser.close()
}
