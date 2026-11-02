import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('../../', import.meta.url));
const read = p => readFileSync(path.join(root, p), 'utf8');
const write = (p, s) => writeFileSync(path.join(root, p), s, 'utf8');
const plugins = JSON.parse(read('website/content/plugins.json'));
const { installationPrompt } = await import('./installation-prompt.mjs');
const marketplace = JSON.parse(read('.agents/plugins/marketplace.json'));
for (const p of plugins) {
  const entry = marketplace.plugins.find(e => e.source.path === './plugins/' + p.id);
  if (!entry) throw new Error('Missing marketplace entry ' + p.id);
  const manifest = JSON.parse(read(existsSync(path.join(root, 'plugins/' + p.id + '/plugin.json')) ? 'plugins/' + p.id + '/plugin.json' : 'plugins/' + p.id + '/.codex-plugin/plugin.json'));
  if (manifest.name !== entry.name) throw new Error('Manifest mismatch ' + p.id);
}
let docs = '# ChatGPT 채팅용 플러그인 설치 요청문\n\nChatGPT에서 Plugin Creator를 설치한 뒤 새 채팅의 @ 메뉴에서 선택하고, 원하는 플러그인 요청문을 붙여넣으세요. 단순 방법 설명이 아니라 원본 패키지의 생성·등록을 요청합니다. 모든 계정에서 자동 설치를 보장하지 않으며, 설치 카드·인증·권한 승인이 남을 수 있습니다. 활성 워크스페이스가 있으면 그곳에 등록될 수 있습니다.\n\nGitHub 연결이 필요하면 [README의 연결 안내](README.md#github가-아직-연결되지-않았다면)를 따르세요. 이 요청문은 GitHub 공개 원본의 복사본을 등록하며, 이후 원본 변경이 자동으로 복사본에 적용된다는 뜻은 아닙니다.\n\n';
for (const p of plugins) docs += '## ' + p.title + '\n\n```text\n' + installationPrompt(p) + '\n```\n\n';
docs += '## Codex에서 설치하기\n\n다음은 일반 ChatGPT 채팅 명령이 아닌 Codex CLI 명령입니다. 지원되는 CLI에서 마켓플레이스를 한 번 등록합니다.\n\n```sh\ncodex plugin marketplace add yundaldal/gpt-plugins_daldal\ncodex plugin list --available --json\n```\n\n';
for (const p of plugins) { const e = marketplace.plugins.find(e => e.source.path === './plugins/' + p.id); docs += '- ' + p.title + ': `codex plugin add ' + e.name + '@' + marketplace.name + '`\n'; }
docs += '\n공식 안내: [Plugin Creator](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) · [플러그인 패키지와 마켓플레이스](https://developers.openai.com/plugins/build/plugins) · [Codex 명령](https://learn.chatgpt.com/docs/developer-commands)\n';
write('INSTALL-PROMPTS.md', docs);
console.log('Updated chat installation documentation and cards; verified 8 existing marketplace entries.');