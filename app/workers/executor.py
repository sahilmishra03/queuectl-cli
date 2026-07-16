import subprocess


class CommandExecutor:

    def execute(self, command: str):
        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )