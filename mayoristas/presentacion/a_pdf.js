// Convierte catalogo_mayorista.html en Catalogo_Mayorista_OPA.pdf y una vista previa PNG.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
  await page.goto('file://' + path.join(__dirname, 'catalogo_mayorista.html'));
  await page.pdf({ path: path.join(__dirname, 'Catalogo_Mayorista_OPA.pdf'), format: 'A4', printBackground: true });
  await page.screenshot({ path: path.join(__dirname, 'preview.png'), fullPage: true });
  await browser.close();
})();
