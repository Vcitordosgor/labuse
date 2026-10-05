// SECTION A — capture les 16 rendus HTML (mails/html/*.html) en PNG desktop + mobile.
import { readdirSync } from 'node:fs'
import { resolve, basename } from 'node:path'
import { pathToFileURL } from 'node:url'
import { launchChromium, makeContext, ROOT, DESKTOP, MOBILE, logStep } from './lib.mjs'

const dir = resolve(ROOT, 'mails/html')
const files = readdirSync(dir).filter((f) => f.endsWith('.html')).sort()
const browser = await launchChromium()

for (const [label, vp] of [['desktop', { width: 800, height: 900 }], ['mobile', MOBILE]]) {
  const { ctx } = await makeContext(browser, vp)
  const page = await ctx.newPage()
  for (const f of files) {
    const slug = basename(f, '.html')
    await page.goto(pathToFileURL(resolve(dir, f)).href, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(150)
    await page.screenshot({ path: resolve(ROOT, 'mails', `${slug}-${label}.png`), fullPage: true })
  }
  await ctx.close()
  logStep({ name: `mails capturés (${label})`, verdict: files.length + ' templates' })
}
await browser.close()
