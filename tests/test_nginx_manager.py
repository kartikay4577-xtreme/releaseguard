import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controller import nginx_manager


class NginxManagerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config = Path(self.tempdir.name) / "nginx.conf"
        self.previous_config = "previous nginx configuration"
        self.config.write_text(self.previous_config, encoding="utf-8")

        self.config_patcher = patch.object(
            nginx_manager, "NGINX_CONFIG", self.config
        )
        self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        self.tempdir.cleanup()

    def test_successful_switch_writes_target_config(self):
        with patch.object(nginx_manager, "reload_nginx") as reload:
            nginx_manager.switch_to("green")

        written_config = self.config.read_text(encoding="utf-8")
        self.assertIn("server green:8000;", written_config)
        self.assertIn("proxy_pass http://backend;", written_config)
        reload.assert_called_once_with()

    def test_failed_switch_restores_previous_config(self):
        with patch.object(
            nginx_manager,
            "reload_nginx",
            side_effect=[RuntimeError("simulated reload failure"), None],
        ) as reload:
            with self.assertRaisesRegex(
                RuntimeError, "previous Nginx configuration was restored"
            ):
                nginx_manager.switch_to("green")

        self.assertEqual(
            self.config.read_text(encoding="utf-8"),
            self.previous_config,
        )
        self.assertEqual(reload.call_count, 2)

    def test_failed_recovery_is_reported(self):
        with patch.object(
            nginx_manager,
            "reload_nginx",
            side_effect=[
                RuntimeError("initial reload failed"),
                RuntimeError("recovery reload failed"),
            ],
        ) as reload:
            with self.assertRaisesRegex(
                RuntimeError, "Restoring the previous Nginx configuration also failed"
            ) as error:
                nginx_manager.switch_to("green")

        self.assertIn("initial reload failed", str(error.exception))
        self.assertIn("recovery reload failed", str(error.exception))
        self.assertEqual(reload.call_count, 2)

    def test_invalid_slot_is_rejected(self):
        with patch.object(nginx_manager, "reload_nginx") as reload:
            with self.assertRaises(ValueError):
                nginx_manager.switch_to("purple")

        self.assertEqual(
            self.config.read_text(encoding="utf-8"),
            self.previous_config,
        )
        reload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
