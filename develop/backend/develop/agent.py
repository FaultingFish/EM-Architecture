"""Claude Code CLI subprocess wrapper.

Spawns `claude` in the project's working directory with the user's prompt.
Streams stdout/stderr line-by-line so the frontend can render the agent's
output live via the WebSocket topic `agent_output`.

Requirements on the lab box:
- Claude Code CLI installed and authenticated (`claude` on PATH)
- The lab box has network access to Anthropic's API (or proxy configured)

See https://docs.anthropic.com/claude/claude-code for installation.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from develop.config import claude_bin
from develop.projects import project_dir


async def run_agent(project_id: str, prompt: str) -> AsyncIterator[str]:
    """Yield agent output lines (mixed stdout + stderr) as they arrive.

    Build-out note:
    - Use `asyncio.create_subprocess_exec(claude_bin(), "--print", prompt,
      cwd=project_dir(project_id), stdout=PIPE, stderr=STDOUT)`
    - Yield each line as it arrives
    - On exit, surface the final return code
    - The Develop WS handler turns this into agent_output events
    """
    raise NotImplementedError("agent.run_agent")
