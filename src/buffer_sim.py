"""Weekly simulation: how many extra drivers to keep on top of the yearly plan."""
import numpy as np
import pandas as pd

import assumptions as A
from simulate_data import ar1_noise, period_of_week, weekly_season


def simulate_needs(avg_need, n_years=A.N_SIMULATED_YEARS, seed=A.SEED):
    """Drivers needed in each week of many simulated years (whole drivers)."""
    rng = np.random.default_rng(seed)
    noise = ar1_noise(rng, n_years, A.WEEKS_PER_YEAR, A.NOISE_SD, A.NOISE_AUTOCORR)
    needs = np.round(avg_need * weekly_season() * (1 + noise))
    return np.clip(needs, 0, None).astype(int)


def peak_week_mask(peak_periods=A.PEAK_PERIODS):
    """True for weeks that fall in the peak periods."""
    weeks = np.arange(1, A.WEEKS_PER_YEAR + 1)
    return np.isin(period_of_week(weeks), peak_periods)


def staff_by_week(base_staff, fixed_buffer, peak_buffer=0):
    """Drivers on staff each week: base + all-year buffer + peak-season buffer."""
    return base_staff + fixed_buffer + peak_buffer * peak_week_mask()


def simulate_weeks(needs, base_staff, fixed_buffer, peak_buffer=0,
                   absence_rate=A.ABSENCE_RATE, overtime_cap=A.OVERTIME_CAP, seed=A.SEED):
    """Driver-weeks missing, covered by overtime, and sent outside, for every simulated week."""
    rng = np.random.default_rng(seed + 1)
    staff = staff_by_week(base_staff, fixed_buffer, peak_buffer)
    absent = rng.binomial(np.broadcast_to(staff, needs.shape), absence_rate)
    available = staff - absent
    gap = np.clip(needs - available, 0, None)              # driver-weeks missing
    overtime = np.minimum(gap, available * overtime_cap)   # covered by overtime
    outside = gap - overtime                               # sent to outside carriers
    return gap, overtime, outside


def outsourced_share_by_period(needs, base_staff, fixed_buffer=0, **kwargs):
    """Share of weeks that still need an outside carrier, for each fiscal period."""
    _, _, outside = simulate_weeks(needs, base_staff, fixed_buffer, **kwargs)
    by_week = (outside > 1e-9).mean(axis=0)
    periods = period_of_week(np.arange(1, A.WEEKS_PER_YEAR + 1))
    return pd.DataFrame({"period": range(1, 14),
                         "outsourced_week_share": [by_week[periods == p].mean() for p in range(1, 14)]})


def evaluate_policy(needs, base_staff, fixed_buffer, peak_buffer=0,
                    absence_rate=A.ABSENCE_RATE, overtime_cap=A.OVERTIME_CAP,
                    short_cost=A.SHORT_COST_PER_WEEK, overtime_cost=A.OVERTIME_COST_PER_WEEK,
                    hold_cost=A.HOLD_COST_PER_WEEK,
                    onboard_cost=A.SEASONAL_ONBOARD_COST, seed=A.SEED):
    """Average yearly results for one staffing policy.

    Each week: drivers on staff minus absences = drivers available.
    A gap is filled with overtime first (up to overtime_cap of each available
    driver's week), and whatever is left goes to an outside carrier.
    """
    gap, overtime, outside = simulate_weeks(needs, base_staff, fixed_buffer, peak_buffer,
                                            absence_rate, overtime_cap, seed)
    extra_weeks = fixed_buffer * A.WEEKS_PER_YEAR + peak_buffer * peak_week_mask().sum()
    extra_cost = extra_weeks * hold_cost + peak_buffer * onboard_cost
    overtime_total = overtime.sum(axis=1).mean() * overtime_cost
    outside_total = outside.sum(axis=1).mean() * short_cost
    return {"fixed_buffer": fixed_buffer,
            "peak_buffer": peak_buffer,
            "gap_week_share": float((gap > 0).mean()),
            "outsourced_week_share": float((outside > 1e-9).mean()),
            "overtime_cost": float(overtime_total),
            "outside_cost": float(outside_total),
            "extra_driver_cost": float(extra_cost),
            "total_cost": float(overtime_total + outside_total + extra_cost)}


def compare_fixed_buffers(needs, base_staff, buffers=A.FIXED_BUFFERS, **kwargs):
    """One row per all-year buffer size."""
    return pd.DataFrame([evaluate_policy(needs, base_staff, b, **kwargs) for b in buffers])


def compare_peak_options(needs, base_staff, max_fixed=6, max_peak=3, **kwargs):
    """Every mix of all-year buffer and extra peak-season drivers."""
    rows = [evaluate_policy(needs, base_staff, f, p, **kwargs)
            for f in range(max_fixed + 1) for p in range(max_peak + 1)]
    return pd.DataFrame(rows)


def cheapest_meeting_target(options, target=A.SERVICE_TARGET):
    """Lowest-cost row whose outsourced-week share is at or below the target."""
    ok = options[options.outsourced_week_share <= target]
    if ok.empty:
        return None
    return ok.sort_values("total_cost").iloc[0]


def smallest_buffer_for_target(needs, base_staff, target=A.SERVICE_TARGET, max_buffer=15, **kwargs):
    """Smallest all-year buffer that keeps outsourced weeks at or below the target."""
    for b in range(max_buffer + 1):
        if evaluate_policy(needs, base_staff, b, **kwargs)["outsourced_week_share"] <= target:
            return b
    return None


def sensitivity_grid(needs, base_staff, short_costs=A.SENS_SHORT_COSTS,
                     absence_rates=A.SENS_ABSENCE_RATES, overtime_caps=A.SENS_OVERTIME_CAPS,
                     max_buffer=6):
    """Lowest-cost all-year buffer for each overtime cap, shortage cost and absence rate."""
    rows = []
    for cap in overtime_caps:
        for rate in absence_rates:
            for cost in short_costs:
                table = compare_fixed_buffers(needs, base_staff, range(max_buffer + 1),
                                              absence_rate=rate, short_cost=cost, overtime_cap=cap)
                best = table.sort_values("total_cost").iloc[0]
                rows.append({"overtime_cap": cap, "absence_rate": rate, "short_cost": cost,
                             "best_buffer": int(best.fixed_buffer),
                             "outsourced_week_share": best.outsourced_week_share})
    return pd.DataFrame(rows)
