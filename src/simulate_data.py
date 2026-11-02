"""Make a simulated weekly history for a fictional distribution center."""
import numpy as np
import pandas as pd

import assumptions as A


def period_of_week(week):
    """Fiscal period (1-13) for a week number (1-52)."""
    return (week - 1) // A.WEEKS_PER_PERIOD + 1


def weekly_season():
    """Seasonal index for each of the 52 weeks, scaled to average 1.0."""
    season = np.repeat(A.SEASONAL_INDEX, A.WEEKS_PER_PERIOD)
    return season / season.mean()


def ar1_noise(rng, n_years, n_weeks, sd, autocorr):
    """Week-to-week noise where each week leans a little on the last one."""
    shocks = rng.normal(0, sd * np.sqrt(1 - autocorr**2), size=(n_years, n_weeks))
    noise = np.zeros((n_years, n_weeks))
    for t in range(n_weeks):
        previous = noise[:, t - 1] if t > 0 else rng.normal(0, sd, size=n_years)
        noise[:, t] = autocorr * previous + shocks[:, t]
    return noise


def make_history(seed=A.SEED):
    """Weekly miles for each simulated history year."""
    rng = np.random.default_rng(seed)
    years = A.HISTORY_YEARS
    noise = ar1_noise(rng, len(years), A.WEEKS_PER_YEAR, A.NOISE_SD, A.NOISE_AUTOCORR)
    season = weekly_season()
    rows = []
    for i, year in enumerate(years):
        level = A.WEEKLY_MILES_BY_YEAR[year]
        for w in range(A.WEEKS_PER_YEAR):
            miles = level * season[w] * (1 + noise[i, w])
            rows.append({"year": year, "week": w + 1,
                         "period": period_of_week(w + 1),
                         "miles": int(round(miles, -1))})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = make_history()
    df.to_csv("data/simulated/weekly_miles.csv", index=False)
    print(df.groupby("year").miles.mean().round())
