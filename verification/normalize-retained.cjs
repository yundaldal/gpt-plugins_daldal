// Formatting only: undo checkout newline conversion in retained text files.
// Refuse any substantive change; original binary references are never written.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..');
const git=(...args)=>cp.execFileSync('git',['-c',`safe.directory=${root.replaceAll('\\','/')}`,'-C',root,...args]);
const files=git('ls-tree','-rz','--name-only','482b406','plugins').toString().split('\0').filter(Boolean);
for(const f of files.filter(f=>!f.includes('/pumui-daldal/')&&(f.includes('/references/')||f.endsWith('openai.yaml')||f.endsWith('knowledge-index.json')))) {
 if(!/\.(md|txt|json|yaml)$/.test(f))continue;
 const full=path.join(root,f), old=git('show',`482b406:${f}`), current=fs.readFileSync(full);
 if(current.equals(old))continue;
 if(current.toString().replace(/\r\n/g,'\n')!==old.toString().replace(/\r\n/g,'\n'))throw Error('Substantive change: '+f);
 fs.writeFileSync(full,old); console.log('Restored original line endings: '+f);
}
