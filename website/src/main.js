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

  const quote = button.closest('.example-body')?.querySelector('blockquote');
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
    : button.dataset.copyText;
  const status = getStatus(button);
  status.textContent = '';

  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API is unavailable');
    await navigator.clipboard.writeText(text);
    status.textContent = button.hasAttribute('data-copy-first')
      ? '복사했어요. ChatGPT에 붙여넣어 보세요.'
      : '요청 예시를 복사했어요.';
  } catch {
    selectFallback(button);
  }
}

document.querySelectorAll('[data-copy-first], [data-copy-text]').forEach((button) => {
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
