const CACHE_NAME = "ai-ai-shell-v1";
const APP_SHELL = ["/offline"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(event.request).catch(async () => {
      const cache = await caches.open(CACHE_NAME);
      return (await cache.match(event.request)) ?? cache.match("/offline");
    }),
  );
});

self.addEventListener("push", (event) => {
  const fallbackTitle = "Ай-Яй";
  let data = {};

  try {
    data = event.data?.json() ?? {};
  } catch {
    data = {
      title: fallbackTitle,
      body: event.data?.text() ?? "У вас новое напоминание.",
    };
  }

  const title = data.title || fallbackTitle;
  const options = {
    body: data.body || "У вас новое напоминание.",
    data: {
      url: data.url || "/settings",
    },
    icon: "/icons/icon.svg",
    badge: "/icons/icon.svg",
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      const matchingClient = clientList.find((client) => {
        return "focus" in client && new URL(client.url).pathname === targetUrl;
      });

      if (matchingClient) {
        return matchingClient.focus();
      }

      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }

      return undefined;
    }),
  );
});
