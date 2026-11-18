/* VocabBot's session page: the day's cards, progress and the plan, in a browser.
 *
 * Every step calls /api/<name>, which runs a command of the engine on the
 * learner's account: a question comes without its answer, the engine grades a
 * typed answer, and a change of the plan is a preview saved only after "Zapisz".
 * Every number shown comes from a result of the engine; every text comes from
 * data/i18n/pl.json through the labels in the page. The look follows Vercel's
 * Geist: neutral surfaces, one dark primary action, colour only for meaning.
 */
(function () {
  "use strict";

  var L = JSON.parse(document.getElementById("labels").textContent || "{}");
  var CSRF = meta("vocabbot-csrf");
  var LOGIN = meta("vocabbot-login");
  var VERSION = meta("vocabbot-version");
  var NS = "http://www.w3.org/2000/svg";
  var VOICES = { en: "en-GB", de: "de-DE", es: "es-ES", fr: "fr-FR", it: "it-IT" };
  var LANG_DOTS = { en: "var(--blue-solid)", de: "var(--amber-solid)", es: "var(--red-solid)", fr: "var(--purple-solid)", it: "var(--green-solid)" };
  var GRADE_TONE = { know: "green", known: "green", almost: "amber", dont_know: "red" };
  var GRADE_ICON = { know: "check", known: "check", almost: "approx", dont_know: "x" };
  var PHASE_TONE = { "new": "blue", review: "purple", drill: "amber" };
  var PHASE_ICON = { "new": "sparkles", review: "repeat", drill: "target" };
  var KEYS = { know: "1", almost: "2", dont_know: "3" };
  var WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  var ICONS = {
    check: ["M20 6 9 17l-5-5"],
    x: ["M18 6 6 18", "m6 6 12 12"],
    approx: ["M4 9.5c1.6-1.3 3.2-1.3 4.8 0s3.2 1.3 4.8 0 3.2-1.3 4.8 0", "M4 14.5c1.6-1.3 3.2-1.3 4.8 0s3.2 1.3 4.8 0 3.2-1.3 4.8 0"],
    eye: ["M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-19.88 0", "M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0"],
    play: ["M7 4.5v15l12-7.5z"],
    arrow: ["M5 12h14", "m12 5 7 7-7 7"],
    rotate: ["M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", "M3 3v5h5"],
    pencil: ["M12 20h9", "M16.38 3.62a1 1 0 0 1 3 3L7.37 18.63a2 2 0 0 1-.86.5l-2.87.84a.5.5 0 0 1-.62-.62l.84-2.87a2 2 0 0 1 .5-.86z"],
    archive: ["M3 4h18v4H3z", "M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8", "M10 12h4"],
    languages: ["m5 8 6 6", "m4 14 6-6 2-3", "M2 5h12", "M7 2h1", "m22 22-5-10-5 10", "M14 18h6"],
    calendar: ["M8 2v4", "M16 2v4", "M3 10h18", "M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"],
    flame: ["M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"],
    plus: ["M5 12h14", "M12 5v14"],
    minus: ["M5 12h14"],
    book: ["M12 7v14", "M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"],
    target: ["M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0", "M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0", "M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0"],
    repeat: ["m17 2 4 4-4 4", "M3 11v-1a4 4 0 0 1 4-4h14", "m7 22-4-4 4-4", "M21 13v1a4 4 0 0 1-4 4H3"],
    sparkles: ["M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z", "M19 15v4", "M21 17h-4"],
    activity: ["M22 12h-4l-3 9L9 3l-3 9H2"],
    alert: ["M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0", "M12 8v4", "M12 16h.01"],
    info: ["M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0", "M12 16v-4", "M12 8h.01"],
    wifiOff: ["M12 20h.01", "M8.5 16.43a5 5 0 0 1 7 0", "M2 8.82a15 15 0 0 1 4.17-2.65", "M10.66 5c4.01-.36 8.14.9 11.34 3.76", "M16.85 11.25a10 10 0 0 1 2.22 1.68", "M5 13a10 10 0 0 1 5.24-2.76", "m2 2 20 20"],
    moon: ["M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"],
    chevron: ["m6 9 6 6 6-6"],
    layers: ["M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z", "m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65", "m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"],
    chart: ["M3 3v16a2 2 0 0 0 2 2h16", "M18 17V9", "M13 17V5", "M8 17v-3"],
    sliders: ["M21 4h-7", "M10 4H3", "M21 12h-9", "M8 12H3", "M21 20h-5", "M12 20H3", "M14 2v4", "M8 10v4", "M16 18v4"],
    user: ["M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2", "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0"]
  };
  var root = document.getElementById("view");
  var S = {
    tab: "session", phase: "loading", data: null, item: null, result: null, revealed: null,
    stage: null, view: {}, given: "", busy: false, notice: ""
  };
  var current = null;

  // ---------------------------------------------------------------- small helpers

  function meta(name) {
    var node = document.querySelector('meta[name="' + name + '"]');
    return node ? node.getAttribute("content") || "" : "";
  }
  function fill(value, params) {
    value = String(value);
    Object.keys(params || {}).forEach(function (name) {
      value = value.split("{" + name + "}").join(String(params[name]));
    });
    return value;
  }
  function t(key, params) { return fill((L.app && L.app[key]) || key, params); }
  function c(key, params) { return fill((L.card && L.card[key]) || key, params); }
  function label(group, code) { return (L[group] && L[group][code]) || code || ""; }
  function langName(code) { return (L.languages && L.languages[code]) || String(code || "").toUpperCase(); }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function add(parent) {
    for (var i = 1; i < arguments.length; i++) if (arguments[i]) parent.appendChild(arguments[i]);
    return parent;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function percent(value) { return Math.round(Number(value || 0) * 100) + "%"; }
  // a number of the engine written the Polish way (a decimal comma)
  function number(value) { return typeof value === "number" ? value.toLocaleString("pl-PL") : String(value); }
  function errorText(data) {
    var error = data && data.error;
    if (!error) return t("error_generic", { message: "?" });
    return error.message || t("error_generic", { message: error.code || "?" });
  }

  function icon(name, filled) {
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "icon" + (filled ? " filled" : ""));
    svg.setAttribute("aria-hidden", "true");
    (ICONS[name] || []).forEach(function (d) {
      var path = document.createElementNS(NS, "path");
      path.setAttribute("d", d);
      svg.appendChild(path);
    });
    return svg;
  }
  function kbd(text) { return el("kbd", null, text); }
  function badge(text, tone, opts) {
    opts = opts || {};
    var node = el("span", "badge" + (tone ? " tone-" + tone : "") + (opts.outline ? " outline" : ""));
    if (opts.dot) {
      var dot = el("span", "dot");
      dot.style.setProperty("--dot", opts.dot);
      node.appendChild(dot);
    }
    if (opts.icon) node.appendChild(icon(opts.icon));
    node.appendChild(document.createTextNode(text));
    return node;
  }
  function btn(text, opts) {
    opts = opts || {};
    var node = el("button", "btn " + (opts.variant || "secondary") + (opts.size ? " " + opts.size : "") +
      (opts.block ? " block" : "") + (opts.grow ? " grow" : "") + (opts.cls ? " " + opts.cls : ""));
    node.type = opts.type || "button";
    if (opts.icon) node.appendChild(icon(opts.icon, opts.filled));
    node.appendChild(document.createTextNode(text));
    if (opts.kbd) node.appendChild(kbd(opts.kbd));
    if (opts.onClick) node.addEventListener("click", function (event) {
      event.preventDefault();
      if (!S.busy) opts.onClick();
    });
    return node;
  }
  function iconButton(name, text, onClick, extra) {
    var node = el("button", "icon-btn" + (extra ? " " + extra : ""));
    node.type = "button";
    node.setAttribute("aria-label", text);
    node.title = text;
    node.appendChild(icon(name, name === "play"));
    node.addEventListener("click", onClick);
    return node;
  }
  function segmented(options, value, onChange, cls) {
    var box = el("div", "segmented" + (cls ? " " + cls : ""));
    box.setAttribute("role", "group");
    options.forEach(function (option) {
      var item = el("button");
      item.type = "button";
      item.setAttribute("aria-pressed", option.value === value ? "true" : "false");
      if (option.data) item.setAttribute("data-stage", option.data);
      if (option.icon) item.appendChild(icon(option.icon));
      item.appendChild(document.createTextNode(option.label));
      if (option.count !== undefined) item.appendChild(el("span", "count", option.count));
      item.addEventListener("click", function () {
        if (S.busy) return;
        Array.prototype.forEach.call(box.children, function (other) { other.setAttribute("aria-pressed", "false"); });
        item.setAttribute("aria-pressed", "true");
        box.value = option.value;
        if (onChange) onChange(option.value);
      });
      box.appendChild(item);
    });
    box.value = value;
    return box;
  }
  function chips(options, selected) {
    var box = el("div", "chips");
    options.forEach(function (option) {
      var item = el("button", "chip", option.label);
      item.type = "button";
      item.value = option.value;
      item.setAttribute("aria-pressed", selected.indexOf(option.value) >= 0 ? "true" : "false");
      item.addEventListener("click", function () {
        item.setAttribute("aria-pressed", item.getAttribute("aria-pressed") === "true" ? "false" : "true");
      });
      box.appendChild(item);
    });
    box.selected = function () {
      return Array.prototype.filter.call(box.children, function (n) { return n.getAttribute("aria-pressed") === "true"; })
        .map(function (n) { return n.value; });
    };
    return box;
  }
  function stepper(value, low, high, id) {
    var box = el("div", "stepper");
    var input = el("input");
    input.type = "number";
    input.inputMode = "numeric";
    input.min = String(low);
    input.max = String(high);
    input.value = String(value);
    if (id) input.id = id;
    function step(by) {
      var next = Math.min(high, Math.max(low, (parseInt(input.value, 10) || 0) + by));
      input.value = String(next);
    }
    var less = el("button");
    less.type = "button";
    less.setAttribute("aria-label", "−");
    less.appendChild(icon("minus"));
    less.addEventListener("click", function () { step(-1); });
    var more = el("button");
    more.type = "button";
    more.setAttribute("aria-label", "+");
    more.appendChild(icon("plus"));
    more.addEventListener("click", function () { step(1); });
    add(box, less, input, more);
    box.input = input;
    return box;
  }
  function gauge(fraction, size, stroke, text, tone, target) {
    var box = el("div", "gauge" + (size >= 80 ? " big" : "") + (tone ? " tone-" + tone : ""));
    var radius = (size - stroke) / 2;
    var length = 2 * Math.PI * radius;
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("width", size);
    svg.setAttribute("height", size);
    svg.setAttribute("viewBox", "0 0 " + size + " " + size);
    svg.setAttribute("aria-hidden", "true");
    function circle(cls, dash, offset) {
      var node = document.createElementNS(NS, "circle");
      node.setAttribute("class", cls);
      node.setAttribute("cx", size / 2);
      node.setAttribute("cy", size / 2);
      node.setAttribute("r", radius);
      node.setAttribute("fill", "none");
      node.setAttribute("stroke-width", stroke);
      if (dash) node.setAttribute("stroke-dasharray", dash);
      if (offset !== undefined) node.setAttribute("stroke-dashoffset", offset);
      node.setAttribute("stroke-linecap", "round");
      return node;
    }
    svg.appendChild(circle("track"));
    var value = Math.max(0, Math.min(1, fraction || 0));
    if (value > 0) svg.appendChild(circle("value", length + " " + length, length * (1 - value)));
    if (target !== undefined && target !== null) {
      var mark = circle("target", "1.5 " + length, -length * target + 0.75);
      mark.setAttribute("stroke-linecap", "butt");
      mark.setAttribute("stroke-width", stroke + 4);
      svg.appendChild(mark);
    }
    box.appendChild(svg);
    box.appendChild(el("span", "label", text));
    return box;
  }
  function skeleton(heights) {
    var box = el("div", "stack");
    heights.forEach(function (height) {
      var bar = el("div", "skeleton");
      bar.style.height = height + "px";
      box.appendChild(bar);
    });
    return box;
  }
  function note(tone, iconName, text) {
    var box = el("div", "note" + (tone ? " tone-" + tone : ""));
    box.appendChild(icon(iconName));
    var body = el("div");
    if (typeof text === "string") body.textContent = text; else body.appendChild(text);
    box.appendChild(body);
    return box;
  }
  function toast(text, error) {
    var area = document.getElementById("toasts");
    var item = el("div", "toast" + (error ? " error" : ""));
    item.setAttribute("role", error ? "alert" : "status");
    item.appendChild(icon(error ? "alert" : "check"));
    item.appendChild(el("span", null, text));
    area.appendChild(item);
    setTimeout(function () { item.remove(); }, 4200);
  }
  function offline(on) {
    var box = document.getElementById("offline");
    if (!box.firstChild) {
      box.appendChild(icon("wifiOff"));
      box.appendChild(el("span", null, t("offline")));
    }
    box.hidden = !on;
  }

  function api(method, name, body) {
    var url = "/api/" + name;
    var options = { method: method, credentials: "same-origin", headers: { Accept: "application/json" } };
    if (method === "GET" && body) {
      var query = new URLSearchParams();
      Object.keys(body).forEach(function (key) {
        if (body[key] !== null && body[key] !== undefined && body[key] !== "") query.set(key, body[key]);
      });
      if (query.toString()) url += "?" + query.toString();
    }
    if (method === "POST") {
      options.headers["Content-Type"] = "application/json";
      options.headers["X-CSRF-Token"] = CSRF;
      options.body = JSON.stringify(body || {});
    }
    S.busy = true;
    return fetch(url, options).then(function (response) {
      S.busy = false;
      offline(false);
      if (response.status === 401) {
        location.href = "/app/login?next=" + encodeURIComponent("/app/");
        return new Promise(function () {});
      }
      if (response.status === 403) {
        // the session changed elsewhere (signed in again): the page takes its new form token
        location.reload();
        return new Promise(function () {});
      }
      return response.json().catch(function () {
        return { ok: false, error: { code: String(response.status), message: t("error_generic", { message: response.status }) } };
      });
    }, function () {
      S.busy = false;
      offline(true);
      return { ok: false, offline: true, error: { code: "offline", message: t("offline") } };
    });
  }

  // ---------------------------------------------------------------- sound

  function speechAvailable() {
    return typeof window.speechSynthesis !== "undefined" && typeof window.SpeechSynthesisUtterance !== "undefined";
  }
  function speak(words, lang) {
    if (!speechAvailable() || !words) return;
    var synth = window.speechSynthesis;
    synth.cancel();
    var utterance = new window.SpeechSynthesisUtterance(words);
    utterance.lang = VOICES[lang] || lang || "";
    var wanted = utterance.lang.toLowerCase();
    var voice = synth.getVoices().filter(function (v) { return (v.lang || "").toLowerCase().replace("_", "-") === wanted; })[0];
    if (voice) utterance.voice = voice;
    synth.speak(utterance);
  }
  function play(url, words, lang) {
    if (current) { current.pause(); current = null; }
    if (speechAvailable()) window.speechSynthesis.cancel();
    if (!url) { speak(words, lang); return; }
    var audio = new Audio(url);
    current = audio;
    var fallen = false;
    function fallback() { if (fallen || current !== audio) return; fallen = true; speak(words, lang); }
    audio.onerror = fallback;
    var started = audio.play();
    if (started && started.catch) started.catch(function (error) { if (!error || error.name !== "AbortError") fallback(); });
  }
  function playButton(url, words, lang, sentence) {
    if (!url && !speechAvailable()) return null;
    var text = (sentence ? c("play_sentence") : c("play")) + " · " + (url ? c("recording") : c("synthesis"));
    return iconButton("play", text, function () { play(url, words, lang); }, url ? "" : "synth");
  }

  // ---------------------------------------------------------------- pieces of a card

  function langBadge(code) { return badge(langName(code), null, { dot: LANG_DOTS[code] || "var(--subtle)" }); }
  function phaseBadge(phase) {
    if (!phase) return null;
    var text = phase === "new" ? c("new_word") : label("phases", phase);
    return badge(text, PHASE_TONE[phase] || null, { icon: PHASE_ICON[phase] });
  }
  function head(lang, phase) {
    return add(el("div", "study-head"), langBadge(lang), phaseBadge(phase));
  }
  function formsLine(word) {
    var parts = [];
    if (word.gender) parts.push(label("genders", word.gender));
    Object.keys(word.forms || {}).forEach(function (key) { parts.push(label("forms", key) + " " + word.forms[key]); });
    return parts.length ? el("div", "forms", parts.join(" · ")) : null;
  }
  function wordRow(word, lang) {
    var row = el("div", "word-row");
    row.appendChild(el("h1", "word", word.word));
    if (word.ipa) row.appendChild(el("span", "ipa", word.ipa));
    var sound = playButton(word.audio, word.word, lang, false);
    if (sound) row.appendChild(sound);
    return row;
  }
  function gapped(text) {
    var line = el("p", "text");
    var parts = String(text).split("___");
    parts.forEach(function (part, index) {
      line.appendChild(document.createTextNode(part));
      if (index < parts.length - 1) {
        var gap = el("span", "gap");
        gap.setAttribute("aria-label", "…");
        line.appendChild(gap);
      }
    });
    return line;
  }
  function sentence(text, polish, lang, speakable) {
    if (!text) return null;
    var box = el("div", "sentence");
    if (speakable) {
      var sound = playButton(null, text, lang, true);
      if (sound) box.appendChild(sound);
    }
    var body = el("div");
    body.appendChild(gapped(text));
    if (polish) {
      var translated = el("p", "pl", polish);
      if (S.view.sentence_translation === "hidden") {
        translated.hidden = true;
        var show = el("button", "linkish");
        show.type = "button";
        show.appendChild(icon("languages"));
        show.appendChild(document.createTextNode(c("translation")));
        show.addEventListener("click", function () { translated.hidden = !translated.hidden; });
        body.appendChild(show);
      }
      body.appendChild(translated);
    }
    box.appendChild(body);
    return box;
  }
  function noteBox(word) {
    if (!word || !word.note) return null;
    var text = el("span");
    text.appendChild(el("b", null, c("note") + ": "));
    text.appendChild(document.createTextNode(word.note));
    var box = note(null, "pencil", text);
    box.className += " note-line";
    return box;
  }

  // ---------------------------------------------------------------- the session

  function startSession(stage) {
    S.stage = stage || null;
    S.phase = "loading";
    render();
    return api("GET", "next", { stage: S.stage }).then(onNext);
  }
  function onNext(data) {
    if (data && data.error && data.error.code === "no_account_plan") { showTab("plan"); return; }
    if (!data || data.offline || data.ok === false) {
      S.phase = "failed";
      S.notice = errorText(data);
      render();
      return;
    }
    S.data = data;
    S.view = data.view || S.view;
    S.item = (data.items || [])[0] || null;
    S.result = null;
    S.revealed = null;
    S.given = "";
    if (!S.item) S.phase = "done";
    else if (S.item.phase === "new" && S.item.word) S.phase = "intro";
    else S.phase = "question";
    render();
  }

  function overview(data) {
    var done = data.done || {}, left = data.left || {};
    var finished = (done.reviews || 0) + (done["new"] || 0);
    var total = finished + (left.reviews || 0) + (left["new"] || 0);
    var fraction = total ? finished / total : 0;
    var box = el("div", "overview");
    box.appendChild(gauge(fraction, 46, 5, total ? Math.round(100 * fraction) + "%" : "–", fraction >= 1 ? "green" : null));
    var text = el("div");
    text.appendChild(el("div", "title", t("today_title")));
    var sub = data.counter || "";
    if (typeof data.minutes === "number" && data.minutes > 0) sub += " · " + c("minutes", { minutes: data.minutes });
    text.appendChild(el("div", "sub", sub));
    box.appendChild(text);
    var wrap = el("div");
    wrap.appendChild(box);
    var stages = segmented(["reviews", "new", "drill"].map(function (stage) {
      return { value: stage, label: c("stage_" + stage), count: left[stage] || 0, data: stage };
    }), data.stage, function (stage) { startSession(stage); }, "stages");
    stages.setAttribute("aria-label", t("stages_label"));
    wrap.appendChild(stages);
    return wrap;
  }

  function questionCard(item) {
    var q = item.question || {};
    var card = el("article", "card study raised");
    card.appendChild(head(item.lang, item.phase));
    if (q.ask === "meaning") {
      card.appendChild(el("h1", "prompt", q.word));
      var shown = sentence(q.sentence, null, item.lang, false);
      if (shown) card.appendChild(shown);
      var actions = el("div", "answer");
      actions.appendChild(btn(t("show_meaning"), { variant: "primary", size: "lg", block: true, icon: "eye", kbd: "↵", onClick: function () { reveal(item.card); } }));
      card.appendChild(actions);
      return card;
    }
    card.appendChild(el("h1", "prompt", q.meaning));
    var about = el("div", "meta");
    if (q.pos) about.appendChild(el("span", null, label("pos", q.pos)));
    if (q.with_article) about.appendChild(badge(c("with_article"), null, { outline: true }));
    if (q.hint) about.appendChild(el("span", null, q.hint));
    card.appendChild(about);
    var gap = sentence(q.sentence, q.sentence_pl, item.lang, false);
    if (gap) card.appendChild(gap);
    var form = el("form", "answer");
    form.autocomplete = "off";
    var field = el("div", "answer-field");
    var input = el("input", "input");
    input.type = "text";
    input.id = "answer";
    input.lang = item.lang;
    input.setAttribute("autocapitalize", "none");
    input.setAttribute("autocorrect", "off");
    input.setAttribute("enterkeyhint", "done");
    input.spellcheck = false;
    input.maxLength = 200;
    input.placeholder = t("answer_placeholder");
    input.setAttribute("aria-label", t("answer_label"));
    add(field, input, kbd("↵"));
    form.appendChild(field);
    var row = el("div", "actions");
    row.appendChild(btn(t("check"), { variant: "primary", type: "submit", grow: true }));
    if (S.view.answer_mode === "self") row.appendChild(btn(t("show"), { icon: "eye", grow: true, onClick: function () { reveal(item.card); } }));
    row.appendChild(btn(t("dont_know"), { variant: "ghost", grow: true, onClick: function () { answer(item.card, ""); } }));
    form.appendChild(row);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!S.busy) answer(item.card, input.value);
    });
    card.appendChild(form);
    return card;
  }

  function introCard(item) {
    var card = el("article", "card study raised");
    card.appendChild(head(item.lang, "new"));
    card.appendChild(wordRow(item.word, item.lang));
    add(card, formsLine(item.word));
    card.appendChild(el("p", "meaning", item.word.meaning));
    var example = sentence(item.word.example, item.word.example_pl, item.lang, true);
    if (example) card.appendChild(example);
    var actions = el("div", "answer");
    actions.appendChild(btn(t("learn_button"), { variant: "primary", size: "lg", block: true, kbd: "↵", onClick: function () { S.phase = "question"; render(); } }));
    actions.appendChild(btn(t("known_button"), { block: true, icon: "check", onClick: function () { grade(item.card, "known"); } }));
    card.appendChild(actions);
    return card;
  }

  function gradeTiles(card, grades) {
    var box = el("div", "grades");
    box.style.setProperty("--count", String(grades.length));
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", t("grade_label"));
    grades.forEach(function (code) {
      var tile = el("button", "grade-tile tone-" + GRADE_TONE[code]);
      tile.type = "button";
      var disc = el("span", "disc");
      disc.appendChild(icon(GRADE_ICON[code]));
      add(tile, disc, el("span", "name", label("grades", code)), kbd(KEYS[code]));
      tile.addEventListener("click", function () { if (!S.busy) grade(card, code); });
      box.appendChild(tile);
    });
    return box;
  }

  function revealCard(data) {
    var card = el("article", "card study raised");
    card.appendChild(head(data.lang || String(data.card).slice(0, 2), data.phase));
    card.appendChild(wordRow(data.word, data.lang));
    add(card, formsLine(data.word));
    card.appendChild(el("p", "meaning", data.word.meaning));
    var example = sentence(data.word.example, data.word.example_pl, data.lang, true);
    if (example) card.appendChild(example);
    add(card, noteBox(data.word));
    var grades = data.grades && data.grades.length ? data.grades : ["know", "almost", "dont_know"];
    card.appendChild(gradeTiles(data.card, grades));
    return card;
  }

  function verdict(result) {
    var tone = GRADE_TONE[result.grade] || "blue";
    var box = el("div", "verdict tone-" + tone);
    var disc = el("span", "disc");
    disc.appendChild(icon(GRADE_ICON[result.grade] || "info"));
    var text = el("div");
    text.appendChild(el("span", "what", result.grade_pl || label("grades", result.grade)));
    if (result.errors_pl && result.errors_pl.length) text.appendChild(el("span", "why", " · " + result.errors_pl.join(", ")));
    add(box, disc, text);
    if (result.back) {
      var back = el("span", "back");
      back.appendChild(icon("calendar"));
      back.appendChild(document.createTextNode(result.back));
      box.appendChild(back);
    }
    return box;
  }

  function resultCard(result) {
    var card = el("article", "card study raised");
    card.appendChild(verdict(result));
    if (result.word) {
      card.appendChild(wordRow(result.word, result.lang));
      add(card, formsLine(result.word));
      card.appendChild(el("p", "meaning", result.word.meaning));
      var example = sentence(result.word.example, result.word.example_pl, result.lang, true);
      if (example) card.appendChild(example);
    }
    if (S.given && result.grade !== "know" && result.grade !== "known") {
      var given = el("div", "given");
      given.appendChild(el("span", null, t("you_typed")));
      given.appendChild(el("del", null, S.given));
      if (result.word) {
        given.appendChild(icon("arrow"));
        given.appendChild(el("ins", null, result.word.word));
      }
      card.appendChild(given);
    }
    if (result.other_lang) card.appendChild(note("blue", "info", t("other_lang", { lang: langName(result.other_lang) })));
    add(card, noteBox(result.word));
    if (result.level_hint) {
      var hint = note("blue", "sparkles", c("level_hint", result.level_hint));
      hint.style.marginTop = "14px";
      card.appendChild(hint);
    }
    var actions = el("div", "answer");
    actions.appendChild(btn(t("next"), { variant: "primary", size: "lg", block: true, kbd: "↵", onClick: nextCard }));
    card.appendChild(actions);
    var tools = el("div", "toolrow");
    var menu = el("div", "menu");
    menu.hidden = true;
    if (result.grade !== "known") {
      var choices = result.kind === "drill" ? ["know", "dont_know"] : ["know", "almost", "dont_know"];
      choices.filter(function (code) { return code !== result.grade; }).forEach(function (code) {
        var choice = btn(label("grades", code), { size: "sm", icon: GRADE_ICON[code], onClick: function () { regrade(result.card, code); } });
        choice.classList.add("tone-" + GRADE_TONE[code]);
        menu.appendChild(choice);
      });
      tools.appendChild(btn(t("regrade"), { variant: "ghost", size: "sm", icon: "rotate", onClick: function () { menu.hidden = !menu.hidden; } }));
    }
    tools.appendChild(btn(result.word && result.word.note ? t("note_edit") : t("note_add"), { variant: "ghost", size: "sm", icon: "pencil", onClick: function () { noteForm(card, result); } }));
    tools.appendChild(btn(t("skip"), { variant: "ghost", size: "sm", icon: "archive", onClick: function () { skip(result.card); } }));
    card.appendChild(tools);
    card.appendChild(menu);
    return card;
  }

  function noteForm(card, result) {
    if (card.querySelector("form.note-form")) return;
    var form = el("form", "answer note-form");
    var area = el("textarea", "input");
    area.maxLength = 500;
    area.placeholder = t("note_placeholder");
    area.value = (result.word && result.word.note) || "";
    form.appendChild(area);
    var row = el("div", "actions");
    row.appendChild(btn(t("note_save"), { variant: "primary", type: "submit", grow: true }));
    if (result.word && result.word.note) row.appendChild(btn(t("note_remove"), { variant: "ghost", onClick: function () { saveNote(result, null); } }));
    form.appendChild(row);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (area.value.trim()) saveNote(result, area.value.trim());
    });
    card.appendChild(form);
    area.focus();
  }

  function doneCards(data) {
    var box = el("div", "stack");
    var left = data.left || {};
    var nothing = !left.reviews && !left["new"] && !left.drill;
    var card = el("article", "card empty raised tone-green");
    var disc = el("div", "disc");
    disc.appendChild(icon(data.off && nothing ? "moon" : "check"));
    card.appendChild(disc);
    card.appendChild(el("h2", null, data.off && nothing ? c("off") : c("done")));
    var lead = data.stage_empty && !nothing ? t("stage_empty", { stage: c("stage_" + data.stage_empty) }) : (data.counter || "");
    card.appendChild(el("p", "muted", lead));
    var more = data.more || {};
    var actions = el("div", "actions");
    if (more["new"] > 0) {
      var count = Math.min(5, more["new"]);
      actions.appendChild(btn(t("more_new", { count: count }), { variant: "primary", icon: "sparkles", onClick: function () { addMore(count, 0); } }));
    }
    var reviews = (more.reviews_due || 0) + (more.reviews_ahead || 0);
    if (reviews > 0) {
      var round = Math.min(10, reviews);
      actions.appendChild(btn(t("more_reviews", { count: round }), { icon: "repeat", onClick: function () { addMore(0, round); } }));
    }
    if (actions.firstChild) card.appendChild(actions);
    box.appendChild(card);
    var list = el("div");
    box.appendChild(list);
    api("GET", "today").then(function (today) { learnedToday(list, today); });
    return box;
  }

  function learnedToday(box, data) {
    var words = (data && data.learned_today) || [];
    if (!words.length) return;
    var card = el("section", "card");
    var title = el("div", "card-title");
    title.appendChild(el("h3", null, c("learned_today", { count: words.length })));
    card.appendChild(title);
    var list = el("ul", "rows");
    words.forEach(function (item) {
      var row = el("li");
      row.appendChild(langBadge(item.lang));
      var main = el("div", "main");
      main.appendChild(el("b", null, item.word));
      main.appendChild(el("span", null, item.meaning));
      row.appendChild(main);
      if (item.known) row.appendChild(badge(c("known"), "green"));
      var sound = playButton(item.audio, item.word, item.lang, false);
      if (sound) row.appendChild(sound);
      list.appendChild(row);
    });
    card.appendChild(list);
    box.appendChild(card);
  }

  function failedCard() {
    var card = el("article", "card empty tone-red");
    var disc = el("div", "disc");
    disc.appendChild(icon("alert"));
    card.appendChild(disc);
    card.appendChild(el("h2", null, t("failed_title")));
    card.appendChild(el("p", "muted", S.notice || t("offline")));
    card.appendChild(add(el("div", "actions"), btn(t("retry"), { variant: "primary", icon: "rotate", onClick: function () { startSession(S.stage); } })));
    return card;
  }

  // ---------------------------------------------------------------- steps of the session

  function afterGraded(data, typed) {
    if (!data || data.offline) { S.notice = errorText(data); S.phase = "failed"; render(); return; }
    var result = Array.isArray(data.results) ? data.results[0] : data;
    if (!result || result.error || (data.ok === false && !result.grade)) {
      toast(errorText(result && result.error ? result : data), true);
      startSession(S.stage);
      return;
    }
    S.result = result;
    S.given = typed || "";
    if (data.next) S.data = data.next;
    S.phase = "result";
    render();
  }
  function answer(card, given) {
    api("POST", "answer", { card: card, answer: given }).then(function (data) { afterGraded(data, given); });
  }
  function grade(card, code) {
    api("POST", "grade", { card: card, grade: code }).then(function (data) { afterGraded(data, ""); });
  }
  function reveal(card) {
    api("POST", "reveal", { card: card }).then(function (data) {
      if (!data || data.ok === false || !data.word) { toast(errorText(data), true); return; }
      S.revealed = data;
      S.view = data.view || S.view;
      S.phase = "reveal";
      render();
    });
  }
  function regrade(card, code) {
    api("POST", "regrade", { card: card, grade: code }).then(function (data) {
      if (!data || data.ok === false) { toast(errorText(data), true); return; }
      S.result.grade = code;
      S.result.grade_pl = label("grades", code);
      S.result.errors_pl = [];
      delete S.result.back;
      toast(t("regraded", { grade: label("grades", code) }));
      api("GET", "next", { stage: S.stage }).then(function (fresh) {
        if (fresh && fresh.ok !== false) S.data = fresh;
        render();
      });
    });
  }
  function saveNote(result, text) {
    var body = text === null ? { card: result.card, clear: true } : { card: result.card, note: text };
    api("POST", "note", body).then(function (data) {
      if (!data || data.ok === false) { toast(errorText(data), true); return; }
      result.word = result.word || {};
      if (text === null) delete result.word.note; else result.word.note = data.note;
      toast(t(text === null ? "note_removed" : "note_saved"));
      render();
    });
  }
  function skip(card) {
    api("POST", "flag", { card: card, skip: true }).then(function (data) {
      if (!data || data.ok === false) { toast(errorText(data), true); return; }
      toast(t("skipped"));
      startSession(S.stage);
    });
  }
  function addMore(count, reviews) {
    api("POST", "more", { count: count, reviews: reviews }).then(function (data) {
      if (!data || data.ok === false || !data.next) { toast(errorText(data), true); return; }
      S.stage = reviews ? "reviews" : "new";
      onNext(data.next);
    });
  }
  function nextCard() { onNext(S.data); }

  // ---------------------------------------------------------------- progress

  function kpi(iconName, title, value, sub) {
    var card = el("div", "card kpi");
    var k = el("div", "k");
    add(k, icon(iconName), document.createTextNode(title));
    add(card, k, el("div", "v", value), sub ? el("div", "s", sub) : null);
    return card;
  }

  function heatmap(activity) {
    var card = el("section", "card");
    var title = el("div", "card-title");
    add(title, icon("activity"), el("h3", null, t("activity_title")), el("span", "spacer"), el("span", "subtle tiny", t("activity_sub")));
    card.appendChild(title);
    var grid = el("div", "heat");
    var days = activity || [];
    var counts = days.map(function (d) { return d.answers || 0; }).filter(function (n) { return n > 0; }).sort(function (a, b) { return a - b; });
    function level(n) {
      if (!n) return 0;
      var rank = counts.indexOf(n) / Math.max(1, counts.length - 1);
      return rank < 0.25 ? 1 : rank < 0.5 ? 2 : rank < 0.8 ? 3 : 4;
    }
    if (days.length) {
      var first = new Date(days[0].day + "T12:00:00");
      var pad = (first.getDay() + 6) % 7;
      for (var i = 0; i < pad; i++) grid.appendChild(el("i", "pad"));
    }
    days.forEach(function (day) {
      var cell = el("i");
      cell.setAttribute("data-l", String(level(day.answers)));
      cell.title = t("answers_on", { day: day.day.slice(8, 10) + "." + day.day.slice(5, 7), count: day.answers });
      grid.appendChild(cell);
    });
    card.appendChild(grid);
    var legend = el("div", "legend");
    legend.appendChild(el("span", null, t("less")));
    ["--heat-0", "--heat-1", "--heat-2", "--heat-3", "--heat-4"].forEach(function (name) {
      var swatch = el("i");
      swatch.style.background = "var(" + name + ")";
      legend.appendChild(swatch);
    });
    legend.appendChild(el("span", null, t("more")));
    card.appendChild(legend);
    return card;
  }

  function languageCard(code, info, target) {
    var card = el("section", "card");
    var title = el("div", "card-title");
    var dot = el("span", "badge");
    dot.style.padding = "0";
    dot.style.background = "transparent";
    var d = el("span", "dot");
    d.style.setProperty("--dot", LANG_DOTS[code] || "var(--subtle)");
    dot.appendChild(d);
    add(title, dot, el("h3", null, langName(code)));
    var levels = Object.keys(info.levels || {}).filter(function (level) { return level !== "own"; });
    if (levels.length) title.appendChild(badge(levels.map(function (l) { return l.toUpperCase(); }).join("–").replace(/–.*–/, "–"), null, { outline: true }));
    if (info.paused) title.appendChild(badge(t("paused"), "amber"));
    card.appendChild(title);
    var top = el("div", "lang-top");
    var measured = info.retention_30;
    var hasValue = measured !== null && measured !== undefined;
    var tone = !hasValue ? null : measured >= target - 0.02 ? "green" : measured >= target - 0.1 ? "amber" : "red";
    var ring = gauge(hasValue ? measured : 0, 84, 8, hasValue ? percent(measured) : "–", tone, target);
    ring.title = t("retention_title", { target: percent(target) });
    top.appendChild(ring);
    var facts = el("div", "facts");
    [["facts_words", info.cards], ["facts_week", info.due_week], ["facts_reviews", info.reviews_30], ["facts_lapses", info.lapses]].forEach(function (pair) {
      var line = el("div");
      add(line, document.createTextNode(t(pair[0]) + ": "), el("b", null, pair[1]));
      facts.appendChild(line);
    });
    facts.appendChild(el("div", "subtle tiny", t("retention_title", { target: percent(target) })));
    top.appendChild(facts);
    card.appendChild(top);
    Object.keys(info.levels || {}).forEach(function (level) {
      var counts = info.levels[level];
      var row = el("div", "level");
      row.appendChild(el("span", "name", level === "own" ? t("own_words") : level.toUpperCase()));
      var meter = el("div", "meter");
      var bar = el("div");
      bar.style.width = counts.total ? Math.max(counts.learned ? 2 : 0, Math.round(100 * counts.learned / counts.total)) + "%" : "0";
      meter.style.setProperty("--meter", LANG_DOTS[code] || "var(--fg)");
      meter.appendChild(bar);
      row.appendChild(meter);
      row.appendChild(el("span", "num", counts.learned + " / " + counts.total));
      card.appendChild(row);
    });
    var errors = info.errors_30_pl || {};
    var names = Object.keys(errors);
    if (names.length) {
      card.appendChild(el("hr", "divider"));
      card.appendChild(add(el("div", "card-title"), el("h3", null, t("errors_title"))));
      var most = Math.max.apply(null, names.map(function (n) { return errors[n]; }));
      var bars = el("div", "bars");
      names.slice(0, 5).forEach(function (name) {
        var row = el("div", "bar-row");
        row.appendChild(el("span", "muted", name));
        var meter = el("div", "meter");
        meter.style.setProperty("--meter", "var(--red-solid)");
        var bar = el("div");
        bar.style.width = Math.round(100 * errors[name] / most) + "%";
        meter.appendChild(bar);
        add(row, meter, el("span", "num", errors[name]));
        bars.appendChild(row);
      });
      card.appendChild(bars);
    }
    // a hard word waiting in today's session keeps its answer back until its question
    var leeches = (info.leeches || []).filter(function (leech) { return !leech.waiting_today; });
    if (leeches.length) {
      card.appendChild(el("hr", "divider"));
      card.appendChild(add(el("div", "card-title"), el("h3", null, t("leeches"))));
      var list = el("ul", "rows");
      leeches.slice(0, 5).forEach(function (leech) {
        var row = el("li");
        var main = el("div", "main");
        add(main, el("b", null, leech.word), el("span", null, leech.meaning));
        add(row, main, badge(t("lapses", { count: leech.lapses }), "red"));
        list.appendChild(row);
      });
      card.appendChild(list);
    }
    return card;
  }

  function forecastCard(forecast) {
    var card = el("section", "card");
    var title = el("div", "card-title");
    add(title, icon("calendar"), el("h3", null, t("forecast_title")));
    card.appendChild(title);
    card.appendChild(el("p", "muted small", t("forecast_avg", { reviews: number(forecast.average_reviews), minutes: number(forecast.average_minutes), peak: number(forecast.peak_reviews) })));
    var days = forecast.days || [];
    var peak = Math.max.apply(null, days.map(function (day) { return (day.reviews || 0) + (day["new"] || 0); }).concat([1]));
    var chart = el("div", "chart");
    chart.style.setProperty("--n", String(days.length || 1));
    days.forEach(function (day, index) {
      var col = el("div", "col" + (index === 0 ? " today" : ""));
      var stack = el("div", "stackbar" + (day.off ? " off" : ""));
      stack.title = day.day + " · " + (day.off ? t("day_off_short") : t("forecast_row", { reviews: day.reviews, "new": day["new"], minutes: day.minutes }));
      if (!day.off) {
        var reviews = el("div", "r");
        reviews.style.height = (100 * (day.reviews || 0) / peak) + "%";
        var fresh = el("div", "n");
        fresh.style.height = (100 * (day["new"] || 0) / peak) + "%";
        add(stack, reviews, fresh);
      }
      var date = new Date(day.day + "T12:00:00");
      col.appendChild(stack);
      col.appendChild(el("span", "day", label("weekdays_short", WEEKDAYS[(date.getDay() + 6) % 7])));
      chart.appendChild(col);
    });
    card.appendChild(chart);
    var legend = el("div", "chart-legend");
    [["var(--purple-solid)", t("legend_reviews")], ["var(--blue-solid)", t("legend_new")]].forEach(function (pair) {
      var item = el("span");
      var swatch = el("i");
      swatch.style.background = pair[0];
      add(item, swatch, document.createTextNode(pair[1]));
      legend.appendChild(item);
    });
    card.appendChild(legend);
    var complete = forecast.levels_complete || {};
    var lines = [];
    Object.keys(complete).forEach(function (code) {
      Object.keys(complete[code]).forEach(function (level) { lines.push([code, level, complete[code][level]]); });
    });
    if (lines.length) {
      card.appendChild(el("hr", "divider"));
      var list = el("ul", "rows");
      lines.forEach(function (line) {
        var row = el("li");
        row.appendChild(langBadge(line[0]));
        var main = el("div", "main");
        add(main, el("b", null, t("level_complete_short", { level: line[1].toUpperCase() })), el("span", null, line[2]));
        row.appendChild(main);
        list.appendChild(row);
      });
      card.appendChild(list);
    }
    return card;
  }

  function showProgress() {
    clear(root);
    root.appendChild(skeleton([92, 140, 260]));
    Promise.all([api("GET", "status"), api("GET", "forecast", { days: 14 })]).then(function (both) {
      var status = both[0], forecast = both[1];
      if (S.tab !== "progress") return;
      clear(root);
      if (!status || status.ok === false) {
        if (status && status.error && status.error.code === "no_account_plan") { showTab("plan"); return; }
        root.appendChild(note("red", "alert", errorText(status)));
        return;
      }
      var box = el("div", "stack");
      var codes = Object.keys(status.languages || {});
      var words = codes.reduce(function (sum, code) { return sum + (status.languages[code].cards || 0); }, 0);
      var week = codes.reduce(function (sum, code) { return sum + (status.languages[code].due_week || 0); }, 0);
      var answers = (status.activity || []).reduce(function (sum, day) { return sum + (day.answers || 0); }, 0);
      var kpis = el("div", "kpis");
      add(kpis,
        kpi("book", t("kpi_words"), words),
        kpi("flame", t("kpi_streak"), status.streak_days || 0),
        kpi("repeat", t("kpi_week"), week),
        kpi("activity", t("kpi_answers"), answers));
      box.appendChild(kpis);
      box.appendChild(heatmap(status.activity));
      codes.forEach(function (code) { box.appendChild(languageCard(code, status.languages[code], Number(status.target_retention || 0.9))); });
      if (forecast && forecast.ok !== false) box.appendChild(forecastCard(forecast));
      var aside = (status.skipped || []).concat(status.reported || []);
      if (aside.length) {
        var card = el("section", "card");
        card.appendChild(add(el("div", "card-title"), icon("archive"), el("h3", null, t("skipped_title"))));
        var list = el("ul", "rows");
        aside.slice(0, 30).forEach(function (word) {
          var row = el("li");
          row.appendChild(langBadge(word.lang || String(word.card).slice(0, 2)));
          var main = el("div", "main");
          add(main, el("b", null, word.word), el("span", null, word.meaning || ""));
          row.appendChild(main);
          row.appendChild(btn(t("restore"), { size: "sm", onClick: function () {
            api("POST", "flag", { card: word.card, clear: true }).then(function () { toast(t("restored")); showProgress(); });
          } }));
          list.appendChild(row);
        });
        card.appendChild(list);
        box.appendChild(card);
      }
      root.appendChild(box);
    });
  }

  // ---------------------------------------------------------------- the plan and the setup

  function previewCard(data, onSaved) {
    var card = el("section", "card raised");
    if (!data || data.ok === false) {
      card.appendChild(note("red", "alert", errorText(data)));
      return card;
    }
    card.appendChild(add(el("div", "card-title"), icon("eye"), el("h3", null, t("preview_title"))));
    var list = el("ul", "preview-list");
    (data.preview || []).forEach(function (line) { list.appendChild(el("li", null, line)); });
    card.appendChild(list);
    var actions = el("div", "actions");
    actions.style.marginTop = "16px";
    actions.appendChild(btn(t("save"), { variant: "primary", grow: true, icon: "check", onClick: function () {
      api("POST", "commit", { token: data.token }).then(function (done) {
        if (!done || done.ok === false) { toast(errorText(done), true); return; }
        toast(t("saved", { summary: done.applied || "" }));
        onSaved();
      });
    } }));
    actions.appendChild(btn(t("cancel"), { variant: "ghost", onClick: function () { card.remove(); } }));
    card.appendChild(actions);
    setTimeout(function () { card.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, 0);
    return card;
  }

  function field(text, control, hint) {
    var box = el("div", "field");
    var name = el(control && control.id ? "label" : "div", "label", text);
    if (control && control.id) name.htmlFor = control.id;
    add(box, name, control, hint ? el("div", "hint", hint) : null);
    return box;
  }
  function dayChips(selected) {
    return chips(WEEKDAYS.map(function (day) { return { value: day, label: label("weekdays_short", day) }; }), selected || []);
  }

  function showPlan() {
    clear(root);
    root.appendChild(skeleton([220, 320]));
    api("GET", "plan").then(function (data) {
      if (S.tab !== "plan") return;
      clear(root);
      if (data && data.error && data.error.code === "no_account_plan") { showSetup(); return; }
      if (!data || data.ok === false) { root.appendChild(note("red", "alert", errorText(data))); return; }
      var plan = data.plan || {};
      var box = el("div", "stack");
      var card = el("section", "card");
      card.appendChild(add(el("div", "card-title"), icon("book"), el("h3", null, t("plan_title"))));
      var list = el("dl", "dl");
      (data.lines || []).forEach(function (line) {
        var at = line.indexOf(": ");
        var row = el("div");
        add(row, el("dt", null, at > 0 ? line.slice(0, at) : line), el("dd", null, at > 0 ? line.slice(at + 2) : ""));
        list.appendChild(row);
      });
      card.appendChild(list);
      box.appendChild(card);
      var form = el("form", "card");
      form.appendChild(add(el("div", "card-title"), icon("pencil"), el("h3", null, t("plan_change"))));
      var perDay = stepper(plan.new_per_day, 0, 100, "new-per-day");
      form.appendChild(field(t("new_per_day"), perDay));
      var off = dayChips(plan.days_off);
      form.appendChild(field(t("days_off"), off));
      var mode = segmented([{ value: "self", label: t("answer_mode_self") }, { value: "type", label: t("answer_mode_type") }], plan.answer_mode);
      form.appendChild(field(t("answer_mode"), mode));
      var translation = segmented([{ value: "hidden", label: t("translation_hidden") }, { value: "shown", label: t("translation_shown") }], plan.sentence_translation);
      form.appendChild(field(t("translation"), translation));
      var advanced = el("input", "input");
      advanced.id = "advanced";
      advanced.placeholder = "retention=0.85";
      advanced.setAttribute("autocapitalize", "none");
      advanced.spellcheck = false;
      form.appendChild(field(t("advanced"), advanced, t("advanced_hint")));
      form.appendChild(btn(t("preview"), { variant: "primary", type: "submit", block: true, icon: "eye" }));
      var holder = el("div");
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var settings = [];
        var value = perDay.input.value;
        if (String(plan.new_per_day) !== value) settings.push("new_per_day=" + value);
        var days = off.selected();
        if (days.join(",") !== (plan.days_off || []).join(",")) settings.push("days_off=" + (days.join(",") || "none"));
        if (mode.value !== plan.answer_mode) settings.push("answer_mode=" + mode.value);
        if (translation.value !== plan.sentence_translation) settings.push("sentence_translation=" + translation.value);
        advanced.value.split(/[\s;]+/).forEach(function (part) { if (part.indexOf("=") > 0) settings.push(part); });
        clear(holder);
        if (!settings.length) { toast(t("no_change")); return; }
        api("POST", "plan", { settings: settings }).then(function (preview) {
          holder.appendChild(previewCard(preview, showPlan));
        });
      });
      box.appendChild(form);
      box.appendChild(holder);
      root.appendChild(box);
    });
  }

  function levelOptions(levels, chosen) {
    var out = [];
    var has = function (level) { return levels.indexOf(level) >= 0; };
    if (has("a1") && has("a2")) out.push(["a1-a2", t("levels_beginner")]);
    if (has("b1") && has("b2")) out.push(["b1-b2", t("levels_intermediate")]);
    if (levels.length > 1) out.push([levels[0] + "-" + levels[levels.length - 1], t("levels_all")]);
    levels.forEach(function (level) { out.push([level, level.toUpperCase()]); });
    if (chosen && !out.some(function (option) { return option[0] === chosen; })) out.push([chosen, chosen.toUpperCase()]);
    return out;
  }
  function select(id, options, value) {
    var node = el("select", "input");
    node.id = id;
    options.forEach(function (option) {
      var item = el("option", null, option[1]);
      item.value = option[0];
      if (option[0] === value) item.selected = true;
      node.appendChild(item);
    });
    return node;
  }

  function showSetup() {
    clear(root);
    root.appendChild(skeleton([420]));
    api("GET", "courses").then(function (courses) {
      if (S.tab !== "plan") return;
      clear(root);
      if (!courses || courses.ok === false) { root.appendChild(note("red", "alert", errorText(courses))); return; }
      var installed = courses.languages || {};
      var chosen = [];
      var settings = {};
      var box = el("div", "stack");
      var form = el("form", "card raised");
      form.appendChild(el("h2", null, t("setup_title")));
      var lead = el("p", "muted small", t("setup_lead"));
      lead.style.margin = "6px 0 18px";
      form.appendChild(lead);
      var picks = el("div", "choices");
      var details = el("div", "stack");
      var testBox = el("div");
      function refresh() {
        clear(details);
        chosen.forEach(function (code) {
          var info = installed[code];
          var codes = Object.keys(info.levels || {});
          var part = el("div", "lang-setting");
          var top = el("div", "head");
          var d = el("span", "badge");
          d.style.padding = "0";
          d.style.background = "transparent";
          var dot = el("span", "dot");
          dot.style.setProperty("--dot", LANG_DOTS[code] || "var(--subtle)");
          d.appendChild(dot);
          add(top, d, document.createTextNode(info.name));
          part.appendChild(top);
          var levels = select("levels-" + code, levelOptions(codes, settings[code].levels), settings[code].levels);
          levels.addEventListener("change", function () { settings[code].levels = levels.value; });
          settings[code].levels = levels.value;
          part.appendChild(field(t("level_label"), levels));
          var weight = segmented([{ value: "1", label: "×1" }, { value: "2", label: "×2" }, { value: "3", label: "×3" }], settings[code].weight, function (value) { settings[code].weight = value; });
          part.appendChild(field(t("weight_label"), weight));
          var test = el("button", "linkish");
          test.type = "button";
          add(test, icon("target"), document.createTextNode(t("test")));
          test.addEventListener("click", function () { placementTest(code, levels, testBox, function (value) { settings[code].levels = value; }); });
          part.appendChild(test);
          details.appendChild(part);
        });
      }
      Object.keys(installed).forEach(function (code) {
        var info = installed[code];
        var choice = el("button", "choice");
        choice.type = "button";
        choice.setAttribute("aria-pressed", "false");
        var name = el("span", "name");
        var dot = el("span", "dot");
        dot.style.setProperty("--dot", LANG_DOTS[code] || "var(--subtle)");
        add(name, dot, document.createTextNode(info.name));
        var counts = Object.keys(info.levels || {}).map(function (level) { return level.toUpperCase() + " " + info.levels[level]; }).join(" · ");
        var tick = el("span", "tick");
        tick.appendChild(icon("check"));
        add(choice, name, el("span", "info", counts), tick);
        choice.addEventListener("click", function () {
          var at = chosen.indexOf(code);
          if (at >= 0) {
            chosen.splice(at, 1);
            choice.setAttribute("aria-pressed", "false");
          } else if (chosen.length >= 3) {
            toast(t("max_three"), true);
            return;
          } else {
            chosen.push(code);
            settings[code] = settings[code] || { levels: "", weight: "1" };
            choice.setAttribute("aria-pressed", "true");
          }
          refresh();
        });
        picks.appendChild(choice);
      });
      form.appendChild(field(t("languages_label"), picks));
      form.appendChild(details);
      form.appendChild(testBox);
      var gapBox = el("div");
      gapBox.style.height = "18px";
      form.appendChild(gapBox);
      var perDay = stepper(15, 0, 100, "setup-new");
      form.appendChild(field(t("new_per_day"), perDay));
      var off = dayChips([]);
      form.appendChild(field(t("days_off"), off));
      form.appendChild(btn(t("create"), { variant: "primary", type: "submit", block: true, size: "lg", icon: "eye" }));
      var holder = el("div");
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (!chosen.length) { toast(t("choose_language"), true); return; }
        var languages = chosen.map(function (code) { return code + ":" + settings[code].levels + ":" + settings[code].weight; });
        var days = off.selected();
        clear(holder);
        api("POST", "setup", {
          languages: languages,
          new_per_day: Number(perDay.input.value || 15),
          settings: ["days_off=" + (days.join(",") || "none")]
        }).then(function (preview) {
          holder.appendChild(previewCard(preview, function () { showTab("session"); }));
        });
      });
      box.appendChild(form);
      box.appendChild(holder);
      root.appendChild(box);
    });
  }

  function placementTest(lang, levelsSelect, box, onLevel) {
    clear(box);
    box.appendChild(skeleton([180]));
    api("GET", "quiz", { lang: lang, levels: "a1-b2", count: 6 }).then(function (data) {
      clear(box);
      if (!data || data.ok === false) { box.appendChild(note("red", "alert", errorText(data))); return; }
      var card = el("section", "card");
      card.style.marginTop = "12px";
      card.appendChild(add(el("div", "card-title"), icon("target"), el("h3", null, t("test_title", { name: langName(lang) }))));
      card.appendChild(el("p", "muted small", t("test_lead")));
      var inputs = [];
      var level = "";
      (data.items || []).forEach(function (item) {
        if (item.level !== level) {
          level = item.level;
          var mark = badge(level.toUpperCase(), null, { outline: true });
          mark.style.marginTop = "10px";
          card.appendChild(mark);
        }
        var q = item.question || {};
        var row = el("div", "quiz-item");
        var about = [label("pos", q.pos)];
        if (q.with_article) about.push(c("with_article"));
        row.appendChild(el("div", null, q.meaning + " (" + about.filter(Boolean).join(", ") + ")"));
        if (q.sentence) row.appendChild(add(el("div", "muted small"), gapped(q.sentence)));
        var input = el("input", "input");
        input.lang = lang;
        input.setAttribute("autocapitalize", "none");
        input.spellcheck = false;
        row.appendChild(input);
        card.appendChild(row);
        inputs.push({ card: item.card, input: input });
      });
      var outcome = el("div", "stack");
      outcome.style.marginTop = "12px";
      card.appendChild(btn(t("test_check"), { variant: "primary", block: true, onClick: function () {
        var answers = inputs.map(function (entry) { return { card: entry.card, answer: entry.input.value }; });
        api("POST", "quiz", { answers: answers }).then(function (checked) {
          clear(outcome);
          if (!checked || checked.ok === false) { outcome.appendChild(note("red", "alert", errorText(checked))); return; }
          Object.keys(checked.levels || {}).forEach(function (code) {
            var info = checked.levels[code];
            var row = el("div", "level");
            row.appendChild(el("span", "name", code.toUpperCase()));
            var meter = el("div", "meter");
            var bar = el("div");
            bar.style.width = percent(info.share);
            meter.style.setProperty("--meter", info.known ? "var(--green-solid)" : "var(--subtle)");
            meter.appendChild(bar);
            add(row, meter, el("span", "num", percent(info.share)));
            outcome.appendChild(row);
          });
          var suggested = checked.suggested_levels;
          if (suggested) {
            outcome.appendChild(note("green", "check", t("test_result", { levels: suggested.toUpperCase() })));
            outcome.appendChild(btn(t("use_level"), { onClick: function () {
              var option = Array.prototype.filter.call(levelsSelect.options, function (o) { return o.value === suggested; })[0];
              if (!option) {
                option = el("option", null, suggested.toUpperCase());
                option.value = suggested;
                levelsSelect.appendChild(option);
              }
              levelsSelect.value = suggested;
              onLevel(suggested);
              clear(box);
              toast(t("level_set", { levels: suggested.toUpperCase() }));
            } }));
          } else {
            outcome.appendChild(note("blue", "info", t("test_none")));
          }
        });
      } }));
      card.appendChild(outcome);
      box.appendChild(card);
    });
  }

  // ---------------------------------------------------------------- the frame

  function render() {
    if (S.tab !== "session") return;
    clear(root);
    if (S.phase === "loading") { root.appendChild(skeleton([46, 40, 320])); return; }
    if (S.phase === "failed") { root.appendChild(failedCard()); return; }
    var data = S.data || {};
    root.appendChild(overview(data));
    if (S.phase === "question") root.appendChild(questionCard(S.item));
    else if (S.phase === "intro") root.appendChild(introCard(S.item));
    else if (S.phase === "reveal") root.appendChild(revealCard(S.revealed));
    else if (S.phase === "result") root.appendChild(resultCard(S.result));
    else root.appendChild(doneCards(data));
    if (S.phase === "question") {
      var helper = el("p", "helper");
      add(helper, kbd("↵"), document.createTextNode(t("keys_check")));
      if (S.view.answer_mode === "self" && S.item && S.item.question && S.item.question.ask !== "meaning") {
        add(helper, document.createTextNode(" · " + t("keys_show")));
      }
      root.appendChild(helper);
    } else if (S.phase === "reveal") {
      var keys = el("p", "helper");
      var shown = S.revealed && S.revealed.grades && S.revealed.grades.length ? S.revealed.grades : ["know", "almost", "dont_know"];
      shown.forEach(function (code) { keys.appendChild(kbd(KEYS[code])); });
      keys.appendChild(document.createTextNode(t("keys_grades")));
      root.appendChild(keys);
    }
    // Enter goes on only where going on is safe: never on a grade or on adding words
    var input = document.getElementById("answer");
    if (input) input.focus({ preventScroll: true });
    else if (S.phase === "result" || S.phase === "intro" || S.phase === "question") {
      var first = root.querySelector(".card .btn.primary");
      if (first) first.focus({ preventScroll: true });
    } else if (document.activeElement && document.activeElement.blur) {
      document.activeElement.blur();
    }
  }

  function showTab(tab) {
    S.tab = tab;
    Array.prototype.forEach.call(document.querySelectorAll("#tabs [data-tab]"), function (node) {
      node.setAttribute("aria-selected", node.getAttribute("data-tab") === tab ? "true" : "false");
    });
    window.scrollTo(0, 0);
    if (tab === "session") startSession(S.stage);
    else if (tab === "progress") showProgress();
    else showPlan();
  }

  function frame() {
    var tabs = document.getElementById("tabs");
    [["session", t("tab_session"), "layers"], ["progress", t("tab_progress"), "chart"], ["plan", t("tab_plan"), "sliders"]].forEach(function (entry) {
      var node = el("button");
      node.type = "button";
      node.setAttribute("data-tab", entry[0]);
      node.setAttribute("role", "tab");
      add(node, icon(entry[2]), el("span", null, entry[1]));
      node.addEventListener("click", function () { if (S.tab !== entry[0] || entry[0] === "session") showTab(entry[0]); });
      tabs.appendChild(node);
    });
    var accountTab = el("a");
    accountTab.href = "/account";
    add(accountTab, icon("user"), el("span", null, t("tab_account")));
    tabs.appendChild(accountTab);
    document.getElementById("who").textContent = LOGIN;
    var avatar = document.getElementById("avatar");
    avatar.textContent = (LOGIN || "?").slice(0, 1).toUpperCase();
    avatar.title = t("tab_account");
    avatar.setAttribute("aria-label", t("tab_account"));
    var foot = document.getElementById("foot");
    foot.appendChild(document.createTextNode("VocabBot " + VERSION + " · "));
    var account = el("a", null, t("tab_account"));
    account.href = "/account";
    foot.appendChild(account);
    foot.appendChild(document.createTextNode(" · "));
    var privacy = el("a", null, t("privacy"));
    privacy.href = "/privacy";
    foot.appendChild(privacy);
  }

  document.addEventListener("keydown", function (event) {
    if (S.tab !== "session" || S.busy || event.ctrlKey || event.metaKey || event.altKey) return;
    var typing = event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName);
    if (S.phase === "reveal" && !typing) {
      var code = { "1": "know", "2": "almost", "3": "dont_know" }[event.key];
      var allowed = S.revealed && S.revealed.grades && S.revealed.grades.length ? S.revealed.grades : ["know", "almost", "dont_know"];
      if (code && S.revealed && allowed.indexOf(code) >= 0) {
        event.preventDefault();
        grade(S.revealed.card, code);
      }
    } else if (event.key === "Enter" && !typing && !(event.target && event.target.tagName === "BUTTON")) {
      if (S.phase === "result") { event.preventDefault(); nextCard(); }
      else if (S.phase === "intro") { event.preventDefault(); S.phase = "question"; render(); }
      else if (S.phase === "question" && S.item && S.item.question && S.item.question.ask === "meaning") {
        event.preventDefault();
        reveal(S.item.card);
      }
    }
  });
  window.addEventListener("offline", function () { offline(true); });
  window.addEventListener("online", function () { offline(false); });
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" }).catch(function () {});
  }
  if (speechAvailable()) window.speechSynthesis.getVoices();
  frame();
  showTab("session");
})();
