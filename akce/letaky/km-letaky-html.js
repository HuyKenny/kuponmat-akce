/**
 * Vrátí VYKRESLENÉ HTML stránky (po doběhnutí JavaScriptu).
 *
 * PROČ: část řetězců na obyčejný request odpoví 403 (Tesco, Kaufland) nebo
 * obsah dosadí až JavaScript. Potřebná data — odkaz na PDF a data platnosti —
 * pak v HTML jsou, jen se k nim bez prohlížeče nedá dostat.
 *
 * Tohle je schválně hloupý nástroj: načti a vrať. Hledání konkrétních dat
 * zůstává v adaptérech, aby se kvůli každému řetězci nemusel měnit prohlížeč.
 *
 *     node km-letaky-html.js <url> [cekani-ms]
 *
 * Vypíše samotné HTML na stdout; chyba jde na stderr a nenulový návratový kód.
 */
const puppeteer = require('puppeteer-core');

const URL_STRANKY = process.argv[2];
const CEKANI = parseInt(process.argv[3] || '4000', 10);

if (!URL_STRANKY) {
  console.error('chybí URL');
  process.exit(1);
}

(async () => {
  let b;
  try {
    b = await puppeteer.launch({
      executablePath: process.env.CHROME_PATH || '/usr/bin/chromium',
      headless: true,
      args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--lang=cs-CZ,cs'],
    });
    const p = await b.newPage();
    await p.setViewport({ width: 1400, height: 1000 });
    await p.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      + '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36');
    await p.setExtraHTTPHeaders({ 'Accept-Language': 'cs-CZ,cs;q=0.9' });
    await p.goto(URL_STRANKY, { waitUntil: 'networkidle2', timeout: 90000 });
    await new Promise(r => setTimeout(r, CEKANI));
    process.stdout.write(await p.content());
  } catch (e) {
    console.error(String(e.message || e).slice(0, 300));
    process.exitCode = 1;
  } finally {
    if (b) await b.close().catch(() => {});
  }
})();
