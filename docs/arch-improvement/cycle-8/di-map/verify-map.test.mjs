import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const dir=dirname(fileURLToPath(import.meta.url));
const source=process.env.SOURCE_ROOT;
assert.ok(source,'SOURCE_ROOT must point to the exact PR85afe89 source checkout/archive');
const data=JSON.parse(await readFile(resolve(dir,'bindings.json'),'utf8'));
const pkg=JSON.parse(await readFile(resolve(dir,'package-dependencies.json'),'utf8'));
const graphs=JSON.parse(await readFile(resolve(dir,'diagrams.json'),'utf8'));

test('every binding has a real consumer/path, a limitation and source evidence at exact file:line',async()=>{
 const seen=new Set();
 for(const b of data.bindings){
  assert.equal(seen.has(b.id),false,b.id);seen.add(b.id);
  for(const k of ['entry','implementation','consumer','how','limitation'])assert.ok(b[k]?.length>0,`${b.id}:${k}`);
  assert.ok(data.legend[b.status]);assert.ok(b.evidence.length>0);
  for(const e of b.evidence){const lines=(await readFile(resolve(source,e.file),'utf8')).split(/\r?\n/);assert.equal(lines[e.line-1]?.trim(),e.quote,`${b.id}:${e.file}:${e.line}`);assert.ok(e.url.includes(data.sourceSha));assert.ok(e.url.endsWith(`#L${e.line}`));}
 }
});

test('all workspace packages are represented; source, type and manifest edges are distinguished',async()=>{
 const ids=[];for(const name of await readdir(resolve(source,'packages'))){try{JSON.parse(await readFile(resolve(source,'packages',name,'package.json'),'utf8'));ids.push(name);}catch{}}
 assert.deepEqual(pkg.packages.map(p=>p.id).sort(),ids.sort());
 for(const e of pkg.edges){assert.ok(ids.includes(e.from)&&ids.includes(e.to));assert.ok(['source','type','manifest-only'].includes(e.kind));if(e.kind==='manifest-only'){assert.equal(e.references.length,0);assert.equal(e.declared,true);}for(const r of e.references){assert.equal(/\/(test|dist)\//.test(r.file),false);const code=await readFile(resolve(source,r.file),'utf8');assert.ok(code.includes(r.specifier));}}
});

test('every field of PiRuntimeDependencies is classified rather than inferred from interface existence',async()=>{
 const code=await readFile(resolve(source,'packages/adapter-pi-durable/src/engine/runtime-types.ts'),'utf8');const body=code.split('export interface PiRuntimeDependencies {')[1].split('\n}')[0];
 const actual=[...body.matchAll(/readonly\s+(\w+)\?/g)].map(m=>m[1]).sort();
 const coverage={nativeExecutionEnvFactory:'native-env',executionEnvFactory:'core-env',hostBridge:'host-bridge',modelRuntime:'model-runtime',nativeProviders:'native-providers',resourceLoader:'resources',settingsManager:'settings',builtins:'builtins',dynamicSections:'dynamic-sections',prompt:'prompt-data'};
 assert.deepEqual(Object.keys(coverage).sort(),actual);for(const id of Object.values(coverage))assert.ok(data.bindings.some(b=>b.id===id));
 assert.equal(data.bindings.find(b=>b.id==='host-bridge').status,'dormant');
});

test('atlas includes every binding, diagram view and current-not-target warning',async()=>{
 const page=await readFile(resolve(dir,'atlas.html'),'utf8');for(const b of data.bindings)assert.ok(page.includes(`binding-${b.id}`));for(const p of JSON.parse(await readFile(resolve(dir,'pages.json'),'utf8')))assert.ok(page.includes(p.file));
 assert.ok(page.includes('не будущий дизайн'));assert.ok(page.includes('не сертификат полной работоспособности'));
 for(const key of ['runtime','interaction','public','lower','fixed','dormant','packages'])assert.ok(graphs[key]?.mermaid.length>0);
});
