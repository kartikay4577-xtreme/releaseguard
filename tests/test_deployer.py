
import unittest
from unittest.mock import call, patch

from controller import deployer


class DeploymentControllerTests(unittest.TestCase):
    def make_mocks(self):
        patches = {
            "get_state": patch(
                "controller.deployer.get_state",
                return_value={"active": "blue", "version": "v1"},
            ),
            "preflight_deployment": patch(
                "controller.deployer.preflight_deployment",
                return_value={"active": "blue", "version": "v1"},
            ),
            "create_or_replace_slot": patch(
                "controller.deployer.create_or_replace_slot"
            ),
            "validate_slot": patch(
                "controller.deployer.validate_slot",
                return_value=True,
            ),
            "switch_to": patch("controller.deployer.switch_to"),
            "check_health": patch(
                "controller.deployer.check_health",
                return_value=True,
            ),
            "save_state": patch("controller.deployer.save_state"),
            "record_deployment": patch(
                "controller.deployer.record_deployment"
            ),
        }

        mocks = {}
        for name, patcher in patches.items():
            mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

        return mocks

    def test_unhealthy_target_does_not_switch_traffic(self):
        mocks = self.make_mocks()
        mocks["validate_slot"].return_value = False

        result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        mocks["switch_to"].assert_not_called()
        mocks["save_state"].assert_not_called()

    def test_failed_traffic_check_restores_previous_version(self):
        mocks = self.make_mocks()
        mocks["check_health"].side_effect = [False, True]

        result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        self.assertEqual(
            mocks["switch_to"].call_args_list,
            [call("green"), call("blue")],
        )
        self.assertEqual(mocks["check_health"].call_count, 2)
        mocks["save_state"].assert_not_called()

    def test_successful_deployment_saves_new_state(self):
        mocks = self.make_mocks()

        result = deployer.deploy("releaseguard-app:v2")

        self.assertTrue(result)
        mocks["create_or_replace_slot"].assert_called_once_with(
            "green", "releaseguard-app:v2", "v2"
        )
        mocks["switch_to"].assert_called_once_with("green")
        mocks["save_state"].assert_called_once_with("green", "v2")
        mocks["record_deployment"].assert_called_once_with(
            "blue",
            "green",
            "v2",
            True,
            "deployment successful",
        )

    def test_state_save_failure_restores_previous_traffic(self):
        mocks = self.make_mocks()
        mocks["save_state"].side_effect = OSError(
            "Simulated state-file write failure"
        )

        result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        self.assertEqual(
            mocks["switch_to"].call_args_list,
            [call("green"), call("blue")],
        )
        self.assertEqual(mocks["check_health"].call_count, 2)
        mocks["save_state"].assert_called_once_with("green", "v2")
        mocks["record_deployment"].assert_called_once_with(
            "blue",
            "green",
            "v2",
            False,
            "Simulated state-file write failure",
        )

    def test_unverified_rollback_is_reported(self):
        mocks = self.make_mocks()
        mocks["check_health"].side_effect = [False, False]

        with self.assertLogs("releaseguard", level="CRITICAL"):
            result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        mocks["switch_to"].assert_has_calls(
            [call("green"), call("blue")]
        )
        mocks["save_state"].assert_not_called()

    def test_unverified_rollback_is_recorded_in_history(self):
        mocks = self.make_mocks()
        mocks["check_health"].side_effect = [False, False]

        with self.assertLogs("releaseguard", level="CRITICAL"):
            result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        mocks["record_deployment"].assert_called_once()

        recorded_detail = mocks["record_deployment"].call_args.args[4]
        self.assertIn("Traffic verification failed", recorded_detail)
        self.assertIn("rollback failed:", recorded_detail)


if __name__ == "__main__":
    unittest.main()
