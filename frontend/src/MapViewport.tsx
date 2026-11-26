
import { useEffect, useRef, useState } from 'react';
import type { Building } from './api.ts';
import { Icon } from './Icons.tsx';
import { createScene, type MapNavigation } from './mapScene.ts';

export function MapViewport({ buildings, selected, onSelect }: {
  buildings: Building[];
  selected?: Building;
  onSelect: (building: Building) => void;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const engine = useRef<MapNavigation | undefined>(undefined);
  const [fallback, setFallback] = useState(false);
  const latitude = selected?.latitude;
  const longitude = selected?.longitude;

  useEffect(() => {
    const target = viewport.current;
    const labels = overlay.current;
    if (!target || !labels) return;
    try {
      engine.current = createScene(target, labels, () => setFallback(true));
    } catch {
      const task = requestAnimationFrame(() => setFallback(true));
      return () => cancelAnimationFrame(task);
    }
    return () => {
      engine.current?.dispose();
      engine.current = undefined;
    };
  }, []);

  useEffect(() => {
    if (latitude != null && longitude != null) {
      engine.current?.focus(latitude, longitude, selected?.id === 'chimkowe' ? 168 : 143);
    }
  }, [selected?.id, latitude, longitude]);

  useEffect(() => { engine.current?.refresh(); }, [buildings, selected?.id]);

  return <div className="map-viewport" ref={viewport} aria-label="Visor 3D de Peñalolén">
    <div className="map-labels" ref={overlay} aria-hidden="true">
      {buildings.filter(({ latitude, longitude }) => latitude != null && longitude != null).map((building) => (
        <button key={building.id} type="button" className="geo-marker" data-lat={building.latitude}
          data-lon={building.longitude} data-selected={selected?.id === building.id} hidden tabIndex={-1}
          onClick={() => onSelect(building)}>
          <Icon name="pin" size={15}/> <span>{building.short_name}</span>
        </button>
      ))}
    </div>
    {fallback ? <div className="map-fallback">
      <Icon name="map" size={30}/>
      <p>La vista 3D no está disponible en este navegador. Puedes consultar los recintos y cómo llegar en la lista.</p>
    </div> : <div className="map-controls" aria-label="Controles del mapa">
      <button className="icon-button" aria-label="Girar a la izquierda" onClick={() => engine.current?.orbit(-Math.PI / 9)}><Icon name="left" size={18}/></button>
      <button className="icon-button" aria-label="Girar a la derecha" onClick={() => engine.current?.orbit(Math.PI / 9)}><Icon name="right" size={18}/></button>
      <button className="icon-button" aria-label="Acercar" onClick={() => engine.current?.zoom(.70)}><Icon name="plus" size={18}/></button>
      <button className="icon-button" aria-label="Alejar" onClick={() => engine.current?.zoom(1.43)}><Icon name="minus" size={18}/></button>
      <button className="icon-button" aria-label="Vista general" onClick={() => engine.current?.overview()}><Icon name="reset" size={18}/></button>
    </div>}
  </div>;
}
