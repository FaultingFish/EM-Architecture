<script lang="ts">
  // Monaco editor wrapper.
  // TODO:
  //   - Dynamic import of monaco-editor (it's large; avoid SSR)
  //   - Bind `value` prop with two-way file content sync
  //   - Language autodetect from path extension (.c, .rs, .ld, .toml, etc.)
  //   - Theme: vs-dark by default
  export let value = '';
  export let language = 'c';
</script>

<div class="monaco-host">
  <!-- TODO: mount Monaco here on browser side -->
  <textarea bind:value rows={30} cols={100} data-lang={language}></textarea>
</div>

<style>
  .monaco-host { width: 100%; height: 100%; }
  textarea { width: 100%; font-family: monospace; }
</style>
