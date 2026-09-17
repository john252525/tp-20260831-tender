#!/usr/bin/env node
/**
 * Проверка карточки тендера в РЕАЛЬНОМ браузере (не моки, не jsdom).
 *
 * Зачем: jsdom-тесты не воспроизводят поведение настоящего браузера.
 * Именно этот скрипт выявил, что карточка тендера с 11 000 позиций
 * не открывалась — браузер падал по памяти.
 *
 * Запуск С ХОСТА (не из контейнера: в alpine-образе нет glibc):
 *   cd /opt/tp-20260831-tender/frontend
 *   node e2e/live-card-check.js
 *   node e2e/live-card-check.js <tender_id>
 */
const path = require('path');
const { execSync } = require('child_process');

const FRONTEND_DIR = path.resolve(__dirname, '..');
const ROOT_DIR = path.resolve(FRONTEND_DIR, '..');
const { chromium } = require(path.join(FRONTEND_DIR, 'node_modules/playwright'));

const BASE = process.env.E2E_BASE || 'http://127.0.0.1:18081';
// headless shell экономит память: полный chromium на больших таблицах падает по OOM
const HEADLESS_SHELL = process.env.E2E_SHELL ||
  '/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell';

const sh = (cmd) => execSync(cmd, { cwd: ROOT_DIR, encoding: 'utf8' }).trim();

function createToken() {
  const out = sh('docker compose exec -T backend python -m app.cli.token_cli create --description e2e-live 2>/dev/null');
  const m = out.match(/Token created: (\w+)/);
  if (!m) throw new Error('не удалось создать токен');
  return m[1];
}

function pickTender(kind) {
  const sql = kind === 'big'
    ? "select tender_id from tender_positions group by tender_id order by count(*) desc limit 1"
    : "select t.id from tenders t where (select count(*) from tender_positions p where p.tender_id = t.id) between 3 and 10 limit 1";
  const id = sh(`docker compose exec -T postgres psql -U tender_user -d tender_pipeline -t -A -c "${sql}"`);
  if (!id) throw new Error('не нашёл тендер для проверки');
  return id.trim();
}

async function checkTender(browser, token, tenderId, label) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const failed = [];
  page.on('response', (r) => {
    if (r.url().includes('/api/v1/') && r.status() >= 400) failed.push(`${r.status()} ${r.url()}`);
  });
  await page.addInitScript((t) => localStorage.setItem('api_token', t), token);

  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message.split('\n')[0]));

  await page.goto(`${BASE}/tenders/${tenderId}`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(2000);

  const title = (await page.locator('h1').first().textContent().catch(() => '')).trim();

  // Вкладка «Позиции» — главная проверка на больших закупках
  await page.getByRole('tab', { name: /Позиции/i }).click();
  await page.waitForTimeout(1500);
  const rows = await page.locator('table tbody tr').count();

  let counter = '';
  const counterLoc = page.locator('text=/Показано \\d+ из \\d+/').first();
  if (await counterLoc.count()) counter = (await counterLoc.textContent()).trim();

  const hasMore = await page.getByRole('button', { name: /Показать ещё/ }).count() > 0;

  await page.getByRole('tab', { name: /Документы/i }).click();
  await page.waitForTimeout(1000);
  const bodyText = await page.locator('body').innerText();
  const docs = [...bodyText.matchAll(/[\wА-Яа-яЁё №()._-]+\.(docx|xlsx|doc|pdf|rar|zip)/gi)].length;

  await page.close();

  const ok = rows > 0 && errors.length === 0;
  console.log(`\n[${label}] ${title.slice(0, 60)}`);
  console.log(`  строк отрисовано: ${rows}`);
  if (counter) console.log(`  счётчик: ${counter}`);
  console.log(`  кнопка «Показать ещё»: ${hasMore ? 'есть' : 'нет'}`);
  console.log(`  документов: ${docs}`);
  if (errors.length) console.log(`  ОШИБКИ JS: ${errors.join(' | ')}`);
  if (failed.length) console.log(`  ОШИБКИ API: ${failed.join(' | ')}`);
  console.log(`  итог: ${ok ? 'OK' : 'ПРОВАЛ'}`);
  return ok;
}

(async () => {
  const token = createToken();
  const explicitId = process.argv[2];

  const browser = await chromium.launch({
    executablePath: HEADLESS_SHELL,
    args: ['--disable-dev-shm-usage', '--no-sandbox', '--disable-gpu'],
  });

  const results = [];
  try {
    if (explicitId) {
      results.push(await checkTender(browser, token, explicitId, 'указанный тендер'));
    } else {
      results.push(await checkTender(browser, token, pickTender('big'), 'большая закупка'));
      results.push(await checkTender(browser, token, pickTender('small'), 'маленькая закупка'));
    }
  } finally {
    await browser.close();
  }

  const passed = results.filter(Boolean).length;
  console.log(`\n=== ИТОГ: ${passed} из ${results.length} проверок пройдено ===`);
  process.exit(passed === results.length ? 0 : 1);
})().catch((e) => {
  console.error('ОШИБКА:', e.message.split('\n')[0]);
  process.exit(1);
});
