import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
const plugins = JSON.parse(await readFile(new URL('../content/plugins.json', import.meta.url), 'utf8'));

test('individual URLs are visible and copy the exact plugin address', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/');
  for (const plugin of plugins) {
    const card = page.locator('[data-plugin-id="' + plugin.id + '"]');
    await expect(card.locator('.plugin-url')).toBeVisible();
    await expect(card.locator('.plugin-url')).toHaveAttribute('href', plugin.sourceUrl);
    await card.locator('[data-copy-url]').click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(plugin.sourceUrl);
  }
  await page.locator('.plugin-url-panel a[href="#github-connect"]').first().click();
  await expect(page.locator('#github-connect')).toBeVisible();
  await expect(page.locator('#github-connect')).toContainText('Continue with Google');
  await expect(page.locator('#github-connect')).toContainText('플러그인 설치는 별도');
});

test('URL remains selectable when clipboard access is denied', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
    configurable: true, value: { writeText: () => Promise.reject(new Error('denied')) },
  }));
  await page.goto('/');
  const card = page.locator('[data-plugin-id]').first();
  await card.locator('[data-copy-url]').click();
  await expect.poll(() => page.evaluate(() => window.getSelection().toString())).toBe(plugins[0].sourceUrl);
  await expect(card.locator('.plugin-url-panel > .example-actions [data-copy-status]')).toContainText('직접 선택');
});

test('copies complete installation requests for every plugin', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/');
  for (const plugin of plugins) {
    const card = page.locator('[data-plugin-id="' + plugin.id + '"]');
    await card.locator('.install-prompt-details summary').click();
    await card.locator('[data-copy-install]').click();
    const text = await page.evaluate(() => navigator.clipboard.readText());
    expect(text).toContain('@plugin-creator');
    expect(text).toContain(plugin.sourceUrl);
    expect(text).toContain(plugin.downloadUrl);
    expect(text).toContain('중복 생성하지 말고');
    expect(text).toContain('실제 반환된 플러그인 링크');
    await expect(card.locator('.install-prompt-text')).toHaveValue(text.replace(/\r\n/g, '\n'));
  }
});

test('installation request fallback selects the full text', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
    configurable: true, value: { writeText: () => Promise.reject(new Error('denied')) },
  }));
  await page.goto('/');
  const card = page.locator('[data-plugin-id]').first();
  await card.locator('.install-prompt-details summary').click();
  await card.locator('[data-copy-install]').click();
  const field = card.locator('.install-prompt-text');
  await expect(field).toBeFocused();
  expect(await field.evaluate(e => e.value.slice(e.selectionStart, e.selectionEnd))).toBe(await field.inputValue());
});
