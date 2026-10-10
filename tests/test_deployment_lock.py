import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from controller import deployment_lock as lock_module


class TestDeploymentLock(unittest.TestCase):
    def test_second_thread_waits_for_first_lock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "deployment.lock"
            first_holds_lock = threading.Event()
            release_first = threading.Event()
            second_acquired_lock = threading.Event()
            errors = []

            def first_worker():
                try:
                    with lock_module.deployment_lock():
                        first_holds_lock.set()
                        if not release_first.wait(5):
                            errors.append("First worker timed out")
                except Exception as error:
                    errors.append(repr(error))

            def second_worker():
                try:
                    with lock_module.deployment_lock():
                        second_acquired_lock.set()
                except Exception as error:
                    errors.append(repr(error))

            with patch.object(lock_module, "LOCK_FILE", lock_path):
                first = threading.Thread(target=first_worker)
                second = threading.Thread(target=second_worker)

                first.start()
                self.assertTrue(first_holds_lock.wait(2))

                second.start()

                # The second thread should remain blocked while the
                # first thread owns the exclusive file lock.
                self.assertFalse(second_acquired_lock.wait(0.3))

                release_first.set()

                self.assertTrue(second_acquired_lock.wait(2))
                first.join(2)
                second.join(2)

                self.assertFalse(first.is_alive())
                self.assertFalse(second.is_alive())
                self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
