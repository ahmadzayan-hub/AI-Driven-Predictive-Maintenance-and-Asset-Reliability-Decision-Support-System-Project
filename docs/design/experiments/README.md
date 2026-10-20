# React connection technology experiment

This folder supports the [21 October study](../REACT_AGENT_CONNECTIONS_STUDY.md). It is a synthetic build comparison, not part of the production frontend.

`react-animation-benchmark.mjs` generates and builds four small applications. The native fixture uses a fixed SVG diagram. React Flow adds canvas controls; Motion mini and LazyMotion add inspector transitions to the native diagram. Total output therefore compares candidate capabilities, not identical implementations or runtime speed.

The production `frontend/package.json`, lockfile and source imports remain unchanged. Install the experiment only in a separate scratch directory. The two renamed package files below preserve exact top-level and transitive versions without becoming another application package in the repository.

From the repository root, in PowerShell with Node 24.22.0 available:

```powershell
$studyDir = Join-Path $env:TEMP 'agent-react-comparison'
New-Item -ItemType Directory -Path $studyDir -Force | Out-Null
Copy-Item -LiteralPath 'docs/design/experiments/react-animation-package.json' -Destination (Join-Path $studyDir 'package.json')
Copy-Item -LiteralPath 'docs/design/experiments/react-animation-package-lock.json' -Destination (Join-Path $studyDir 'package-lock.json')
npm ci --prefix $studyDir --ignore-scripts --no-audit --no-fund
node docs/design/experiments/react-animation-benchmark.mjs $studyDir
node docs/design/experiments/react-animation-smoke.mjs $studyDir frontend
```

The smoke check requires the existing frontend Playwright dependency and its Chromium installation. It starts an ephemeral loopback server, checks the examples, saves screenshots and closes its own server/browser. It does not connect to platform APIs.

- `react-animation-results.json`: measured compressed assets, versions and lockfile SHA-256.
- `react-animation-package*.json`: the experiment manifest and reproducible dependency lock.
- `react-native-study.png` and `react-flow-study.png`: actual desktop screenshots of the synthetic fixture, captured with reduced motion after interaction.
- `react-animation-benchmark.mjs`: generates `entries/`, builds `dist/` and writes `results.json` inside the supplied scratch directory.
- `react-animation-smoke.mjs`: writes `smoke-results.json` and captures inside that directory. It is a limited desktop check; it does not establish product accessibility or performance acceptance.

Vite emitted module-level `use client` directive warnings from the third-party libraries. These experiments are entirely client-rendered; they do not test server-component behavior. All builds completed. The `LazyMotion` experiment imports `domAnimation` eagerly and measures aggregate bytes, not an optimized initial-load split.

Verification counts belong in [README Testing](../../../README.md#testing). Raw build/smoke logs and additional screenshots were kept in local assessment evidence outside Git.
