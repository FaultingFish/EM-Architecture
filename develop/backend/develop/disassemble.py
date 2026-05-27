"""Disassembly: arm-none-eabi-objdump -d → AssemblyListing.

Parser strategy:
1. Run `arm-none-eabi-objdump -d -S <elf>` and capture stdout.
2. Parse the output line-by-line:
   - Function header: `00001234 <function_name>:`
   - Instruction line: `    1234: aabb  mnemonic operands`
   - Source line (with -S): `path/to/file.c:42`
3. Optionally cross-reference with `pyelftools` for symbol info, or
   `capstone` for richer per-instruction metadata.

Output is an `emfi_protocol.AssemblyListing`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from emfi_protocol.projects import AssemblyListing

log = logging.getLogger(__name__)


def disassemble(elf_path: Path, project_id: str, build_sha: str) -> AssemblyListing:
    """Parse objdump output into an AssemblyListing."""
    log.info("Disassembling %s (project=%s sha=%s)", elf_path, project_id, build_sha)
    raise NotImplementedError("disassemble.disassemble")
