import { test, expect } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const plugins = JSON.parse(await readFile(new URL('../content/plugins.json', import.meta.url), 'utf8'));

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('shows all eight free tools and filters by teacher task', async ({ page }) => {
  await expect(page.getByRole('heading', { level: 1 })).toContainText('선생님의 익숙한 AI 도우미');
  await expect(page.locator('[data-plugin-id]:not([hidden])')).toHaveCount(8);
  await expect(page.getByText('8종 모두 무료 ChatGPT 사용자도 사용할 수 있어요.').first()).toBeVisible();

  const counts = [
    ['행정·품의', 3],
    ['특수교육', 2],
    ['개념기반 수업', 2],
    ['학습 게임', 1],
    ['전체', 8],
  ];
  for (const [label, count] of counts) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.locator('[data-plugin-id]:not([hidden])')).toHaveCount(count);
    await expect(page.locator('.filter-status')).toContainText(`${count}개`);
  }
});

test('shows the historical GPTs usage proof and its scope on mobile', async ({ page }) => {
  const proof = page.locator('.hero-proof');
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await page.reload();
    await expect(proof).toBeVisible();
    await expect(proof).toContainText('GPTs 시절 누적 이용 4,800회+');
    await expect(proof).toContainText('기록이 확인된 GPTs 6종 기준');
    const layout = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      proofRight: document.querySelector('.hero-proof').getBoundingClientRect().right,
    }));
    expect(layout.documentWidth, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(layout.viewportWidth);
    expect(layout.proofRight, `proof badge overflow at ${width}px`).toBeLessThanOrEqual(layout.viewportWidth);
  }
});

test('reveals the original name and example prompt for a tool', async ({ page }) => {
  const firstCard = page.locator('[data-plugin-id="pumui-daldal"]');
  await firstCard.locator('summary').click();
  await expect(firstCard.getByText('품의 기안 도우미 (교육청·교육행정용)')).toBeVisible();
  await expect(firstCard.getByText(/첨부 자료를 바탕으로 품의 유형/)).toBeVisible();
  await expect(firstCard.getByText('문서·엑셀은 ChatGPT가 안내하는 자료와 생성 절차에 따라 준비해요.')).toBeVisible();
  await expect(page.locator('[data-plugin-id="approval-excel"]').getByText(/문서·엑셀은 ChatGPT가/)).toHaveCount(0);
});

test('maps every card to its exact ZIP and installation details', async ({ page }) => {
  for (const plugin of plugins) {
    const card = page.locator(`[data-plugin-id="${plugin.id}"]`);
    const download = card.getByRole('link', { name: `${plugin.title} ZIP 다운로드` });
    await expect(download).toHaveAttribute('href', plugin.downloadUrl);
    await card.getByRole('link', { name: '이 도구 설치 방법' }).click();
    await expect(page).toHaveURL(/#install$/);
    await expect(page.locator('[data-selected-plugin]')).toContainText(plugin.title);
    await expect(page.locator('[data-selected-plugin]')).toContainText(plugin.originalName);
    await expect(page.locator('[data-selected-plugin]')).toContainText(plugin.zipFile);
    await expect(page.locator('[data-selected-download]')).toHaveAttribute('href', plugin.downloadUrl);
  }
});

test('loads each original installation screenshot in the guide', async ({ page }) => {
  const screenshots = page.locator('.guide-visual-image .screenshot-trigger img');
  await expect(screenshots).toHaveCount(4);

  for (const image of await screenshots.all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((element) => element.naturalWidth))
      .toBeGreaterThan(0);
  }
});

test('supports keyboard operation of filters and example details', async ({ page }) => {
  const specialEducation = page.getByRole('button', { name: '특수교육', exact: true });
  await specialEducation.focus();
  await page.keyboard.press('Space');
  await expect(page.locator('[data-plugin-id]:not([hidden])')).toHaveCount(2);

  const details = page.locator('[data-plugin-id]:not([hidden]) details').first();
  const summary = details.locator('summary');
  await summary.focus();
  await page.keyboard.press('Enter');
  await expect(details).toHaveAttribute('open', '');
});

test('keeps primary text and touch controls readable with reduced motion', async ({ page }) => {
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: width < 500 ? 844 : 900 });
    await page.reload();
    const metrics = await page.evaluate(() => ({
      bodyFontSize: Number.parseFloat(getComputedStyle(document.body).fontSize),
      bodyCopy: [...document.querySelectorAll(
        '.plugin-facts dd, .guide-description, .faq-item p, .example-guidance, .example-body blockquote, .plugin-detail-note, .original-name strong, .inline-question p, .inline-question blockquote, .section-lede, .catalog-note, .hero-footnote, .selected-tool-copy p, .start-copy > p:not(.eyebrow), .prompt-note, .footer-inner > p',
      )].map((element) => ({
        text: element.textContent.trim().slice(0, 32),
        fontSize: Number.parseFloat(getComputedStyle(element).fontSize),
      })),
      controls: [...document.querySelectorAll(
        '.main-nav a, .button, .filter-button, .button-download, .install-link, .example-details > summary, .screenshot-trigger, .faq-item > summary',
      )].map((element) => ({
        label: element.textContent.trim(),
        height: element.getBoundingClientRect().height,
      })),
    }));
    expect(metrics.bodyFontSize).toBeGreaterThanOrEqual(16);
    for (const paragraph of metrics.bodyCopy) {
      expect(paragraph.fontSize, `${paragraph.text} at ${width}px`).toBeGreaterThanOrEqual(16);
    }
    for (const control of metrics.controls) {
      expect(control.height, `${control.label} at ${width}px`).toBeGreaterThanOrEqual(44);
    }
  }

  await page.emulateMedia({ reducedMotion: 'reduce' });
  const transitionDuration = await page.locator('.button').first().evaluate(
    (element) => getComputedStyle(element).transitionDuration,
  );
  expect(Number.parseFloat(transitionDuration)).toBeLessThan(0.001);
});

test('copies the exact first question from both start and installation guide buttons', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);

  const buttonScopes = [
    '#start',
    '[data-step-id="first-question"]',
  ];
  for (const scope of buttonScopes) {
    const section = page.locator(scope);
    await section.scrollIntoViewIfNeeded();
    await section.locator('[data-copy-first]').click();
    await expect(section.locator('[data-copy-status]')).toContainText('복사했어요');
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText()))
      .toBe('너를 어떻게 활용해? 순서대로 알려줘');
  }
});

test('shows a usable manual-copy fallback when clipboard writing fails', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error('denied')) },
    });
  });
  await page.reload();
  await page.locator('#start').scrollIntoViewIfNeeded();
  await page.locator('#start [data-copy-first]').click();
  await expect(page.locator('#start [data-copy-status]')).toContainText('문장을 직접 선택해 복사해 주세요');
  await expect(page.getByLabel('첫 질문 문장')).toHaveValue('너를 어떻게 활용해? 순서대로 알려줘');
});

test('opens a screenshot detail and returns keyboard focus when dismissed', async ({ page }) => {
  const openButton = page.getByRole('button', { name: '화면 크게 보기' }).first();
  await openButton.focus();
  await openButton.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(openButton).toBeFocused();
});

test('preserves each screenshot highlight in the enlarged dialog', async ({ page }) => {
  const dialog = page.getByRole('dialog');
  const highlight = dialog.locator('[data-dialog-highlight]');
  const boxes = [];

  for (const stepId of ['step-02', 'step-03']) {
    await page.locator(`.guide-visual-${stepId} .screenshot-trigger`).click();
    await expect(dialog).toBeVisible();
    await expect(highlight).toHaveAttribute('data-step', stepId);
    boxes.push(await highlight.boundingBox());
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
  }

  expect(Math.abs(boxes[0].width - boxes[1].width)).toBeGreaterThan(100);
  expect(Math.abs(boxes[0].x - boxes[1].x)).toBeGreaterThan(20);
});

test('fits the page without horizontal scrolling on a phone viewport', async ({ page }) => {
  const reviewDir = path.resolve('review');
  await mkdir(reviewDir, { recursive: true });

  for (const width of [360, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: width < 500 ? 844 : 900 });
    await page.reload();
    const widths = await page.evaluate(() => ({
      document: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(widths.document, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(widths.viewport);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.screenshot({ path: path.join(reviewDir, 'preview-mobile-390.png'), fullPage: true });
  await expect(page.getByRole('link', { name: 'GPT무료계정 설치 방법' })).toBeVisible();

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.reload();
  await page.screenshot({ path: path.join(reviewDir, 'preview-desktop-1440.png'), fullPage: true });
});

test('keeps the catalog and setup copy available when JavaScript is disabled', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto('/');
  await expect(page.locator('[data-plugin-id]')).toHaveCount(8);
  await expect(page.getByText('무료 ChatGPT 사용자도 사용할 수 있어요.', { exact: false }).first()).toBeVisible();
  await expect(page.locator('#first-question')).toHaveValue('너를 어떻게 활용해? 순서대로 알려줘');
  await expect(page.getByText(/카드의.*설치.*설치됨/).first()).toBeVisible();
  await context.close();
});

test('keeps text and alternative descriptions when images cannot load', async ({ page }) => {
  await page.route('**/assets/**', (route) => route.abort());
  await page.reload();
  await expect(page.locator('[data-plugin-id]')).toHaveCount(8);
  await expect(page.getByText('너를 어떻게 활용해? 순서대로 알려줘').first()).toBeVisible();
  await expect(page.locator('.guide-visual-step-03 img')).toHaveAttribute('alt', /업로드 항목/);
  await expect(page.locator('.guide-visual-step-04 figcaption')).toContainText('설치됨');
});
