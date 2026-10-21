import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const plugins = JSON.parse(await readFile(path.join(root, 'content/plugins.json'), 'utf8'));
const guide = JSON.parse(await readFile(path.join(root, 'content/guide.json'), 'utf8'));
const html = await readFile(path.join(root, 'index.html'), 'utf8');

const expectedIds = [
  'pumui-daldal',
  'approval-excel',
  'related-document-extractor',
  'iep-plan',
  'iep-eval',
  'ib-core',
  'ib-planner',
  'canva-game',
];
const expectedFiles = [
  'pumui-daldal-0.1.11.zip',
  'approval-excel.zip',
  'related-document-extractor.zip',
  'iep-plan.zip',
  'iep-eval.zip',
  'ib-core.zip',
  'ib-planner.zip',
  'canva-game.zip',
];
const expectedSteps = [
  'prepare',
  'step-01',
  'step-02',
  'step-03',
  'step-04',
  'choose-plugin',
  'first-question',
  'provide-materials',
];

assert.deepEqual(plugins.map(({ id }) => id), expectedIds, 'catalog IDs must match the approved eight tools');
assert.deepEqual(plugins.map(({ zipFile }) => zipFile), expectedFiles, 'ZIP filenames must match the release directory');
assert.ok(plugins.every(({ freeAvailable }) => freeAvailable === true), 'all eight tools must retain the free availability message');
assert.ok(plugins.every(({ downloadUrl, zipFile }) => downloadUrl.endsWith(`/downloads/${zipFile}`)), 'each link must point to its matching individual ZIP');
assert.ok(plugins.every(({ output }) => /줄여요|덜어요/.test(output)), 'each plugin outcome must explain workload saved');
assert.deepEqual(guide.steps.map(({ id }) => id), expectedSteps, 'guide steps must retain the approved order');
assert.equal(guide.firstPrompt, '너를 어떻게 활용해? 순서대로 알려줘', 'first question must stay exact');
const educationAdminNote = '문서·엑셀은 ChatGPT가 안내하는 자료와 생성 절차에 따라 준비해요.';
assert.equal(plugins[0].detailNote, educationAdminNote, 'education administration note must belong to the first plugin');
assert.ok(plugins.slice(1).every((plugin) => !Object.hasOwn(plugin, 'detailNote')), 'education administration note must not appear on other plugins');

const approvalOutput = plugins.find(({ id }) => id === 'approval-excel').output;
assert.match(approvalOutput, /장바구니 목록을 붙여 넣고/);
assert.match(approvalOutput, /견적서를 올린 뒤 필요한 정보를 몇 가지 입력하면/);
assert.match(approvalOutput, /학교 품의문 초안과 에듀파인 업로드용 엑셀/);
assert.match(approvalOutput, /품목을 하나씩 다시 입력하는 수고를 덜어요/);

const gameOutput = plugins.find(({ id }) => id === 'canva-game').output;
assert.match(gameOutput, /생성한 프롬프트|만든 프롬프트/);
assert.match(gameOutput, /GPT, 클로드\(Claude\), 제미나이\(Gemini\)/);
assert.doesNotMatch(gameOutput, /플러그인.*GPT|GPT.*플러그인/);

for (const id of expectedIds) {
  assert.match(html, new RegExp(`data-plugin-id="${id}"`), `rendered page is missing ${id}`);
}
for (const file of expectedFiles) {
  assert.ok(html.includes(file), `rendered page is missing ${file}`);
}
assert.ok(html.includes('너를 어떻게 활용해? 순서대로 알려줘'), 'rendered page is missing the first question');
assert.ok(html.includes('플러그인 압축 파일 업로드'), 'rendered page is missing the upload action');
assert.ok(html.includes('카드 오른쪽의 +를 누르고'), 'rendered page is missing the separate install action');
assert.ok(html.includes('설치됨'), 'rendered page is missing the installed state');
assert.equal(html.split(educationAdminNote).length - 1, 1, 'rendered page must show the education administration note only once');
assert.equal((html.match(/data-step-id=/g) ?? []).length, expectedSteps.length, 'rendered page must include all guide steps');

assert.ok(html.includes('반복 작업을 이렇게 줄여요'), 'rendered page is missing the workload-saving heading');
assert.ok(!html.includes('어떤 결과를 받아요'), 'rendered page retains the old results heading');
assert.ok(html.includes('이 안내는 무료 ChatGPT 계정 기준이에요.'), 'rendered install section must identify the free-account instructions');
assert.ok(html.includes('8종 모두 무료 ChatGPT 사용자도 사용할 수 있어요.'), 'rendered page must retain free ChatGPT availability');

const heroProof = html.match(/<p class="hero-proof">[\s\S]*?<\/p>/)?.[0];
assert.ok(heroProof?.includes('GPTs 시절 누적 이용 4,800회+'), 'rendered page must show the historical usage count');
assert.ok(heroProof?.includes('기록이 확인된 GPTs 6종 기준'), 'usage count must identify its confirmed scope');
assert.doesNotMatch(heroProof ?? '', /다운로드|사용자|이용자/, 'usage count must not imply downloads or people');

console.log(`Content OK: ${plugins.length} tools, ${guide.steps.length} guide steps, ${guide.faq.length} FAQs.`);
