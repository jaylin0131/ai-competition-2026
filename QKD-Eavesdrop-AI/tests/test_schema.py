import pytest

from common.schema import (
    ALL_COLUMNS,
    ATTACK_LABELS,
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    LABELS,
    STAGE1_LABELS,
    check_no_leakage,
    is_attack,
)


def test_columns_unique():
    assert len(ALL_COLUMNS) == len(set(ALL_COLUMNS))


def test_features_do_not_leak():
    check_no_leakage(FEATURE_COLUMNS)


def test_leakage_is_caught():
    with pytest.raises(ValueError):
        check_no_leakage(FEATURE_COLUMNS + [FORBIDDEN_FEATURES[0]])


def test_seven_labels():
    assert len(LABELS) == len(set(LABELS)) == 7


def test_stage1_is_subset():
    assert set(STAGE1_LABELS) <= set(LABELS)


def test_is_attack():
    assert all(is_attack(x) for x in ATTACK_LABELS)
    assert not is_attack("normal")
    assert not is_attack("fiber_aging")
