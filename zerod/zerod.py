# zerod/zerod.py — AI-Native Daemonless Sandbox Runtime for Agent Zero
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

class Sandbox:
    """Drop-in daemonless replacement for DockerContainerManager in Agent Zero.
    Uses podman under the hood (rootless OCI) + ready for future Rust Landlock/eBPF core."""

    def __init__(
        self,
        image: str = "python:3.12-slim",
        resources: Optional[Dict[str, str]] = None,
        policy: Optional[str] = None,   # LLM-generated: "read-only-except-tmp" | "no-net" | "default"
        cwd: str = "/a0/workspace"
    ):
        self.image = image
        self.resources = resources or {"cpu": "2", "memory": "4g"}
        self.policy = policy or "default"
        self.cwd = cwd
        self.container_name = f"zerod-{id(self)}"
        self._proc = None

    async def __aenter__(self):
        cmd = [
            "podman", "run", "--rm", "-i", "--name", self.container_name,
            "--read-only", "--network=slirp4netns",
            "--cpus", self.resources.get("cpu", "2"),
            "--memory", self.resources.get("memory", "4g"),
            "-w", self.cwd,
        ]

        # AI-driven dynamic policy (the groundbreaking part)
        if "read-only" in self.policy.lower():
            cmd.append("--read-only")
        if "no-net" in self.policy.lower():
            cmd.append("--network=none")

        # Mount Agent Zero workspace
        cmd.extend(["-v", f"{Path.cwd()}:/a0/workspace:z"])

        cmd.extend([self.image, "sh", "-c", "cat > /tmp/exec.sh && sh /tmp/exec.sh"])

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self

    async def exec(self, command: str) -> Dict[str, Any]:
        """Execute command inside the sandbox."""
        if not self._proc or self._proc.stdin is None:
            raise RuntimeError("Sandbox not entered")

        script = f"#!/bin/sh\n{command}\n"
        self._proc.stdin.write(script.encode())
        await self._proc.stdin.drain()

        stdout, stderr = await self._proc.communicate()
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "exit_code": self._proc.returncode or 0,
        }

    async def __aexit__(self, *args):
        if self._proc:
            try:
                await asyncio.create_subprocess_exec(
                    "podman", "stop", self.container_name, check=False
                )
            except Exception:
                pass


# Singleton for easy import in Agent Zero
sandbox = Sandbox()
