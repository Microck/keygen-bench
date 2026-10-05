"""Offline behavioral contracts; real Boat/SSH smoke is a separate opt-in gate."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile
import unittest
import uuid
from unittest.mock import patch

from benchmark import boat
from benchmark.boat_transport import ssh_command


class BoatTransportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_real_tar_reads_mounted_root_and_preserves_nested_binary(self):
        mounted = self.root / "mounted-volume"
        submission = mounted / "submission"
        submission.mkdir(parents=True)
        payload = bytes(range(256)) * 4096
        (submission / "raw.bin").write_bytes(payload)
        (mounted / "outside-submission").write_text("not submitted")
        archive_path = self.root / "submission.tar"
        boat.stream_command(boat.workspace_tar_command("/workspace/submission/.", mount_root=str(mounted)), archive_path, timeout=10, max_bytes=2 * 1024 * 1024)
        boat.validate_tar(archive_path, max_bytes=2 * 1024 * 1024)
        with tarfile.open(archive_path) as archive:
            files = {Path(item.name).name: item for item in archive if item.isfile()}
            self.assertEqual(set(files), {"raw.bin"})
            self.assertEqual(archive.extractfile(files["raw.bin"]).read(), payload)
        single_path = self.root / "single.tar"
        boat.stream_command(boat.workspace_tar_command("/workspace/submission/raw.bin", mount_root=str(mounted)), single_path, timeout=10, max_bytes=2 * 1024 * 1024)
        with tarfile.open(single_path) as archive:
            self.assertEqual(archive.getnames(), ["raw.bin"])
            self.assertEqual(archive.extractfile("raw.bin").read(), payload)

    @unittest.skipUnless(os.environ.get("KEYGEN_DOCKER_TRANSPORT_TEST_IMAGE"), "requires an existing immutable FT2 image and local Docker")
    def test_real_paused_tmpfs_volume_export_includes_live_mount_bytes(self):
        image = os.environ["KEYGEN_DOCKER_TRANSPORT_TEST_IMAGE"]
        self.assertRegex(image, boat.IMAGE_ID)
        name = "keygen-export-test-" + uuid.uuid4().hex[:12]
        volume = name + "-work"
        payload = bytes(range(256)) * 4096
        def docker(args):
            return subprocess.run(["docker", *args], capture_output=True, timeout=30, check=True)
        class LocalDockerSession(boat.BoatSession):
            @property
            def docker_prefix(self):
                return ["docker"]
        # This is a real Docker integration, not a mock output. Only the SSH
        # transport is replaced with the local Docker binary.
        docker(["image", "inspect", image])
        try:
            docker(["volume", "create", "--driver", "local", "--opt", "type=tmpfs", "--opt", "device=tmpfs", "--opt", "o=size=16m,uid=10001,gid=10001", volume])
            for suffix, mount in (("-files", f"type=volume,source={volume},target=/export,readonly,volume-nocopy"), ("", f"type=volume,source={volume},target=/workspace,volume-nocopy")):
                docker(["create", "--name", name + suffix, "--network", "none", "--read-only", "--user", "10001:10001", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "32", "--memory", "128m", "--mount", mount, "--entrypoint", "/bin/sleep", image, "infinity"])
                docker(["start", name + suffix])
            docker(["exec", name, "python3", "-c", "from pathlib import Path; Path('/workspace/raw.bin').write_bytes(bytes(range(256))*4096)"])
            docker(["pause", name])
            session = LocalDockerSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
            path = self.root / "live-volume.tar"
            result = session.collect_tar(name, "/workspace/.", path, timeout=30, max_bytes=2 * 1024 * 1024)
            with tarfile.open(path) as archive:
                members = {Path(item.name).name: item for item in archive if item.isfile()}
                self.assertEqual(archive.extractfile(members["raw.bin"]).read(), payload)
            self.assertEqual(result["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        finally:
            subprocess.run(["docker", "rm", "-f", name, name + "-files"], capture_output=True, timeout=30)
            subprocess.run(["docker", "volume", "rm", volume], capture_output=True, timeout=30)

    def test_binary_stream_preserves_nul_and_non_utf8(self):
        output = self.root / "artifact.tar"
        payload = bytes(range(256)) * 4096
        result = boat.stream_command([sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes(range(256))*4096)"], output, timeout=10, max_bytes=len(payload))
        self.assertEqual(output.read_bytes(), payload)
        self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(result["bytes"], len(payload))
        self.assertEqual(result["exit_code"], 0)

    def test_failure_preserves_exit_and_removes_partial_export(self):
        output = self.root / "partial"
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            boat.stream_command([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'partial'); sys.exit(17)"], output, timeout=10, max_bytes=1024)
        self.assertEqual(caught.exception.returncode, 17)
        self.assertFalse(output.exists())

    def test_oversize_stream_is_rejected_without_publishing_partial(self):
        output = self.root / "oversize"
        with self.assertRaisesRegex(boat.BoatError, "exceeded"):
            boat.stream_command([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x'*65536)"], output, timeout=10, max_bytes=1024)
        self.assertFalse(output.exists())

    def test_timeout_never_publishes_partial(self):
        output = self.root / "timeout"
        with self.assertRaises(subprocess.TimeoutExpired):
            boat.stream_command([sys.executable, "-c", "import time; time.sleep(30)"], output, timeout=0.1, max_bytes=1024)
        self.assertFalse(output.exists())

    def test_shell_words_do_not_turn_container_argv_into_host_commands(self):
        connection = {"host": "203.0.113.10", "port": 22, "user": "user", "identity": "/private/key", "known_hosts": "/private/hosts"}
        words = ["docker", "exec", "offline", "bash", "-lc", "printf '%s' \"$(cat /home/user/private)\"; echo ';'", "two words"]
        command = ssh_command(connection, words)
        self.assertEqual(shlex.split(command[-1]), ["exec", *words])
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn("ForwardAgent=no", command)
        self.assertIn("ClearAllForwardings=yes", command)
        self.assertIn("-T", command)

    def test_artifact_archives_reject_traversal_links_and_duplicates(self):
        for kind in ("traversal", "absolute", "symlink", "hardlink", "duplicate"):
            with self.subTest(kind=kind):
                output = self.root / f"{kind}.tar"
                with tarfile.open(output, "w") as archive:
                    name = "../escape" if kind == "traversal" else "/escape" if kind == "absolute" else "workspace/file"
                    item = tarfile.TarInfo(name)
                    if kind in {"symlink", "hardlink"}:
                        item.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
                        item.linkname = "/home/user/private"
                    archive.addfile(item)
                    if kind == "duplicate":
                        archive.addfile(item)
                with self.assertRaises(boat.BoatError):
                    boat.validate_tar(output, max_bytes=1024)

    def test_tar_expanded_bytes_are_bounded(self):
        output = self.root / "large.tar"
        with tarfile.open(output, "w") as archive:
            item = tarfile.TarInfo("workspace/file")
            item.size = 1025
            archive.addfile(item, io.BytesIO(b'x' * item.size))
        with self.assertRaisesRegex(boat.BoatError, "expanded-byte"):
            boat.validate_tar(output, max_bytes=1024)

    def test_context_never_contains_private_configs_or_legacy(self):
        for relative in boat.SOURCE_ALLOWLIST:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(relative.encode())
        (self.root / "credentials.json").write_text("not a source")
        legacy = self.root / "legacy/private.json"
        legacy.parent.mkdir()
        legacy.write_text("not a source")
        output = self.root / "context.tar"
        manifest = boat.source_context(self.root, output)
        with tarfile.open(output) as archive:
            self.assertEqual(set(archive.getnames()), set(boat.SOURCE_ALLOWLIST))
            for member in archive:
                self.assertEqual(hashlib.sha256(archive.extractfile(member).read()).hexdigest(), manifest[member.name])

    def test_context_rejects_symlink_source(self):
        for relative in boat.SOURCE_ALLOWLIST:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source")
        source = self.root / boat.SOURCE_ALLOWLIST[0]
        source.unlink()
        source.symlink_to("../private.json")
        with self.assertRaisesRegex(boat.BoatError, "regular allowlisted"):
            boat.source_context(self.root, self.root / "context.tar")

    def test_stop_escalates_only_after_normal_stop_failure(self):
        calls = []
        class API:
            state = "ready"
            def call(self, method, path, body=None, **kwargs):
                calls.append((method, path, body))
                if path.endswith("/stop") and body == {}:
                    raise boat.BoatError("snapshot failed")
                if path.endswith("/stop") and body.get("force"):
                    self.state = "archived"
                if method == "GET":
                    return {"sandbox": {"state": self.state, "snapshotAvailable": False}}
                return {"ok": True}
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
        session.id, session.api = "bx_23456789", API()
        session.close()
        self.assertEqual([entry[2] for entry in calls if entry[0] == "POST"], [{}, {"force": True}])
        self.assertTrue(session.stop_record["forced"])
        self.assertEqual(session.stop_record["state"], "archived")
        count = len(calls)
        session.close()
        self.assertEqual(len(calls), count)

    def test_failed_entry_stops_allocated_machine(self):
        calls = []
        class API:
            def call(self, method, path, body=None, **kwargs):
                calls.append((method, path, body))
                if path == "/sandboxes":
                    return {"sandbox": {"id": "bx_23456789"}}
                if path.endswith("/stop"):
                    return {"ok": True}
                if method == "GET":
                    stopped = any(entry[1].endswith("/stop") for entry in calls)
                    return {"sandbox": {"state": "archived" if stopped else "ready", "archiveAfter": None}}
                raise AssertionError(path)
        config = {"backend": "boat", "boat": {"ttl_seconds": 600}}
        with patch.object(boat, "doctor"), patch.object(boat, "BoatAPI", return_value=API()):
            with self.assertRaisesRegex(boat.BoatError, "deadman TTL"):
                with boat.BoatSession(config):
                    self.fail("failed entry must not run body")
        self.assertEqual([entry[1] for entry in calls if entry[1].endswith("/stop")], ["/sandboxes/bx_23456789/stop"])

    def test_quota_doctor_does_not_double_count_subscription(self):
        class API:
            def call(self, *args, **kwargs):
                return {"canStart": True, "creditBalanceSeconds": 100, "subscriptionRemainingSeconds": 100}
        with patch.object(boat, "BoatAPI", return_value=API()), patch.object(boat.shutil, "which", return_value="program"):
            result = boat.doctor({"backend": "boat", "boat": {"ttl_seconds": 600}})
        self.assertEqual(result["remaining_seconds"], 100)

    def test_interrupted_create_recovers_same_machine_before_stopping(self):
        class API:
            def __init__(self):
                self.machines = {}
                self.states = {}
                self.first = True
            def call(self, method, path, body=None, **kwargs):
                if path == "/sandboxes":
                    key = kwargs["key"]
                    if key not in self.machines:
                        identity = "bx_2345678" + str(len(self.machines) + 2)
                        self.machines[key] = identity
                        self.states[identity] = "ready"
                    if self.first:
                        self.first = False
                        raise KeyboardInterrupt()
                    return {"sandbox": {"id": self.machines[key]}}
                identity = path.split("/")[2]
                if path.endswith("/stop"):
                    self.states[identity] = "archived"
                    return {"ok": True}
                return {"sandbox": {"state": self.states[identity]}}
        api = API()
        with patch.object(boat, "doctor"), patch.object(boat, "BoatAPI", return_value=api):
            with self.assertRaises(KeyboardInterrupt):
                with boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}}):
                    self.fail("interrupted provisioning must not enter session")
        self.assertEqual(len(api.machines), 1)
        self.assertEqual(list(api.states.values()), ["archived"])

    def test_pending_readiness_exhausts_startup_budget_and_stops_vm(self):
        clock = [0.0]
        class API:
            def __init__(self):
                self.state = "cloning"
            def call(self, method, path, body=None, **kwargs):
                clock[0] += min(1, kwargs.get("timeout", 1))
                if path == "/sandboxes":
                    return {"sandbox": {"id": "bx_23456789"}}
                if path.endswith("/stop"):
                    self.state = "archived"
                    return {"ok": True}
                return {"sandbox": {"state": self.state}}
        api = API()
        config = {"backend": "boat", "boat": {"ttl_seconds": 600, "startup_seconds": 10, "stop_seconds": 10}}
        def sleep(seconds):
            clock[0] += seconds
        with patch.object(boat, "doctor"), patch.object(boat, "BoatAPI", return_value=api), patch.object(boat.time, "monotonic", side_effect=lambda: clock[0]), patch.object(boat.time, "sleep", side_effect=sleep):
            with self.assertRaisesRegex(boat.BoatError, "lifecycle deadline"):
                with boat.BoatSession(config, audit_dir=self.root):
                    self.fail("pending readiness must not enter session")
        self.assertEqual(api.state, "archived")
        self.assertLessEqual(clock[0], 20)
        self.assertEqual(json.loads((self.root / "stopped.json").read_text())["state"], "archived")
        self.assertEqual(json.loads((self.root / "entry-error.json").read_text())["code"], "lifecycle_deadline")

    def test_ready_wait_preserves_remaining_image_load_budget(self):
        class API:
            def call(self, *args, **kwargs):
                return {"sandbox": {"state": "ready", "archiveAfter": "1970-01-01T03:00:00+00:00"}}
        session = boat.BoatSession({"backend": "boat", "boat": {
            "ttl_seconds": 10800, "startup_seconds": 600, "stop_seconds": 120}})
        session.id, session.api, session._startup_deadline = "bx_23456789", API(), 600
        with patch.object(boat.time, "monotonic", return_value=0), patch.object(boat.time, "time", return_value=0):
            session._wait({"ready"}, timeout=30)
            self.assertEqual(session._timeout(300), 300)

    def test_ready_wait_keeps_deadman_cleanup_reserve_for_image_load(self):
        class API:
            def call(self, *args, **kwargs):
                return {"sandbox": {"state": "ready", "archiveAfter": "1970-01-01T00:01:40+00:00"}}
        session = boat.BoatSession({"backend": "boat", "boat": {
            "ttl_seconds": 100, "startup_seconds": 600, "stop_seconds": 10}})
        session.id, session.api, session._startup_deadline = "bx_23456789", API(), 600
        with patch.object(boat.time, "monotonic", return_value=0), patch.object(boat.time, "time", return_value=0):
            session._wait({"ready"}, timeout=30)
            self.assertEqual(session._timeout(300), 90)

    def test_audit_write_failure_after_allocation_cannot_prevent_stop(self):
        class API:
            def __init__(self):
                self.state = "ready"
            def call(self, method, path, body=None, **kwargs):
                if path == "/sandboxes":
                    return {"sandbox": {"id": "bx_23456789"}}
                if path.endswith("/stop"):
                    self.state = "archived"
                    return {"ok": True}
                return {"sandbox": {"state": self.state}}
        api = API()
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
        def audit(name, data):
            if name in {"machine.json", "entry-error.json", "stopped.json", "stop-error.json"}:
                raise OSError("artifact storage full")
        with patch.object(boat, "doctor"), patch.object(boat, "BoatAPI", return_value=api), patch.object(session, "_audit", side_effect=audit):
            with self.assertRaises(OSError):
                with session:
                    self.fail("failed audit must not enter session")
        self.assertEqual(api.state, "archived")

    def test_restore_error_rejects_provisioned_healthy_vm_and_stops(self):
        class API:
            def __init__(self):
                self.state = "provisioned"
            def call(self, method, path, body=None, **kwargs):
                if path == "/sandboxes":
                    return {"sandbox": {"id": "bx_23456789"}}
                if path.endswith("/stop"):
                    self.state = "archived"
                    return {"ok": True}
                return {"sandbox": {"state": self.state, "health": "ok", "error": "Restore incomplete: 4/9 image files missing"}}
        api = API()
        with patch.object(boat, "doctor"), patch.object(boat, "BoatAPI", return_value=api):
            with self.assertRaises(boat.BoatError) as failure:
                with boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}}, audit_dir=self.root):
                    self.fail("incomplete restoration must not enter a session")
        self.assertEqual(failure.exception.code, "restore_incomplete")
        self.assertEqual(api.state, "archived")
        self.assertEqual(json.loads((self.root / "stopped.json").read_text())["state"], "archived")

    def test_already_archived_cleanup_does_not_force_or_post_stop(self):
        class API:
            def call(self, method, path, body=None, **kwargs):
                if method != "GET":
                    raise AssertionError("Boat rejects POST stop on an already archived VM")
                return {"sandbox": {"state": "archived", "snapshotAvailable": True}}
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}}, audit_dir=self.root)
        session.id, session.api = "bx_23456789", API()
        session.close()
        self.assertEqual(session.stop_record["state"], "archived")
        self.assertFalse(session.stop_record["forced"])

    def test_securing_gate_waits_for_metadata_transition_before_registration(self):
        clock = [0.0]
        class API:
            def __init__(self):
                self.state = "securing"
                self.polls = 0
                self.authorized = set()
            def call(self, method, path, body=None, **kwargs):
                if path.endswith("/sshkey"):
                    if self.state == "securing":
                        raise boat.BoatError("security scrub pending", code="sandbox_securing", status=409)
                    self.authorized.add(body["key"])
                    return {"success": True}
                self.polls += 1
                if self.polls == 2:
                    self.state = "provisioned"
                return {"sandbox": {"state": self.state}}
        api = API()
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
        session.id, session.api, session._startup_deadline = "bx_23456789", api, 10
        with patch.object(boat.time, "monotonic", side_effect=lambda: clock[0]), patch.object(boat.time, "sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            session._authorize_ssh("ssh-ed25519 public-key-fixture")
        self.assertEqual(api.state, "provisioned")
        self.assertEqual(len(api.authorized), 1)
        self.assertEqual(api.polls, 2)

    def test_securing_gate_cannot_outlive_startup_budget(self):
        clock = [0.0]
        class API:
            def call(self, method, path, body=None, **kwargs):
                if path.endswith("/sshkey"):
                    raise boat.BoatError("security scrub pending", code="sandbox_securing", status=409)
                return {"sandbox": {"state": "provisioned"}}
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
        session.id, session.api, session._startup_deadline = "bx_23456789", API(), 10
        with patch.object(boat.time, "monotonic", side_effect=lambda: clock[0]), patch.object(boat.time, "sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            with self.assertRaises(boat.BoatError) as failure:
                session._authorize_ssh("ssh-ed25519 public-key-fixture")
        self.assertEqual(failure.exception.code, "lifecycle_deadline")
        self.assertEqual(clock[0], 10)

    def test_unrelated_ssh_conflict_is_not_retried(self):
        class API:
            def __init__(self):
                self.calls = 0
            def call(self, method, path, body=None, **kwargs):
                self.calls += 1
                raise boat.BoatError("unrelated conflict", code="other_conflict", status=409)
        api = API()
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
        session.id, session.api = "bx_23456789", api
        with self.assertRaises(boat.BoatError) as failure:
            session._authorize_ssh("ssh-ed25519 public-key-fixture")
        self.assertEqual(failure.exception.code, "other_conflict")
        self.assertEqual(api.calls, 1)

    def _gnu_bundle(self):
        directory = self.root / "bundle-source"
        directory.mkdir()
        (directory / "layer.bin").write_bytes(bytes(range(256)) * 4096)
        (directory / "manifest.json").write_text("[]")
        path = self.root / "images.tar"
        subprocess.run(["/bin/tar", "-C", str(directory), "-cf", str(path), "layer.bin", "manifest.json"], check=True, timeout=10)
        images = {"agent": "sha256:" + "a" * 64, "visualizer": "sha256:" + "b" * 64}
        spec = {"controller_path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size, "images": images}
        return path, images, spec

    def test_verified_bundle_rewinds_real_tar_for_full_binary_delivery(self):
        path, images, spec = self._gnu_bundle()
        expected = path.read_bytes()
        with boat._verified_bundle(spec, images) as (source, _):
            self.assertEqual(source.read(), expected)
        with tarfile.open(path) as archive:
            self.assertEqual(archive.extractfile("layer.bin").read(), bytes(range(256)) * 4096)

    def test_bundle_same_size_tampering_fails_sha_gate(self):
        path, images, spec = self._gnu_bundle()
        with path.open("r+b") as output:
            output.seek(4096)
            output.write(b"changed")
        with self.assertRaises(boat.BoatError) as failure:
            boat.verify_image_bundle(spec, images)
        self.assertEqual(failure.exception.code, "image_bundle_hash_mismatch")

    def test_missing_bundle_is_refused_before_controller_auth(self):
        images = {"agent": "sha256:" + "a" * 64, "visualizer": "sha256:" + "b" * 64}
        spec = {"controller_path": str(self.root / "missing.tar"), "sha256": "c" * 64, "bytes": 1024}
        config = {"backend": "boat", "boat": {"ttl_seconds": 600, "images": images, "image_bundle": spec}}
        with patch.object(boat, "BoatAPI", side_effect=AssertionError("must not authenticate/allocate for missing bundle")):
            with self.assertRaises(boat.BoatError) as failure:
                boat.doctor(config)
        self.assertEqual(failure.exception.code, "image_bundle_missing")

    def test_bundle_size_and_image_tuple_mismatches_are_refused(self):
        _, images, spec = self._gnu_bundle()
        with self.assertRaises(boat.BoatError) as failure:
            boat.verify_image_bundle({**spec, "bytes": spec["bytes"] + 1}, images)
        self.assertEqual(failure.exception.code, "image_bundle_size_mismatch")
        different = {**images, "agent": "sha256:" + "d" * 64}
        with self.assertRaises(ValueError):
            boat.verify_image_bundle(spec, different)

    def test_bundle_source_symlink_is_not_followed(self):
        path, images, spec = self._gnu_bundle()
        link = self.root / "linked.tar"
        link.symlink_to(path)
        with self.assertRaises(boat.BoatError) as failure:
            boat.verify_image_bundle({**spec, "controller_path": str(link)}, images)
        self.assertEqual(failure.exception.code, "image_bundle_missing")

    def test_export_refuses_existing_bundle_without_overwrite(self):
        destination = self.root / "existing.tar"
        destination.write_bytes(b"user-owned")
        session = boat.BoatSession({"backend": "boat", "boat": {"ttl_seconds": 600}})
        with self.assertRaises(FileExistsError):
            session.export_image_bundle(destination, max_bytes=1024, reserve_bytes=0)
        self.assertEqual(destination.read_bytes(), b"user-owned")

    def test_bundle_loading_cannot_be_combined_with_snapshot_restore(self):
        _, images, spec = self._gnu_bundle()
        for options in ({"mode": "fork", "id": "bx_23456789"}, {"mode": "new", "snapshot": "warm"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                boat.validate_config({"backend": "boat", "boat": {"ttl_seconds": 600, "images": images, "image_bundle": spec, **options}})


if __name__ == "__main__":
    unittest.main()
