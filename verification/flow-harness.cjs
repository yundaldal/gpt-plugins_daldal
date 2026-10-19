// Static contract/package checks, NOT a model conversation test.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const cp = require('node:child_process');
const YAML = require('yaml');
const root = path.resolve(__dirname, '..');
const baseline = '482b406';
const git = (...args) => cp.execFileSync('git', ['-c',`safe.directory=${root.replaceAll('\\','/')}`, '-C',root,...args], {encoding:'utf8'});
const read = f => fs.readFileSync(path.join(root,f),'utf8');
const json = f => JSON.parse(read(f));
const ids = ['approval-excel','canva-game','ib-core','ib-planner','iep-eval','iep-plan','related-document-extractor'];
let passed=0;
function check(name,run) { run(); passed++; console.log('PASS '+name); }
function walk(dir) { return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(dir,e.name)):[path.join(dir,e.name)]); }
for(const id of ids) {
  const base=`plugins/${id}`;
  check(`${id}: YAML and knowledge paths`,()=>{
    const skill=read(`${base}/skills/instructions/SKILL.md`);
    const front=skill.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    assert(front);
    const meta=YAML.parse(front[1]);
    assert.equal(meta.name,'instructions'); assert.equal(typeof meta.description,'string');
    const agent=YAML.parse(read(`${base}/skills/instructions/agents/openai.yaml`));
    assert.equal(typeof agent.interface.display_name,'string');
    assert.equal(typeof agent.interface.short_description,'string');
    assert.equal(typeof agent.interface.default_prompt,'string');
    for(const f of json(`${base}/skills/instructions/lookup/knowledge-index.json`).files) {
      const target=path.resolve(root,base,'skills/instructions',f.path);
      assert(target.startsWith(path.resolve(root,base)+path.sep)); assert(fs.existsSync(target),f.path);
    }
  });
  check(`${id}: preserved references and invocation settings`,()=>{
    for(const file of walk(path.join(root,base)).filter(f=>f.includes(path.sep+'references'+path.sep)||f.endsWith('openai.yaml')||f.endsWith('knowledge-index.json'))) {
      const rel=path.relative(root,file).replaceAll('\\','/');
      const oldHash=git('rev-parse',`${baseline}:${rel}`).trim();
      assert.equal(git('hash-object','--no-filters',file).trim(),oldHash,rel);
    }
  });
  check(`${id}: manifests, identity and prompts`,()=>{
    const files=['.codex-plugin/plugin.json','plugin.json'].filter(f=>fs.existsSync(path.join(root,base,f)));
    const manifests=files.map(f=>{
      const m=json(`${base}/${f}`), old=JSON.parse(git('show',`${baseline}:${base}/${f}`));
      const ui=m.extensions?.['com.openai']?.interface??m.interface;
      const oldUI=old.extensions?.['com.openai']?.interface??old.interface;
      assert.equal(m.name,old.name); assert.deepEqual(ui.defaultPrompt,oldUI.defaultPrompt);
      assert.equal(ui.displayName,oldUI.displayName); assert.deepEqual(ui.capabilities,oldUI.capabilities);
      if(ids.includes(id)) { assert.notEqual(m.version,old.version); assert(ui.shortDescription.length<=30); }
      assert(/^\d+\.\d+\.\d+(?:\+[\w.]+)?$/.test(m.version));
      for(const key of ['logo','composerIcon']) if(ui[key]) assert(fs.existsSync(path.resolve(root,base,ui[key])));
      if(f==='plugin.json') assert.equal(m.$schema,'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json');
      return m;
    });
    if(manifests.length===2) {
      assert.equal(manifests[0].version,manifests[1].version);
      assert.deepEqual(manifests[0].interface,manifests[1].extensions['com.openai'].interface);
    }
  });
}
const contracts={
 'approval-excel': ['부족한 내용만 질문하고 응답을 끝내세요','3단계 확인','사용자가 확인한 후에만 4단계','금액·유형 수정','새로운 품의문 작성 요청 시 1단계'],
 'iep-plan':['업로드 없이 진행','응답을 끝낸다','한 번의 \'다음\'','새 학생의 IEP는 1단계','기준이나 분류번호를 추정하여 진행하지 않는다'],
 'iep-eval':['평가문 확인 질문 뒤에는 응답을 끝낸다','현재 평가문의 확인 후 다음 항목','목표 80%를 실제 성취 80%로 바꾸거나','중간 질문에 답한 뒤에도 현재 항목','새 학생·평가월'],
 'ib-core':['2~5번은 분석 기준','선택·검토 질문을 제시한 뒤에는 응답을 끝낸다','선택 변경 시 일반화와 탐구 질문','새 주제는 사전 정보 확인'],
 'ib-planner':['각 선택·확인 질문 뒤에는 응답을 끝내고','B 선택과 프로젝트 이름을 모두','필요한 자료를 요청한다','새 단원은 1단계'],
 'related-document-extractor':['이미지가 없으면','이미지가 명확하면 바로','주변 번호의 연속성만으로 값을 확정하지 않는다','확인 답변을 받으면 해당 행을 바로잡아']
};
for(const [id,phrases] of Object.entries(contracts)) check(`${id}: static flow contracts`,()=>{
  const s=read(`plugins/${id}/skills/instructions/SKILL.md`);
  for(const p of phrases) assert(s.includes(p),`${id}: ${p}`);
});
check('IEP: visible stages agree and run from 1 through 6',()=>{
 const s=read('plugins/iep-plan/skills/instructions/SKILL.md');
 assert.deepEqual([...s.matchAll(/^### (\d)단계:/gm)].map(m=>+m[1]),[1,2,3,4,5,6]);
});
check('Removed conflicting auto-fill and missing reference rules',()=>{
 const s=read('plugins/approval-excel/skills/instructions/SKILL.md');
 assert(!s.includes('부족한 정보가 있는 경우 자동으로 생성')); assert(!s.includes('예시 모음.docx'));
 assert(!s.includes('불완전하더라도'));
});
check('Excluded plugin and marketplace unchanged',()=>{
 assert.equal(git('diff',baseline,'--','plugins/pumui-daldal','.agents/plugins/marketplace.json').trim(),'');
 const files=git('ls-tree','-r','--name-only',baseline,'downloads').split('\n').filter(x=>x.includes('pumui'));
 assert(files.length); for(const f of files) assert.equal(git('diff',baseline,'--',f).trim(),'');
});
check('Canva: original behavior retained with upload guidance added',()=>{
 const p='plugins/canva-game/skills/instructions/SKILL.md';
 const current=read(p).replace(/\r\n/g,'\n');
 const original=git('show',`${baseline}:${p}`).replace(/\r\n/g,'\n');
 const withoutAddition=current.replace(/(## 필수 정보 확인\n)학습 자료를 활용하려는[\s\S]*?\n\n/,'$1');
 assert.equal(withoutAddition.trim(),original.trim());
});
for(const id of ids) check(`${id}: explicit upload request and reply handling`,()=>{
 const s=read(`plugins/${id}/skills/instructions/SKILL.md`);
 assert(s.includes('올려 주세요') || s.includes('붙여넣어 주세요'));
 assert(/업로드 (후|자료에서)/.test(s));
});
check('README: merged categories, eight rows, usage and valid local links',()=>{
 const s=read('README.md'); const tbody=s.match(/<tbody>([\s\S]*?)<\/tbody>/)[1];
 const rows=[...tbody.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(m=>m[1]);
 assert.equal(rows.length,8); assert.equal((tbody.match(/rowspan="2"/g)||[]).length,3);
 assert(s.includes('관련문서 양식을 캡처만 하면')); assert(s.includes('집계일은 미상'));
 const values={'approval-excel':'700회+','iep-plan':'1,000회+','iep-eval':'1,000회+','ib-core':'1,000회+','ib-planner':'700회+','canva-game':'400회+','related-document-extractor':'미확인','pumui-daldal':'해당 없음'};
 for(const [id,value] of Object.entries(values)) assert(rows.find(r=>r.includes(`plugins/${id}/`)).includes(`<td>${value}</td>`));
 for(const [,href] of s.matchAll(/href="([^"]+)"/g)) {
   const relative=href.replace('https://github.com/yundaldal/gpt-plugins_daldal/raw/refs/heads/main/','');
   if(!relative.startsWith('https:')) assert(fs.existsSync(path.join(root,relative)),relative);
 }
});
console.log(JSON.stringify({staticChecks:passed,modelConversationTests:'NOT RUN',hostInstallation:'NOT RUN',baseline}));
