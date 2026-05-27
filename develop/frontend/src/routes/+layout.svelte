<script lang="ts">
  // TODO: shared header/nav
</script>

<header>
  <h1>EMFI Develop</h1>
  <nav>
    <a href="/">Projects</a>
  </nav>
</header>

<main>
  <slot />
</main>

<style>
  header {
    padding: 0.5rem 1rem;
    border-bottom: 1px solid #ddd;
  }
  main {
    padding: 1rem;
  }
</style>
