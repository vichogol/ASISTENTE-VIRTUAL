
import { useEffect, useRef, useState } from 'react';
import { type Building, routeTo } from './api.ts';
import { Icon } from './Icons.tsx';
import { BuildingPhoto } from './BuildingPhoto.tsx';
import { MapViewport } from './MapViewport.tsx';

export function MapDialog({ buildings, initial, unavailable, onRetry, onClose, onService }:
  { buildings: Building[]; initial?: Building; unavailable: boolean; onRetry: () => void; onClose: () => void; onService: (query: string) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [selectedId, setSelectedId] = useState(initial?.id);
  const selected = buildings.find((building) => building.id === selectedId);

  useEffect(() => {
    const node = dialog.current;
    if (node && !node.open) node.showModal();
    return () => { if (node?.open) node.close(); };
  }, []);

  return <dialog className="map-dialog" ref={dialog} onClose={() => { if (!dialog.current?.open) onClose(); }}
    aria-labelledby="map-title">
    <div className="map-heading">
      <div><h2 id="map-title">Mapa 3D de Peñalolén</h2><p>Selecciona un recinto para ver sus trámites y cómo llegar.</p></div>
      <button className="icon-button" aria-label="Cerrar mapa" onClick={() => dialog.current?.close()}><Icon name="close"/></button>
    </div>
    <div className="map-layout">
      <div>
        <MapViewport buildings={buildings} selected={selected} onSelect={(building) => setSelectedId(building.id)}/>
        <p className="map-credit">Modelos arquitectónicos de referencia. Calles y huellas de <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap</a>. Relieve de <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md" target="_blank" rel="noreferrer">Mapzen Terrain Tiles</a> (USGS/NASA SRTM).</p>
        {unavailable && <p role="status">El catálogo completo está temporalmente fuera de servicio. <button className="text-button" onClick={onRetry}>Reintentar</button></p>}
        {!unavailable && !buildings.length && <p role="status">Cargando recintos…</p>}
        <div className="map-places" aria-label="Seleccionar recinto">
          {buildings.map((building) => <button key={building.id} aria-pressed={building.id === selectedId}
            onClick={() => setSelectedId(building.id)}><Icon name="pin" size={16}/>{building.short_name}</button>)}
        </div>
      </div>
      <aside className="map-detail" aria-live="polite">
        {selected ? <>
          <BuildingPhoto key={selected.id} building={selected}/>
          {selected.photo_caption && <p className="photo-description">{selected.photo_caption}</p>}
          <h3>{selected.name}</h3>
          <p className="location"><Icon name="pin" size={17}/>{selected.address}</p>
          {selected.latitude == null && <p>Ubicación 3D pendiente de confirmar. Puedes consultar la dirección publicada.</p>}
          {(selected.services.length > 0 || selected.service) && <h4>Trámites y servicios</h4>}
          {selected.service && <p className="map-associated">{selected.service}</p>}
          {selected.services.length > 0 && <ul>{selected.services.map((service) => <li key={service}><button className="text-button" onClick={() => onService(service)}>{service} <Icon name="arrow" size={13}/></button></li>)}</ul>}
          <a className="primary-button" href={routeTo(selected)} target="_blank" rel="noreferrer">Cómo llegar <Icon name="external" size={16}/></a>
          <a className="source-link" href={selected.source_url} target="_blank" rel="noreferrer">Fuente municipal <Icon name="external" size={14}/></a>
        </> : <><h3>Recintos municipales</h3><p>Elige un edificio en el mapa o en la lista para abrir su ficha.</p></>}
      </aside>
    </div>
  </dialog>;
}
