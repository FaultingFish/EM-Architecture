<script lang="ts">
  // Panic stop. Also listens for Esc / Space globally.
  // TODO: pass campaign_id to scope the stop; track active campaign in a store.
  import { onMount } from 'svelte';

  export let onStop: () => void = () => {};

  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ') {
        e.preventDefault();
        onStop();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });
</script>

<button on:click={onStop}>STOP</button>

<style>
  button {
    padding: 1rem 2rem;
    background: #c00;
    color: #fff;
    border: none;
    font-weight: 800;
    font-size: 1.2rem;
    border-radius: 0.5rem;
    cursor: pointer;
  }
</style>
