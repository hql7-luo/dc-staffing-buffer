import pytest

from staffing_lp import solve_staffing_plan

WEEK_MILES = 2000


def miles_for(drivers):
    """Yearly miles that exactly `drivers` fully productive drivers can cover."""
    return drivers * 52 * WEEK_MILES


def test_plan_covers_demand_and_minimum():
    plan = solve_staffing_plan({2026: miles_for(17.5), 2027: miles_for(19)},
                               start_headcount=17, min_headcount=16, max_hires=6,
                               training_weeks=0, miles_per_driver_week=WEEK_MILES)
    assert plan.drivers.tolist() == [18, 19]
    assert plan.hires.tolist() == [1, 1]
    assert (plan.drivers >= 16).all()


def test_training_weeks_need_an_extra_hire():
    # 20 drivers would be enough, but 3 new hires lose 4 weeks each to training
    plan = solve_staffing_plan({2026: miles_for(20)}, start_headcount=17,
                               training_weeks=4, miles_per_driver_week=WEEK_MILES)
    assert plan.drivers.iloc[0] == 21


def test_layoff_when_cheaper_than_keeping():
    plan = solve_staffing_plan({2026: miles_for(16)}, start_headcount=20, min_headcount=10,
                               miles_per_driver_week=WEEK_MILES, layoff_cost=1000)
    assert plan.drivers.iloc[0] == 16
    assert plan.layoffs.iloc[0] == 4


def test_hiring_limit_can_make_plan_infeasible():
    with pytest.raises(ValueError):
        solve_staffing_plan({2026: miles_for(30)}, start_headcount=10, max_hires=2,
                            training_weeks=0, miles_per_driver_week=WEEK_MILES)
