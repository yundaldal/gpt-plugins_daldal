import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { installationPrompt } from './installation-prompt.mjs';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const template = await readFile(path.join(root, 'src/index.template.html'), 'utf8');
const plugins = JSON.parse(await readFile(path.join(root, 'content/plugins.json'), 'utf8'));
const skills = JSON.parse(await readFile(path.join(root, 'content/skills.json'), 'utf8'));
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
  const installPrompt = escapeHtml(installationPrompt(plugin));
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
      <div class="plugin-url-panel">
        <p><strong>ChatGPT에 전달할 개별 GitHub URL</strong></p>
        <a class="plugin-url" href="${sourceUrl}" target="_blank" rel="noreferrer">${sourceUrl}</a>
        <div class="example-actions">
          <button class="example-copy" type="button" data-copy-text="${sourceUrl}" data-copy-url aria-label="${title} GitHub URL 복사">URL 복사</button>
          <span class="copy-status" data-copy-status role="status" aria-live="polite"></span>
        </div>
        <p>Plugin Creator를 선택한 채팅에 설치 요청문을 붙여넣으세요. 지원되는 환경에서 생성·등록을 진행하며, 설치 확인이 추가로 필요할 수 있어요. <a href="#github-connect">연결·설치 안내</a></p>
        <details class="install-prompt-details">
          <summary>채팅 설치 요청문 보기</summary>
          <label class="visually-hidden" for="install-prompt-${escapeHtml(plugin.id)}">${title} 설치 요청문</label>
          <textarea id="install-prompt-${escapeHtml(plugin.id)}" class="install-prompt-text" readonly rows="9">${installPrompt}</textarea>
          <div class="example-actions">
            <button class="example-copy" type="button" data-copy-text="${installPrompt}" data-copy-install aria-label="${title} 설치 요청문 복사">설치 요청문 복사</button>
            <span class="copy-status" data-copy-status role="status" aria-live="polite"></span>
          </div>
        </details>
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

function renderSkill(skill) {
  const title = escapeHtml(skill.title);
  const sourceUrl = escapeHtml(skill.sourceUrl);
  const skillFileUrl = escapeHtml(skill.skillFileUrl);
  const downloadUrl = escapeHtml(skill.downloadUrl);
  const githubHelp = 'https://support.claude.com/ko/articles/12512180-claude%EC%97%90%EC%84%9C-%EC%8A%A4%ED%82%AC-%EC%82%AC%EC%9A%A9%ED%95%98%EA%B8%B0';

  return `
    <article class="plugin-card skill-card" data-skill-id="${escapeHtml(skill.id)}">
      <div class="plugin-card-top">
        <span class="category-chip">독립 스킬</span>
        <span class="free-mini">Claude 무료 사용 가능</span>
        <span class="availability-chip unavailable">ChatGPT 무료 사용 불가</span>
      </div>
      <h3>${title}</h3>
      <dl class="plugin-facts">
        <div><dt>무엇을 하나요</dt><dd>${escapeHtml(skill.input)}</dd></div>
        <div><dt>어떤 도움을 주나요</dt><dd>${escapeHtml(skill.output)}</dd></div>
      </dl>
      <div class="skill-platform-notes">
        <h4>Claude 무료 계정</h4>
        <ol>
          <li><strong>설정 → 기능</strong>에서 <strong>코드 실행 및 파일 생성</strong>이 켜져 있는지 확인하세요. 새 화면에서는 <strong>파일 생성 및 편집</strong>으로 표시될 수 있어요. 무료 계정은 기본으로 켜져 있을 수 있으니, 꺼져 있을 때만 켜면 됩니다.</li>
          <li>ZIP을 받은 뒤 <strong>사용자 정의 → 스킬 → + → + 스킬 만들기 → 스킬 업로드</strong>를 차례로 누르세요. 업로드가 끝나면 스킬 목록에서 켜세요.</li>
        </ol>
        <p><a href="${githubHelp}" target="_blank" rel="noreferrer">Claude 한국어 공식 스킬 안내</a></p>
        <h4>ChatGPT 무료 계정</h4>
        <p>이 독립 Skill은 무료 ChatGPT에서 사용할 수 없습니다. ChatGPT에서 Skill을 직접 등록·실행할 수 있다고 보장하지 않으며, Plugin Creator가 보이더라도 스킬 설치가 지원되는지 계정에서 확인해야 합니다.</p>
      </div>
      <div class="card-actions">
        <a class="button button-download" href="${downloadUrl}" target="_blank" rel="noreferrer" aria-label="${title} Claude 스킬 ZIP 다운로드">스킬 ZIP 받기</a>
        <a class="source-link" href="${sourceUrl}" target="_blank" rel="noreferrer">GitHub 원본 <span aria-hidden="true">↗</span></a>
      </div>
      <p class="skill-source-note">원본 Skill.md: <a href="${skillFileUrl}" target="_blank" rel="noreferrer">${skillFileUrl}</a> · ${escapeHtml(skill.license)} License</p>
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
  .replace('{{SKILL_COUNT}}', String(skills.length))
  .replace('{{SKILL_CARDS}}', skills.map(renderSkill).join('\n'))
  .replace('{{INSTALL_STEPS}}', guide.steps.map(renderStep).join('\n'))
  .replace('{{FAQ_ITEMS}}', guide.faq.map(renderFaq).join('\n'));

if (/\{\{[A-Z_]+\}\}/.test(output)) {
  throw new Error('index template contains an unfilled content token');
}

await writeFile(path.join(root, 'index.html'), output, 'utf8');
console.log(`Rendered ${plugins.length} plugin cards, ${skills.length} skill cards, and ${guide.steps.length} guide steps to website/index.html`);
