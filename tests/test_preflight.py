import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from controller import deployer


class PreflightTests(unittest.TestCase):

    def setUp(self):
        self.valid_state = {"active": "blue", "version": "v1"}

    @patch("subprocess.run")
    @patch("controller.deployer.get_state")
    def test_preflight_accepts_existing_image(self, mock_state, mock_run):
        mock_state.return_value = self.valid_state
        mock_run.return_value = SimpleNamespace(returncode=0, stderr="")

        state = deployer.preflight_deployment(
            "releaseguard-app:v2", "v2"
        )

        self.assertEqual(state, self.valid_state)
        mock_run.assert_called_once()
        self.assertEqual(
            mock_run.call_args.args[0],
            ["docker", "image", "inspect", "releaseguard-app:v2"],
        )

    @patch("subprocess.run")
    @patch("controller.deployer.get_state")
    def test_preflight_rejects_missing_image(self, mock_state, mock_run):
        mock_state.return_value = self.valid_state
        mock_run.return_value = SimpleNamespace(
            returncode=1, stderr="No such image"
        )

        with self.assertRaisesRegex(ValueError, "not available locally"):
            deployer.preflight_deployment(
                "releaseguard-app:missing", "missing"
            )

    @patch("subprocess.run")
    @patch("controller.deployer.get_state")
    def test_preflight_rejects_invalid_state(self, mock_state, mock_run):
        mock_state.return_value = {
            "active": "purple",
            "version": "v1",
        }

        with self.assertRaisesRegex(RuntimeError, "invalid active slot"):
            deployer.preflight_deployment(
                "releaseguard-app:v2", "v2"
            )

        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
