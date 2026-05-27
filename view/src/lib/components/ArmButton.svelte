<script lang="ts">
  // Hold-to-arm button. Press + hold for `holdMs` to engage.
  // - Mouse: mousedown / mouseup
  // - Touch: touchstart / touchend
  // - Keyboard: focus + space, must remain pressed
  //
  // TODO: wire to control/api/arm + disarm; reflect armStore state visually.
  import { armStore } from '$lib/stores/arm';
  import { arm, disarm } from '$lib/api/control';

  export let holdMs = 1000;

  let pressing = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  function start() {
    if ($armStore.armed) {
      disarm();
      return;
    }
    pressing = true;
    timer = setTimeout(() => { if (pressing) arm(); }, holdMs);
  }
  function end() {
    pressing = false;
    if (timer) clearTimeout(timer);
    timer = null;
  }
</script>

<button
  class:armed={$armStore.armed}
  on:mousedown={start} on:mouseup={end} on:mouseleave={end}
  on:touchstart|preventDefault={start} on:touchend={end}
>
  {$armStore.armed ? 'DISARM' : 'Hold to ARM'}
</button>

<style>
  button {
    padding: 1rem 2rem;
    font-weight: 700;
    font-size: 1rem;
    border-radius: 0.5rem;
    border: 2px solid #888;
    background: #fff;
    cursor: pointer;
  }
  button.armed {
    background: #c00;
    color: #fff;
    border-color: #800;
  }
</style>
