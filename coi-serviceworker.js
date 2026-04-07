/* Adds COOP + COEP + CORP headers via Service Worker so the page becomes
   cross-origin isolated, enabling SharedArrayBuffer (required by ffmpeg.wasm).
   Based on coi-serviceworker by Guido Zuidhof (MIT). */

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  e.respondWith(
    fetch(e.request).then(response => {
      if (response.type === 'opaque') return response;

      const headers = new Headers(response.headers);
      headers.set('Cross-Origin-Opener-Policy', 'same-origin');
      headers.set('Cross-Origin-Embedder-Policy', 'require-corp');
      headers.set('Cross-Origin-Resource-Policy', 'cross-origin');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    }).catch(() => fetch(e.request))
  );
});
