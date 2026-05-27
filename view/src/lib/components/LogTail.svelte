<script lang="ts">
  // Append-only attempt list (last N). Auto-scrolls to bottom.
  // TODO: outcome color coding (glitch=green, hang=yellow, crash=orange, nothing=gray).
  import { logStore } from '$lib/stores/log';
  export let limit = 50;
</script>

<ul>
  {#each $logStore.slice(-limit) as e (e.id)}
    <li class={e.outcome}>{e.ts} — {e.outcome} @ ({e.x}, {e.y}, {e.z})</li>
  {/each}
</ul>

<style>
  ul { list-style: none; padding: 0; font-family: monospace; font-size: 0.9rem; }
  li.glitch { color: #1a7; }
  li.hang { color: #b80; }
  li.crash { color: #c30; }
  li.nothing { color: #888; }
</style>
