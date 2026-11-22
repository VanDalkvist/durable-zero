import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root=path.resolve(process.env.SOURCE_ROOT ?? process.cwd());
const out=path.resolve(process.env.OUTPUT_DIR ?? path.dirname(fileURLToPath(import.meta.url)));
const require=createRequire(import.meta.url);
const ts=require(process.env.TYPESCRIPT_MODULE ?? require.resolve('typescript',{paths:[root]}));
fs.mkdirSync(out,{recursive:true});
const dirs=fs.readdirSync(path.join(root,'packages')).sort();
const packages=dirs.map(id=>({id,...JSON.parse(fs.readFileSync(path.join(root,'packages',id,'package.json'),'utf8'))}));
const byName=new Map(packages.map(p=>[p.name,p]));
const references=[];
function walk(d){if(!fs.existsSync(d))return[];return fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>{const p=path.join(d,e.name);return e.isDirectory()?walk(p):/\.[cm]?[jt]sx?$/.test(e.name)?[p]:[]});}
function owner(p){const m=p.replaceAll('\\','/').match(/\/packages\/([^/]+)\//);return m?.[1];}
for(const pkg of packages){
 const dir=path.join(root,'packages',pkg.id);
 const files=['src','bin','vendor'].flatMap(s=>walk(path.join(dir,s)));
 for(const file of files){
  const code=fs.readFileSync(file,'utf8');const ast=ts.createSourceFile(file,code,ts.ScriptTarget.Latest,true);
  function add(spec,kind,pos){
   let target;
   if(spec.startsWith('.'))target=owner(path.resolve(path.dirname(file),spec));
   else target=packages.find(p=>spec===p.name||spec.startsWith(p.name+'/'))?.id;
   if(target===pkg.id)return;
   const external=target?null:(!spec.startsWith('.')?spec.match(/^@[^/]+\/[^/]+|^[^/]+/)?.[0]:null);
   if(!target&&!external)return;
   references.push({from:pkg.id,to:target??external,workspace:!!target,kind,specifier:spec,file:path.relative(root,file),line:ast.getLineAndCharacterOfPosition(pos).line+1});
  }
  function visit(n){
   if(ts.isImportDeclaration(n)&&ts.isStringLiteral(n.moduleSpecifier)){
    const c=n.importClause;const named=c?.namedBindings;
    const typeOnly=!!c?.isTypeOnly||(!c?.name&&named&&ts.isNamedImports(named)&&named.elements.length>0&&named.elements.every(e=>e.isTypeOnly));
    add(n.moduleSpecifier.text,typeOnly?'type':'import',n.getStart());
   } else if(ts.isExportDeclaration(n)&&n.moduleSpecifier&&ts.isStringLiteral(n.moduleSpecifier))add(n.moduleSpecifier.text,n.isTypeOnly?'type':'export',n.getStart());
   else if(ts.isCallExpression(n)&&n.arguments[0]&&ts.isStringLiteral(n.arguments[0])){
    const call=n.expression.getText(ast);if(n.expression.kind===ts.SyntaxKind.ImportKeyword||['require','require.resolve','createRequire(import.meta.url).resolve'].includes(call))add(n.arguments[0].text,'dynamic-or-resolve',n.getStart());
   }
   ts.forEachChild(n,visit);
  }visit(ast);
 }
}
const edges=[];
for(const from of packages)for(const to of packages){
 if(from.id===to.id)continue;
 const refs=references.filter(r=>r.from===from.id&&r.to===to.id&&r.workspace);
 const declared=!!from.dependencies?.[to.name]||!!from.peerDependencies?.[to.name];
 if(!refs.length&&!declared)continue;
 const hasRuntime=refs.some(r=>r.kind!=='type');
 edges.push({from:from.id,to:to.id,declared,kind:hasRuntime?'source':refs.length?'type':'manifest-only',references:refs});
}
const data={sourceSha:'85afe89869e60b887703d215005d4c37bac3c177',date:'2026-11-06',scope:'All workspace src/bin/vendor import/export/require string references; tests/dist excluded. Syntactic source dependencies, not dynamic execution proof; package manifests separately flagged.',packages:packages.map(p=>({id:p.id,name:p.name,dependencies:p.dependencies??{},peerDependencies:p.peerDependencies??{}})),edges,externalReferences:references.filter(r=>!r.workspace)};
fs.writeFileSync(path.join(out,'package-dependencies.json'),JSON.stringify(data,null,2)+'\n');
console.log(JSON.stringify({packages:packages.length,edges:edges.map(({from,to,kind})=>({from,to,kind}))},null,2));
