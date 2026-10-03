import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import boat  # noqa: E402
import boat_pool  # noqa: E402


class FakeSession:
    started = []
    fail = False

    def __init__(self, transport, audit_dir=None):
        self.id = f"bx_{len(FakeSession.started):08d}"
        self.closed = False
        self.archive_deadline = time.time() + transport["boat"]["ttl_seconds"]

    def __enter__(self):
        if FakeSession.fail:
            raise boat.BoatError("boot failed")
        FakeSession.started.append(self)
        return self

    def __exit__(self, *exc):
        self.closed = True

    def command(self, argv):
        return ["echo", "4"] if argv == ["nproc"] else ["sh", "-c", "echo 'oom_kill 0'"]


def transport(tenants=3, linger=0, ttl=14400):
    return {"backend": "boat", "boat": {"mode": "new", "type": "default", "ttl_seconds": ttl,
                                        "attempts_per_vm": tenants, "linger_seconds": linger}}


class OomLedgerTests(unittest.TestCase):
    def test_container_own_kills_are_not_host_kills(self):
        ledger = boat_pool.OomLedger(5, {"a": 1})
        self.assertEqual(ledger.sample(7, {"a": 2, "b": 1}, 10, 0), 0)
        self.assertEqual(ledger.events, [])

    def test_unexplained_kill_is_a_host_event(self):
        ledger = boat_pool.OomLedger(5, {"a": 1})
        self.assertEqual(ledger.sample(7, {"a": 2}, 10, 0), 1)
        self.assertEqual(ledger.events, [{"from": 0, "to": 10, "host_oom_kills": 1}])

    def test_vanished_cgroup_increment_fails_safe_as_host_event(self):
        ledger = boat_pool.OomLedger(5, {"a": 1})
        self.assertEqual(ledger.sample(6, {}, 10, 0), 1)

    def test_parse_requires_global_counter(self):
        with self.assertRaises(boat.BoatError):
            boat_pool.parse_oom("/sys/fs/cgroup/docker-x/memory.events oom_kill 1\n")
        self.assertEqual(boat_pool.parse_oom("oom_kill 3\n/sys/x/memory.events oom_kill 1\n"),
                         (3, {"/sys/x/memory.events": 1}))


class PoolTests(unittest.TestCase):
    def setUp(self):
        FakeSession.started, FakeSession.fail = [], False
        patcher = mock.patch.object(boat_pool, "BoatSession", FakeSession)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.monitor = mock.patch.object(boat_pool, "MONITOR_SECONDS", 3600)
        self.monitor.start()
        self.addCleanup(self.monitor.stop)
        self.root = Path(tempfile.mkdtemp())

    def pool(self, **kwargs):
        return boat_pool.BoatPool(transport(**kwargs), self.root, 7200, lambda: None)

    def test_packs_up_to_capacity_then_opens_a_new_vm(self):
        pool = self.pool(tenants=3)
        leases = [pool.lease(f"a{i}", self.root / f"a{i}") for i in range(4)]
        entered = [lease.__enter__() for lease in leases]
        self.assertEqual(len(FakeSession.started), 2)
        self.assertEqual([lease.vm.index for lease in entered], [1, 1, 1, 2])
        for lease in leases:
            lease.__exit__(None, None, None)
        self.assertTrue(all(session.closed for session in FakeSession.started))

    def test_shared_slots_pin_distinct_cpu_pairs_and_reuse_freed_slots(self):
        pool = self.pool(tenants=3)
        leases = [pool.lease(f"a{i}", self.root / f"a{i}") for i in range(3)]
        entered = [lease.__enter__() for lease in leases]
        self.assertEqual([lease.cpuset for lease in entered], ["0,1", "2,3", "0,1"])
        leases[1].__exit__(None, None, None)
        late = pool.lease("late", self.root / "late")
        self.assertEqual(late.__enter__().cpuset, "2,3")

    def test_sole_tenant_is_not_pinned(self):
        pool = self.pool(tenants=1)
        lease = pool.lease("a", self.root / "a")
        self.assertIsNone(lease.__enter__().cpuset)

    def test_fullest_vm_is_filled_first(self):
        pool = self.pool(tenants=3)
        a = [pool.lease(f"a{i}", self.root / f"a{i}") for i in range(4)]
        for lease in a:
            lease.__enter__()
        a[0].__exit__(None, None, None)  # vm 1 has 2 tenants, vm 2 has 1
        late = pool.lease("late", self.root / "late")
        self.assertEqual(late.__enter__().vm.index, 1)

    def test_lingering_vm_is_reused_and_shutdown_stops_it(self):
        pool = self.pool(tenants=3, linger=600)
        first = pool.lease("r1", self.root / "r1")
        vm = first.__enter__().vm
        first.__exit__(None, None, None)
        self.assertFalse(FakeSession.started[0].closed)
        second = pool.lease("r2", self.root / "r2")
        self.assertIs(second.__enter__().vm, vm)
        second.__exit__(None, None, None)
        pool.shutdown()
        self.assertTrue(FakeSession.started[0].closed)
        self.assertEqual(len(FakeSession.started), 1)

    def test_vm_without_enough_ttl_left_is_not_joined(self):
        pool = self.pool(tenants=3, ttl=10000)
        first = pool.lease("a", self.root / "a")
        lease = first.__enter__()
        lease.vm.deadline = time.time() + 7000  # less than the 7200 s an attempt needs
        second = pool.lease("b", self.root / "b")
        self.assertIsNot(second.__enter__().vm, lease.vm)

    def test_failed_start_fails_waiting_tenants_and_closes(self):
        pool = self.pool(tenants=3)
        FakeSession.fail = True
        gate = threading.Event()
        original = pool._start

        def slow_start(vm, run_dir):
            gate.wait(5)
            original(vm, run_dir)

        pool._start = slow_start
        errors = []

        def attempt(name):
            try:
                with pool.lease(name, self.root / name):
                    pass
            except boat.BoatError as exc:
                errors.append(exc)

        threads = [threading.Thread(target=attempt, args=(name,)) for name in ("x", "y")]
        for thread in threads:
            thread.start()
        time.sleep(0.2)
        gate.set()
        for thread in threads:
            thread.join(5)
        self.assertEqual(len(errors), 2)
        self.assertEqual(pool.vms, [])


class ConfigTests(unittest.TestCase):
    def base(self, **boat_options):
        return {"backend": "boat", "boat": {"mode": "new", "ttl_seconds": 14400, **boat_options}}

    def test_attempts_per_vm_bounded_by_type(self):
        boat.validate_config(self.base(type="default", attempts_per_vm=3))
        for options in ({"type": "small", "attempts_per_vm": 2}, {"type": "default", "attempts_per_vm": 4},
                        {"type": "large", "attempts_per_vm": 7}):
            with self.assertRaises(ValueError):
                boat.validate_config(self.base(**options))


if __name__ == "__main__":
    unittest.main()
