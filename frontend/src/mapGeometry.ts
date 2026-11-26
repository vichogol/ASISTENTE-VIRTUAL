
import { MathUtils, Vector3 } from 'three';
import { elevations, terrainBounds, type GeoPoint } from './mapGeodata.ts';

const origin = { latitude: -33.4813, longitude: -70.5552 };
const southScale = 111_132;
const eastScale = 111_320 * Math.cos(origin.latitude * Math.PI / 180);
const [south, north, west, east] = terrainBounds;

export function toWorld(latitude: number, longitude: number) {
  return { x: (longitude - origin.longitude) * eastScale, z: (origin.latitude - latitude) * southScale };
}

export function elevation(x: number, z: number) {
  const lon = x / eastScale + origin.longitude;
  const lat = origin.latitude - z / southScale;
  const nx = elevations[0].length - 1;
  const nz = elevations.length - 1;
  const u = MathUtils.clamp((lon - west) / (east - west) * nx, 0, nx);
  const v = MathUtils.clamp((north - lat) / (north - south) * nz, 0, nz);
  const c = Math.min(Math.floor(u), nx - 1);
  const r = Math.min(Math.floor(v), nz - 1);
  const top = MathUtils.lerp(elevations[r][c], elevations[r][c + 1], u - c);
  const bottom = MathUtils.lerp(elevations[r + 1][c], elevations[r + 1][c + 1], u - c);
  return (MathUtils.lerp(top, bottom, v - r) - 568) * 1.12;
}

export function onGround([latitude, longitude]: GeoPoint, offset = 0) {
  const { x, z } = toWorld(latitude, longitude);
  return new Vector3(x, elevation(x, z) + offset, z);
}
