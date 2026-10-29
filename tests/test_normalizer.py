from app.utils.normalizer import normalize_time, normalize_name


def test_normalize_time():
    assert normalize_time("13:00").hour == 13
    assert normalize_time("2:00").hour == 2
    assert normalize_time("14.00").hour == 14
    assert normalize_time("11:50").minute == 50
    assert normalize_time(None) is None
    assert normalize_time("") is None


def test_normalize_name():
    assert normalize_name("juan perez") == "JUAN PEREZ"
    assert normalize_name("  MARIA   LOPEZ  ") == "MARIA LOPEZ"
    assert normalize_name(None) is None
