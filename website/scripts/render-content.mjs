import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const template = await readFile(path.join(root, 'src/index.template.html'), 'utf8');
const plugins = JSON.parse(await readFile(path.join(root, 'content/plugins.json'), 'utf8'));
const guide = JSON.parse(await readFile(path.join(root, 'content/guide.json'), 'utf8'));

const categories = {
  admin: '행정·품의',
  iep: '특수교육',
  concept: '개념기반 수업',
  game: '학습 게임',
};

const icons = {
  'pumui-daldal': '🧾',
  'approval-excel': '📑',
  'related-document-extractor': '🔎',
  'iep-plan': '🧩',
  'iep-eval': '✏️',
  'ib-core': '💡',
  'ib-planner': '🗂️',
  'canva-game': '🎲',
};

const visuals = {
  prepare: ['ZIP', '압축은 풀지 않아요'],
  'choose-plugin': ['+', '플러그인을 골라요'],
  'first-question': ['“ ”', '첫 질문을 보내요'],
  'provide-materials': ['↗', '자료와 내용을 건네요'],
};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
}

function renderPlugin(plugin) {
  const title = escapeHtml(plugin.title);
  const originalName = escapeHtml(plugin.originalName);
  const examplePrompt = escapeHtml(plugin.examplePrompt);
  const category = escapeHtml(plugin.category);
  const categoryLabel = escapeHtml(categories[plugin.category]);
  const zipFile = escapeHtml(plugin.zipFile);
  const downloadUrl = escapeHtml(plugin.downloadUrl);
  const sourceUrl = escapeHtml(plugin.sourceUrl);
  const detailNote = plugin.detailNote
    ? `<p class="plugin-detail-note">${escapeHtml(plugin.detailNote)}</p>`
    : '';

  return `
    <article class="plugin-card accent-${category}" data-plugin-id="${escapeHtml(plugin.id)}" data-category="${category}" data-zip-file="${zipFile}">
      <div class="plugin-card-top">
        <span class="plugin-icon" aria-hidden="true">${icons[plugin.id]}</span>
        <span class="category-chip">${categoryLabel}</span>
        <span class="free-mini"><span aria-hidden="true">✿</span> 무료 사용 가능</span>
      </div>
      <h3>${title}</h3>
      <dl class="plugin-facts">
        <div><dt>무엇을 준비해요</dt><dd>${escapeHtml(plugin.input)}</dd></div>
        <div><dt>반복 작업을 이렇게 줄여요</dt><dd>${escapeHtml(plugin.output)}</dd></div>
      </dl>
      <div class="card-actions">
        <a class="button button-download" href="${downloadUrl}" target="_blank" rel="noreferrer" aria-label="${title} ZIP 다운로드">
          <svg aria-hidden="true" viewBox="0 0 20 20"><path d="M10 2.5v9m0 0 3.4-3.4M10 11.5 6.6 8.1M3.5 13.5v3h13v-3" /></svg>
          ZIP 다운로드
        </a>
        <a class="install-link" href="#install" data-install-plugin="${escapeHtml(plugin.id)}">
          이 도구 설치 방법 <span aria-hidden="true">↗</span>
        </a>
      </div>
      <details class="example-details">
        <summary>사용 예시 보기</summary>
        <div class="example-body">
          <p class="original-name"><span>플러그인 목록 이름</span><strong>${originalName}</strong></p>
          ${detailNote}
          <a class="source-link" href="${sourceUrl}" target="_blank" rel="noreferrer">원본 안내 보기 <span aria-hidden="true">↗</span></a>
          <p class="example-guidance">이 도구를 채팅에서 선택한 뒤 아래처럼 물어보세요.</p>
          <blockquote>${examplePrompt}</blockquote>
          <div class="example-actions">
            <button class="example-copy" type="button" data-copy-text="${examplePrompt}">요청 예시 복사</button>
            <span class="copy-status" data-copy-status role="status" aria-live="polite"></span>
          </div>
        </div>
      </details>
      <span class="card-fold" aria-hidden="true"></span>
    </article>`;
}

function renderStep(step, index) {
  const badge = step.id === 'prepare'
    ? 'ZIP 준비'
    : step.id.startsWith('step-')
      ? step.id.slice(-2)
      : step.id === 'choose-plugin'
        ? '채팅에서 선택'
        : step.id === 'first-question'
          ? '첫 질문'
          : '자료 제공';
  const imagePath = step.image ? `./${escapeHtml(step.image)}` : '';
  const imageBlock = step.image
    ? `<figure class="guide-visual guide-visual-image guide-visual-${escapeHtml(step.id)}">
        <button class="screenshot-trigger" type="button" data-open-image data-image-src="${imagePath}" data-image-alt="${escapeHtml(step.imageAlt)}" data-image-title="${escapeHtml(step.title)}" aria-label="화면 크게 보기: ${escapeHtml(step.title)}">
          <img src="${imagePath}" alt="${escapeHtml(step.imageAlt)}" loading="lazy" decoding="async" />
          <span class="screenshot-highlight" aria-hidden="true"></span>
          <span class="zoom-cue"><span aria-hidden="true">⌕</span> 화면 크게 보기</span>
        </button>
        <figcaption>${step.id === 'step-03'
          ? '02와 같은 메뉴 화면이에요. 이 항목을 누른 뒤 ZIP을 골라 업로드해요.'
          : step.id === 'step-04'
            ? '캡처는 카드 오른쪽 +까지 보여요. 다음 메뉴에서 설치를 누르고 설치됨을 확인해요.'
            : escapeHtml(step.description)}</figcaption>
      </figure>`
    : `<div class="guide-visual guide-visual-note" aria-hidden="true">
        <span class="guide-visual-symbol">${visuals[step.id][0]}</span>
        <span class="guide-visual-label">${visuals[step.id][1]}</span>
      </div>`;
  const questionBlock = step.id === 'first-question'
    ? `<div class="inline-question"><p>${escapeHtml(step.description)}</p><blockquote>${escapeHtml(guide.firstPrompt)}</blockquote><button class="example-copy" type="button" data-copy-first>질문 복사</button><span class="copy-status" data-copy-status role="status" aria-live="polite"></span></div>`
    : '';
  const description = questionBlock ? '' : `<p class="guide-description">${escapeHtml(step.description)}</p>`;

  return `
    <article class="guide-card ${step.image ? 'has-screenshot' : 'has-illustration'}" data-step-id="${escapeHtml(step.id)}" style="--step-order:${index + 1}">
      <div class="guide-card-copy">
        <span class="guide-step-badge">${escapeHtml(badge)}</span>
        <h3>${escapeHtml(step.title)}</h3>
        ${description}
        ${questionBlock}
      </div>
      ${imageBlock}
    </article>`;
}

function renderFaq(item) {
  return `<details class="faq-item"><summary>${escapeHtml(item.question)}</summary><p>${escapeHtml(item.answer)}</p></details>`;
}

const output = template
  .replace('{{FREE_MESSAGE}}', escapeHtml(guide.freeMessage))
  .replace('{{FIRST_PROMPT}}', escapeHtml(guide.firstPrompt))
  .replace('{{GITHUB_URL}}', escapeHtml(guide.sourceUrls.github))
  .replaceAll('{{NOTION_URL}}', escapeHtml(guide.sourceUrls.notion))
  .replace('{{PLUGIN_CARDS}}', plugins.map(renderPlugin).join('\n'))
  .replace('{{INSTALL_STEPS}}', guide.steps.map(renderStep).join('\n'))
  .replace('{{FAQ_ITEMS}}', guide.faq.map(renderFaq).join('\n'));

if (/\{\{[A-Z_]+\}\}/.test(output)) {
  throw new Error('index template contains an unfilled content token');
}

await writeFile(path.join(root, 'index.html'), output, 'utf8');
console.log(`Rendered ${plugins.length} plugin cards and ${guide.steps.length} guide steps to website/index.html`);
