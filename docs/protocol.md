# Protocol

Crucible runs move through INTAKE, DISCOVERY, DESIGN, PLAN, IMPLEMENT, REVIEW, VERIFY, DELIVER, LEARN, and COMPLETE. PAUSED and ABORTED are durable control states.

Stage transitions are requests, not prose claims. The transition service reads durable artifacts, human approvals, tasks, review outcome, and current evidence before allowing movement. Quick may skip selected stages with a recorded reason. Standard requires human design and plan approvals. Critical adds destructive-action and completion authority plus stronger evidence requirements.

Model tools may record work products and request transitions. They cannot create protected human approvals or waivers. Human slash and terminal commands share the same service layer and record actor and source.

Verification succeeds only with an explicit zero exit code, an unchanged workspace during execution, and evidence matching the current Git snapshot. Missing, failed, indeterminate, or stale evidence blocks delivery.
