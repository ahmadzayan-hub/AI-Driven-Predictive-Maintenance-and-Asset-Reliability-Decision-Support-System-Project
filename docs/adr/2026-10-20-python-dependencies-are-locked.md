# Python deployments use a reviewed dependency lock

Date: 2026-10-20

## Context

Python dependency floors let an unchanged commit install different software
over time. The corrective review observed this directly: the installed
environment used FastAPI 0.152.0 while a fresh resolution selected 0.153.0.
Both audited clean, but an audit of one was not evidence about the other.

## Decision

Keep direct requirements and explanations in `requirements.in`. Generate
`requirements.txt` with exact transitive versions, platform markers and
artifact hashes using:

```sh
uv pip compile requirements.in --universal --python-version 3.11 --generate-hashes --output-file requirements.txt
```

The first lock preserves the reviewed installed versions and includes the
Linux-only uvloop dependency. Normal installations and Vercel continue to
read `requirements.txt`; pip enforces hash checking when hashes are present.
CI additionally specifies `--require-hashes`. The command above retains
existing compatible pins; use `--upgrade-package NAME` for a reviewed update
or `--upgrade` for an intentional full refresh.

The SBOM still reads actual installed distributions, starting from the direct
roots in `requirements.in`. CI installs its audit tool in a separate virtual
environment so tool dependencies cannot mutate the tested application or
inflate its inventory.

## Consequences and verification

This locks supported server installations across platform markers. Optional
voice and agent integrations remain separate opt-in environments and are not
claimed locked by this decision. The command-line core gains no dependency.
Regular reviewed updates remain necessary; a lock is not an advisory waiver.

Verify hash-checked installation, installed dependency consistency, the SBOM
tests, vulnerability audits and the complete CI suite. The canonical executed
results are in README testing. Local environment packages not required by the
lock are not automatically removed by `pip install`.

Sources: [uv locking environments](https://docs.astral.sh/uv/pip/compile/)
and [pip repeatable installs](https://pip.pypa.io/en/stable/topics/repeatable-installs/).
