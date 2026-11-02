"""All model inputs in one place.

Every number here is either a public figure (source noted) or a labeled
assumption. None of them come from the course partner's data.
"""

# ---------- Fictional distribution center (simulated data) ----------
SEED = 2026
HISTORY_YEARS = list(range(2020, 2026))   # simulated history, 2020-2025
PLAN_YEARS = list(range(2026, 2031))      # staffing plan, 2026-2030
WEEKS_PER_YEAR = 52
WEEKS_PER_PERIOD = 4                      # 13 four-week fiscal periods

# Fictional average weekly miles for each history year (assumption).
WEEKLY_MILES_BY_YEAR = {2020: 33000, 2021: 35000, 2022: 36000,
                        2023: 37500, 2024: 38500, 2025: 39500}

# Seasonal shape by fiscal period, rounded to 0.05 (assumption).
# Quieter around the winter holidays (period 5), busier in summer (periods 8-13).
SEASONAL_INDEX = [1.00, 1.00, 1.00, 0.95, 0.80, 0.95, 1.00,
                  1.05, 1.05, 1.05, 1.05, 1.00, 1.05]

# Week-to-week noise on top of the seasonal shape (assumption, rounded).
NOISE_SD = 0.10        # about +/-10% in a typical week
NOISE_AUTOCORR = 0.3   # a busy week is a bit more likely to follow a busy week

# ---------- Forecast (same method as the course project) ----------
SES_ALPHA = 0.75       # simple exponential smoothing weight

# ---------- Driver productivity and pay ----------
# Assumption: one driver covers about 2,000 miles in a normal week
# (a common figure for regional truck drivers).
MILES_PER_DRIVER_WEEK = 2000
PAID_HOURS_PER_WEEK = 40   # assumption

# BLS OEWS, May 2023: mean hourly wage, heavy and tractor-trailer truck
# drivers (SOC 53-3032), Washington State.
WAGE_PER_HOUR = 30.36

# BLS ECEC, Sep 2025, private industry, production, transportation and
# material moving occupations: wages are about 68% of total compensation.
WAGE_SHARE_OF_COMP = 0.68

# Cost of keeping one extra driver for one week (wage + benefits),
# rounded to the nearest $100: 30.36 * 40 / 0.68 is about $1,786 -> $1,800.
HOLD_COST_PER_WEEK = round(WAGE_PER_HOUR * PAID_HOURS_PER_WEEK / WAGE_SHARE_OF_COMP, -2)

# ---------- Cost of being one driver short for one week ----------
# ATRI, Operational Costs of Trucking (2026 update, 2025 data):
# average marginal cost $2.336 per mile, of which fuel is about $0.48.
# Assumption: a missing driver-week is covered by an outside carrier at
# about ATRI's cost per mile, and our own truck saves its fuel.
OUTSIDE_COST_PER_MILE = 2.336
OWN_FUEL_PER_MILE = 0.48
SHORT_COST_PER_WEEK = round(MILES_PER_DRIVER_WEEK * (OUTSIDE_COST_PER_MILE - OWN_FUEL_PER_MILE), -2)

# ---------- Overtime ----------
# Assumption: each driver can work up to 10% more hours in a week, paid at
# 1.5x the hourly wage (no extra benefits). Overtime fills a gap first;
# anything left goes to an outside carrier.
OVERTIME_CAP = 0.10
OVERTIME_PAY_MULTIPLIER = 1.5
# Cost of one driver-week of work done as overtime: 1.5 * 30.36 * 40, about $1,820
OVERTIME_COST_PER_WEEK = round(OVERTIME_PAY_MULTIPLIER * WAGE_PER_HOUR * PAID_HOURS_PER_WEEK, -1)

# ---------- Absences ----------
# BLS CPS 2024, Table 47: 3.2% of full-time wage and salary workers were
# absent in a given week. Assumption: each driver misses a whole week
# with this chance, independently of other drivers.
ABSENCE_RATE = 0.03

# ---------- Staffing plan (linear program) ----------
START_HEADCOUNT = 18          # fictional drivers on staff at the end of 2025
MIN_HEADCOUNT = 16            # assumption: policy floor
MAX_HIRES_PER_YEAR = 6        # assumption: recruiting limit
TRAINING_WEEKS = 4            # assumption: a new hire is not productive yet
# UGPTI (2000), "The Costs of Truckload Driver Turnover": $8,234 per driver
# in 2000 dollars. Moved to 2025 dollars with the BLS CPI-U annual average
# (2000: 172.2, 2025: 321.943): 8,234 * 321.943 / 172.2 is about $15,400.
# Used here as the cost to hire and train one driver (assumption).
TURNOVER_COST_2000 = 8234
CPI_2000, CPI_2025 = 172.2, 321.943
HIRE_TRAIN_COST = round(TURNOVER_COST_2000 * CPI_2025 / CPI_2000, -2)
LAYOFF_COST = 2 * HOLD_COST_PER_WEEK   # assumption: two weeks of pay

# ---------- Buffer analysis ----------
N_SIMULATED_YEARS = 10000
FIXED_BUFFERS = [0, 1, 2, 3, 4]
PEAK_PERIODS = [10, 11, 12, 13]  # periods where a seasonal buffer is added
SERVICE_TARGET = 0.05            # goal: outside carriers needed in at most 5% of weeks
# A seasonal driver must also be hired and trained each year (assumption).
SEASONAL_ONBOARD_COST = HIRE_TRAIN_COST

# Sensitivity grid
SENS_SHORT_COSTS = [2000, 3000, 3700, 5000, 6500, 8000]
SENS_ABSENCE_RATES = [0.01, 0.02, 0.03, 0.04, 0.06, 0.08]
SENS_OVERTIME_CAPS = [0.0, 0.10, 0.20]
