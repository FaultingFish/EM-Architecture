<script lang="ts">
  // 3D grid inputs (origin, top_right, step sizes, z range).
  // TODO: "use current position as origin" button, validation, sane defaults.
  export let value = {
    origin: [0, 0],
    top_right: [10, 10],
    step_size_mm: 1.0,
    z_min_mm: 0.0,
    z_max_mm: 0.5,
    z_step_mm: 0.1
  };
</script>

<fieldset>
  <legend>Grid</legend>
  <p>TODO: numeric inputs.</p>
  <pre>{JSON.stringify(value, null, 2)}</pre>
</fieldset>
