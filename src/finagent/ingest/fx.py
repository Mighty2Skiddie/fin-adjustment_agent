"""FX rate selection and translation.

Which rate to use when one is missing is a *policy* a human owns (`config.fx.missing_rate_policy`),
not something the code decides. A fallback rate keeps its own id (`GBP/period_average`) and is
marked `is_fallback=True` so every line it touches says so in its lineage.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from finagent.domain.models import FxRate, TbRow
from finagent.domain.money import q

FALLBACK_RATE_TYPE = {
    "fallback_average": "period_average",
    "fallback_opening": "opening",
}


class MissingRateError(LookupError):
    def __init__(self, currency: str, rate_type: str) -> None:
        super().__init__(f"No {rate_type} rate for {currency}")
        self.currency = currency
        self.rate_type = rate_type


class RateBook:
    def __init__(
        self, rates: Iterable[FxRate], policy: str, functional_currency: str = "USD"
    ) -> None:
        self._rates: dict[tuple[str, str], FxRate] = {(r.currency, r.rate_type): r for r in rates}
        self.policy = policy
        self.functional_currency = functional_currency

    def has(self, currency: str, rate_type: str) -> bool:
        return (currency, rate_type) in self._rates

    def get(self, currency: str, rate_type: str) -> FxRate | None:
        """Exact lookup, no policy applied."""
        return self._rates.get((currency, rate_type))

    def rates(self) -> list[FxRate]:
        return list(self._rates.values())

    def rate_for(self, currency: str, rate_type: str) -> FxRate:
        exact = self._rates.get((currency, rate_type))
        if exact is not None:
            return exact
        if currency == self.functional_currency:
            # The functional currency translates at 1 for every rate type (no USD opening row).
            return FxRate(
                id=f"{currency}/{rate_type}",
                currency=currency,
                rate_type=rate_type,
                rate=Decimal("1"),
                period="",
            )
        fallback_type = FALLBACK_RATE_TYPE.get(self.policy)
        if fallback_type is None:
            raise MissingRateError(currency, rate_type)
        fb = self._rates.get((currency, fallback_type))
        if fb is None:
            raise MissingRateError(currency, rate_type)
        return fb.model_copy(update={"is_fallback": True, "requested_rate_type": rate_type})


def translate(row: TbRow, rate: FxRate) -> tuple[Decimal, Decimal]:
    """Debit and credit are translated and quantized separately (no netting before rounding)."""
    return q(row.debit * rate.rate), q(row.credit * rate.rate)
