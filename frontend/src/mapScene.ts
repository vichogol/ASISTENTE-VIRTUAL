
import * as T from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { addBuildings } from './mapBuildings.ts';
import { onGround } from './mapGeometry.ts';
import { addRoads, addTerrain, addVegetation } from './mapLandscape.ts';

export type MapNavigation = {
  focus: (latitude: number, longitude: number, distance: number) => void;
  orbit: (angle: number) => void;
  zoom: (scale: number) => void;
  overview: () => void;
  refresh: () => void;
  dispose: () => void;
};

export function createScene(viewport: HTMLElement, overlay: HTMLElement, onUnavailable: () => void): MapNavigation {
  const renderer = new T.WebGLRenderer({ antialias: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(1.65, window.devicePixelRatio || 1));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFShadowMap;
  renderer.domElement.setAttribute('aria-hidden', 'true');
  viewport.prepend(renderer.domElement);

  const scene = new T.Scene();
  scene.background = new T.Color('#dbe4e6');
  const camera = new T.PerspectiveCamera(40, 1, 2, 38_000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = .13;
  controls.minDistance = 65;
  controls.maxDistance = 20_000;
  controls.maxPolarAngle = Math.PI / 2.35;
  controls.minPolarAngle = .1;
  controls.target.set(-180, 65, 360);
  scene.add(new T.HemisphereLight('#f5f8ff', '#8a775d', 2.6));

  const sunlight = new T.DirectionalLight('#fff1d7', 2.2);
  const offset = new T.Vector3(-145, 210, -100);
  sunlight.castShadow = true;
  sunlight.shadow.mapSize.set(1024, 1024);
  Object.assign(sunlight.shadow.camera, { left: -115, right: 115, top: 115, bottom: -115, near: 5, far: 420 });
  sunlight.shadow.camera.updateProjectionMatrix();
  sunlight.shadow.bias = -.0006;
  sunlight.shadow.normalBias = .45;
  scene.add(sunlight, sunlight.target);

  addTerrain(scene);
  const roads = addRoads(scene);
  addVegetation(scene);
  addBuildings(scene);

  const labels = roads.map(({ name, points }) => {
    const element = document.createElement('span');
    element.className = 'street-label';
    element.textContent = name;
    element.setAttribute('aria-hidden', 'true');
    overlay.append(element);
    return { points, element };
  });

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const overviewPoint = controls.target.clone();
  const initialOffset = new T.Vector3(-.07, .9, .63).normalize();
  const overviewDistance = () => Math.max(7950, 6250 / Math.max(.42, camera.aspect));
  const setInitialOrientation = () => {
    camera.position.copy(overviewPoint).addScaledVector(initialOffset, overviewDistance());
    controls.update();
  };

  const screen = new T.Vector3();
  let dirty = true;
  let frame = 0;
  const refresh = () => { dirty = true; };
  function resize() {
    const width = Math.max(1, viewport.clientWidth);
    const height = Math.max(1, viewport.clientHeight);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    refresh();
  }
  resize();
  setInitialOrientation();
  const observer = new ResizeObserver(resize);
  observer.observe(viewport);

  type Flight = { from: T.Vector3; to: T.Vector3; eye: T.Vector3; destination: T.Vector3; started: number };
  let flight: Flight | null = null;
  const stopFlight = () => { flight = null; };
  controls.addEventListener('start', stopFlight);
  controls.addEventListener('change', refresh);
  renderer.domElement.addEventListener('webglcontextlost', onUnavailable);

  function fly(target: T.Vector3, eye: T.Vector3) {
    if (reduceMotion.matches) {
      flight = null;
      controls.target.copy(target);
      camera.position.copy(eye);
      controls.update();
      refresh();
      return;
    }
    flight = { from: controls.target.clone(), to: target,
      eye: camera.position.clone(), destination: eye, started: performance.now() };
  }

  function positionOverlay() {
    const width = viewport.clientWidth;
    const height = viewport.clientHeight;
    const claimed: { x: number; y: number }[] = [];
    const placeMarkers = [...overlay.querySelectorAll<HTMLButtonElement>('.geo-marker')].sort(
      (a, b) => Number(b.dataset.selected === 'true') - Number(a.dataset.selected === 'true'),
    );
    const within = (point: T.Vector3, limit: number) => {
      screen.copy(point).project(camera);
      return screen.z >= -1 && screen.z <= 1 && Math.abs(screen.x) < limit && Math.abs(screen.y) < limit;
    };
    const position = (element: HTMLElement) => {
      const x = (screen.x + 1) * width / 2;
      const y = (1 - screen.y) * height / 2;
      element.style.left = x + 'px';
      element.style.top = y + 'px';
      return { x, y };
    };

    for (const marker of placeMarkers) {
      const point = onGround([Number(marker.dataset.lat), Number(marker.dataset.lon)], 16);
      if (!within(point, .95)) { marker.hidden = true; continue; }
      const coord = position(marker);
      marker.hidden = claimed.some(({ x, y }) => Math.hypot((x - coord.x) / 1.6, y - coord.y) < 19);
      if (!marker.hidden) claimed.push(coord);
    }
    for (const { element, points } of labels) {
      let best: T.Vector3 | undefined;
      let nearest = Infinity;
      for (const point of points) {
        if (!within(point, .91)) continue;
        const distance = Math.abs(screen.y - .11) + Math.abs(screen.x + .34) * .7;
        const x = (screen.x + 1) * width / 2;
        const y = (1 - screen.y) * height / 2;
        if (distance < nearest && !claimed.some((c) => Math.abs(c.x - x) < 82 && Math.abs(c.y - y) < 23)) {
          best = point;
          nearest = distance;
        }
      }
      element.hidden = !best;
      if (best) {
        screen.copy(best).project(camera);
        claimed.push(position(element));
      }
    }
  }

  function draw(now: number) {
    if (flight) {
      const t = Math.min(1, (now - flight.started) / 720);
      const ease = t * t * (3 - 2 * t);
      controls.target.lerpVectors(flight.from, flight.to, ease);
      camera.position.lerpVectors(flight.eye, flight.destination, ease);
      if (t >= 1) flight = null;
      refresh();
    }
    controls.update();
    if (dirty) {
      sunlight.target.position.copy(controls.target);
      sunlight.position.copy(controls.target).add(offset);
      const distance = camera.position.distanceTo(controls.target);
      camera.near = Math.max(.6, distance / 360);
      camera.far = Math.max(11500, distance * 2.35);
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
      positionOverlay();
      dirty = false;
    }
    frame = requestAnimationFrame(draw);
  }
  frame = requestAnimationFrame(draw);

  return {
    focus(latitude, longitude, distance) {
      const target = onGround([latitude, longitude], 8);
      const facing = camera.position.clone().sub(controls.target);
      if (facing.length() > 620) facing.set(-.65, .62, -.94);
      facing.normalize();
      fly(target, target.clone().addScaledVector(facing, distance));
    },
    orbit(angle) {
      const direction = camera.position.clone().sub(controls.target);
      direction.applyAxisAngle(new T.Vector3(0, 1, 0), angle);
      fly(controls.target.clone(), controls.target.clone().add(direction));
    },
    zoom(scale) {
      const direction = camera.position.clone().sub(controls.target);
      const length = T.MathUtils.clamp(direction.length() * scale, controls.minDistance, controls.maxDistance);
      fly(controls.target.clone(), controls.target.clone().add(direction.setLength(length)));
    },
    overview() {
      fly(overviewPoint.clone(), overviewPoint.clone().addScaledVector(initialOffset, overviewDistance()));
    },
    refresh,
    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', onUnavailable);
      renderer.domElement.remove();
      labels.forEach(({ element }) => element.remove());
      const materials = new Set<T.Material>();
      const geometries = new Set<T.BufferGeometry>();
      scene.traverse((object) => {
        if (object instanceof T.Mesh) {
          geometries.add(object.geometry);
          [object.material].flat().forEach((material) => materials.add(material));
        }
      });
      for (const material of materials) {
        if (material instanceof T.MeshStandardMaterial) material.map?.dispose();
        material.dispose();
      }
      for (const geometry of geometries) geometry.dispose();
      sunlight.shadow.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
