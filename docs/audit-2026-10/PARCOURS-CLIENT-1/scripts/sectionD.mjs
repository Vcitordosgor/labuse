// SECTION D — step 9 (écran régulariser, desktop+mobile), step 12 (dashboard : activité du client).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { launchChromium, makeContext, attachPageErrors, loginVic, loginClient, probe, capture, logStep, BASE, ROOT, DESKTOP, MOBILE } from './lib.mjs'

const ctx0 = JSON.parse(readFileSync(resolve(ROOT, 'run-logs/ctx.json'), 'utf-8'))
const browser = await launchChromium()

// ——— step 9 : client expiré, desktop + mobile ———
for (const [device, vp, n] of [['desktop', DESKTOP, 20], ['mobile', MOBILE, 1]]) {
  const { ctx, errors } = await makeContext(browser, vp)
  const page = await ctx.newPage(); attachPageErrors(page, errors)
  const ls = await loginClient(page, ctx0.A_email, ctx0.A_pw, errors)
  await page.waitForTimeout(800)
  await capture(page, device, n, 'D9-essai-expire-regulariser', { fullPage: true })
  const p = await probe(page, errors)
  logStep({ device, name: 'D9 client essai expiré (login)', verdict: p.bodyText.match(/régulariser|intactes|suspendu/i)?.[0] || 'voir capture', url: p.url })
  // in-app : tenter d'ouvrir l'app expirée
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' }).catch(() => {})
  await page.waitForTimeout(1000)
  await capture(page, device, n + 1, 'D9-essai-expire-inapp', { fullPage: true })
  await ctx.close()
}

// ——— step 12 : dashboard Vic — activité du client A ———
{
  const { ctx, errors } = await makeContext(browser, DESKTOP)
  const page = await ctx.newPage(); attachPageErrors(page, errors)
  await loginVic(page, errors)
  // fiche A
  if (!(await page.getByText('TOUR DE CONTRÔLE').count().catch(() => 0))) {
    await page.getByRole('button', { name: 'Admin' }).first().click().catch(() => {}); await page.waitForTimeout(700)
  }
  await page.getByRole('button', { name: /Comptes/ }).first().click().catch(() => {}); await page.waitForTimeout(600)
  await page.getByRole('button', { name: /Tous/ }).first().click().catch(() => {}); await page.waitForTimeout(500)
  const row = page.getByText(ctx0.A_email).first()
  if (await row.count().catch(() => 0)) await row.click(); else await page.getByText(/Téoulé/).first().click().catch(() => {})
  await page.waitForTimeout(800)
  await capture(page, 'desktop', 30, 'D12-fiche-A-apercu', { fullPage: true })
  // onglet Activité
  await page.getByRole('button', { name: /^Activité$/ }).first().click().catch(() => {}); await page.waitForTimeout(700)
  await capture(page, 'desktop', 31, 'D12-fiche-A-activite', { fullPage: true })
  // onglet IA (plafond)
  await page.getByRole('button', { name: /^IA$/ }).first().click().catch(() => {}); await page.waitForTimeout(600)
  await capture(page, 'desktop', 32, 'D12-fiche-A-IA', { fullPage: true })
  // Pilotage global
  await page.getByRole('button', { name: /Pilotage/ }).first().click().catch(() => {}); await page.waitForTimeout(800)
  await capture(page, 'desktop', 33, 'D12-pilotage', { fullPage: true })
  const p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'D12 dashboard activité', verdict: p.bodyText.slice(0, 180).replace(/\n/g, ' ') })
  await ctx.close()
}

await browser.close()
logStep({ name: 'SECTION D captures terminées', verdict: 'OK' })
