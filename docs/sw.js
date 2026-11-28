"use strict";

// Kendi dosyalarımız ağ öncelikli; sürümü sabit Pyodide dosyaları önbellek öncelikli.
// Denetim bir kez çalıştırıldıktan sonra sayfa internetsiz de kullanılabilir.
const CACHE = "kaynakca-denetcisi-v2";
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const DOSYALAR = ["./", "./index.html", "./app.js", "./crossref.js", "./pages.js", "./pages.css", "./style.css",
  "./manifest.webmanifest", "./ikon.svg", "./ikon-192.png", "./ikon-512.png", "./py/manifest.json"];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(DOSYALAR);
    const adlar = await (await cache.match("./py/manifest.json")).json();
    await cache.addAll(adlar.map(ad => "./py/kaynakca/" + ad));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(key => key.startsWith("kaynakca-denetcisi-") && key !== CACHE)
      .map(key => caches.delete(key))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const istek = event.request;
  if (istek.method !== "GET") return;
  if (istek.url.startsWith(PYODIDE)) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const kayitli = await cache.match(istek.url);
      if (kayitli) return kayitli;
      const yanit = await fetch(istek);
      if (yanit.ok) cache.put(istek.url, yanit.clone()).catch(() => {});
      return yanit;
    })());
    return;
  }
  if (new URL(istek.url).origin !== self.location.origin) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const yanit = await fetch(istek);
      if (yanit.ok) cache.put(istek, yanit.clone()).catch(() => {});
      return yanit;
    } catch {
      return (await cache.match(istek, { ignoreSearch: true })) || Response.error();
    }
  })());
});
