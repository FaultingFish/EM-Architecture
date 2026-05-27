<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { positionStore } from '$lib/stores/position';
  import { logStore, type AttemptEntry } from '$lib/stores/log';
  import { moveAbs } from '$lib/api/control';
  import { toasts } from '$lib/stores/toast';

  let container: HTMLDivElement;
  let scene: any;
  let camera: any;
  let renderer: any;
  let controls: any;
  let probe: any;
  let scanBoxMesh: any;
  let highlightRing: any;
  let trails: Record<string, { points: number[][]; mesh: any }> = {};
  let frameId: number;
  let THREE: any;

  export let scanBox: { width: number; height: number; depth: number } | null = null;

  const OUTCOME_COLORS: Record<string, number> = {
    glitch: 0x00c853,
    hang: 0xff5252,
    crash: 0xf9a825,
    nothing: 0x607d8b,
  };

  onMount(async () => {
    THREE = await import('three');
    const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0b0f);

    camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.01, 5000);
    camera.position.set(20, 20, 20);
    camera.up.set(0, 0, 1);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const dir = new THREE.DirectionalLight(0xffffff, 0.7);
    dir.position.set(10, 20, 30);
    scene.add(dir);

    const axes = new THREE.AxesHelper(5);
    scene.add(axes);

    const grid = new THREE.GridHelper(100, 100, 0x222637, 0x1c2030);
    grid.rotation.x = Math.PI / 2;
    scene.add(grid);

    const coneGeo = new THREE.ConeGeometry(0.5, 1.2, 16);
    const coneMat = new THREE.MeshStandardMaterial({ color: 0x00d18f });
    probe = new THREE.Mesh(coneGeo, coneMat);
    probe.rotation.x = Math.PI;
    scene.add(probe);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    for (const outcome of Object.keys(OUTCOME_COLORS)) {
      trails[outcome] = { points: [], mesh: null };
    }

    renderer.domElement.addEventListener('dblclick', onDoubleClick);

    const ro = new ResizeObserver(() => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    ro.observe(container);

    function animate() {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();
  });

  onDestroy(() => {
    if (frameId) cancelAnimationFrame(frameId);
    renderer?.dispose();
  });

  $: if (probe && $positionStore) {
    probe.position.set($positionStore.x, $positionStore.y, $positionStore.z);
  }

  $: if (scene && scanBox) {
    updateScanBox(scanBox);
  }

  let prevLogLen = 0;
  $: if (scene && $logStore.length > prevLogLen) {
    for (let i = prevLogLen; i < $logStore.length; i++) {
      addAttemptPoint($logStore[i]);
    }
    prevLogLen = $logStore.length;
  }

  function updateScanBox(box: { width: number; height: number; depth: number }) {
    if (scanBoxMesh) {
      scene.remove(scanBoxMesh);
      scanBoxMesh.geometry.dispose();
      scanBoxMesh.material.dispose();
    }
    const geo = new THREE.BoxGeometry(box.width, box.height, box.depth);
    const edges = new THREE.EdgesGeometry(geo);
    const mat = new THREE.LineBasicMaterial({ color: 0x00d18f, opacity: 0.6, transparent: true });
    scanBoxMesh = new THREE.LineSegments(edges, mat);
    scanBoxMesh.position.set(box.width / 2, box.height / 2, box.depth / 2);
    scene.add(scanBoxMesh);
  }

  function addAttemptPoint(entry: AttemptEntry) {
    if (!THREE) return;
    const outcome = entry.outcome;
    const trail = trails[outcome];
    if (!trail) return;
    trail.points.push([entry.x, entry.y, entry.z]);
    if (trail.mesh) {
      scene.remove(trail.mesh);
      trail.mesh.geometry.dispose();
      trail.mesh.material.dispose();
    }
    const positions = new Float32Array(trail.points.flat());
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const mat = new THREE.PointsMaterial({
      color: OUTCOME_COLORS[outcome],
      size: 0.4,
      sizeAttenuation: true,
    });
    trail.mesh = new THREE.Points(geo, mat);
    scene.add(trail.mesh);
  }

  export function highlightPoint(x: number, y: number, z: number) {
    if (!THREE) return;
    if (highlightRing) {
      scene.remove(highlightRing);
      highlightRing.geometry.dispose();
      highlightRing.material.dispose();
    }
    const geo = new THREE.RingGeometry(0.8, 1.0, 24);
    const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
    highlightRing = new THREE.Mesh(geo, mat);
    highlightRing.position.set(x, y, z + 0.01);
    scene.add(highlightRing);
    controls.target.set(x, y, z);
  }

  export function resetView() {
    if (!camera || !controls) return;
    camera.position.set(20, 20, 20);
    controls.target.set(0, 0, 0);
  }

  async function onDoubleClick(ev: MouseEvent) {
    if (!THREE || !camera || !renderer) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((ev.clientX - rect.left) / rect.width) * 2 - 1,
      -((ev.clientY - rect.top) / rect.height) * 2 + 1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);
    const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    const point = new THREE.Vector3();
    if (raycaster.ray.intersectPlane(plane, point)) {
      try {
        await moveAbs(point.x, point.y, $positionStore.z);
      } catch {
        toasts.error('Move failed');
      }
    }
  }
</script>

<div class="scene-wrap">
  <div bind:this={container} class="scene"></div>
  <div class="overlay">
    <button on:click={resetView}>Reset view</button>
  </div>
</div>

<style>
  .scene-wrap { position: relative; width: 100%; height: 100%; min-height: 300px; }
  .scene { width: 100%; height: 100%; background: #0a0b0f; }
  .overlay {
    position: absolute;
    top: 0.5rem;
    left: 0.5rem;
    display: flex;
    gap: 0.5rem;
  }
  .overlay button {
    font-size: 11px;
    padding: 0.25rem 0.5rem;
    opacity: 0.7;
  }
  .overlay button:hover { opacity: 1; }
</style>
