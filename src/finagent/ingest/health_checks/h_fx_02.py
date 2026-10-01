"""H-FX-02: opening rates allow a translation-reserve (CTA) walk; noting they exist tells the
reviewer what the prototype could, but does not, use them for."""

from __future__ import annotations

from finagent.domain.models import HealthFinding, HealthSeverity
from finagent.ingest.health_checks.base import AuditContext

CHECK_ID = "H-FX-02"


def check(ctx: AuditContext) -> list[HealthFinding]:
    functional = ctx.settings.functional_currency
    found = {
        r.currency: str(r.rate)
        for r in ctx.fx_rates
        if r.rate_type == "opening" and r.currency != functional
    }
    if not found:
        return []
    opening = dict(sorted(found.items()))
    listed = ", ".join(f"{c} {v}" for c, v in opening.items())
    return [
        HealthFinding(
            id=CHECK_ID,
            severity=HealthSeverity.INFO,
            file="fx_rates.csv",
            title="Opening rates present",
            message=(
                f"Opening rates are available ({listed}). They support a translation-reserve "
                "walk but are only used here to translate the prior-period TB."
            ),
            evidence={"opening_rates": opening},
            suggested_action="No action needed; available for a translation-reserve walk.",
        )
    ]
