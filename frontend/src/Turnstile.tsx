
import { useEffect, useRef, useState } from 'react';

type Widget = {
  render: (node: HTMLElement, options: {
    sitekey: string;
    callback: (token: string) => void;
    'expired-callback': () => void;
    'error-callback': () => void;
  }) => string;
  remove: (id: string) => void;
  reset: (id: string) => void;
};

declare global {
  interface Window { turnstile?: Widget }
}

let script: Promise<void> | undefined;

function loadWidget() {
  if (window.turnstile) return Promise.resolve();
  script ??= new Promise<void>((resolve, reject) => {
    const element = document.createElement('script');
    element.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    element.async = true;
    element.onload = () => resolve();
    element.onerror = () => {
      element.remove();
      script = undefined;
      reject(new Error('No se pudo cargar Turnstile'));
    };
    document.head.append(element);
  });
  return script;
}

export function Turnstile({ siteKey, cycle, onToken }:
  { siteKey: string; cycle: number; onToken: (token: string | undefined) => void }) {
  const anchor = useRef<HTMLDivElement>(null);
  const widget = useRef<string>(undefined);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let disposed = false;
    loadWidget().then(() => {
      if (disposed || !anchor.current) return;
      if (!window.turnstile) throw new Error('Verificación no disponible');
      widget.current = window.turnstile.render(anchor.current, {
        sitekey: siteKey,
        callback: onToken,
        'expired-callback': () => onToken(undefined),
        'error-callback': () => { onToken(undefined); setError(true); },
      });
    }).catch(() => { if (!disposed) setError(true); });
    return () => {
      disposed = true;
      if (widget.current) window.turnstile?.remove(widget.current);
      widget.current = undefined;
    };
  }, [siteKey, onToken, attempt]);

  useEffect(() => {
    if (cycle && widget.current) window.turnstile?.reset(widget.current);
  }, [cycle]);

  return <div className="captcha">
    <div ref={anchor}/>
    {error && <p role="status">No se pudo completar la verificación. <button className="text-button" type="button"
      onClick={() => { setError(false); setAttempt(attempt + 1); }}>Reintentar</button></p>}
  </div>;
}
