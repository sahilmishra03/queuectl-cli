import sys
from app.workers.executor import CommandExecutor


def test_successful_command():
    executor = CommandExecutor()
    result = executor.execute("echo Hello")
    assert result.returncode == 0
    assert "Hello" in result.stdout
    assert not result.timed_out


def test_failed_command():
    executor = CommandExecutor()
    result = executor.execute("abcxyz_nonexistent_command_12345")
    assert result.returncode != 0
    assert not result.timed_out


def test_timeout():
    executor = CommandExecutor()
    # Use python sleep which responds cleanly to subprocess timeout
    python_exe = sys.executable
    cmd = f'"{python_exe}" -c "import time; time.sleep(3)"'
    result = executor.execute(cmd, timeout=1)
    assert result.timed_out
    assert result.returncode == -1
    assert "timed out after 1 seconds" in result.stderr


def test_stdout_and_stderr_captured():
    executor = CommandExecutor()
    python_exe = sys.executable
    cmd = f'"{python_exe}" -c "import sys; print(\'out\'); print(\'err\', file=sys.stderr)"'
    result = executor.execute(cmd)
    assert result.returncode == 0
    assert "out" in result.stdout
    assert "err" in result.stderr
