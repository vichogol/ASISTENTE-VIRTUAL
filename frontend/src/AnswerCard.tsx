
import { useState } from 'react';
import { type Building, type ChatResponse, type Contact, safeLink, saveFeedback } from './api.ts';
import { Icon } from './Icons.tsx';
import { BuildingPhoto } from './BuildingPhoto.tsx';

function ContactDetails({ contact }: { contact: Contact }) {
  return <div className="contact-details">
    <strong>{contact.unit}</strong>
    {contact.address && <span className="location"><Icon name="pin" size={16}/>{contact.address}</span>}
    {contact.phone && <a href={'tel:' + contact.phone.replace(/[^\d+]/g, '')}><Icon name="phone" size={16}/>{contact.phone}</a>}
    {contact.email && <a href={'mailto:' + contact.email}>{contact.email}</a>}
    <a href={safeLink(contact.url)} target="_blank" rel="noreferrer">Abrir canal municipal <Icon name="external" size={14}/></a>
    <a className="source-link" href={safeLink(contact.source_url)} target="_blank" rel="noreferrer">Ver fuente del contacto</a>
  </div>;
}

export function PlacePreview({ building, onOpen }: { building: Building; onOpen: () => void }) {
  return <article className="place-preview">
    <BuildingPhoto building={building}/>
    <div>
      <h3>{building.name}</h3>
      <p className="location"><Icon name="pin" size={17}/>{building.address}</p>
      {(building.service || building.services.length > 0) && <p className="place-service">
        {building.service ?? building.services.join(" · ")}
      </p>}
      <button className="text-button" onClick={onOpen}>Ver en el mapa 3D <Icon name="arrow" size={16}/></button>
    </div>
  </article>;
}

export function AnswerCard({ data, session, onMap, onQuestion, busy }: {
  data: ChatResponse; session: string; onMap: (building: Building) => void;
  onQuestion: (question: string) => void; busy: boolean;
}) {
  const [rating, setRating] = useState<boolean>();
  const [pending, setPending] = useState(false);
  const [feedbackError, setFeedbackError] = useState(false);

  async function rate(helpful: boolean) {
    if (!data.interaction_id || pending) return;
    setFeedbackError(false);
    setPending(true);
    try {
      await saveFeedback(data.interaction_id, session, helpful);
      setRating(helpful);
    } catch {
      setFeedbackError(true);
    } finally {
      setPending(false);
    }
  }

  return <article className="answer">
    <p className="answer-intro">{data.intro ?? data.answer}</p>
    {data.sections.map((section, index) => <section key={index} className="answer-section">
      <h3>{section.title}</h3>
      <SectionBody lines={section.lines}/>
    </section>)}
    {data.suggestions.length > 0 && <ul className="answer-suggestions" aria-label="Consultas sugeridas">
      {data.suggestions.map(({ label, question }) => <li key={question}>
        <button type="button" disabled={busy} onClick={() => onQuestion(question)}>
          {label} <Icon name="arrow" size={16}/>
        </button>
      </li>)}
    </ul>}
    {data.buildings.length > 0 && <div className="places-in-answer">
      {data.buildings.map((building) => <PlacePreview key={building.id} building={building} onOpen={() => onMap(building)}/>)}
    </div>}
    {data.actions.length > 0 && <div className="answer-actions">
      {data.actions.map((action) => {
        const href = safeLink(action.url);
        return href ? <a key={action.url} href={href} target="_blank" rel="noreferrer">{action.label}<Icon name="external" size={15}/></a> : null;
      })}
    </div>}
    {data.referral && <section className="referral">
      <h3><Icon name="info" size={18}/> Dónde pueden ayudarte</h3>
      <ContactDetails contact={data.referral}/>
      {data.referral.central && <ContactDetails contact={data.referral.central}/>}
    </section>}
    {data.sources.length > 0 && <details className="answer-sources">
      <summary>{data.sources.length === 1 ? 'Ver fuente municipal' : 'Ver fuentes municipales'}</summary>
      <ul>{data.sources.map((source, i) => <li key={i}>
        <strong>{source.pregunta}</strong>
        {source.direccion && <span>{source.direccion}</span>}
        <small>{source.hoja ? 'Base municipal · ' + source.hoja + ' · Ficha ' + source.id : 'Base municipal de preguntas frecuentes'}</small>
      </li>)}</ul>
    </details>}
    {data.interaction_id && <div className="feedback">
      <span>¿Te sirvió esta respuesta?</span>
      <button disabled={pending} aria-pressed={rating === true} onClick={() => void rate(true)}>Sí</button>
      <button disabled={pending} aria-pressed={rating === false} onClick={() => void rate(false)}>No</button>
      <small role="status">{feedbackError ? 'No se guardó. Puedes reintentar.' : rating !== undefined ? 'Gracias por tu valoración.' : ''}</small>
    </div>}
  </article>;
}

const ORDERED = /^(?:\d+[.)]|\(\d+\))\s+/;
const BULLET = /^(?:[•▪-])\s*/;

function lineType(line: string) {
  if (ORDERED.test(line)) return 'ol';
  if (BULLET.test(line)) return 'ul';
  return 'p';
}

function SectionBody({ lines }: { lines: string[] }) {
  const groups: { type: 'ol' | 'ul' | 'p'; lines: string[] }[] = [];
  for (const line of lines) {
    const type = lineType(line);
    const last = groups.at(-1);
    if (type !== 'p' && last?.type === type) last.lines.push(line);
    else groups.push({ type, lines: [line] });
  }
  return groups.map(({ type: Tag, lines: group }, i) => Tag === 'p'
    ? <p key={i}>{group[0]}</p>
    : <Tag key={i}>{group.map((line, j) => <li key={j}>{line.replace(Tag === 'ol' ? ORDERED : BULLET, '')}</li>)}</Tag>
  );
}
