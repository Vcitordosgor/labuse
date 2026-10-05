import { launchChromium, makeContext, BASE, MOBILE, logStep } from './lib.mjs'
const browser = await launchChromium()
const { ctx } = await makeContext(browser, MOBILE)
const page = await ctx.newPage()
let seq = 2
for (const [u, slug] of [['/login','login'],['/cgv','legal-cgv'],['/mentions-legales','legal-mentions'],['/confidentialite','legal-confidentialite'],['/invitation?token=EXPIRE','invitation-expire']]) {
  await page.goto(BASE + u, { waitUntil: 'domcontentloaded' }).catch(()=>{})
  await page.waitForTimeout(400)
  await page.screenshot({ path: `captures/mobile/${String(++seq).padStart(2,'0')}-C-${slug}.png`, fullPage: true })
}
logStep({ name: 'mobile public pages', verdict: '5 pages' })
await browser.close()
