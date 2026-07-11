# Crucible Profiles

Crucible applies process in proportion to risk. Profiles change required artifacts, approvals, review, and evidence counts; none can waive fresh successful verification.

## Quick

Quick is for low-risk, localized work. It requires intake, implementation, at least one fresh verification check, and a completion artifact. Discovery, design, planning, review, and learning may be skipped only with a recorded reason.

## Standard

Standard is the default. It requires discovery, design and human design approval, a plan and human plan approval, tracked implementation, review, fresh verification, delivery, and a learning decision.

## Critical

Critical covers security, secrets, migrations, destructive actions, concurrency, billing, deployment, and other high-impact work. It includes every Standard gate plus at least two verification checks, explicit rollback and unresolved-risk material, approval-gated high-risk actions, human completion approval, and fail-closed mutation when policy state cannot be loaded.

Crucible policy coordinates engineering work; it is not a security sandbox and does not replace operating-system controls, isolation, or human review.
