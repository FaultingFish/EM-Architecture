<script lang="ts">
  // Renders an AssemblyListing as a virtualized list.
  // Each row: address, bytes, mnemonic+operands, source line.
  // Click a row → emits 'select-target' with the PC + metadata.
  //
  // TODO:
  //   - Virtualize so very long .lst files (10k+ lines) stay fluid
  //   - Highlight currently selected targets (from targets.json)
  //   - Provide a small popover with "Add target" form
  import type { AssemblyListing } from '$lib/types';
  export let listing: AssemblyListing | null = null;
</script>

{#if listing}
  <table>
    <thead>
      <tr><th>PC</th><th>bytes</th><th>instruction</th><th>source</th></tr>
    </thead>
    <tbody>
      {#each listing.instructions as ins}
        <tr>
          <td>{ins.pc.toString(16).padStart(8, '0')}</td>
          <td>{ins.bytes_hex}</td>
          <td>{ins.mnemonic} {ins.operands}</td>
          <td>{ins.source_file ?? ''}:{ins.source_line ?? ''}</td>
        </tr>
      {/each}
    </tbody>
  </table>
{:else}
  <p>No listing loaded.</p>
{/if}

<style>
  table { border-collapse: collapse; font-family: monospace; }
  td, th { padding: 0.1rem 0.5rem; border-bottom: 1px solid #eee; }
</style>
