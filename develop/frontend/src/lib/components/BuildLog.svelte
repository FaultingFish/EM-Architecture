<script lang="ts">
  // Append-only build log fed by WS topic `build_log`.
  // TODO: autoscroll, ANSI color stripping, line cap (e.g. last 10k lines).
  export let lines: string[] = [];
</script>

<pre>
{#each lines as line}{line}
{/each}
</pre>

<style>
  pre {
    background: #111;
    color: #eee;
    padding: 0.5rem;
    max-height: 50vh;
    overflow-y: auto;
    font-size: 0.85rem;
  }
</style>
