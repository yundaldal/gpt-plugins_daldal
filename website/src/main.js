const filterButtons = [...document.querySelectorAll('[data-filter]')];
const pluginCards = [...document.querySelectorAll('[data-plugin-id]')];
const filterStatus = document.querySelector('.filter-status');

for (const button of filterButtons) {
  button.addEventListener('click', () => {
    const category = button.dataset.filter;
    let visibleCount = 0;

    for (const card of pluginCards) {
      const isVisible = category === 'all' || card.dataset.category === category;
      card.hidden = !isVisible;
      if (isVisible) visibleCount += 1;
    }

    for (const filterButton of filterButtons) {
      const isActive = filterButton === button;
      filterButton.classList.toggle('is-active', isActive);
      filterButton.setAttribute('aria-pressed', String(isActive));
    }

    filterStatus.textContent = `${visibleCount}개 도구를 보고 있어요.`;
  });
}

const selectedTool = document.querySelector('[data-selected-plugin]');
const selectedDownload = document.querySelector('[data-selected-download]');

document.querySelectorAll('[data-install-plugin]').forEach((link) => {
  link.addEventListener('click', () => {
    const card = document.querySelector(`[data-plugin-id="${CSS.escape(link.dataset.installPlugin)}"]`);
    if (!card) return;

    const title = card.querySelector('h3')?.textContent.trim() ?? '';
    const originalName = card.querySelector('.original-name strong')?.textContent.trim() ?? '';
    const download = card.querySelector('.button-download');
    const zipFile = card.dataset.zipFile;

    selectedTool.querySelector('strong').textContent = title;
    selectedTool.querySelector('p').textContent = `플러그인 목록 이름: ${originalName} · 받을 파일: ${zipFile}`;
    selectedDownload.href = download.href;
    selectedDownload.textContent = `${zipFile} 받기`;
    selectedDownload.hidden = false;
  });
});

function getStatus(button) {
  return button.closest('.example-actions, .inline-question, .prompt-card-bottom')?.querySelector('[data-copy-status]');
}

function selectFallback(button) {
  const status = getStatus(button);
  if (button.hasAttribute('data-copy-first')) {
    const field = document.querySelector('#first-question');
    field.focus();
    field.select();
    status.textContent = '문장을 직접 선택해 복사해 주세요.';
    return;
  }

  if (button.hasAttribute('data-copy-install')) {
    const field = button.closest('.install-prompt-details').querySelector('textarea');
    field.focus();
    field.select();
    status.textContent = '설치 요청문을 직접 선택해 복사해 주세요.';
    return;
  }
  if (button.hasAttribute('data-copy-generated-request')) {
    const field = document.querySelector('#generated-request');
    field.focus();
    field.select();
    status.textContent = '요청문을 직접 선택해 복사한 뒤 @plugin-creator 채팅에 붙여넣으세요.';
    return;
  }
  const quote = button.hasAttribute('data-copy-url')
    ? button.closest('.plugin-url-panel')?.querySelector('.plugin-url')
    : button.closest('.example-body')?.querySelector('blockquote');
  if (quote) {
    const range = document.createRange();
    range.selectNodeContents(quote);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }
  status.textContent = '복사하지 못했어요. 문장을 직접 선택해 복사해 주세요.';
}

async function copyFromButton(button) {
  const text = button.hasAttribute('data-copy-first')
    ? document.querySelector('#first-question').value
    : button.hasAttribute('data-copy-generated-request')
      ? document.querySelector('#generated-request').value
    : button.dataset.copyText;
  const status = getStatus(button);
  status.textContent = '';

  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API is unavailable');
    await navigator.clipboard.writeText(text);
    status.textContent = button.hasAttribute('data-copy-first')
      ? '복사했어요. ChatGPT에 붙여넣어 보세요.'
      : button.hasAttribute('data-copy-url')
        ? 'GitHub URL을 복사했어요. ChatGPT에 붙여넣어 보세요.'
        : button.hasAttribute('data-copy-install')
          ? '설치 요청문을 복사했어요. Plugin Creator 채팅에 붙여넣으세요.'
          : button.hasAttribute('data-copy-generated-request')
            ? '요청문을 복사했어요. 새 채팅에서 @plugin-creator를 선택해 붙여넣으세요.'
          : '요청 예시를 복사했어요.';
  } catch {
    selectFallback(button);
  }
}

const requestForm = document.querySelector('#request-generator');
const repositoryUrlField = document.querySelector('#github-repo-url');
const generatedRequestField = document.querySelector('#generated-request');
const requestFeedback = document.querySelector('#request-feedback');
const copyGeneratedRequest = document.querySelector('[data-copy-generated-request]');

function normalizeGitHubUrl(value) {
  let url;
  try {
    url = new URL(value.trim());
  } catch {
    return null;
  }

  if (url.protocol !== 'https:' || url.hostname !== 'github.com' || url.username || url.password) return null;
  const segments = url.pathname.split('/').filter(Boolean);
  if (segments.length < 2 || segments[0] === 'login' || segments[0] === 'settings') return null;

  url.search = '';
  url.hash = '';
  url.pathname = `/${segments.join('/')}`.replace(/\.git$/, '');
  return { url: url.toString().replace(/\/$/, ''), path: url.pathname.toLowerCase() };
}

function makeInstallRequest({ url, path }) {
  const isPluginFolder = /\/plugins\/[^/]+(?:\/|$)/i.test(path);
  const isStandaloneSkill = !isPluginFolder && (/\/yundaldal\/korean-official-doc(?:\/|$)/i.test(url)
    || /\/skills\/[^/]+(?:\/|$)/i.test(path)
    || /\/skill\.md$/i.test(path));
  const intent = isStandaloneSkill
    ? '스킬을 사용하고 싶다.'
    : isPluginFolder
      ? '플러그인을 설치하고 싶다.'
      : '자료를 설치하고 싶다. 저장소 형식은 직접 판별해 주세요.';
  const chatgptFreeNote = isStandaloneSkill
    ? '\n\n참고: 이 주소는 독립 Skill 저장소입니다. 무료 ChatGPT에서는 이 스킬을 사용할 수 없습니다. 현재 계정에서 Skill 등록이 지원되지 않으면 설치했다고 말하지 말고, 지원 한계와 다른 지원 방법을 안내해 주세요.'
    : '';

  return `@plugin-creator\n\n${url} 의 ${intent}\n\nGitHub 주소의 파일만 확인해서 이 자료의 형식을 먼저 판별해 주세요. 플러그인이면 매니페스트와 skills/ 지침을 읽고 기존 내용을 유지해 개인용 플러그인으로 생성·등록을 시도해 주세요. 독립 Skill이면 SKILL.md와 필요한 스크립트를 스킬로 보존하고, 현재 ChatGPT 환경이 직접 지원하는지 확인해 주세요.\n\n다른 플러그인이나 저장소 파일은 수정하지 마세요. GitHub 접근, 계정 권한 또는 별도 설치 확인이 필요하면 제가 해야 할 단계만 안내해 주세요. 실제 완료 여부와 남은 단계를 구분해 알려 주세요. 설치할 수 없는 환경에서는 성공했다고 표현하지 마세요.${chatgptFreeNote}`;
}

function generateInstallRequest() {
  const repository = normalizeGitHubUrl(repositoryUrlField.value);
  if (!repository) {
    requestFeedback.textContent = 'https://github.com/소유자/저장소 형식의 주소를 입력해 주세요.';
    generatedRequestField.value = '';
    copyGeneratedRequest.disabled = true;
    return;
  }

  generatedRequestField.value = makeInstallRequest(repository);
  copyGeneratedRequest.disabled = false;
  requestFeedback.textContent = '요청문을 만들었어요. 복사한 뒤 ChatGPT에서 @plugin-creator를 선택해 붙여넣으세요.';
}

requestForm.addEventListener('submit', (event) => {
  event.preventDefault();
  generateInstallRequest();
});
generateInstallRequest();

document.querySelectorAll('[data-copy-first], [data-copy-text], [data-copy-generated-request]').forEach((button) => {
  button.addEventListener('click', () => copyFromButton(button));
});

const dialog = document.querySelector('[data-screenshot-dialog]');
const dialogImage = dialog.querySelector('[data-dialog-image]');
const dialogHighlight = dialog.querySelector('[data-dialog-highlight]');
const dialogTitle = dialog.querySelector('[data-dialog-title]');
const dialogCaption = dialog.querySelector('[data-dialog-caption]');
let lastDialogTrigger = null;

document.querySelectorAll('[data-open-image]').forEach((button) => {
  button.addEventListener('click', () => {
    lastDialogTrigger = button;
    dialogImage.src = button.dataset.imageSrc;
    dialogImage.alt = button.dataset.imageAlt;
    const stepClass = [...button.closest('.guide-visual').classList]
      .find((className) => className.startsWith('guide-visual-step-'));
    if (stepClass) dialogHighlight.dataset.step = stepClass.replace('guide-visual-', '');
    dialogTitle.textContent = button.dataset.imageTitle;
    dialogCaption.textContent = button.closest('figure').querySelector('figcaption').textContent;
    dialog.showModal();
    dialog.querySelector('[data-close-dialog]').focus();
  });
});

function closeScreenshotDialog() {
  if (dialog.open) dialog.close();
}

dialog.querySelector('[data-close-dialog]').addEventListener('click', closeScreenshotDialog);
dialog.addEventListener('click', (event) => {
  if (event.target === dialog) closeScreenshotDialog();
});
dialog.addEventListener('close', () => {
  dialogImage.removeAttribute('src');
  dialogHighlight.removeAttribute('data-step');
  lastDialogTrigger?.focus();
});
