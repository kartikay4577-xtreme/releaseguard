from controller.health import check_health


def test_invalid_url():
    assert check_health("http://127.0.0.1:9999/health") is False

