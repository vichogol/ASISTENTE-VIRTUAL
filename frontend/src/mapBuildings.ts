
import * as T from 'three';
import { footprints } from './mapGeodata.ts';
import { elevation, onGround } from './mapGeometry.ts';

type Surface = [number, number];
type Plan = { ring: Surface[]; bearing: number; span: number; depth: number };
const heights: Record<string, number> = { consistorial: 7, chimkowe: 13, yunus: 8, piscina: 8, cav: 10, kintun: 5 };

function shape(ring: Surface[], scale = 1) {
  return new T.Shape(ring.map(([x, z]) => new T.Vector2(x * scale, -z * scale)));
}

function extrude(group: T.Group, ring: Surface[], base: number, height: number, material: T.Material, scale = 1) {
  const geometry = new T.ExtrudeGeometry(shape(ring, scale), { depth: height, bevelEnabled: false });
  geometry.rotateX(-Math.PI / 2);
  const mesh = new T.Mesh(geometry, material);
  mesh.position.y = base;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
}

function block(group: T.Group, w: number, h: number, d: number, x: number, y: number, z: number,
  material: T.Material, yaw = 0) {
  const mesh = new T.Mesh(new T.BoxGeometry(w, h, d), material);
  mesh.position.set(x, y, z);
  mesh.rotation.y = yaw;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
}

function grain(base: string, accent: string, masonry = false) {
  const canvas = document.createElement('canvas');
  canvas.width = 128;
  canvas.height = 128;
  const context = canvas.getContext('2d');
  if (!context) return undefined;
  context.fillStyle = base;
  context.fillRect(0, 0, 128, 128);
  context.fillStyle = accent;
  if (masonry) {
    for (let row = 0; row < 128; row += 11) {
      context.fillRect(0, row, 128, 1);
      for (let col = -14; col < 128; col += 20) {
        context.fillRect(col + (row % 2) * 8, row, 1, 11);
      }
    }
  }
  for (let i = 0; i < 1600; i++) {
    context.globalAlpha = .13 + (i % 8) * .03;
    context.fillRect((i * 43 + i * i) % 128, (i * 61 + (i % 13) * 17) % 128, i % 3 + 1, 1);
  }
  const texture = new T.CanvasTexture(canvas);
  texture.colorSpace = T.SRGBColorSpace;
  texture.wrapS = texture.wrapT = T.RepeatWrapping;
  texture.anisotropy = 4;
  return texture;
}

function materials() {
  const plain = (color: string, metalness = 0, roughness = .76) =>
    new T.MeshStandardMaterial({ color, metalness, roughness });
  return {
    cream: plain('#d9bf8c'),
    plaster: plain('#d2c8b1'),
    cornice: plain('#e9e3d4'),
    iron: plain('#323c3b', .35),
    walk: plain('#b4ab94'),
    stone: new T.MeshStandardMaterial({ map: grain('#8e8470', '#55524d', true), roughness: 1 }),
    clay: new T.MeshStandardMaterial({ map: grain('#a55e3f', '#57382d', true), roughness: .93, side: T.DoubleSide }),
    facade: new T.MeshStandardMaterial({ map: grain('#b59d80', '#83715d'), roughness: .95 }),
    glass: plain('#638d91', .42, .18),
    glassDark: plain('#365a60', .46, .23),
    skylight: plain('#789399', .32, .30),
    wood: plain('#68402b'),
  };
}

type Materials = ReturnType<typeof materials>;

function planFor(ring: Surface[]): Plan {
  let bearing = 0;
  let longest = 0;
  ring.forEach(([x, z], i) => {
    const [nx, nz] = ring[(i + 1) % ring.length];
    const length = Math.hypot(nx - x, nz - z);
    if (length > longest) {
      longest = length;
      bearing = Math.atan2(x - nx, nz - z);
    }
  });
  const across = ring.map(([x, z]) => x * Math.cos(bearing) + z * Math.sin(bearing));
  const along = ring.map(([x, z]) => -x * Math.sin(bearing) + z * Math.cos(bearing));
  return {
    ring, bearing, span: Math.max(...across) - Math.min(...across),
    depth: Math.max(...along) - Math.min(...along),
  };
}

function windows(group: T.Group, ring: Surface[], levels: number[], height: number, spacing: number,
  inset: number, glass: T.Material, frame: T.Material) {
  ring.forEach(([x, z], i) => {
    const [nx, nz] = ring[(i + 1) % ring.length];
    const length = Math.hypot(nx - x, nz - z);
    if (length < 5) return;
    const panels = Math.max(1, Math.floor(length / spacing));
    const width = length / panels;
    const yaw = -Math.atan2(nz - z, nx - x);
    for (let j = 0; j < panels; j++) {
      const t = (j + .5) / panels;
      const mx = T.MathUtils.lerp(x, nx, t) * inset;
      const mz = T.MathUtils.lerp(z, nz, t) * inset;
      for (const y of levels) {
        block(group, width * .92, height, .34, mx, y, mz, frame, yaw);
        block(group, width * .75, height * .81, .58, mx, y, mz, glass, yaw);
      }
    }
  });
}

function gabledRoof(group: T.Group, w: number, d: number, y: number, rise: number,
  roofing: T.Material, wall: T.Material, offset = 0) {
  const slope = Math.atan2(rise, w / 2);
  const length = Math.hypot(w / 2, rise) + .9;
  [-1, 1].forEach((side) => {
    const mesh = new T.Mesh(new T.BoxGeometry(length, .43, d + 1.9), roofing);
    mesh.position.set(offset + side * w / 4, y + rise / 2, 0);
    mesh.rotation.z = -slope * side;
    mesh.castShadow = true;
    group.add(mesh);
  });
  const triangle = new T.Shape([new T.Vector2(-w / 2, 0), new T.Vector2(w / 2, 0), new T.Vector2(0, rise)]);
  const infill = new T.Mesh(new T.ExtrudeGeometry(triangle, { depth: d, bevelEnabled: false }), wall);
  infill.position.set(offset, y, -d / 2);
  group.add(infill);
}

function chimkowe(group: T.Group, plan: Plan, m: Materials) {
  extrude(group, plan.ring, 0, 3.65, m.stone);
  extrude(group, plan.ring, 3.6, 8.4, m.glassDark, .966);
  windows(group, plan.ring, [7.7], 7.25, 2.1, .978, m.glass, m.iron);
  extrude(group, plan.ring, 3.45, .4, m.cornice);
  extrude(group, plan.ring, 11.7, .85, m.cornice);
  extrude(group, plan.ring, 12.1, .65, m.iron, .94);
  const roof = new T.Group();
  roof.rotation.y = -plan.bearing;
  group.add(roof);
  for (let i = -2; i <= 2; i++) {
    block(roof, plan.span * .57, 1.4, 2.7, 0, 13.2, i * plan.depth * .115, m.skylight);
    block(roof, plan.span * .60, .32, 3.35, 0, 13.98, i * plan.depth * .115, m.cornice);
  }
  for (let i = 0; i < 4; i++) {
    block(roof, plan.span * .48, .28, 2.1, 0, .16 + i * .25, -plan.depth * .34 - (3 - i) * 1.8, m.stone);
  }
}

function consistorial(group: T.Group, plan: Plan, m: Materials) {
  extrude(group, plan.ring, 0, 6.6, m.cream);
  extrude(group, plan.ring, 6.5, .4, m.wood);
  windows(group, plan.ring, [2.1, 4.95], 2.25, 3.7, 1.004, m.glassDark, m.wood);
  const roof = new T.Group();
  roof.rotation.y = -plan.bearing;
  group.add(roof);
  gabledRoof(roof, plan.span * .60, plan.depth * .71, 6.8, 3.9, m.clay, m.cream);
  gabledRoof(roof, plan.span * .22, plan.depth * .55, 6.5, 2.1, m.clay, m.cream, -plan.span * .34);
  gabledRoof(roof, plan.span * .22, plan.depth * .55, 6.5, 2.1, m.clay, m.cream, plan.span * .34);
}

function yunus(group: T.Group, plan: Plan, m: Materials) {
  extrude(group, plan.ring, 0, 7.4, m.cornice);
  windows(group, plan.ring, [2.25, 5.45], 2.35, 3, 1.004, m.glassDark, m.cornice);
  extrude(group, plan.ring, 7.25, 1.15, m.cornice, 1.015);
  extrude(group, plan.ring, 8.35, .25, m.stone, .91);
  const canopy = new T.Group();
  canopy.rotation.y = -plan.bearing;
  group.add(canopy);
  block(canopy, plan.span * .40, .42, 3.8, 0, 3.55, -plan.depth * .36, m.facade);
}

export function addBuildings(scene: T.Scene) {
  const m = materials();
  for (const [id, footprint] of Object.entries(footprints)) {
    const points = footprint.map((point) => onGround(point));
    const x = points.reduce((sum, point) => sum + point.x, 0) / points.length;
    const z = points.reduce((sum, point) => sum + point.z, 0) / points.length;
    const group = new T.Group();
    group.position.set(x, elevation(x, z) - .25, z);
    const plan = planFor(points.map((point) => [point.x - x, point.z - z]));
    extrude(group, plan.ring, -.35, .6, m.walk, 1.10);
    if (id === 'chimkowe') {
      group.scale.y = .76;
      chimkowe(group, plan, m);
    }
    else if (id === 'consistorial') consistorial(group, plan, m);
    else if (id === 'yunus') yunus(group, plan, m);
    else {
      const h = heights[id] ?? 6;
      extrude(group, plan.ring, 0, h, m.plaster);
      windows(group, plan.ring, [h * .57], h * .43, 3.9, 1.004, m.glass, m.iron);
      extrude(group, plan.ring, h - .16, .53, m.cornice);
    }
    scene.add(group);
  }
}
