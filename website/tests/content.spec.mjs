import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const plugins = JSON.parse(await readFile(path.join(root, 'content/plugins.json'), 'utf8'));
const guide = JSON.parse(await readFile(path.join(root, 'content/guide.json'), 'utf8'));
const template = await readFile(path.join(root, 'src/index.template.html'), 'utf8');

test('catalog contains the eight approved plugins in the approved order', () => {
  assert.deepEqual(plugins.map(({ id }) => id), [
    'pumui-daldal',
    'approval-excel',
    'related-document-extractor',
    'iep-plan',
    'iep-eval',
    'ib-core',
    'ib-planner',
    'canva-game',
  ]);
  assert.equal(new Set(plugins.map(({ id }) => id)).size, 8);
  assert.ok(plugins.every(({ freeAvailable }) => freeAvailable === true));
  assert.equal(
    plugins[0].detailNote,
    '문서·엑셀은 ChatGPT가 안내하는 자료와 생성 절차에 따라 준비해요.',
  );
  assert.ok(plugins.slice(1).every((plugin) => !Object.hasOwn(plugin, 'detailNote')));
});

test('each catalog item links its exact individual ZIP', () => {
  const files = [
    'pumui-daldal-0.1.10.zip',
    'approval-excel.zip',
    'related-document-extractor.zip',
    'iep-plan.zip',
    'iep-eval.zip',
    'ib-core.zip',
    'ib-planner.zip',
    'canva-game.zip',
  ];

  assert.deepEqual(plugins.map(({ zipFile }) => zipFile), files);
  for (const plugin of plugins) {
    assert.equal(
      plugin.downloadUrl,
      `https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/downloads/${plugin.zipFile}`,
    );
  }
});

test('plugin outcomes describe concrete workload savings and model compatibility', () => {
  for (const plugin of plugins) {
    assert.match(plugin.output, /줄여요|덜어요/, `${plugin.id} should state a workload reduction`);
  }

  const approvalOutput = plugins.find(({ id }) => id === 'approval-excel').output;
  assert.match(approvalOutput, /장바구니 목록을 붙여 넣고/);
  assert.match(approvalOutput, /견적서를 올린 뒤 필요한 정보를 몇 가지 입력하면/);
  assert.match(approvalOutput, /학교 품의문 초안과 에듀파인 업로드용 엑셀/);
  assert.match(approvalOutput, /품목을 하나씩 다시 입력하는 수고를 덜어요/);

  const gameOutput = plugins.find(({ id }) => id === 'canva-game').output;
  assert.match(gameOutput, /생성한 프롬프트를 GPT, 클로드\(Claude\), 제미나이\(Gemini\)/);
  assert.doesNotMatch(gameOutput, /플러그인.*GPT|GPT.*플러그인/);
});

test('hero proof states historical GPTs usage and its confirmed six-plugin scope', () => {
  assert.match(template, /<strong>GPTs 시절 누적 이용 4,800회\+<\/strong>/);
  assert.match(template, /<span>기록이 확인된 GPTs 6종 기준<\/span>/);
  assert.doesNotMatch(template.match(/<p class="hero-proof">[\s\S]*?<\/p>/)?.[0] ?? '', /다운로드|사용자|이용자/);
});

test('free install instructions explicitly target a free ChatGPT account', () => {
  assert.match(template, /이 안내는 무료 ChatGPT 계정 기준이에요/);
  assert.match(guide.freeMessage, /8종 모두 무료 ChatGPT 사용자도 사용할 수 있어요/);
});

test('guide preserves the exact first question and the real install sequence', () => {
  assert.equal(guide.firstPrompt, '너를 어떻게 활용해? 순서대로 알려줘');
  assert.deepEqual(guide.steps.map(({ id }) => id), [
    'prepare',
    'step-01',
    'step-02',
    'step-03',
    'step-04',
    'choose-plugin',
    'first-question',
    'provide-materials',
  ]);

  const step03 = guide.steps.find(({ id }) => id === 'step-03');
  const step04 = guide.steps.find(({ id }) => id === 'step-04');
  assert.match(step03.description, /플러그인 압축 파일 업로드/);
  assert.match(step03.imageAlt, /추가 메뉴/);
  assert.doesNotMatch(step03.imageAlt, /파일 선택 창/);
  assert.match(step04.description, /\+.*설치.*설치됨/);
});

test('installation screenshots use the original PNGs and distinct descriptions', () => {
  assert.deepEqual(
    guide.steps.filter(({ image }) => image).map(({ image }) => image),
    [
      'assets/install/source-01.png',
      'assets/install/source-02.png',
      'assets/install/source-03.png',
      'assets/install/source-04.png',
    ],
  );
  assert.ok(guide.steps.filter(({ image }) => image).every(({ imageAlt }) => imageAlt?.length > 10));
});

test('answers the common setup questions without promising automatic installation', () => {
  const faqText = guide.faq.map(({ question, answer }) => `${question} ${answer}`).join(' ');
  assert.ok(guide.faq.length >= 5);
  assert.match(faqText, /무료 ChatGPT/);
  assert.match(faqText, /압축을 풀지/);
  assert.match(faqText, /\+.*설치/);
  assert.match(faqText, /채팅/);
  assert.doesNotMatch(faqText, /자동 설치 완료|한 번의 클릭으로 설치/);
});
