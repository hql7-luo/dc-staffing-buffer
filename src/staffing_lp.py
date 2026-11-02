"""Yearly staffing plan as a small linear program (rebuilt in PuLP).

This is a reconstruction from the project description, not the course
model. The cost inputs are the labeled assumptions in assumptions.py.
"""
import pandas as pd
import pulp

import assumptions as A


def solve_staffing_plan(demand_miles, start_headcount=A.START_HEADCOUNT,
                        min_headcount=A.MIN_HEADCOUNT, max_hires=A.MAX_HIRES_PER_YEAR,
                        training_weeks=A.TRAINING_WEEKS,
                        miles_per_driver_week=A.MILES_PER_DRIVER_WEEK,
                        weekly_cost=A.HOLD_COST_PER_WEEK,
                        hire_cost=A.HIRE_TRAIN_COST, layoff_cost=A.LAYOFF_COST):
    """demand_miles: {year: total miles that year}. Returns one row per year."""
    years = sorted(demand_miles)
    weeks = A.WEEKS_PER_YEAR
    model = pulp.LpProblem("staffing_plan", pulp.LpMinimize)

    # Decision variables: drivers on staff, hires and layoffs each year
    staff = {y: pulp.LpVariable(f"staff_{y}", lowBound=0, cat="Integer") for y in years}
    hires = {y: pulp.LpVariable(f"hires_{y}", lowBound=0, upBound=max_hires, cat="Integer") for y in years}
    layoffs = {y: pulp.LpVariable(f"layoffs_{y}", lowBound=0, cat="Integer") for y in years}

    # Objective: pay and benefits + hiring and training + layoffs
    model += pulp.lpSum(weekly_cost * weeks * staff[y] + hire_cost * hires[y]
                        + layoff_cost * layoffs[y] for y in years)

    previous = start_headcount
    for y in years:
        # Headcount carries over from last year
        model += staff[y] == previous + hires[y] - layoffs[y], f"balance_{y}"
        # Enough driver-weeks to cover the forecast miles
        # (new hires spend their first weeks in training)
        productive_weeks = weeks * staff[y] - training_weeks * hires[y]
        model += productive_weeks * miles_per_driver_week >= demand_miles[y], f"demand_{y}"
        # Never go below the minimum crew
        model += staff[y] >= min_headcount, f"minimum_{y}"
        previous = staff[y]

    model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[model.status] != "Optimal":
        raise ValueError("Staffing plan has no feasible solution: " + pulp.LpStatus[model.status])

    rows = []
    for y in years:
        rows.append({"year": y,
                     "avg_drivers_needed": demand_miles[y] / (weeks * miles_per_driver_week),
                     "drivers": int(staff[y].value()),
                     "hires": int(hires[y].value()),
                     "layoffs": int(layoffs[y].value())})
    plan = pd.DataFrame(rows)
    plan["cost"] = (weekly_cost * weeks * plan.drivers + hire_cost * plan.hires
                    + layoff_cost * plan.layoffs)
    return plan
