
import { useState } from 'react';
import { type Building, safeLink } from './api.ts';
import { Icon } from './Icons.tsx';

export function BuildingPhoto({ building }: { building: Pick<Building, 'name' | 'photo_url' | 'photo_caption' | 'photo_source'> }) {
  const [failed, setFailed] = useState(false);
  const raw = building.photo_url ?? '';
  const src = /^\/recintos\/[a-z0-9.-]+$/i.test(raw) ? import.meta.env.BASE_URL + raw.slice(1) : safeLink(raw);
  const credit = building.photo_source && safeLink(building.photo_source);
  return <figure className="building-photo">
    {src && !failed
      ? <img src={src} alt={building.photo_caption || building.name} loading="lazy" decoding="async"
          referrerPolicy="no-referrer" onError={() => setFailed(true)}/>
      : <div className="photo-placeholder"><Icon name="pin" size={24}/><span>{failed ? 'Foto no disponible' : 'Sin foto verificada'}</span></div>}
    {src && !failed && credit && <figcaption>
      <a href={credit} target="_blank" rel="noreferrer" aria-label={'Fuente de la fotografía de ' + building.name}>
        Fuente de la foto <Icon name="external" size={12}/>
      </a>
    </figcaption>}
  </figure>;
}
