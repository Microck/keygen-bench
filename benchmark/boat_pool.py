"""Share Boat VMs between concurrent attempts of one campaign process.

Sandboxes spend ~97% of an attempt idle while the model generates, so one VM can host several
attempts. Each attempt keeps its own fresh offline containers with unchanged per-container caps
(2 CPU, 2 GiB); only the host is shared. Fairness guard: a monitor compares the VM's global
oom_kill counter with every Docker cgroup's own oom_kill count. A kill not explained by some
container's own cap is a host-level OOM, and every attempt alive on that VM at the time is marked
infrastructure (rerun), never charged to a model.

attempts_per_vm == 1 with linger_seconds == 0 reproduces one fresh VM per attempt.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid

from boat import BoatError, BoatSession

MONITOR_SECONDS = 15
OOM_SCRIPT = ("grep '^oom_kill ' /proc/vmstat; "
              "find /sys/fs/cgroup -name memory.events -path '*docker*' 2>/dev/null | "
              "while read f; do echo \"$f $(grep '^oom_kill ' \"$f\")\"; done")


def parse_oom(text: str) -> tuple[int, dict[str, int]]:
    """(global oom_kill, {cgroup path: oom_kill}) from OOM_SCRIPT output."""
    host, groups = None, {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "oom_kill":
            host = int(parts[1])
        elif len(parts) == 3 and parts[1] == "oom_kill":
            groups[parts[0]] = int(parts[2])
    if host is None:
        raise BoatError("VM did not report /proc/vmstat oom_kill", code="monitor_error")
    return host, groups


class OomLedger:
    """Attribute global OOM kills to container cgroups; the remainder are host-level kills.

    A cgroup that disappears between samples takes its last increments with it; those count as
    host-level, which fails safe (rerun) rather than charging a model.
    """

    def __init__(self, host: int, groups: dict[str, int]):
        self.host, self.groups = host, dict(groups)
        self.events: list[dict] = []

    def sample(self, host: int, groups: dict[str, int], at: float, previous_at: float) -> int:
        own = sum(count - self.groups.get(path, 0) for path, count in groups.items())
        unexplained = (host - self.host) - own
        self.host, self.groups = host, dict(groups)
        if unexplained > 0:
            self.events.append({"from": previous_at, "to": at, "host_oom_kills": unexplained})
        return max(unexplained, 0)


class _VM:
    def __init__(self, pool: "BoatPool", index: int):
        self.pool, self.index = pool, index
        self.key = f"vm-{index:03d}-{uuid.uuid4().hex[:8]}"
        self.audit = pool.root / ".boat-vms" / self.key
        self.session: BoatSession | None = None
        self.ready = threading.Event()
        self.error: BaseException | None = None
        self.tenants: set[str] = set()
        self.served = 0
        self.created_at = time.time()
        self.deadline = self.created_at + pool.options["ttl_seconds"]
        self.closing = False
        self.linger: threading.Timer | None = None
        self.ledger: OomLedger | None = None
        self.last_sample = None
        self.monitor_stop = threading.Event()
        self.monitor_lock = threading.Lock()
        self.log: list[dict] = []
        self.cpus = 2
        self.slots: dict[str, int] = {}

    # The monitor and the final per-tenant sample share one ledger.
    def sample(self) -> None:
        with self.monitor_lock:
            result = subprocess.run(self.session.command(["sh", "-c", OOM_SCRIPT]), capture_output=True,
                                    text=True, timeout=30, stdin=subprocess.DEVNULL)
            if result.returncode != 0:
                raise BoatError("VM OOM monitor command failed", code="monitor_error")
            host, groups = parse_oom(result.stdout)
            now = time.time()
            if self.ledger is None:
                self.ledger = OomLedger(host, groups)
            else:
                kills = self.ledger.sample(host, groups, now, self.last_sample)
                if kills:
                    self.log.append({"at": now, "event": "host_oom", "kills": kills,
                                     "tenants": sorted(self.tenants)})
            self.last_sample = now

    def monitor(self) -> None:
        while not self.monitor_stop.wait(MONITOR_SECONDS):
            try:
                self.sample()
            except Exception as exc:  # the next good sample still covers the gap
                self.log.append({"at": time.time(), "event": "monitor_error", "error": type(exc).__name__})

    def host_oom_between(self, start: float, end: float) -> list[dict]:
        if self.ledger is None:
            return []
        return [event for event in self.ledger.events if event["to"] >= start and event["from"] <= end]


class Lease:
    def __init__(self, vm: _VM, attempt_id: str, tenant_index: int, tenants_at_join: int, slot: int):
        self.vm, self.attempt_id = vm, attempt_id
        self.session = vm.session
        self.joined_at = time.time()
        self.tenant_index, self.tenants_at_join, self.slot = tenant_index, tenants_at_join, slot
        # Each shared attempt is pinned to 2 CPUs so nproc and its CPU share look as on a sole
        # 2-vCPU VM; None leaves a sole tenant's containers exactly as before.
        self.cpuset = (None if vm.pool.capacity == 1
                       else f"{(2 * slot) % vm.cpus},{(2 * slot + 1) % vm.cpus}")

    def record(self) -> dict:
        return {"boat_id": self.session.id, "vm": self.vm.key, "attempts_per_vm": self.vm.pool.capacity,
                "vm_type": self.vm.pool.options.get("type", "small"), "tenant_index": self.tenant_index,
                "tenants_at_join": self.tenants_at_join, "slot": self.slot, "cpuset": self.cpuset}

    def host_oom(self) -> list[dict]:
        """Sample now, then return host-level OOM kills overlapping this attempt's stay."""
        if self.vm.pool.capacity == 1:
            return []  # a sole tenant's kills are its own container's, as before
        self.vm.sample()
        return self.vm.host_oom_between(self.joined_at, time.time())


class BoatPool:
    """Bin-pack attempts onto shared VMs; stop each VM once it has been empty for linger_seconds."""

    def __init__(self, transport: dict, root: Path, required_seconds: float, pace):
        self.transport = transport
        self.options = transport["boat"]
        self.capacity = self.options.get("attempts_per_vm", 1)
        self.linger_seconds = self.options.get("linger_seconds", 0)
        self.root, self.required, self.pace = root, required_seconds, pace
        self.lock = threading.Lock()
        self.vms: list[_VM] = []
        self.count = 0

    def _admissible(self, vm: _VM, now: float) -> bool:
        return (not vm.closing and vm.error is None and len(vm.tenants) < self.capacity
                and vm.deadline - now >= self.required)

    def _reserve(self, attempt_id: str) -> tuple[_VM, bool]:
        with self.lock:
            now = time.time()
            candidates = [vm for vm in self.vms if self._admissible(vm, now)]
            if candidates:
                # Fullest first, so partly used VMs fill up and empty ones can stop.
                vm = max(candidates, key=lambda item: (len(item.tenants), -item.index))
                if vm.linger is not None:
                    vm.linger.cancel()
                    vm.linger = None
                vm.tenants.add(attempt_id)
                return vm, False
            self.count += 1
            vm = _VM(self, self.count)
            vm.tenants.add(attempt_id)
            self.vms.append(vm)
            return vm, True

    def _start(self, vm: _VM, run_dir: Path) -> None:
        try:
            self.pace()
            # Shared VMs keep their audit outside any attempt directory: attempts are archived
            # and evicted while the VM may still serve others. One VM per attempt keeps the
            # original per-attempt audit location.
            vm.audit = vm.audit if self.capacity > 1 else run_dir / "transport"
            vm.session = BoatSession(self.transport, audit_dir=vm.audit).__enter__()
            vm.deadline = vm.session.archive_deadline
            if self.capacity > 1:
                result = subprocess.run(vm.session.command(["nproc"]), capture_output=True, text=True,
                                        timeout=30, stdin=subprocess.DEVNULL)
                vm.cpus = int(result.stdout.strip()) if result.returncode == 0 else 0
                if vm.cpus < 2 or vm.cpus % 2:
                    raise BoatError("Shared VM must expose an even CPU count of at least 2", code="vm_cpus")
                vm.sample()
                threading.Thread(target=vm.monitor, name=vm.key + "-oom", daemon=True).start()
        except BaseException as exc:
            vm.error = exc
            raise
        finally:
            vm.ready.set()

    def _close(self, vm: _VM) -> None:
        with self.lock:
            if vm.tenants or vm.closing:
                return
            vm.closing = True
            vm.linger = None
            self.vms.remove(vm)
        vm.monitor_stop.set()
        try:
            if vm.session is not None:
                vm.session.__exit__(None, None, None)
        finally:
            if self.capacity > 1:
                vm.audit.mkdir(parents=True, exist_ok=True)
                (vm.audit / "pool.json").write_text(json.dumps(
                    {"vm": vm.key, "served": vm.served, "events": vm.log,
                     "host_oom": vm.ledger.events if vm.ledger else []}, indent=2) + "\n")

    def _release(self, vm: _VM, attempt_id: str) -> None:
        with self.lock:
            vm.tenants.discard(attempt_id)
            vm.slots.pop(attempt_id, None)
            empty = not vm.tenants
            if empty and vm.error is None and vm.session is not None and self.linger_seconds:
                # Non-daemon: interpreter exit waits for it, so a lingering VM is always stopped.
                vm.linger = threading.Timer(self.linger_seconds, self._close, args=(vm,))
                vm.linger.start()
                return
        if empty:
            self._close(vm)

    def shutdown(self) -> None:
        """Stop every idle (lingering) VM now; called when the campaign process finishes."""
        with self.lock:
            idle = [vm for vm in self.vms if not vm.tenants]
            for vm in idle:
                if vm.linger is not None:
                    vm.linger.cancel()
        for vm in idle:
            self._close(vm)

    @contextmanager
    def lease(self, attempt_id: str, run_dir: Path):
        vm, creator = self._reserve(attempt_id)
        lease = None
        try:
            if creator:
                self._start(vm, run_dir)
            else:
                vm.ready.wait()
                if vm.error is not None:
                    raise BoatError("Shared Boat VM failed to start", code="shared_vm_start") from vm.error
            with self.lock:
                vm.served += 1
                slot = min(set(range(self.capacity)) - set(vm.slots.values()))
                vm.slots[attempt_id] = slot
                lease = Lease(vm, attempt_id, vm.served, len(vm.tenants), slot)
            yield lease
        finally:
            if self.capacity > 1 and vm.session is not None:
                target = run_dir / "transport"
                target.mkdir(parents=True, exist_ok=True)
                (target / "shared-vm.json").write_text(json.dumps(
                    {**(lease.record() if lease else {"vm": vm.key}),
                     "joined_at": lease.joined_at if lease else None, "left_at": time.time(),
                     "vm_log": list(vm.log)}, indent=2) + "\n")
                for name in ("provision-request.json", "machine.json", "ready.json", "image-bundle-identities.json"):
                    if (vm.audit / name).exists():
                        shutil.copyfile(vm.audit / name, target / name)
            self._release(vm, attempt_id)
