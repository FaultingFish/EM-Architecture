<script lang="ts">
  // File tree for a project. Emits 'select' with the relative path.
  // TODO: nested rendering, ignore .git, lazy-load on expand.
  export let tree: any = null;
</script>

<div class="tree">
  {#if tree}
    <pre>{JSON.stringify(tree, null, 2)}</pre>
  {:else}
    <p>Loading…</p>
  {/if}
</div>

<style>
  .tree { font-family: monospace; }
</style>
