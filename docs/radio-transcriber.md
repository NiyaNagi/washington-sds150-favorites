# Offline Radio Transcriber — moved

The offline radio transcriber project has moved to its own repository:

**https://github.com/NiyaNagi/offline-radio-transcriber**

It was developed here through September 2026 — research, functional specification,
technical design, implementation plan and an adversarial audit — and split out with its full
commit history once it became clear it was a separate product rather than part of this
repository's channel-plan tooling.

## Why it moved

Different toolchain (Kotlin/Gradle versus Python), different release cadence, different
audience. The coupling between them runs one way and through a single file: the transcriber's
lexicon needs frequency and repeater data, and this repository is where that data lives.

## What this repository still owes it

Nothing yet. The transcriber's technical design proposes that this repository grow an
asset-build target emitting a **versioned, checksummed lexicon bundle** — WWARA repeaters,
SDS150 favorites, POTA parks, band plans — which the app consumes through its normal asset
lifecycle. That work has not started, and the transcriber does not currently depend on it.

## What stayed here

The Kenwood TH-D75A reference material in `thd75a programming details/` stays, including
`TH_D75_Commands.pdf`. The transcriber needs the *facts* in that document, which are recorded
in its own `docs/reference/th-d75a-cat.md` with attribution — but the PDF is a third party's
copyrighted work and the new repository is public, so it was not redistributed.
