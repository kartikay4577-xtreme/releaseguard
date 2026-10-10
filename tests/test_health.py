import unittest
from unittest.mock import Mock, patch

from controller.health import check_health


class HealthCheckTests(unittest.TestCase):

    @patch("controller.health.requests.get")
    def test_accepts_healthy_expected_version(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "status": "healthy",
            "version": "v2",
        }
        mock_get.return_value = response

        self.assertTrue(
            check_health(
                "http://127.0.0.1:8001/health",
                expected_version="v2",
            )
        )

    @patch("controller.health.requests.get")
    def test_rejects_wrong_version(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "status": "healthy",
            "version": "v1",
        }
        mock_get.return_value = response

        self.assertFalse(
            check_health(
                "http://127.0.0.1:8001/health",
                expected_version="v2",
            )
        )

    @patch("controller.health.requests.get")
    def test_rejects_unhealthy_response(self, mock_get):
        response = Mock()
        response.status_code = 503
        mock_get.return_value = response

        self.assertFalse(
            check_health("http://127.0.0.1:8001/health")
        )

    @patch("controller.health.requests.get")
    def test_handles_connection_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.ConnectionError()

        self.assertFalse(
            check_health("http://127.0.0.1:9999/health")
        )


if __name__ == "__main__":
    unittest.main()
