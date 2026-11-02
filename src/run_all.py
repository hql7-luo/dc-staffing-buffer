"""Run the whole analysis on simulated data and save results and figures.

Usage: python src/run_all.py [--sims 10000]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import assumptions as A
import buffer_sim as B
import make_figures as F
from forecast import mape, ses_fitted, ses_next
from simulate_data import make_history
from staffing_lp import solve_staffing_plan

ROOT = Path(__file__).resolve().parent.parent


def main(n_sims):
    for folder in ["data/simulated", "results", "figures"]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)

    # 1. Simulated weekly history
    history = make_history()
    history.to_csv(ROOT / "data/simulated/weekly_miles.csv", index=False)

    # 2. Forecast yearly miles with simple exponential smoothing
    yearly = history.groupby("year").miles.sum()
    fitted = ses_fitted(yearly.values, A.SES_ALPHA)
    forecast = ses_next(yearly.values, A.SES_ALPHA)
    print(f"Forecast MAPE on simulated history: {mape(yearly.values, fitted):.1%}")

    # 3. Yearly staffing plan (linear program)
    plan = solve_staffing_plan({y: forecast for y in A.PLAN_YEARS})
    plan.to_csv(ROOT / "results/staffing_plan.csv", index=False)
    base_staff = int(plan.drivers.iloc[0])
    avg_need = float(plan.avg_drivers_needed.iloc[0])
    print(f"Plan: {base_staff} drivers (average need {avg_need:.1f})")

    # 4. Weekly simulation of the buffer
    needs = B.simulate_needs(avg_need, n_years=n_sims)
    fixed = B.compare_fixed_buffers(needs, base_staff)
    fixed.to_csv(ROOT / "results/fixed_buffers.csv", index=False)
    target_buffer = B.smallest_buffer_for_target(needs, base_staff)

    options = B.compare_peak_options(needs, base_staff)
    options.to_csv(ROOT / "results/fixed_vs_peak.csv", index=False)
    fixed_only = options[options.peak_buffer == 0]
    best_fixed = B.cheapest_meeting_target(fixed_only)
    best_any = B.cheapest_meeting_target(options)

    sens = B.sensitivity_grid(needs, base_staff)
    sens.to_csv(ROOT / "results/sensitivity.csv", index=False)

    # Where do the gaps come from? Absences only (flat volume) vs volume swings only
    flat_needs = np.full_like(needs, round(avg_need))
    split = pd.DataFrame([
        {"case": "absences only", **B.evaluate_policy(flat_needs, base_staff, 0)},
        {"case": "volume swings only", **B.evaluate_policy(needs, base_staff, 0, absence_rate=0.0)},
        {"case": "both", **B.evaluate_policy(needs, base_staff, 0)},
    ])
    split.to_csv(ROOT / "results/where_gaps_come_from.csv", index=False)
    by_period = B.outsourced_share_by_period(needs, base_staff)
    by_period.to_csv(ROOT / "results/outsourced_by_period.csv", index=False)
    by_cap = pd.DataFrame([
        {"overtime_cap": cap,
         "buffer_for_target": B.smallest_buffer_for_target(needs, base_staff, overtime_cap=cap)}
        for cap in A.SENS_OVERTIME_CAPS])
    by_cap.to_csv(ROOT / "results/buffer_for_target_by_overtime.csv", index=False)

    # 5. Figures
    F.plot_fixed_buffers(fixed, ROOT / "figures/1_fixed_buffers.png")
    F.plot_fixed_vs_peak(options, best_fixed, best_any, ROOT / "figures/2_fixed_vs_peak.png")
    F.plot_sensitivity(sens, ROOT / "figures/3_sensitivity.png")

    # 6. Short summary for the README
    print("\nAll-year buffer:")
    print(fixed.round(3).to_string(index=False))
    print(f"\nSmallest all-year buffer for <= {A.SERVICE_TARGET:.0%} outsourced weeks: {target_buffer}")
    for name, row in [("Best all-year option", best_fixed), ("Best overall option", best_any)]:
        if row is not None:
            print(f"{name}: fixed {int(row.fixed_buffer)} + peak {int(row.peak_buffer)}, "
                  f"outsourced weeks {row.outsourced_week_share:.1%}, total ${row.total_cost:,.0f}")
    print("\nWhere gaps come from (no buffer):")
    print(split[["case", "gap_week_share", "outsourced_week_share"]].round(3).to_string(index=False))
    print("\nOutsourced weeks by fiscal period (no buffer):")
    print(by_period.round(3).to_string(index=False))
    print("\nBuffer needed for the target by overtime cap:")
    print(by_cap.to_string(index=False))
    for cap in A.SENS_OVERTIME_CAPS:
        print(f"\nLowest-cost buffer, overtime cap {cap:.0%} (columns: shortage cost, rows: absence rate):")
        part = sens[sens.overtime_cap == cap]
        print(part.pivot(index="absence_rate", columns="short_cost", values="best_buffer"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", type=int, default=A.N_SIMULATED_YEARS)
    main(parser.parse_args().sims)
