
import * as T from 'three';
import { elevations, localStreets, parks, roads, terrainBounds } from './mapGeodata.ts';
import { elevation, onGround, toWorld } from './mapGeometry.ts';

export type RoadLabel = { name: string; points: T.Vector3[] };
const earth = new T.Color('#b6aa84');
const fields = new T.Color('#969e78');
const slopes = new T.Color('#aea78a');

export function addTerrain(scene: T.Scene) {
  const [south, north, west, east] = terrainBounds;
  const rows = elevations.length;
  const cols = elevations[0].length;
  const positions = [];
  const colors = [];
  const faces = [];
  const tint = new T.Color();
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const { x, z } = toWorld(north + (south - north) * r / (rows - 1), west + (east - west) * c / (cols - 1));
      const y = elevation(x, z);
      positions.push(x, y, z);
      const variation = .45 + .2 * Math.sin(x * .004 + z * .001) + .15 * Math.sin(z * .012);
      tint.copy(earth).lerp(fields, variation).lerp(slopes, T.MathUtils.smoothstep(y, 85, 320));
      colors.push(tint.r, tint.g, tint.b);
      if (r < rows - 1 && c < cols - 1) {
        const i = r * cols + c;
        faces.push(i, i + cols, i + 1, i + 1, i + cols, i + cols + 1);
      }
    }
  }
  const ground = new T.BufferGeometry();
  ground.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  ground.setAttribute('color', new T.Float32BufferAttribute(colors, 3));
  ground.setIndex(faces);
  ground.computeVertexNormals();
  const terrain = new T.Mesh(ground, new T.MeshStandardMaterial({ vertexColors: true, roughness: .95 }));
  terrain.receiveShadow = true;
  scene.add(terrain);
}

const MAIN = new Set(['Av. Grecia', 'Av. Las Torres', 'Av. Tobalaba', 'Av. Oriental']);

export function addRoads(scene: T.Scene): RoadLabel[] {
  const asphalt = new T.MeshBasicMaterial({ color: '#798381', side: T.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  const minor = new T.MeshBasicMaterial({ color: '#d9d2bc', side: T.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
  const network: number[] = [];
  for (const path of localStreets) {
    const nodes = path.map((point) => onGround(point));
    for (let i = 1; i < nodes.length; i++) {
      const a = nodes[i - 1];
      const b = nodes[i];
      const distance = a.distanceTo(b);
      if (distance > .1) {
        const dx = (b.z - a.z) / distance;
        const dz = (a.x - b.x) / distance;
        const steps = Math.max(1, Math.ceil(distance / 42));
        for (let j = 0; j < steps; j++) {
          appendLane(network, a.clone().lerp(b, j / steps), a.clone().lerp(b, (j + 1) / steps), dx, dz, 3.3, .80);
        }
      }
    }
  }
  scene.add(roadMesh(network, minor));
  const labels: RoadLabel[] = [];
  for (const road of roads) {
    const important = MAIN.has(road.name);
    const edges: number[] = [];
    const points: T.Vector3[] = [];
    for (const path of road.paths) {
      const nodes = path.map((point) => onGround(point));
      for (let i = 1; i < nodes.length; i++) {
        const from = nodes[i - 1];
        const to = nodes[i];
        const distance = from.distanceTo(to);
        if (distance < .05) continue;
        const dx = (to.z - from.z) / distance;
        const dz = (from.x - to.x) / distance;
        const steps = Math.max(1, Math.ceil(distance / 20));
        if (important && distance > 35) points.push(from.clone().lerp(to, .5));
        for (let j = 0; j < steps; j++) {
          const a = from.clone().lerp(to, j / steps);
          const b = from.clone().lerp(to, (j + 1) / steps);
          appendLane(edges, a, b, dx, dz, important ? 6.8 : 5, important ? 1.6 : 1.0);
        }
      }
    }
    scene.add(roadMesh(edges, important ? asphalt : minor));
    if (important) labels.push({ name: road.name, points });
  }
  return labels;
}

function appendLane(positions: number[], a: T.Vector3, b: T.Vector3, dx: number, dz: number, width: number, lift: number) {
  const left = (p: T.Vector3) => surface(p.x + dx * width, p.z + dz * width, lift);
  const right = (p: T.Vector3) => surface(p.x - dx * width, p.z - dz * width, lift);
  positions.push(...left(a), ...right(a), ...left(b), ...left(b), ...right(a), ...right(b));
}

function surface(x: number, z: number, lift: number): [number, number, number] {
  return [x, elevation(x, z) + lift, z];
}

function roadMesh(positions: number[], material: T.Material) {
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.Float32BufferAttribute(positions, 3));
  return new T.Mesh(geometry, material);
}

function inside(x: number, z: number, ring: T.Vector3[]) {
  let contained = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i];
    const b = ring[j];
    if ((a.z > z) !== (b.z > z) && x < (b.x - a.x) * (z - a.z) / (b.z - a.z) + a.x) contained = !contained;
  }
  return contained;
}

export function addVegetation(scene: T.Scene) {
  const trees: [number, number, number][] = [];
  for (const park of parks) {
    const ring = park.map((point) => onGround(point));
    const xs = ring.map(({ x }) => x);
    const zs = ring.map(({ z }) => z);
    const west = Math.min(...xs);
    const east = Math.max(...xs);
    const north = Math.min(...zs);
    const south = Math.max(...zs);
    const spacing = Math.max(16, Math.sqrt((east - west) * (south - north) / 50));
    for (let x = west + spacing / 2; x < east; x += spacing) {
      for (let z = north + spacing / 2; z < south; z += spacing) {
        if (inside(x, z, ring)) trees.push([x, z, .65 + .55 * Math.abs(Math.sin(x * .47 + z * .033))]);
      }
    }
  }
  // Landscaping around the civic complex. The individual trees are illustrative.
  const centre = toWorld(-33.47691, -70.54223);
  for (let i = 0; i < 14; i++) {
    trees.push([centre.x - 7 - i * 4.7, centre.z + 14 + i * 4, .8 + (i % 3) * .13]);
  }
  const garden = toWorld(-33.47739, -70.54137);
  for (let i = 0; i < 9; i++) {
    trees.push([garden.x - i * 3.8, garden.z + 7 + (i % 2) * 4, .7 + (i % 3) * .11]);
  }
  const trunks = new T.InstancedMesh(new T.CylinderGeometry(.29, .52, 4.4, 6),
    new T.MeshStandardMaterial({ color: '#796345' }), trees.length);
  const crowns = new T.InstancedMesh(new T.IcosahedronGeometry(3.4, 1),
    new T.MeshStandardMaterial({ roughness: .96 }), trees.length);
  const object = new T.Object3D();
  trees.forEach(([x, z, size], i) => {
    const y = elevation(x, z);
    object.scale.setScalar(size);
    object.position.set(x, y + 2.2 * size, z);
    object.updateMatrix();
    trunks.setMatrixAt(i, object.matrix);
    object.position.y = y + 6.0 * size;
    object.scale.set(size * .93, size * (i % 5 === 0 ? 1.7 : .88), size);
    object.updateMatrix();
    crowns.setMatrixAt(i, object.matrix);
    crowns.setColorAt(i, new T.Color(['#465f43', '#69805a', '#728456', '#586e4d'][i % 4]));
  });
  scene.add(trunks, crowns);
}
