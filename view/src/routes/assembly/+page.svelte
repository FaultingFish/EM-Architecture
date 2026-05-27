<script lang="ts">
  import { onMount } from 'svelte';
  import { listProjects, listBuilds, disassembly, listTargets } from '$lib/api/develop';
  import { toasts } from '$lib/stores/toast';

  let projects: any[] = [];
  let selectedProject = '';
  let builds: any[] = [];
  let selectedBuild = '';
  let instructions: any[] = [];
  let targets: any[] = [];
  let loading = false;
  let filter = '';

  onMount(async () => {
    try {
      projects = await listProjects();
    } catch {
      toasts.warn('Could not load projects — is Develop running?');
    }
  });

  async function onProjectChange() {
    builds = [];
    selectedBuild = '';
    instructions = [];
    if (!selectedProject) return;
    try {
      const result = await listBuilds(selectedProject);
      builds = Array.isArray(result) ? result : result?.builds ?? [];
    } catch {
      toasts.warn('Could not load builds');
    }
  }

  async function loadDisassembly() {
    if (!selectedProject || !selectedBuild) return;
    loading = true;
    try {
      const result = await disassembly(selectedProject, selectedBuild);
      instructions = result?.instructions ?? [];
      targets = await listTargets(selectedProject);
    } catch {
      toasts.error('Failed to load disassembly');
      instructions = [];
    } finally {
      loading = false;
    }
  }

  $: filtered = filter
    ? instructions.filter((i: any) =>
        i.mnemonic?.toLowerCase().includes(filter.toLowerCase()) ||
        i.function?.toLowerCase().includes(filter.toLowerCase()) ||
        ('0x' + i.pc.toString(16)).includes(filter.toLowerCase())
      )
    : instructions;

  $: targetPCs = new Set(targets.map((t: any) => t.pc_address));

  function formatPC(pc: number): string {
    return '0x' + pc.toString(16).padStart(8, '0');
  }
</script>

<div class="page">
  <h2>Assembly</h2>

  <div class="controls">
    <select bind:value={selectedProject} on:change={onProjectChange}>
      <option value="">Select project</option>
      {#each projects as p}
        <option value={p.id}>{p.name} ({p.language})</option>
      {/each}
    </select>
    <select bind:value={selectedBuild} disabled={builds.length === 0}>
      <option value="">Select build</option>
      {#each builds as b}
        <option value={b.sha ?? b}>{b.sha ?? b} {b.built_at ? `(${new Date(b.built_at).toLocaleDateString()})` : ''}</option>
      {/each}
    </select>
    <button on:click={loadDisassembly} disabled={loading || !selectedProject || !selectedBuild}>
      {loading ? 'Loading…' : 'Load'}
    </button>
    {#if instructions.length > 0}
      <input type="text" bind:value={filter} placeholder="Filter mnemonic/function/PC" class="filter" />
    {/if}
  </div>

  {#if instructions.length > 0}
    <div class="listing">
      <table>
        <thead>
          <tr>
            <th>PC</th>
            <th>Bytes</th>
            <th>Instruction</th>
            <th>Function</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {#each filtered as inst}
            <tr class:target={targetPCs.has(inst.pc)}>
              <td class="pc">{formatPC(inst.pc)}</td>
              <td class="bytes">{inst.bytes_hex}</td>
              <td class="asm">
                <span class="mnemonic">{inst.mnemonic}</span>
                {#if inst.operands}<span class="operands">{inst.operands}</span>{/if}
              </td>
              <td class="func">{inst.function ?? ''}</td>
              <td class="src">{inst.source_file ? `${inst.source_file}:${inst.source_line}` : ''}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="info">{filtered.length} / {instructions.length} instructions. {targets.length} targets marked.</p>
  {:else if !loading}
    <p class="empty-msg">Select a project and build SHA to view disassembly.</p>
  {/if}
</div>

<style>
  .page { padding: 1rem 1.5rem; height: 100%; display: flex; flex-direction: column; }
  h2 { margin-bottom: 0.75rem; }
  .controls { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; }
  .filter { flex: 1; min-width: 12rem; }
  .listing { flex: 1; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); }
  table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 11px; }
  thead { position: sticky; top: 0; background: var(--panel-2); z-index: 1; }
  th {
    text-align: left; padding: 0.3rem 0.5rem; font-size: 10px;
    text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--border);
  }
  td { padding: 0.2rem 0.5rem; border-bottom: 1px solid var(--border); white-space: nowrap; }
  .pc { color: var(--accent); }
  .bytes { color: var(--muted); }
  .mnemonic { color: #7ec8e3; font-weight: 600; }
  .operands { color: var(--fg); margin-left: 0.5rem; }
  .func { color: var(--warn); }
  .src { color: var(--muted); font-size: 10px; }
  tr.target { background: rgba(0, 209, 143, 0.08); }
  tr.target .pc { font-weight: 700; }
  tr:hover { background: var(--panel-2); }
  .info { color: var(--muted); font-size: 11px; margin-top: 0.5rem; }
  .empty-msg { color: var(--muted); margin-top: 2rem; }
</style>
