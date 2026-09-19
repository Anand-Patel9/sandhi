from app.core.guards import prices_consistent, redact_private
from app.core.models import Terms
from app.core.scenarios import get_scenario
from app.core.utilities import (buyer_surplus, financier_floor_rate, financier_surplus,
                                supplier_surplus)


def test_walk_away_points_are_zero():
    sc = get_scenario("auto_parts")
    s, b = sc.supplier, sc.buyer
    assert abs(supplier_surplus(Terms(s.batna_price, s.batna_days), s, sc.spec)) < 1e-6
    batna = buyer_surplus(Terms(b.batna_price, b.batna_days), b, sc.spec, sc.market)
    assert abs(batna - b.switching_cost) < 1e-6


def test_financier_breaks_even_at_floor_rate():
    sc = get_scenario("auto_parts")
    t = Terms(400, 45, True, 0.0, financier_floor_rate(sc.financier))
    assert abs(financier_surplus(t, sc.financier, sc.spec)) < 1e-6


def test_late_payment_costs_buyer_under_43bh():
    sc = get_scenario("auto_parts")
    on_time = buyer_surplus(Terms(410, 45), sc.buyer, sc.spec, sc.market)
    late = buyer_surplus(Terms(410, 60), sc.buyer, sc.spec, sc.market)
    assert on_time > late


def test_privacy_guard_redacts_private_numbers_only():
    msg, leaked = redact_private("Our runway is 38 days and we offer ₹400.00", [38, 355], "₹400.00")
    assert leaked and "38" not in msg and "400.00" in msg


def test_consistency_guard():
    assert prices_consistent("We offer ₹400.00/unit", [400.0])
    assert not prices_consistent("We offer ₹405/unit", [400.0])