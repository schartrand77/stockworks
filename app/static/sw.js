const CACHE_NAME = "stockworks-shell-v2";
const CORE_ASSETS = [
  "/login",
  "/static/styles.css",
  "/static/app.js",
  "/manifest.webmanifest",
  "/public/favicon.png",
];
const STATIC_DESTINATIONS = new Set(["style", "script", "image", "font", "worker"]);
const STATIC_PREFIXES = ["/static/", "/public/", "/favicon", "/apple-touch-icon"];
const OFFLINE_FALLBACK = "/login";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then(precacheCoreAssets)
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(handleNavigation(request));
    return;
  }

  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;
  if (!sameOrigin || !shouldCache(request, url)) {
    return;
  }

  event.respondWith(cacheFirst(request));
});

function shouldCache(request, url) {
  if (CORE_ASSETS.includes(url.pathname)) {
    return true;
  }
  if (STATIC_DESTINATIONS.has(request.destination)) {
    return true;
  }
  return STATIC_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}

async function handleNavigation(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    const fallback = await caches.match(OFFLINE_FALLBACK);
    if (fallback) {
      return fallback;
    }
    throw error;
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }

  const response = await fetch(request);
  if (response && response.status === 200 && response.type !== "opaque" && response.type !== "opaqueredirect") {
    cache.put(request, response.clone());
  }
  return response;
}

async function precacheCoreAssets(cache) {
  for (const asset of CORE_ASSETS) {
    try {
      await cache.add(asset);
    } catch (error) {
      console.warn(`[SW] Failed to precache ${asset}:`, error);
    }
  }
}
