# PR #3 — final self-review of 85afe89

**VERDICT: FAIL — confirmed P1 startup regression; do not merge this head.**

Reviewed head: `85afe89869e60b887703d215005d4c37bac3c177`. Previous reviewed head: `877b50b2a86a6f5e1137117b658070c48b3a295f`. No production runtime code was changed by the reviewer, and nothing was installed globally.

## [P1] An optional HTTP MCP server can prevent the entire native runtime from becoming ready

- **Evidence:** `packages/adapter-pi-durable/src/engine/extension-mount.ts:179-182` now awaits the headless `mcp` status command before Harness.open. The pinned pi-coding-agent1.5.0 command handler awaits the entire initial connection promise. In pi-mcp1.5.0, `McpClient.connect()` first awaits initialize, then awaits `notifyInternal("notifications/initialized")`. Request deadlines cover `requestInternal`, not that notification's HTTP send. The transport uses its lifetime abort signal, not a request deadline, for this send.
- **Reproduction:** a local HTTP MCP fixture responds successfully to initialize and never acknowledges the initialized notification. Set MCP timeout to1second. The exact baseline877b50b reaches runtime ready; exact latest85afe89 does not reach ready by the4.5second watchdog. No model/API credentials or external network were involved. The actual observations and native JUnit are retained; this is not an inference from a missing Promise.race alone.
- **Impact:** the reference Harness cannot open because an optional tool provider stalls. The new reload path also reconstructs this assembly after closing the previous one, so the same wait can hold the serialized command queue during reload. A healthy model/local tools cannot be used through this runtime while it is stuck.
- **Rule:** AP-011 (component failure isolation), AP-012 (explicit bounded failure), AP-023 (async lifecycle), AP-075 (entrypoint outcome).
- **Fix decision:** fix-now upstream before merge. Provide bounded, cancellation-aware initial readiness/failure handling with owned-resource cleanup. Do not merely race an uncancelled startup task, remove permission hooks, release a native owner before it closes, or introduce another model loop. A failed external MCP peer must not hold startup/reload indefinitely beyond the selected failure policy. Add this server behavior as a regression case.

## [P2] Launcher test identity and cleanup are not portable to macOS

- **Evidence:** `packages/local-terminal/test/launch-native.test.ts:22-25` hashes an uncanonicalized temporary cwd, while production launch.ts hashes realpath(cwd). On macOS /tmp resolves to /private/tmp. The test therefore inspects a different session key, accidentally starts an additional runtime in the wrong-cwd rejection case, and times out at25seconds. Its original cleanup only knew the first runtime PID.
- **Impact:** the scoped suite is RED on an ordinary macOS temporary path; failure can leave a detached test runtime. The reviewer terminated only the positively identified orphan from the isolated test.
- **Rule:** AP-028, AP-076.
- **Fix decision:** fix-now for the regression fixture. `launcher-fixture-fix.patch` is a proposed fixture-only correction: normalize expected identity, retain alias reconnection/same-PID assertions and track every runtime announced by an owned launcher. All original behavioral assertions remain. Production launcher behavior is correct for this identity case; do not remove realpath from it.

## Verification and boundaries

- Fresh offline frozen install, root build, runtime/client builds and strict official source typecheck passed at85afe89.
- Unmodified upstream scoped suite:54cases,53passed,1launcher timeout on macOS. Original RED is retained.
- Same unmodified launcher test passes with canonical TMPDIR=/private/tmp, isolating the fixture identity defect.
- With the proposed local fixture correction only:54passed,0failed,0skipped; no owned runtime survived teardown. This GREEN is NOT claimed for the unmodified upstream test file.
- The independent startup counterexample remains RED on unmodified production85afe89. Passing normal MCP discovery/reload cases does not cover a peer that never acknowledges initialized.
- Core/contracts/protocol/execution have no changes in this PR relative to main. No new native/terminal dependency was added to those neutral packages.
- Native view/controller/resources/isIdle in the concrete Durable composition are intentional reference-assembly seams, not themselves a leak into generic Core. The terminal still uses the same native execution owner, not a second agent loop.
- The P1 is a concrete failure-domain coupling between optional MCP integration and overall Harness startup, not a demand to make every Durable UI type engine-neutral.

## Architecture verification

Passed in the reviewed changed source scope: AP-020 (Core dependency direction), AP-074 (owned dependencies used on actual paths), AP-076 (actual behavioral outcomes and preserved negative controls).

Failed: AP-011/AP-012/AP-023 for the confirmed MCP startup case; AP-028 for the unmodified macOS launcher fixture. No full PR PASS is issued while these findings remain open.

Residual risk: this is bounded source/product verification, not a universal proof. No fresh installed rich-PTY acceptance, live-model test, user-session migration, global switch or independent Zero extraction was performed. The imported AGENTS operating policy still needs explicit scope handling; the earlier proposed merge retained main's canonical policy, but no merge has occurred.

## Reproduce the startup regression

Prepare built baseline877b50b and latest85afe89 checkouts using their locked dependencies, root build and new runtime/client package builds. Then:

```sh
PR3_BASELINE_ROOT=/absolute/path/to/built-baseline \
PR3_LATEST_ROOT=/absolute/path/to/built-latest \
REPRO_OUTPUT_DIR=/absolute/path/to/output \
node --test --test-reporter=junit --test-reporter-destination=/absolute/path/to/output/startup.junit.xml \
  mcp-startup-repro.test.mjs
```

The output directory must already exist. Expected before the upstream fix: baseline control PASS, latest readiness assertion FAIL. The fixture binds only localhost, uses isolated HOME/agent/session/work directories and tears down only its own runtime/server. Its wait is bounded; an observed readiness failure is not misreported as an infinite-duration measurement.

See [structured findings](findings.json), [original startup observations](evidence/startup-observations.json), [original negative-control JUnit](evidence/mcp-startup-original.junit.xml), [unmodified macOS RED](evidence/upstream-macos-red.junit.xml), [local fixture GREEN](evidence/local-fixture-green.junit.xml), and [proposed test-only patch](launcher-fixture-fix.patch).
