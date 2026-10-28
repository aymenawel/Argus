import warnings

import pytest

from argus.measure.uncertainty import combined_uncertainty, format_pm, is_real_effect, noise_floor


@pytest.mark.parametrize(
    "v,u,unit,text",
    [
        (12.34567, 0.02345, "mm", "12.346 ± 0.023 mm"),
        (12.34567, 0.1, "mm", "12.35 ± 0.10 mm"),
        (1234, 250, "s", "1230 ± 250 s"),
        (19.23, 2.61, "mm", "19.2 ± 2.6 mm"),
        (4.63, 0.41, "mm", "4.6 ± 0.4 mm"),
        # 0.3 / 0.1 is 2.999… in floating point; the leading digit is still 3.
        (4.6312, 0.3, "mm", "4.6 ± 0.3 mm"),
        (0.04012, 0.003, "mm", "0.040 ± 0.003 mm"),
    ],
)
def test_format_pm_follows_the_reporting_rule(v, u, unit, text):
    assert format_pm(v, u, unit) == text


def test_format_pm_rejects_a_missing_uncertainty():
    with pytest.raises(ValueError):
        format_pm(1.0, 0.0, "mm")


def test_noise_floor_and_the_3x_rule():
    nf = noise_floor([10.0, 10.4, 9.6, 10.2, 9.8])
    assert nf == pytest.approx(0.3162, rel=1e-3) and is_real_effect(1.0, nf) and not is_real_effect(0.9, nf)


def test_area_uncertainty_counts_the_scale_twice():
    assert combined_uncertainty(100.0, 0.0, 0.01, power=2) == pytest.approx(2.0, rel=1e-3)


def test_zero_noise_or_scale_error_works_without_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert combined_uncertainty(100.0, 0.0, 0.01) == pytest.approx(1.0)
        assert combined_uncertainty(100.0, 0.5, 0.0) == pytest.approx(0.5)
        assert combined_uncertainty(100.0, 0.0, 0.0) == 0.0
