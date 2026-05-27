// Types mirror emfi_protocol/projects.py.
// TODO: replace this hand-written shadow with output of openapi-typescript.

export interface AssemblyInstruction {
  pc: number;
  bytes_hex: string;
  mnemonic: string;
  operands: string;
  source_file?: string | null;
  source_line?: number | null;
  function?: string | null;
}

export interface AssemblyListing {
  project_id: string;
  build_sha: string;
  cpu_mhz: number;
  instructions: AssemblyInstruction[];
}

export interface Project {
  id: string;
  name: string;
  language: 'c' | 'rust';
  target: string;
  hal: 'ti' | 'b01lers';
  created_at: string;
  description?: string | null;
  versions: string[];
}
