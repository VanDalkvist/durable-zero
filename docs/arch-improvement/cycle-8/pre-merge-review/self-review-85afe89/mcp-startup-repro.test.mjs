import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const storage = process.env.REPRO_OUTPUT_DIR ?? process.cwd();
const baseline = process.env.PR3_BASELINE_ROOT;
const latest = process.env.PR3_LATEST_ROOT;
if (!baseline || !latest) throw new Error('Set PR3_BASELINE_ROOT and PR3_LATEST_ROOT to built checkouts');
const observations = [];

async function probe(root, name) {
  const base = await mkdtemp('/tmp/pr3-mcp-startup-');
  const agent = join(base, 'agent');
  const cwd = join(base, 'work');
  await mkdir(agent); await mkdir(cwd); await mkdir(join(base, 'home'));
  const requests = [];
  const server = http.createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    if (req.method !== 'POST') { res.writeHead(405); res.end(); return; }
    const message = JSON.parse(body);
    requests.push({ method: message.method, elapsedMs: Date.now() - started });
    if (message.method === 'initialize') {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ jsonrpc: '2.0', id: message.id, result: {
        protocolVersion: message.params.protocolVersion,
        capabilities: {}, serverInfo: { name: 'owned-stalled-notification-peer', version: '1' },
      } }));
    } else if (message.method === 'notifications/initialized') {
      // A permitted HTTP peer that accepts initialization but never acknowledges the notification.
      // Keep headers/body pending. This must not be mistaken for a model/network dependency.
    } else {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ jsonrpc: '2.0', id: message.id, result: { tools: [] } }));
    }
  });
  const started = Date.now();
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  await writeFile(join(agent, 'mcp.json'), JSON.stringify({ mcpServers: {
    local: { url: `http://127.0.0.1:${server.address().port}/mcp`,
      headers: { Authorization: 'Bearer local-test-fixture' }, timeout: 1 },
  } }));
  const runtime = spawn(process.execPath, [join(root, 'packages/local-runtime/bin/runtime.mjs'),
    '--session-dir', join(base, 'session'), '--cwd', cwd,
    '--extension', join(root, 'packages/local-runtime/test/fixtures/provider.ts'),
    '--provider', 'local-test', '--model', 'scripted'], {
    env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', HOME: join(base, 'home'),
      XDG_CONFIG_HOME: join(base, 'config'), XDG_DATA_HOME: join(base, 'data'),
      XDG_CACHE_HOME: join(base, 'cache'), PI_AGENT_DIR: agent, PI_CODING_AGENT_DIR: agent,
      PI_ADDITIONAL_EXTENSIONS: '', TMPDIR: '/tmp' }, cwd, stdio: ['ignore', 'pipe', 'pipe'],
  });
  const exited = once(runtime, 'exit');
  let stdout = '', stderr = '';
  runtime.stdout.on('data', c => { stdout += c; });
  runtime.stderr.on('data', c => { stderr += c; });
  const ready = () => stdout.includes('"status":"ready"');
  try {
    const deadline = Date.now() + 4500;
    while (!ready() && runtime.exitCode === null && Date.now() < deadline) await delay(20);
    const result = { name, runtimeRoot: root, runtimePid: runtime.pid, ready: ready(),
      elapsedMs: Date.now() - started, configuredMcpTimeoutMs: 1000, requests, stdout, stderr };
    observations.push(result);
    await writeFile(join(storage, 'pr3-mcp-startup-repro.json'), JSON.stringify(observations, null, 2));
    return result;
  } finally {
    if (runtime.exitCode === null && runtime.signalCode === null) {
      runtime.kill('SIGTERM');
      await Promise.race([exited, delay(1000)]);
      if (runtime.exitCode === null && runtime.signalCode === null) runtime.kill('SIGKILL');
      await exited;
    }
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
}

test('baseline: optional stalled MCP peer does not block native runtime readiness', { timeout: 8000 }, async () => {
  const result = await probe(baseline, 'baseline-877b50b');
  assert.equal(result.ready, true, JSON.stringify(result));
});
test('latest: optional stalled MCP peer must not block native runtime readiness', { timeout: 8000 }, async () => {
  const result = await probe(latest, 'latest-85afe89');
  assert.equal(result.ready, true, JSON.stringify(result));
});
