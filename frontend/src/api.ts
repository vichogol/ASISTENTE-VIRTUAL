
export type Building = {
  id: string;
  name: string;
  short_name: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  style: string;
  services: string[];
  source_url: string;
  map_source: string | null;
  photo_url?: string | null;
  photo_source?: string | null;
  photo_caption?: string | null;
  service?: string | null;
};

export type Suggestion = { label: string; question: string };
export type Link = { label: string; url: string };
export type Contact = {
  unit: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  url: string;
  source_url: string;
  building: string | null;
};

export type ChatResponse = {
  answer: string;
  intro?: string | null;
  sections: { title: string; lines: string[] }[];
  sources: {
    id?: number | string;
    pregunta?: string;
    direccion?: string;
    hoja?: string;
    categoria?: string;
    revision?: string;
  }[];
  actions: Link[];
  suggestions: Suggestion[];
  referral?: (Contact & { central?: Contact | null }) | null;
  buildings: Building[];
  interaction_id?: string | null;
};

const base = import.meta.env?.VITE_API_URL ?? '';

export class RequestError extends Error {
  readonly status: number;

  constructor(status: number) {
    super('HTTP ' + status);
    this.status = status;
  }
}

export async function sendQuestion(message: string, sessionId: string, token?: string): Promise<ChatResponse> {
  const response = await fetch(base + '/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, turnstile_token: token }),
  });
  if (!response.ok) throw new RequestError(response.status);
  const data: Partial<ChatResponse> = await response.json();
  if (typeof data.answer !== 'string') throw new Error('Respuesta inválida');
  return { ...data, answer: data.answer, sections: data.sections ?? [], sources: data.sources ?? [],
    actions: data.actions ?? [], buildings: data.buildings ?? [], suggestions: data.suggestions ?? [] };
}

export async function getBuildings(signal: AbortSignal): Promise<Building[]> {
  const response = await fetch(base + '/api/buildings', { signal });
  if (!response.ok) throw new RequestError(response.status);
  return response.json();
}

export async function saveFeedback(interaction: string, sessionId: string, helpful: boolean) {
  const response = await fetch(base + '/api/chat/' + encodeURIComponent(interaction) + '/feedback', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, helpful }),
  });
  if (!response.ok) throw new RequestError(response.status);
}

export function safeLink(raw: string): string | undefined {
  try {
    const url = new URL(raw);
    if ((url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password) return url.href;
  } catch {
    return undefined;
  }
}

export function routeTo(building: Building): string {
  return 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(building.address);
}
