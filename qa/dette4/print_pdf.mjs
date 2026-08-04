// HTML → PDF A4 (Chrome système, pattern pack_print_clair : media print émulé AVANT page.pdf).
// Usage : node qa/dette4/print_pdf.mjs <in.html> <out.pdf>   (depuis frontend/ pour node_modules)
import { chromium } from 'playwright'
const [inHtml, outPdf] = process.argv.slice(2)
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage()
await p.goto('file://' + inHtml, { waitUntil: 'load' })
await p.emulateMedia({ media: 'print' })
await p.pdf({ path: outPdf, printBackground: true, format: 'A4' })
await b.close()
console.log('pdf →', outPdf)
