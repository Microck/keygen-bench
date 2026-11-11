# Experimental argv construction only. This does not create a sandbox.
# Source contract: benchmark/run.py start_container.
import Base

def helper_args(host: String, +name: String, image: String) -> List<String>:
  ["--host", host, "create", "--name", name ++ "-files", "--network", "none",
   "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
   "--user", "10001:10001", "--memory", "256m", "--pids-limit", "32",
   "--mount", "type=volume,source=" ++ name ++ "-work,target=/export,readonly,volume-nocopy",
   "--entrypoint", "/bin/sleep", image, "infinity"]

def agent_args(host: String, +name: String, image: String) -> List<String>:
  ["--host", host, "create", "--name", name, "--network", "none", "--read-only",
   "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "256",
   "--cpus", "2", "--memory", "2g", "--memory-swap", "2g", "--user", "10001:10001",
   "--mount", "type=volume,source=" ++ name ++ "-work,target=/workspace,volume-nocopy",
   "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m,uid=10001,gid=10001",
   "--tmpfs", "/home/agent:rw,nosuid,nodev,size=16m,uid=10001,gid=10001", image]

def show(xs: List<String>) -> IO(Unit):
  match xs:
    case Nil{}:
      IO.pure(Unit, Unit{})
    case x <> rest:
      do IO<Unit>:
        a : Unit <- IO.print(x)
        show(rest)

def main() -> IO(Unit):
  do IO<Unit>:
    a : Unit <- show(helper_args("unix:///var/run/docker.sock", "fixture", "sha256:fixture"))
    b : Unit <- IO.print("---")
    show(agent_args("unix:///var/run/docker.sock", "fixture", "sha256:fixture"))
