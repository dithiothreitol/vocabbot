/* The service worker of VocabBot's session page: it keeps the page's own files, so the page
 * opens from the home screen at once; every answer still goes to the server (/api is never kept). */
"use strict";
var CACHE = "vocabbot-/*VOCABBOT_VERSION*/";
// only the page's own files: the page of a signed-in account is never kept on the device
var FILES = ["/static/app.js", "/static/geist.woff2", "/static/vocabbot.png", "/static/vocabbot.svg"];
var SHELL = FILES;

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) { return cache.addAll(FILES); }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (names) {
    return Promise.all(names.filter(function (name) { return name.indexOf("vocabbot-") === 0 && name !== CACHE; }).map(function (name) { return caches.delete(name); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  var url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.indexOf("/api/") === 0) return;
  if (SHELL.indexOf(url.pathname) < 0) return;
  // the network first, so a new version and the signed-in state come through; the copy when offline
  event.respondWith(fetch(request).then(function (response) {
    if (response.ok && !response.redirected) {
      var copy = response.clone();
      caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
    }
    return response;
  }).catch(function () {
    return caches.match(request).then(function (found) { return found || Response.error(); });
  }));
});
