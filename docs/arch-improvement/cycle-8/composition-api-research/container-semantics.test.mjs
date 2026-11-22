import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const packageRoot = resolve(process.env.TYPED_INJECT_ROOT ?? new URL('./typed-inject-published/package', import.meta.url).pathname);
const metadata = JSON.parse(await readFile(resolve(packageRoot, 'package.json'), 'utf8'));
assert.equal(metadata.version, '5.0.0', 'Research evidence is pinned to published typed-inject@5.0.0');
const { createInjector } = await import(pathToFileURL(resolve(packageRoot, metadata.main)).href);

// Research probes of published typed-inject@5.0.0, not acceptance of Zero or a container migration.
test('typed-inject passes async factory output as a Promise to dependent factories', async () => {
  const makeDependency = async () => ({ ready: true });
  const consume = (dependency) => ({ dependency });
  consume.inject = ['dependency'];
  const root = createInjector();
  const injector = root.provideFactory('dependency', makeDependency).provideFactory('consumer', consume);
  try {
    const result = injector.resolve('consumer');
    assert.equal(result.dependency instanceof Promise, true);
    assert.equal((await result.dependency).ready, true);
  } finally { await root.dispose(); }
});

test('typed-inject does not automatically dispose the resolved object inside an async factory Promise', async () => {
  let disposed = 0;
  const resource = { dispose() { disposed++; } };
  const root = createInjector();
  const injector = root.provideFactory('resource', async () => resource);
  await injector.resolve('resource');
  await root.dispose();
  assert.equal(disposed, 0);
  resource.dispose(); // Research fixture explicitly owns the cleanup missing from naive Promise registration.
  assert.equal(disposed, 1);
});

test('typed-inject explicit child scope needs explicit disposal in the published version', async () => {
  let disposed = 0;
  const root = createInjector();
  const child = root.createChildInjector();
  const injector = child.provideFactory('resource', () => ({ dispose() { disposed++; } }));
  injector.resolve('resource');
  await root.dispose();
  assert.equal(disposed, 0);
  await child.dispose();
  assert.equal(disposed, 1);
});

test('native AsyncDisposableStack awaits reverse-order cleanup and continues after a disposer throws', async () => {
  const trace = [];
  const stack = new AsyncDisposableStack();
  stack.defer(async () => { trace.push('dependency'); });
  stack.defer(async () => { trace.push('consumer'); throw new Error('fixture disposal failure'); });
  await assert.rejects(stack.disposeAsync(), /fixture disposal failure/);
  assert.deepEqual(trace, ['consumer', 'dependency']);
});
