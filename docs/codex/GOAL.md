# Hardproof: From Core Heat to Proven

Build Hardproof as a production-grade, contributor-ready, open-source engineering protocol for Hermes Agent through the gated release train v0.1.0 to v1.0.0.

The binding source is `hardproof_codex_plan_and_roadmap.md`. Each release must satisfy its specification, tests, documentation, migration, security, packaging, compatibility, and evidence gates before the next release begins.

## Operating contract

- Work autonomously and choose the smallest reversible solution for ordinary ambiguity.
- Record consequential decisions in ADRs and lock them with tests.
- Use only current public Hermes plugin APIs; never patch Hermes or use private attributes.
- Keep project state local, durable, bounded, secret-safe, and free of telemetry or hidden network traffic.
- Never create human approvals through model-callable tools.
- Never claim verification without an explicit zero exit status tied to the current workspace snapshot.
- Maintain `STATUS.md` before and after every task so another session can resume from repository state alone.
- Produce a release report and all required evidence for every version.

## Release train

`v0.1.0 -> v0.2.0 -> v0.3.0 -> v0.4.0 -> v0.5.0 -> v0.6.0 -> v0.7.0 -> v0.8.0 -> v0.9.0 -> v1.0.0`

## Final definition of done

All ten releases have passed their gates; migrations from every prior public version pass; supported-platform, package, security, compatibility, and end-to-end evidence is current; no placeholders or secrets remain; `FINAL_AUDIT.md` maps every promise to inspectable code, tests, documentation, release evidence, and Git history; and `STATUS.md` reads `GOAL COMPLETE`.

The full originating goal contract is preserved at `docs/codex/source/HARDPROOF_CODEX_GOAL.md` once the repository bootstrap task establishes the documentation import.
