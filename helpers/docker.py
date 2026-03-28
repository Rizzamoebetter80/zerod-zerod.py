        from zerod.zerod import Sandbox
import json

# ================================================
# ZERO D REPLACEMENT — DAEMONLESS, AI-NATIVE
# Replaces all old DockerContainerManager / docker run / docker exec
# ================================================

async def execute_tool(self, **kwargs):
    """ZeroD-powered code execution (drop-in replacement).
    No dockerd, no root, LLM-controlled sandbox, <80 ms startup."""
    
    await self.agent.handle_intervention()
    
    runtime = self.args.get("runtime", "python")
    code_or_cmd = self.args.get("code") or self.args.get("command", "")
    
    # LLM generates dynamic security policy (the groundbreaking part)
    policy_prompt = f"""Generate a strict sandbox policy for this command ONLY. 
    Reply with exactly one of: read-only-except-tmp | no-net | default
    Command: {code_or_cmd}"""
    policy = await self.agent.llm_call(policy_prompt)
    
    async with Sandbox(
        image="python:3.12-slim",  # or "agent0ai/agent-zero:latest" if you want full env
        resources={"cpu": "2", "memory": "4g", "gpu": getattr(self.agent.config, "gpu_enabled", False)},
        policy=policy.strip(),
        cwd="/a0/workspace"
    ) as sb:
        
        if runtime == "python":
            result = await sb.exec(f"python -c {json.dumps(code_or_cmd)}")
        elif runtime == "nodejs":
            result = await sb.exec(f"node -e {json.dumps(code_or_cmd)}")
        elif runtime == "terminal":
            result = await sb.exec(code_or_cmd)
        else:
            result = {
                "stdout": "",
                "stderr": f"Unsupported runtime: {runtime}",
                "exit_code": 1
            }
        
        return {
            "output": result["stdout"] + result["stderr"],
            "exit_code": result["exit_code"]
        }
