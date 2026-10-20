import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const distDir = path.join(root, 'dist');
const basePath = '/gpt-plugins_daldal/';
const plugins = JSON.parse(await readFile(path.join(root, 'content/plugins.json'), 'utf8'));
const mimeTypes = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.md', 'text/markdown; charset=utf-8'],
]);

async function startSubpathServer() {
  await stat(path.join(distDir, 'index.html'));
  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url ?? '/', 'http://127.0.0.1');
      if (url.pathname === basePath.slice(0, -1)) {
        response.writeHead(308, { Location: basePath });
        response.end();
        return;
      }
      if (!url.pathname.startsWith(basePath)) {
        response.writeHead(404);
        response.end('Not found');
        return;
      }
      if (url.pathname.endsWith('/favicon.ico')) {
        response.writeHead(204);
        response.end();
        return;
      }

      const relativePath = decodeURIComponent(url.pathname.slice(basePath.length)) || 'index.html';
      let filePath = path.resolve(distDir, relativePath);
      if (filePath !== distDir && !filePath.startsWith(`${distDir}${path.sep}`)) {
        response.writeHead(403);
        response.end('Forbidden');
        return;
      }
      if ((await stat(filePath)).isDirectory()) filePath = path.join(filePath, 'index.html');

      const body = await readFile(filePath);
      response.writeHead(200, {
        'Content-Type': mimeTypes.get(path.extname(filePath).toLowerCase()) ?? 'application/octet-stream',
        'Cache-Control': 'no-store',
      });
      response.end(body);
    } catch {
      response.writeHead(404);
      response.end('Not found');
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  assert.ok(address && typeof address === 'object');
  return {
    server,
    origin: `http://127.0.0.1:${address.port}`,
    url: `http://127.0.0.1:${address.port}${basePath}`,
  };
}

const parseColor = (value) => {
  const color = value.trim();
  if (color.startsWith('#')) {
    const hex = color.slice(1);
    if (hex.length === 3 || hex.length === 4) {
      const parts = [...hex].map((part) => Number.parseInt(part + part, 16));
      return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] === undefined ? 1 : parts[3] / 255 };
    }
    if (hex.length === 6 || hex.length === 8) {
      return {
        r: Number.parseInt(hex.slice(0, 2), 16),
        g: Number.parseInt(hex.slice(2, 4), 16),
        b: Number.parseInt(hex.slice(4, 6), 16),
        a: hex.length === 8 ? Number.parseInt(hex.slice(6, 8), 16) / 255 : 1,
      };
    }
  }
  const match = color.match(/^rgba?\((.*)\)$/i);
  if (!match) return null;
  const values = match[1].trim().split(/[\s,/]+/).filter(Boolean);
  if (values.length < 3) return null;
  const channel = (part) => part.endsWith('%') ? Number.parseFloat(part) * 2.55 : Number.parseFloat(part);
  const alpha = (part) => part === undefined ? 1 : part.endsWith('%') ? Number.parseFloat(part) / 100 : Number.parseFloat(part);
  return {
    r: channel(values[0]),
    g: channel(values[1]),
    b: channel(values[2]),
    a: alpha(values[3]),
  };
};

const preview = await startSubpathServer();
const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort());
  const sameOriginRequests = [];
  const sameOriginResponses = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.origin === preview.origin) sameOriginRequests.push(url.pathname);
  });
  page.on('response', (response) => {
    const url = new URL(response.url());
    if (url.origin === preview.origin) sameOriginResponses.push({ path: url.pathname, status: response.status() });
  });

  const pageResponse = await page.goto(preview.url, { waitUntil: 'domcontentloaded' });
  assert.equal(pageResponse.status(), 200, 'subpath HTML must return HTTP 200');
  await page.waitForFunction(() => [...document.styleSheets].some((sheet) => sheet.href?.includes('/assets/')));
  assert.equal(await page.locator('[data-plugin-id]').count(), 8, 'subpath page must render all eight cards');

  const images = page.locator('.hero-mascot, .screenshot-trigger img');
  assert.equal(await images.count(), 5, 'character image and all four setup screenshots must be present');
  for (const image of await images.all()) {
    await image.scrollIntoViewIfNeeded();
    await image.evaluate((element) => element.decode());
    assert.ok(await image.evaluate((element) => element.naturalWidth > 0), 'each deployed image must decode');
  }
  assert.equal(await page.locator('.screenshot-trigger img').count(), 4, 'all four setup screenshots must be present');
  await page.waitForLoadState('networkidle');

  const localAssetResponses = sameOriginResponses.filter(({ path: requestPath }) => requestPath.includes('/assets/'));
  assert.ok(localAssetResponses.length >= 7, `expected CSS, JS, character art, and screenshots; saw ${localAssetResponses.length} local assets`);
  assert.ok(localAssetResponses.every(({ status }) => status === 200), 'every requested local asset must return HTTP 200');
  assert.ok(localAssetResponses.every(({ path: requestPath }) => requestPath.startsWith(basePath)), 'local assets must stay below the repository subpath');
  assert.ok(localAssetResponses.some(({ path: requestPath }) => requestPath.endsWith('.css')), 'production stylesheet must load under the subpath');
  assert.ok(localAssetResponses.some(({ path: requestPath }) => requestPath.endsWith('.js')), 'production JavaScript must load under the subpath');

  for (const plugin of plugins) {
    const download = page.locator(`[data-plugin-id="${plugin.id}"] .button-download`);
    assert.equal(await download.getAttribute('href'), plugin.downloadUrl, `${plugin.id} ZIP URL must stay correct`);
  }

  for (const anchor of ['plugins', 'install', 'start']) {
    await page.goto(preview.url, { waitUntil: 'domcontentloaded' });
    await page.locator(`a[href="#${anchor}"]`).first().click();
    assert.equal(new URL(page.url()).hash, `#${anchor}`, `#${anchor} navigation must work under the subpath`);
    assert.equal(await page.locator(`#${anchor}`).count(), 1, `#${anchor} target must exist`);
  }

  const badAssetResponses = sameOriginResponses.filter(({ path: requestPath, status }) => requestPath.includes('/assets/') && status !== 200);
  assert.deepEqual(badAssetResponses, [], 'no subpath assets may fail to load');
  assert.ok(sameOriginRequests.filter((requestPath) => requestPath.includes('/assets/')).every((requestPath) => requestPath.startsWith(basePath)));
  console.log(`H15 PASS: served ${basePath}; local CSS/JS/assets returned 200; 4 screenshots, 3 anchors, and 8 ZIP links verified.`);

  const contrastPage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await contrastPage.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort());
  await contrastPage.goto(preview.url, { waitUntil: 'domcontentloaded' });
  await contrastPage.waitForFunction(() => [...document.styleSheets].some((sheet) => sheet.href?.includes('/assets/')));
  await contrastPage.addStyleTag({ content: '*, *::before, *::after { animation: none !important; transition: none !important; }' });
  await contrastPage.evaluate(() => {
    document.querySelectorAll('details').forEach((details) => { details.open = true; });
  });

  const auditVisibleText = () => contrastPage.evaluate(() => {
    const parse = (value) => {
      const normalized = value.trim();
      if (normalized.startsWith('#')) {
        const hexValue = normalized.slice(1);
        if (hexValue.length === 3 || hexValue.length === 4) {
          const channels = [...hexValue].map((part) => Number.parseInt(part + part, 16));
          return { r: channels[0], g: channels[1], b: channels[2], a: channels[3] === undefined ? 1 : channels[3] / 255 };
        }
        if (hexValue.length === 6 || hexValue.length === 8) {
          return {
            r: Number.parseInt(hexValue.slice(0, 2), 16),
            g: Number.parseInt(hexValue.slice(2, 4), 16),
            b: Number.parseInt(hexValue.slice(4, 6), 16),
            a: hexValue.length === 8 ? Number.parseInt(hexValue.slice(6, 8), 16) / 255 : 1,
          };
        }
      }
      const match = normalized.match(/^rgba?\((.*)\)$/i);
      if (!match) return null;
      const values = match[1].trim().split(/[\s,/]+/).filter(Boolean);
      if (values.length < 3) return null;
      const channel = (part) => part.endsWith('%') ? Number.parseFloat(part) * 2.55 : Number.parseFloat(part);
      const alpha = (part) => part === undefined ? 1 : part.endsWith('%') ? Number.parseFloat(part) / 100 : Number.parseFloat(part);
      return { r: channel(values[0]), g: channel(values[1]), b: channel(values[2]), a: alpha(values[3]) };
    };
    const blend = (foreground, background) => {
      const alpha = Math.max(0, Math.min(1, foreground.a));
      return {
        r: foreground.r * alpha + background.r * (1 - alpha),
        g: foreground.g * alpha + background.g * (1 - alpha),
        b: foreground.b * alpha + background.b * (1 - alpha),
        a: 1,
      };
    };
    const unique = (colors) => [...new Map(colors.map((color) => [
      [color.r, color.g, color.b].map((part) => Math.round(part)).join(','), color,
    ])).values()];
    const splitLayers = (value) => {
      const layers = [];
      let depth = 0;
      let start = 0;
      for (let index = 0; index < value.length; index += 1) {
        if (value[index] === '(') depth += 1;
        if (value[index] === ')') depth -= 1;
        if (value[index] === ',' && depth === 0) {
          layers.push(value.slice(start, index));
          start = index + 1;
        }
      }
      layers.push(value.slice(start));
      return layers;
    };
    const imageColors = (layer) => [...layer.matchAll(/#[0-9a-f]{3,8}|rgba?\([^)]*\)/gi)]
      .map((match) => parse(match[0]))
      .filter((color) => color && color.a > 0);
    const applyBackground = (samples, style, opacity) => {
      const color = parse(style.backgroundColor);
      let result = samples;
      if (color && color.a > 0) {
        result = unique(result.map((background) => blend({ ...color, a: color.a * opacity }, background)));
      }
      if (style.backgroundImage && style.backgroundImage !== 'none') {
        for (const layer of splitLayers(style.backgroundImage).reverse()) {
          const colors = imageColors(layer);
          for (const imageColor of colors) {
            result = unique([...result, ...result.map((background) => blend({ ...imageColor, a: imageColor.a * opacity }, background))]);
          }
        }
      }
      return result;
    };
    const backgroundSamples = (element) => {
      const ancestors = [];
      for (let node = element; node; node = node.parentElement) ancestors.push(node);
      let samples = [{ r: 255, g: 255, b: 255, a: 1 }];
      for (const node of ancestors.reverse()) {
        const style = getComputedStyle(node);
        const opacity = Number.parseFloat(style.opacity);
        samples = applyBackground(samples, style, Number.isFinite(opacity) ? opacity : 1);
        if (node.classList?.contains('install-section')) {
          const texture = getComputedStyle(node, '::before');
          samples = applyBackground(samples, texture, Number.parseFloat(texture.opacity));
        }
      }
      return samples;
    };
    const luminance = ({ r, g, b }) => {
      const linear = (component) => {
        const value = component / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
    };
    const ratio = (first, second) => {
      const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
      return (values[0] + 0.05) / (values[1] + 0.05);
    };
    const hex = ({ r, g, b }) => `#${[r, g, b].map((part) => Math.round(part).toString(16).padStart(2, '0')).join('')}`;
    const failures = [];
    const pairs = new Map();
    let checked = 0;
    let minimum = Number.POSITIVE_INFINITY;
    const textElements = [...document.body.querySelectorAll('*')];
    for (const element of textElements) {
      const tag = element.tagName.toLowerCase();
      if (['script', 'style', 'noscript'].includes(tag) || element.closest('[hidden], .visually-hidden, [aria-hidden="true"]')) continue;
      const textNodes = [...element.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
      const controlText = ['textarea', 'input', 'select'].includes(tag)
        ? (tag === 'select' ? element.selectedOptions[0]?.textContent : element.value)
        : '';
      if (textNodes.length === 0 && !controlText) continue;
      const style = getComputedStyle(element);
      if (style.display === 'none' || style.visibility === 'hidden') continue;
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) continue;
      const color = parse(style.color);
      if (!color || color.a <= 0) continue;

      const ancestors = [];
      for (let node = element; node; node = node.parentElement) ancestors.push(node);
      if (ancestors.some((node) => Number.parseFloat(getComputedStyle(node).opacity) === 0)) continue;
      const alpha = ancestors.reduce((value, node) => value * Number.parseFloat(getComputedStyle(node).opacity), color.a);
      const backgrounds = backgroundSamples(element);
      const values = [...textNodes.map((node) => node.textContent.trim()), ...(controlText ? [controlText.trim()] : [])]
        .filter(Boolean);
      for (const background of backgrounds) {
        const effectiveColor = blend({ ...color, a: alpha }, background);
        const contrast = ratio(effectiveColor, background);
        minimum = Math.min(minimum, contrast);
        const key = `${hex(effectiveColor)} on ${hex(background)}`;
        pairs.set(key, Math.min(pairs.get(key) ?? Number.POSITIVE_INFINITY, contrast));
        checked += values.length;
        if (contrast < 4.5) {
          failures.push({
            text: values.join(' ').slice(0, 90),
            rawColor: hex(color),
            effectiveAlpha: Number(alpha.toFixed(3)),
            color: hex(effectiveColor),
            background: hex(background),
            contrast: Number(contrast.toFixed(2)),
            selector: `${tag}${element.id ? `#${element.id}` : ''}${element.className && typeof element.className === 'string' ? `.${element.className.trim().split(/\s+/).join('.')}` : ''}`,
          });
        }
      }
    }
    return {
      checked,
      uniquePairs: pairs.size,
      minimum: Number(minimum.toFixed(2)),
      failures: [...new Map(failures.map((failure) => [`${failure.selector}|${failure.text}|${failure.color}|${failure.background}`, failure])).values()],
    };
  });

  const audits = [];
  for (let step = 0; step < 4; step += 1) {
    await contrastPage.locator('.screenshot-trigger').nth(step).click();
    audits.push(await auditVisibleText());
    await contrastPage.keyboard.press('Escape');
  }
  audits.push(await auditVisibleText());
  const failures = audits.flatMap((audit) => audit.failures);
  const checked = Math.max(...audits.map((audit) => audit.checked));
  const uniquePairs = Math.max(...audits.map((audit) => audit.uniquePairs));
  const minimum = Math.min(...audits.map((audit) => audit.minimum));
  if (failures.length > 0) {
    console.error(`H13 FAIL: ${failures.length} low-contrast text/background pairs found; minimum ${minimum}:`);
    console.error(JSON.stringify(failures.slice(0, 40), null, 2));
  } else {
    console.log(`H13 PASS: ${checked} rendered text samples across ${uniquePairs} computed color pairs; minimum contrast ${minimum}:1 (threshold 4.5:1).`);
  }

  if (failures.length > 0) process.exitCode = 1;
} finally {
  await browser.close();
  await new Promise((resolve, reject) => preview.server.close((error) => error ? reject(error) : resolve()));
}
