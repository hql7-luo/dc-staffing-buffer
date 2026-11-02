import numpy as np
import pandas as pd

import assumptions as A
import buffer_sim as B
from simulate_data import make_history, period_of_week, weekly_season


def test_season_averages_one_and_has_52_weeks():
    season = weekly_season()
    assert len(season) == 52
    assert abs(season.mean() - 1) < 1e-12


def test_periods_and_peak_mask():
    assert period_of_week(1) == 1 and period_of_week(4) == 1 and period_of_week(52) == 13
    mask = B.peak_week_mask([10, 11, 12, 13])
    assert mask.sum() == 16 and mask[36] and not mask[35]


def test_simulated_history_shape():
    df = make_history()
    assert list(df.columns) == ["year", "week", "period", "miles"]
    assert len(df) == len(A.HISTORY_YEARS) * 52
    assert (df.miles > 0).all()


def test_no_shortage_without_noise_or_absence():
    needs = np.full((50, 52), 20)
    result = B.evaluate_policy(needs, base_staff=20, fixed_buffer=0, absence_rate=0.0)
    assert result["outsourced_week_share"] == 0
    assert result["outside_cost"] == 0


def test_costs_add_up():
    needs = np.full((10, 52), 22)
    r = B.evaluate_policy(needs, base_staff=20, fixed_buffer=1, absence_rate=0.0,
                          overtime_cap=0.0, short_cost=1000, hold_cost=100)
    # no overtime, always 1 driver short: 52 weeks * $1,000; one extra driver: 52 weeks * $100
    assert r["outside_cost"] == 52 * 1000
    assert r["extra_driver_cost"] == 52 * 100
    assert r["total_cost"] == r["overtime_cost"] + r["outside_cost"] + r["extra_driver_cost"]


def test_peak_buffer_cost_counts_only_peak_weeks():
    needs = np.full((10, 52), 20)
    r = B.evaluate_policy(needs, base_staff=20, fixed_buffer=0, peak_buffer=2,
                          absence_rate=0.0, hold_cost=100, onboard_cost=500)
    assert r["extra_driver_cost"] == 2 * 16 * 100 + 2 * 500


def test_more_buffer_means_fewer_outsourced_weeks():
    needs = B.simulate_needs(20, n_years=2000)
    table = B.compare_fixed_buffers(needs, base_staff=20, buffers=[0, 1, 2, 3, 4])
    assert table.outsourced_week_share.is_monotonic_decreasing
    assert table.outside_cost.is_monotonic_decreasing


def test_overtime_fills_gap_before_outside_carriers():
    needs = np.full((10, 52), 21)
    # 20 drivers, 1 short each week; 10% overtime of 20 drivers = 2 driver-weeks
    r = B.evaluate_policy(needs, base_staff=20, fixed_buffer=0, absence_rate=0.0,
                          overtime_cap=0.10, overtime_cost=100, short_cost=1000)
    assert r["gap_week_share"] == 1
    assert r["outsourced_week_share"] == 0
    assert r["overtime_cost"] == 52 * 100
    assert r["outside_cost"] == 0


def test_gap_bigger_than_overtime_goes_outside():
    needs = np.full((10, 52), 23)
    # 3 short, overtime covers 2, so 1 driver-week goes outside every week
    r = B.evaluate_policy(needs, base_staff=20, fixed_buffer=0, absence_rate=0.0,
                          overtime_cap=0.10, overtime_cost=100, short_cost=1000)
    assert r["outsourced_week_share"] == 1
    assert r["overtime_cost"] == 52 * 2 * 100
    assert r["outside_cost"] == 52 * 1 * 1000


def test_more_overtime_means_fewer_outsourced_weeks():
    needs = B.simulate_needs(20, n_years=2000)
    shares = [B.evaluate_policy(needs, 20, 0, overtime_cap=c)["outsourced_week_share"]
              for c in (0.0, 0.1, 0.2)]
    assert shares[0] > shares[1] > shares[2]


def test_cheapest_meeting_target():
    options = pd.DataFrame({"fixed_buffer": [1, 2, 3], "peak_buffer": [0, 0, 1],
                            "outsourced_week_share": [0.10, 0.04, 0.03],
                            "total_cost": [100, 300, 200]})
    best = B.cheapest_meeting_target(options, target=0.05)
    assert best.fixed_buffer == 3
    assert B.cheapest_meeting_target(options, target=0.01) is None
