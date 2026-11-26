
import type { ReactNode } from 'react';

const paths = {
  chat: <path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l1.5-3A7.5 7.5 0 1 1 20 11.5Z"/>,
  map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15m6-12v15"/></>,
  arrow: <path d="M4 12h15m-6-6 6 6-6 6"/>,
  external: <path d="M14 4h6v6m0-6-9 9m6-1v7H5V7h7"/>,
  pin: <><path d="M19 10c0 5-7 10-7 10s-7-5-7-10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.2"/></>,
  car: <><path d="m5 10 2-5h10l2 5m1 7H4v-5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2Zm-14 0v2m12-2v2M7 14h1m8 0h1"/></>,
  card: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18m-14 5h4"/></>,
  leaf: <><path d="M5 19c5-7 8-9 12-11M7 16C2 7 14 6 20 4c0 8-2 15-13 12Z"/></>,
  home: <path d="m3 11 9-7 9 7m-2-1v10H5V10m5 10v-6h4v6"/>,
  send: <path d="m3 11 18-7-7 17-3-7-8-3Zm8 3 5-5"/>,
  phone: <path d="M7 3H4c-2 0 0 8 4 12s12 6 12 4v-3l-4-2-2 2a12 12 0 0 1-6-6l2-2-2-5Z"/>,
  close: <path d="m6 6 12 12M18 6 6 18"/>,
  plus: <path d="M6 12h12m-6-6v12"/>,
  minus: <path d="M6 12h12"/>,
  left: <path d="m14 6-6 6 6 6"/>,
  right: <path d="m10 6 6 6-6 6"/>,
  reset: <path d="M4 10a8 8 0 1 1 1 7m-1-7V4m0 6h6"/>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
};

export type IconName = keyof typeof paths;

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  const shape: ReactNode = paths[name];
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{shape}</svg>;
}

export function Avatar({ className = '' }: { className?: string }) {
  return <svg aria-hidden="true" className={className} viewBox="0 0 80 80" fill="none">
    <rect width="80" height="80" rx="22" fill="#222858"/>
    <circle cx="53" cy="26" r="9" fill="#FF8500"/>
    <path d="M14 47 31 21 45 38l7-6 14 16v10H14Z" fill="#9CCAF5"/>
    <path d="m22 35 9-14 9 13-8-4-4 4-3-2z" fill="white"/>
    <path d="M14 48c15-9 36-9 52 0v7a10 10 0 0 1-10 10h-6l-10 7v-7H24a10 10 0 0 1-10-10z" fill="#fff"/>
    <circle cx="30" cy="53" r="2.3" fill="#222858"/>
    <circle cx="50" cy="53" r="2.3" fill="#222858"/>
    <path d="M37 56q3 4 6 0" stroke="#222858" strokeWidth="2" strokeLinecap="round"/>
  </svg>;
}
