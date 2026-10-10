import unittest
from unittest.mock import call, patch

from controller import deployer


class DeploymentControllerTests(unittest.TestCase):

    def make_mocks(self):
        names = (
            "get_state",
            "create_or_replace_slot",
            "validate_slot",
            "switch_to",
            "check_health",
            "save_state",
            "record_deployment",
        )

        mocks = {}
        for name in names:
            patcher = patch(f"controller.deployer.{name}")
            mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

        mocks["get_state"].return_value = {
            "active": "blue",
            "version": "v1",
        }
        mocks["validate_slot"].return_value = True
        mocks["check_health"].return_value = True
        return mocks

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
            "blue", "green", "v2", True, "deployment successful"
        )

    def test_unhealthy_target_does_not_switch_traffic(self):
        mocks = self.make_mocks()
        mocks["validate_slot"].return_value = False

        result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        mocks["switch_to"].assert_not_called()
        mocks["save_state"].assert_not_called()
        mocks["record_deployment"].assert_called_once()
        self.assertFalse(mocks["record_deployment"].call_args.args[3])

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
        mocks["record_deployment"].assert_called_once()

    def test_unverified_rollback_is_reported(self):
        mocks = self.make_mocks()
        mocks["check_health"].side_effect = [False, False]

        with self.assertLogs("releaseguard", level="CRITICAL") as captured:
            result = deployer.deploy("releaseguard-app:v2")

        self.assertFalse(result)
        self.assertTrue(
            any("Traffic restoration could not be verified" in line
                for line in captured.output)
        )
        self.assertEqual(
            mocks["switch_to"].call_args_list,
            [call("green"), call("blue")],
        )
        mocks["save_state"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
