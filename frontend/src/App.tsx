
import { lazy, Suspense, useEffect, useRef, useState, type FormEvent } from 'react';
import { getBuildings, RequestError, sendQuestion, type Building, type ChatResponse } from './api.ts';
import { AnswerCard } from './AnswerCard.tsx';
import { Avatar, Icon, type IconName } from './Icons.tsx';
import { BuildingPhoto } from './BuildingPhoto.tsx';
import { Turnstile } from './Turnstile.tsx';
import './App.css';

const MapDialog = lazy(() => import('./MapDialog.tsx').then(({ MapDialog }) => ({ default: MapDialog })));
const FEATURED = {
  name: 'Centro Cultural Chimkowe',
  photo_caption: 'Fachada del Centro Cultural Chimkowe',
  photo_url: '/recintos/chimkowe.jpg',
  photo_source: 'https://commons.wikimedia.org/wiki/File:Centro_Cultural_Chimkowe,_Pe%C3%B1alol%C3%A9n,_Santiago_20260916_03.jpg',
};
const PORTAL = 'https://tramites.penalolen.cl/';
const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY;
const TOPICS: { label: string; question: string; icon: IconName; color: string }[] = [
  { label: 'Licencia de conducir', question: '¿Cómo puedo obtener o renovar mi licencia de conducir?', icon: 'car', color: 'blue' },
  { label: 'Permiso de circulación', question: '¿Cómo pago el permiso de circulación en línea?', icon: 'card', color: 'orange' },
  { label: 'Reciclaje y compostaje', question: '¿Cuáles son los canales de comunicación para preguntas sobre reciclaje en Peñalolén?', icon: 'leaf', color: 'green' },
  { label: 'Registro Social de Hogares', question: '¿Cómo puedo obtener el Registro Social de Hogares (RSH)?', icon: 'home', color: 'violet' },
];
type Turn = { question: string; data?: ChatResponse; error?: string };

function browserSession() {
  const random = Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, '0')).join('');
  try {
    const current = sessionStorage.getItem('penalolen-session');
    if (current) return current;
    sessionStorage.setItem('penalolen-session', random);
  } catch {
    return random;
  }
  return random;
}

export default function App() {
  const [session] = useState(browserSession);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState<string>();
  const [captchaCycle, setCaptchaCycle] = useState(0);
  const [catalog, setCatalog] = useState<Building[]>([]);
  const [catalogError, setCatalogError] = useState(false);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [map, setMap] = useState<{ initial?: Building } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const historyRef = useRef<HTMLDivElement>(null);
  const inFlight = useRef(false);
  const mapOpener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!turns.length || !historyRef.current) return;
    const region = historyRef.current;
    region.scrollTop = region.scrollHeight;
  }, [turns, loading]);

  useEffect(() => {
    if (catalogAttempt === 0) return;
    const controller = new AbortController();
    getBuildings(controller.signal)
      .then((buildings) => { if (!controller.signal.aborted) setCatalog(buildings); })
      .catch(() => { if (!controller.signal.aborted) setCatalogError(true); });
    return () => controller.abort();
  }, [catalogAttempt]);

  function loadCatalog() {
    setCatalogError(false);
    setCatalogAttempt((attempt) => attempt + 1);
  }

  function openMap(initial?: Building) {
    if (!catalog.length) loadCatalog();
    mapOpener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setMap({ initial });
  }

  function closeMap(service?: string) {
    if (service) setInput('Quiero orientación sobre ' + service.toLocaleLowerCase('es-CL') + '.');
    setMap(null);
    requestAnimationFrame(() => {
      if (service) inputRef.current?.focus();
      else mapOpener.current?.focus();
    });
  }

  async function submit(question: string, retry = false) {
    if (!question.trim() || inFlight.current) return;
    if (SITE_KEY && !token) {
      setInput(question);
      inputRef.current?.focus();
      return;
    }
    inFlight.current = true;
    setInput('');
    setLoading(true);
    const pendingTurn = { question: question.trim() };
    setTurns((previous) => retry ? [...previous.slice(0, -1), pendingTurn] : [...previous, pendingTurn]);
    try {
      const data = await sendQuestion(pendingTurn.question, session, token);
      setTurns((previous) => [...previous.slice(0, -1), { ...pendingTurn, data }]);
    } catch (failure) {
      let error = 'No pude conectarme en este momento. Puedes volver a intentar o llamar a la OIRS.';
      if (failure instanceof RequestError && failure.status === 429) {
        error = 'Recibimos varias consultas seguidas. Espera un momento y vuelve a intentar.';
      }
      if (failure instanceof RequestError && failure.status === 400) {
        error = 'La verificación venció o no se pudo completar. Intenta enviar la consulta nuevamente.';
      }
      setTurns((previous) => [...previous.slice(0, -1), { ...pendingTurn, error }]);
    } finally {
      if (SITE_KEY) {
        setToken(undefined);
        setCaptchaCycle((cycle) => cycle + 1);
      }
      inFlight.current = false;
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(input);
  }

  const initial = map?.initial;
  const mapPlaces = initial
    ? [initial, ...catalog.filter((building) => building.id !== initial.id)]
    : catalog;

  return <div className="app-shell">
    <a className="skip-link" href="#chat-title">Ir al chat</a>
    <header className="site-header">
      <div className="container masthead">
        <a className="brand" href="#" aria-label="Inicio del asistente">
          <Avatar className="brand-avatar"/>
          <div><strong>Peñalolín</strong><small>Municipalidad de Peñalolén</small></div>
        </a>
        <nav aria-label="Navegación principal">
          <a className="nav-current" href="#chat-title"><Icon name="chat" size={18}/> Asistente</a>
          <button className="nav-link" onClick={() => openMap()}><Icon name="map" size={18}/> Mapa 3D</button>
        </nav>
        <a className="portal-link" href={PORTAL} target="_blank" rel="noreferrer">Portal de trámites <Icon name="external" size={17}/></a>
      </div>
    </header>

    <main className="container">
      <section className="hero" aria-labelledby="site-title">
        <img className="hero-photo" src={import.meta.env.BASE_URL + 'recintos/consistorial.png'}
          alt="Fachada del Edificio Consistorial de Peñalolén"/>
        <div className="hero-content">
          <div className="hero-rule" aria-hidden="true"/>
          <h1 id="site-title"><span>Peñalolén,</span> tu asistente<br className="hero-break"/> virtual municipal</h1>
          <p>Encuentra orientación sobre trámites, servicios y lugares de atención en tu comuna.</p>
        </div>
      </section>

      <div className="workspace">
        <section className="chat-panel" aria-labelledby="chat-title">
          <header className="chat-heading">
            <Avatar className="chat-logo"/>
            <div><h2 id="chat-title" tabIndex={-1}>Peñalolín</h2>
              <p className="availability"><span aria-hidden="true"/> {loading ? 'Buscando en la base municipal' : 'Disponible para orientarte'}</p>
            </div>
          </header>
          <div className="chat-history" ref={historyRef} role="log" aria-label="Conversación" aria-live="polite">
            <div className="assistant-turn welcome-turn">
              <div className={'avatar-orbit' + (!turns.length ? ' idle' : '')}><Avatar className="message-avatar"/></div>
              <div className="welcome-message">
                <h3>¡Hola! Soy Peñalolín. ¿En qué te puedo ayudar?</h3>
                <p>Escribe tu pregunta o elige uno de los temas de abajo para empezar.</p>
              </div>
            </div>
            {turns.length === 0 && <div className="topics">
              <h3>Consultas frecuentes</h3>
              <div className="topic-grid">{TOPICS.map((topic) => <button key={topic.label} onClick={() => void submit(topic.question)}>
                <span className={'topic-icon ' + topic.color}><Icon name={topic.icon} size={19}/></span>
                <span>{topic.label}</span><Icon name="right" size={16}/>
              </button>)}</div>
            </div>}
            {turns.map((turn, i) => <div className="exchange" key={i}>
              <div className="user-turn"><span className="sr-only">Tu consulta: </span>{turn.question}</div>
              {turn.data && <div className={'assistant-turn replied' + (!loading && i === turns.length - 1 ? ' waiting' : '')}><Avatar className="message-avatar"/>
                <AnswerCard data={turn.data} session={session} onMap={openMap} busy={loading}
                  onQuestion={(question) => void submit(question)}/>
              </div>}
              {turn.error && <div className="answer chat-error" role="status">
                <p>{turn.error} <a href="tel:+56224868000">+56 2 2486 8000</a></p>
                {i === turns.length - 1 && <button className="text-button" onClick={() => void submit(turn.question, true)}>Reintentar</button>}
              </div>}
            </div>)}
            {loading && <div className="assistant-turn thinking" role="status"><Avatar className="message-avatar"/>
              <p><span className="thinking-dots" aria-hidden="true"><i/><i/><i/></span> Estoy buscando información…</p>
            </div>}
          </div>
          <form className="composer" onSubmit={onSubmit}>
            <label className="sr-only" htmlFor="question">Tu consulta municipal</label>
            <div className="composer-row">
              <input id="question" ref={inputRef} value={input} maxLength={1000}
                onChange={(event) => setInput(event.target.value)} placeholder="Escribe tu consulta aquí…" aria-describedby="privacy-note"/>
              <button className="primary-button send" disabled={loading || !input.trim() || Boolean(SITE_KEY && !token)}
                aria-label="Enviar consulta"><Icon name="send" size={20}/><span>Enviar</span></button>
            </div>
            {SITE_KEY && <Turnstile siteKey={SITE_KEY} cycle={captchaCycle} onToken={setToken}/>}
            <p id="privacy-note"><Icon name="info" size={15}/> Evita compartir tu RUT, claves o datos personales.</p>
          </form>
        </section>

        <aside className="sidebar" aria-label="Mapa y atención municipal">
          <section className="map-card" aria-labelledby="explore-title">
            <div className="map-art"><BuildingPhoto building={FEATURED}/></div>
            <div className="map-copy">
              <span className="map-icon" aria-hidden="true"><Icon name="map" size={21}/></span>
              <h2 id="explore-title">Explora Peñalolén</h2>
              <p>Ubica los recintos municipales y descubre qué trámites puedes hacer en cada uno.</p>
              <button className="primary-button" onClick={() => openMap()}>Abrir mapa 3D <Icon name="arrow" size={18}/></button>
            </div>
          </section>
          <section className="help-card" aria-labelledby="contact-title">
            <span className="help-icon" aria-hidden="true"><Icon name="phone" size={20}/></span>
            <div><h2 id="contact-title">Atención vecinal</h2><p>Comunícate con la OIRS municipal.</p>
              <a href="tel:+56224868000">+56 2 2486 8000 <Icon name="arrow" size={15}/></a>
            </div>
          </section>
        </aside>
      </div>
    </main>
    <footer className="site-footer container">
      <span>Municipalidad de Peñalolén</span>
      <a href={PORTAL} target="_blank" rel="noreferrer">Trámites y servicios <Icon name="external" size={14}/></a>
    </footer>
    {map && <Suspense fallback={<p role="status" className="map-loading">Cargando el mapa 3D…</p>}><MapDialog initial={map.initial} buildings={mapPlaces} unavailable={catalogError}
      onRetry={loadCatalog} onClose={() => closeMap()} onService={closeMap}/></Suspense>}
  </div>;
}
