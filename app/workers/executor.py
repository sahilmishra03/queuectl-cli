import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class CommandExecutor:

    def execute(self, command: str, timeout: Optional[int] = None) -> ExecutionResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                returncode=-1,
                stdout=e.stdout or "" if isinstance(e.stdout, str) else (e.stdout.decode() if e.stdout else ""),
                stderr=f"Job timed out after {timeout} seconds",
                timed_out=True,
            )