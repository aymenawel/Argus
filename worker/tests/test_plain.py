"""The words a reader with no lab training sees (D-95)."""

from argus.domain import Role
from argus.measure.uncertainty import format_measurement
from argus.plain import metric_words, role_word, unit_label


def test_a_measurement_is_named_in_everyday_words():
    assert metric_words("delta_e") == "colour change"
    assert metric_words("germinated_count") == "sprouted seeds"
    assert metric_words("some_new_metric") == "some new metric"  # a drafted recipe's id still reads as words


def test_units_read_as_people_write_them():
    assert unit_label("dE00") == "ΔE"
    assert unit_label("mm2") == "mm²"
    assert unit_label("dE00/h") == "ΔE per hour"
    assert unit_label("mm") == "mm"


def test_a_treatment_is_a_test_sample():
    assert role_word(Role.TREATMENT) == "test" and role_word(Role.CONTROL) == "control"


def test_a_reading_shows_its_plain_unit():
    assert format_measurement(25.123, 0.06, "dE00") == "25.12 ± 0.06 ΔE"
    assert format_measurement(12.0, 0.4, "mm2") == "12.0 ± 0.4 mm²"
