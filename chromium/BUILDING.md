# Windows source builder for Soulu Chromium Preview 1

This procedure builds Chromium's native `chrome` target with the Soulu source
overlay. CEF, Electron, WebView2 and separately embedded browser engines are not
used. **Native compilation has not yet been run. There is no accepted ZIP.**

## Locked inputs

| Input | Immutable revision |
| --- | --- |
| Chromium 156.0.8078.48 | `d0c02bfad08ec92a6ffcf989e53cd995e6381a4c` |
| depot_tools | `816da11f80777dcf8c10bdaa84df18450dcba12a` |
| Soulu CEF visual reference | `f3a4ae3fc1f15487c95811de8010524ab95b311b` |

Chromium DEPS pins the dependency/tool downloads. depot_tools self-update is
disabled. `args.gn` fixes the release-like x64 build configuration without
disabling sandboxing, the GPU, or site isolation. Exact binary reproducibility
has not been established: Windows/Visual Studio servicing versions and the
generated build metadata can affect the final bytes.

## Builder requirements

The **pinned revision's** `docs/windows_build_instructions.md` requires VS 2026
18.x, C++ desktop tools, MFC/ATL, Windows SDK installer 10.0.28000.2270
(header directory 10.0.28000.0), SDK Debugging Tools 10.0.26100.3323 or later,
Windows 10+ x64, and at least 100 GB free NTFS. This project's build preflight
requires at least 16 GB RAM. 100 GB is an upstream minimum, not a promise of
sufficient space for every build configuration.

Practical recommendation: Windows 11/Server 2025 x64, 16 CPU cores, 64 GB RAM,
at least 300 GB **free** SSD on NTFS (a 600 GB disk is comfortable), a persistent
work directory such as `C:\soulu-build`, Git, Python 3, Node.js, PowerShell 7,
and the toolchain above. A network connection must reach GitHub, Google's
Chromium Git/dependency storage and Chrome Infrastructure Package Deployment
(CIPD) services. The runner must retain its source tree between build attempts.

## Available remote approaches

| Option | Suitability | Owner action |
| --- | --- | --- |
| Standard `windows-2025-vs2026` Actions runner | Source/transport tests and environment diagnostics. GitHub guarantees only 14 GB working storage for standard hosted runners; not a reliable full Chromium builder. | None; source checks run on branch pushes. |
| GitHub larger Windows runner, 16 cores / 64 GB / 600 GB SSD | Suitable size, subject to actual preflight and SDK availability; billed even for public repositories. Available to organizations/enterprises on Team/Enterprise Cloud. | Configure paid organization runner access, then set its exact labels. A larger-runner label is not created just by writing `runs-on`. |
| Dedicated self-hosted Windows x64 runner | Works with a personal repository and permits persistent incremental builds. | Register a suitable Windows machine with this repository, label it `soulu-chromium`, then set the repository variable below. |

The connector used in this session cannot enumerate repository runners or
provision a machine. Their availability has not been inferred from public
repository metadata. No paid infrastructure was created.

Actual hosted probe on 2026-11-03, run
https://github.com/sanderstripa/soulu/actions/runs/41602674329:
Windows Server 2025, VS 2026, 4 logical CPUs, 17,174,360,064 bytes RAM,
32,821,063,680 bytes free on the selected C: NTFS volume. SDK 10.0.28000.0
headers were absent. Windows source/transport tests and PowerShell syntax
passed; the native compilation job was skipped because no builder label was
configured. See the run's `chromium-source-checks-*` artifact for the report.

Sources:

* https://chromium.googlesource.com/chromium/src/+/d0c02bfad08ec92a6ffcf989e53cd995e6381a4c/docs/windows_build_instructions.md
* https://docs.github.com/en/actions/reference/runners/github-hosted-runners
* https://docs.github.com/en/actions/concepts/runners/larger-runners
* https://docs.github.com/en/actions/reference/runners/larger-runners
* https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners

## Minimum steps to enable the prepared Actions build

1. On the prepared Windows machine, follow the exact commands shown at
   repository **Settings → Actions → Runners → New self-hosted runner → Windows
   x64**. Use a dedicated build account and add custom label `soulu-chromium`.
   Do not paste the temporary registration token into the repository or chat.
2. In **Settings → Secrets and variables → Actions → Variables**, create
   `SOULU_CHROMIUM_RUNNER` with the JSON value
   `["self-hosted","Windows","X64","soulu-chromium"]`.
   Optionally set `SOULU_CHROMIUM_WORK_ROOT` to a short NTFS path with enough
   free space; otherwise `C:\soulu-build` is used.
3. Trigger a new branch push (including an empty commit), or rerun all jobs in
   an existing branch workflow after configuring the runner. The new workflow
   exists only in this branch, so it is not necessary to add it to `main` to
   trigger `push`. A manual dispatch entry may not be exposed until a workflow
   exists on the default branch; do not change `main` to work around this.

The workflow never runs self-hosted jobs on external pull requests. Source
checks run first on a standard GitHub runner. The native job has read-only
repository permissions, no persistent checkout credentials and a six-hour
timeout; a cancelled or timed-out compilation can be resumed from the preserved
source/build directory. Use only this project's trusted branch on the dedicated
runner, not arbitrary fork code.

For an organization larger runner, set `SOULU_CHROMIUM_RUNNER` to a JSON array
containing the exact configured label, and grant the repository access to its
runner group. This requires organization/billing setup by the owner.

## Direct build on that machine

From a clean checkout of `chromium-preview`:

```powershell
python chromium/check_builder.py --work-root C:\soulu-build
./chromium/build-windows.ps1 -WorkRoot C:\soulu-build -Jobs 8
```

For 16 GB RAM start with `-Jobs 2`. An initial Chromium checkout and compilation
can take hours. `-PrepareOnly` fetches locked source/dependencies and applies the
overlay without compiling. The script never cleans an existing unrelated
checkout. If its revisions differ, use a separate work root. Previously applied
Soulu files must still match their recorded hashes before an incremental rerun.

Expected compilation output: `C:\soulu-build\chromium\src\out\Soulu\chrome.exe`.
Do not distribute the executable alone: Chromium needs its DLLs, resource packs,
locales and other runtime files. Runtime packaging and acceptance are subsequent
steps; neither a source-check artifact nor `chromium-build-result.json` is a
working portable distribution.

## What is still required for a releasable Preview 1

First compile and resolve any API/GRIT/GN compatibility errors in this source
overlay. Adapt original dynamic HTML writes to Chromium WebUI Trusted Types
enforcement without disabling it. Then integrate the Home page and all Soulu settings sessions, native
history/bookmark/profile services, Xray/Sudoku IPC/proxy management, the own
network/cosmetic ad blocker and privacy/permission controls. Settings not yet
applied must continue to fail explicitly.

Finally assemble a full portable runtime and perform the original requested
Windows acceptance: equal-size CEF comparisons, light/dark and adaptive states,
tab and address behavior, YouTube playback, real VPN tunnels and blocking,
history/bookmark/profile/incognito isolation, settings persistence and smoothness.
Interactive GPU checks require a suitable desktop session; service-only CI
cannot establish physical GPU smoothness. Publish the ZIP as Preview 1 only
after mandatory functionality passes. The current workflow deliberately does
not create tags, releases or an allegedly accepted browser archive.
