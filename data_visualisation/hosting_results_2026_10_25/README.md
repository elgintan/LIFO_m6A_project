# Public full-score explorer — 25 October 2026

**Live:** [SG-NEx m6A Explorer](https://lifo-sgnex-m6a-explorer.wittylemon1025.chatgpt.site).
Sites deployment succeeded and access is public. The full explorer is hosted:
23 runs, seven cell lines, 17 metadata groups, 451,352 scoreable keys,
2,983,948 scored run-site observations and all four biological cases. No subset
was selected for hosting. The same fixed model and scientific rules apply.

The deployment contains 174 static assets / 199,752,416 bytes. It reuses the
completed 24 October hosting archive without new inference or score building.
All 132 original score JSON files remain exact in the deployment source.
The local `integration_complete.json` was deliberately excluded because it
contains a private computer path; the public hosting manifest retains its hash.
No credential, private machine address or raw signal input was uploaded.

## Verified scope

- [Independent audit](independent_check.json): 33 checks passed, covering every
  static asset, all original score JSONs, both archives, the retained browser
  download and the two saved HTML responses. The native Sites archive contains
  175 regular files: 174 static assets plus one safe platform configuration.
- [Deployment receipt](deployment.json): returned production URL, saved version,
  successful deployment, public access revision and exact pushed source commit.
- [Hosted browser checks](browser_qa.json): all 36 case/depth/cutoff combinations,
  all four literal-site click/reload routes and an actual original-score CSV
  download. The downloaded 25,051-byte CSV has SHA256
  `eac092e7f83f4080eb83ed88e4ad38c261f8086e83924f0253a04b3c89cf4ded`,
  matching the frozen original. No browser console warnings/errors observed.
- [Anonymous HTTP verification](public_http_verification.json): 15 selected files
  returned HTTP200 without cookies, authentication or a private bypass token.
  Thirteen non-HTML files match source bytes exactly. Two HTML responses add
  one 938-byte Cloudflare JavaScript-detection script each; every original HTML
  byte is retained after isolating that added script locally for comparison.
  The hosting protection remains active. Request-specific injected values make
  raw HTML fingerprints vary. The [initial raw comparison](public_http_check.json)
  preserves its two HTML mismatches instead of silently calling them exact.
- [Live screenshot](hosted_explorer.png). Full-page capture timed out; viewport
  capture succeeded. A cold gene-bucket load exceeded an initial short browser
  wait; explicit network-aware waits subsequently passed all four routes. One
  combined browser call took unexpectedly long; this was not model computation.

The HTTP check sampled 15 files, not all 174 hosted assets. Full source/archive
fingerprints were checked before deployment. Browser checks cover one desktop
Chromium browser in the observed dark theme. Prior local 390px checks apply to
the identical frontend; no separate hosted phone, physical-device, cross-browser
or light-mode test is claimed. D3 and Google Fonts remain public runtime assets.
A default Python client received403 during diagnosis; the named verification
client and ordinary browser worked. No access-control bypass was used.

## Maintenance and next steps

The Sites identity and deployed source commit are in `deployment.json`. The
ignored local hosting checkout is `data_visualisation/outputs/sites_explorer_20261025_v1/`;
`.openai/hosting.json` retains the same project identity. Use the supported Sites
workflow and a fresh session credential for updates; never copy its token into
files or reports. Preserve current public access and update this Site rather
than creating a duplicate. Do not upload the original local integration receipt.

Original model/folds/23-run checkpoints, completed output directories, negative
experiments and unpromoted external candidate remain untouched. No RONIN restart.
Report drafting/layout/team checking and the actual new-test prediction/submission
remain separate. The user confirmed on 25 October that the new input has not been
received and will update later. A live website does not establish completed
course submission or independent biological validation.
