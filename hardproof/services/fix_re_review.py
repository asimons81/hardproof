"""Fix/re-review loop for Challenge Chamber (CC-08)."""

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class FixReReviewLoop:
    """Encapsulates a blocking review finding that must return to IMPLEMENT then re-review."""
    run_id: str
    blocking_finding: str
    reviewer: str
    severity: str = "high"  # high|medium|low
    target_stage: str = "IMPLEMENT"

    def trigger_fix(self) -> dict[str, str]:
        """Return transition payload to send blocking fixes back to IMPLEMENT."""
        return {
            "action": "return_to_implement",
            "reason": self.blocking_finding,
            "reviewer": self.reviewer,
            "severity": self.severity,
        }

    def require_re_review(self) -> bool:
        """Gate blocks until a fresh re-review approval is recorded."""
        return True
