import { useState } from "react";
import "./App.css";

type Source = { id?: number | string; pregunta?: string; direccion?: string };
type Msg = { role: "user" | "assistant"; text: string; sources?: Source[] };

const API = import.meta.env.VITE_API_URL ?? "";

export default function App() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "assistant", text: "Hola, soy el asistente virtual de la Municipalidad de Peñalolén. ¿En qué trámite te puedo ayudar?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMsgs((m) => [...m, { role: "assistant", text: data.answer, sources: data.sources }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "assistant", text: "Ocurrió un error. Intenta nuevamente o contacta a la OIRS (+562 2486 8000)." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Asistente Virtual — Municipalidad de Peñalolén</h1>
      </header>
      <main className="chat">
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">{m.text}</div>
            {m.sources && m.sources.length > 0 && (
              <ul className="sources">
                {m.sources.map((s, j) => (
                  <li key={j}>{s.pregunta} {s.direccion ? `— ${s.direccion}` : ""}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {loading && <div className="msg assistant"><div className="bubble typing">Escribiendo…</div></div>}
      </main>
      <footer className="inputbar">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Escribe tu consulta…"
          disabled={loading}
        />
        <button onClick={send} disabled={loading || !input.trim()}>Enviar</button>
      </footer>
    </div>
  );
}
