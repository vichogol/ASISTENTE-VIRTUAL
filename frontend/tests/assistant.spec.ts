
import { expect, test } from '@playwright/test';

const pool = {
  id: 'piscina', name: 'Piscina Municipal', short_name: 'Piscina Municipal',
  address: 'Ricardo Grellet de los Reyes 2101, Peñalolén',
  latitude: -33.47812, longitude: -70.54212, style: 'pool',
  services: ['Cursos y talleres de piscina'],
  source_url: 'https://tramites.penalolen.cl/Tramites/buscar',
  map_source: 'https://www.openstreetmap.org/way/678461082',
  service: '¿Dónde queda la Piscina Temperada Municipal de Peñalolén?',
};
const townHall = { ...pool, id: 'cav', name: 'Centro de Atención al Vecino', short_name: 'Atención al Vecino',
  latitude: -33.47678, longitude: -70.54261, style: 'civic', address: 'Av. Grecia 8735, Peñalolén', service: null };

test('consulta, fuente, valoración y mapa centrado en el recinto', async ({ page }) => {
  let sessionId: string;
  await page.route('**/api/chat', async (route) => {
    const request = route.request().postDataJSON();
    expect(request.message).toBe('¿Dónde queda la Piscina Municipal?');
    expect(request.session_id).toBeTruthy();
    sessionId = request.session_id;
    await route.fulfill({ json: {
      answer: 'Orientación sobre la Piscina Municipal.',
      intro: 'Aquí puedes encontrar la Piscina Municipal.',
      sections: [{ title: 'Información del trámite', lines: ['Para tu visita:', '1. Confirma la actividad.', '2. Revisa la dirección.'] }],
      sources: [{ id: 3, pregunta: pool.service, hoja: 'Revisdas', direccion: 'Corporación Deportes' }],
      actions: [{ label: 'Ver directorio municipal', url: pool.source_url }, { label: 'Enlace inválido', url: 'javascript:alert(1)' }],
      buildings: [pool], interaction_id: '42',
    } });
  });
  await page.route('**/api/chat/42/feedback', async (route) => {
    expect(route.request().method()).toBe('PUT');
    expect(route.request().postDataJSON()).toEqual({ helpful: true, session_id: sessionId });
    await route.fulfill({ status: 204 });
  });
  await page.route('**/api/buildings', (route) => route.fulfill({ json: [townHall, pool] }));

  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Peñalolén, tu asistente virtual municipal');
  await expect(page.getByRole('banner')).toHaveCSS('background-color', 'rgb(37, 45, 107)');
  await expect(page.locator('.hero-photo')).toHaveJSProperty('complete', true);
  expect(await page.locator('.hero-photo').evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  await page.getByRole('textbox', { name: 'Tu consulta municipal' }).fill('¿Dónde queda la Piscina Municipal?');
  await page.getByRole('button', { name: 'Enviar consulta' }).click();
  await expect(page.getByRole('listitem').filter({ hasText: 'Revisa la dirección.' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Enlace inválido' })).toHaveCount(0);
  await page.getByText('Ver fuente municipal', { exact: true }).click();
  await expect(page.getByText('Base municipal · Revisdas · Ficha 3')).toBeVisible();
  await page.getByRole('button', { name: 'Sí', exact: true }).click();
  await expect(page.getByText('Gracias por tu valoración.')).toBeVisible();
  const open = page.getByRole('button', { name: 'Ver en el mapa 3D' });
  await open.click();
  const map = page.getByRole('dialog', { name: 'Mapa 3D de Peñalolén' });
  await expect(map.getByRole('button', { name: 'Piscina Municipal' })).toHaveAttribute('aria-pressed', 'true');
  await expect(map.getByRole('link', { name: 'Cómo llegar' })).toHaveAttribute('href', /Ricardo%20Grellet/);
  await expect(map.locator('canvas')).toBeVisible();
  await expect(map.locator('.geo-marker[data-selected=true]')).toHaveCount(1);
  await map.getByRole('button', { name: 'Girar a la derecha' }).click();
  await map.getByRole('button', { name: 'Acercar' }).click();
  await map.getByRole('button', { name: 'Atención al Vecino' }).click();
  await expect(map.getByRole('heading', { name: townHall.name })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(map).toHaveCount(0);
  await expect(open).toBeFocused();
  await open.click();
  await map.getByRole('button', { name: 'Cursos y talleres de piscina' }).click();
  await expect(map).toHaveCount(0);
  await expect(page.getByRole('textbox', { name: 'Tu consulta municipal' })).toHaveValue(/cursos y talleres de piscina/);
});

test('acceso móvil, movimiento reducido, error temporal y derivación', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  let attempts = 0;
  await page.route('**/api/chat', async (route) => {
    attempts++;
    if (attempts === 1) return route.fulfill({ status: 503 });
    await route.fulfill({ json: {
      answer: 'La oficina puede revisar tu caso.',
      referral: {
        unit: 'OIRS municipal', phone: '+56 2 2486 8000', address: townHall.address,
        email: 'oirsdigital@penalolen.cl', url: townHall.source_url, source_url: townHall.source_url,
      },
    } });
  });

  await page.goto('/');
  await expect(page.locator('.avatar-orbit .message-avatar')).toHaveCSS('animation-name', 'none');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
  await page.getByRole('button', { name: 'Licencia de conducir' }).click();
  await expect(page.getByText(/No pude conectarme/)).toBeVisible();
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Dónde pueden ayudarte' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'oirsdigital@penalolen.cl' })).toHaveAttribute('href', 'mailto:oirsdigital@penalolen.cl');
  await expect(page.getByRole('button', { name: 'Enviar consulta' })).toBeDisabled();
  expect(attempts).toBe(2);
});

test('el navegador consulta la API real y envía feedback', async ({ page }) => {
  test.skip(process.env.RUN_LIVE_API !== '1', 'Requiere Uvicorn en el puerto 8000');
  await page.goto('/');
  await page.getByRole('button', { name: 'Licencia de conducir' }).click();
  await expect(page.getByText(/agendar una hora a través del sitio web oficial/i)).toBeVisible();
  await page.getByRole('button', { name: 'Sí', exact: true }).click();
  await expect(page.getByText('Gracias por tu valoración.')).toBeVisible();
  await page.getByRole('button', { name: 'Ver en el mapa 3D' }).click();
  await expect(page.getByRole('dialog').getByRole('heading', { name: 'Centro de Atención al Vecino' })).toBeVisible();
});


test('saluda, aclara un tema general y responde al elegir una consulta', async ({ page }) => {
  test.skip(process.env.RUN_LIVE_API !== '1', 'Requiere Uvicorn en el puerto 8000');
  await page.goto('/');
  const input = page.getByRole('textbox', { name: 'Tu consulta municipal' });
  await input.fill('Hola');
  await input.press('Enter');
  await expect(page.getByText('¡Hola! Soy Peñalolín. ¿En qué te puedo ayudar hoy?')).toBeVisible();
  await expect(page.getByRole('list', { name: 'Consultas sugeridas' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Dónde pueden ayudarte' })).toHaveCount(0);

  await input.fill('piscina');
  await input.press('Enter');
  await page.getByRole('button', { name: 'Ver horarios de la piscina' }).click();
  await expect(page.getByText(/Horario continuado/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ver en el mapa 3D' })).toBeVisible();
});
