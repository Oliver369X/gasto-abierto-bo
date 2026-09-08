from common.discrepancy import delta_pct
from decimal import Decimal


def test_delta_pct():
    assert delta_pct(Decimal("100"), Decimal("150")) == 33.333333333333336 or abs(
        delta_pct(Decimal("100"), Decimal("150")) - 33.333
    ) < 0.01
    assert delta_pct(None, Decimal("1")) is None
    assert delta_pct(Decimal("0"), Decimal("0")) == 0.0
    assert delta_pct(Decimal("0"), Decimal("100")) is None
    assert delta_pct(Decimal("50"), Decimal("0")) is None
