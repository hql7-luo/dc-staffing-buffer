import numpy as np
import pytest

from forecast import mape, ses_fitted, ses_next


def test_ses_by_hand():
    values = [100, 120, 110]
    # forecasts: 100, then 0.5*100 + 0.5*100 = 100, then 0.5*120 + 0.5*100 = 110
    assert ses_fitted(values, 0.5).tolist() == [100, 100, 110]
    assert ses_next(values, 0.5) == pytest.approx(0.5 * 110 + 0.5 * 110)


def test_alpha_one_is_naive_forecast():
    values = [5, 8, 6, 9]
    assert ses_next(values, 1.0) == 9
    assert ses_fitted(values, 1.0).tolist() == [5, 5, 8, 6]


def test_mape_skips_first_period():
    actual = np.array([100, 100, 200])
    forecast = np.array([0, 90, 220])
    assert mape(actual, forecast) == pytest.approx((0.10 + 0.10) / 2)
