import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const plugins = JSON.parse(await readFile(path.join(root, 'content/plugins.json'), 'utf8'));
const signature = Buffer.from([0x50, 0x4b, 0x03, 0x04]);

const results = await Promise.all(plugins.map(async (plugin) => {
  const response = await fetch(plugin.downloadUrl, {
    headers: { Range: 'bytes=0-3' },
    signal: AbortSignal.timeout(20_000),
  });
  const bytes = Buffer.from(await response.arrayBuffer());
  const expectedUrl = `https://raw.githubusercontent.com/yundaldal/gpt-plugins_daldal/refs/heads/main/downloads/${plugin.zipFile}`;

  if (!response.ok) {
    throw new Error(`${plugin.id}: HTTP ${response.status} for ${plugin.downloadUrl}`);
  }
  if (response.url !== expectedUrl) {
    throw new Error(`${plugin.id}: resolved to unexpected URL ${response.url}`);
  }
  if (!bytes.subarray(0, 4).equals(signature)) {
    throw new Error(`${plugin.id}: response does not start with a ZIP signature`);
  }

  console.log(`${plugin.id}: HTTP ${response.status}, ${plugin.zipFile}, ZIP signature OK`);
}));

console.log(`Verified ${results.length} plugin ZIP links.`);
