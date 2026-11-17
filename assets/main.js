// Burnerator landing page: EN/ES toggle. Progressive enhancement only — the page is
// complete without JavaScript (English). Text is set with textContent (never innerHTML).
(function () {
  "use strict";

  var ES = {
    "skip": "Saltar al contenido",
    "nav.what": "Qué",
    "nav.projects": "Proyectos",
    "nav.how": "Cómo",
    "nav.join": "Únete",
    "term.l1": "calentando la forja...",
    "term.l2": "amigos conectados: unos cuantos",
    "term.l3": "asistentes de IA: listos (los humanos siguen al mando)",
    "term.l4": "nivel de curiosidad: peligrosamente alto",
    "hero.kicker": "// una forja de ideas y open source",
    "hero.title": "Calentamos ideas hasta que se convierten en proyectos.",
    "hero.lead1": "Burnerator es un grupo de amigos que experimenta con nuevas tecnologías, en plan geek. Construimos en abierto, con la IA como compañera, y lo contamos para que cualquiera pueda seguirlo:",
    "hero.lead2": "IA para dummies",
    "hero.lead3": ", sin necesidad de doctorado.",
    "hero.cta1": "Explóralo en GitHub",
    "hero.cta2": "Mira qué hay en la forja",
    "what.title": "Qué pasa en la forja",
    "what.c1.t": "Ideas, a golpe de martillo",
    "what.c1.p": "Cada “¿y si...?” loco tiene su oportunidad. Prototipamos rápido, nos quedamos con lo que funciona y aprendemos de lo que se funde.",
    "what.c2.t": "Open source por defecto",
    "what.c2.p": "El código, los experimentos y los benchmarks son públicos. Haz un fork, experimenta y mejóralos.",
    "what.c3.t": "IA para dummies",
    "what.c3.p": "Probamos herramientas de IA con problemas reales y te contamos, en palabras sencillas, qué hacen, cuánto cuestan y dónde fallan.",
    "projects.title": "Sobre el yunque",
    "projects.anvil": "Nuestro banco de trabajo: las herramientas con las que forjamos cada proyecto, con tests, escaneo de secretos y un revisor de IA independiente en cada cambio. Lo primero sobre el yunque: el mismo modelo en la nube de NVIDIA frente a un portátil con Ollama.",
    "projects.next.t": "Tu idea aquí",
    "projects.next.p": "El próximo proyecto empieza con una conversación. Trae la tuya.",
    "projects.next.tag": "pronto",
    "how.title": "Cómo trabajamos",
    "how.s1.t": "Primero, jugar",
    "how.s1.p": "Elegimos una tecnología nueva y brillante y la toqueteamos hasta que tiene sentido.",
    "how.s2.t": "Con ayuda de IA, liderado por personas",
    "how.s2.p": "La IA escribe, revisa y sugiere. Las personas deciden, prueban y dan el visto bueno. Probamos cada cambio y buscamos revisiones independientes.",
    "how.s3.t": "Seguro desde el diseño",
    "how.s3.p": "Nada de secretos en repos públicos, nada de rastreadores en esta web, y medimos antes de fiarnos.",
    "how.s4.t": "Explicarlo fácil",
    "how.s4.p": "Si no podemos explicárselo a un amigo con un café, es que aún no lo entendemos.",
    "join.title": "Acércate al fuego",
    "join.p": "Curioso, principiante o geek veterano: todos bienvenidos. Abre un issue, manda un pull request o simplemente ven a ver las chispas.",
    "join.cta": "github.com/Burnerator",
    "join.mascot": "La mascota de Burnerator: un pequeño robot herrero muy simpático, con ojos de brasa y un martillo",
    "foot.p": "hecho con curiosidad, café y un poco de IA",
    "foot.privacy": "El código de esta web no usa cookies, analítica ni rastreadores. Tu elección de idioma se guarda en tu navegador. Alojada en GitHub Pages, que puede registrar datos técnicos como la dirección IP."
  };

  var nodes = document.querySelectorAll("[data-i18n]");
  var alts = document.querySelectorAll("[data-i18n-alt]");
  var EN = {};
  nodes.forEach(function (el) { EN[el.getAttribute("data-i18n")] = el.textContent; });
  alts.forEach(function (el) { EN[el.getAttribute("data-i18n-alt")] = el.getAttribute("alt"); });

  var btn = document.getElementById("lang-toggle");
  var meta = {
    en: { title: document.title, label: "Cambiar a español", next: "ES", nextLang: "es" },
    es: { title: "Burnerator · una forja de ideas y open source", label: "Switch to English", next: "EN", nextLang: "en" }
  };

  function apply(lang) {
    var dict = lang === "es" ? ES : EN;
    nodes.forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (Object.prototype.hasOwnProperty.call(dict, key)) el.textContent = dict[key];
    });
    alts.forEach(function (el) {
      var key = el.getAttribute("data-i18n-alt");
      if (Object.prototype.hasOwnProperty.call(dict, key)) el.setAttribute("alt", dict[key]);
    });
    document.documentElement.lang = lang;
    document.title = meta[lang].title;
    btn.textContent = meta[lang].next;
    btn.setAttribute("aria-label", meta[lang].label);
    btn.setAttribute("lang", meta[lang].nextLang);
    btn.dataset.lang = lang;
  }

  function stored() {
    try { return window.localStorage.getItem("lang"); } catch (e) { return null; }
  }
  function store(lang) {
    try { window.localStorage.setItem("lang", lang); } catch (e) { /* private mode */ }
  }

  function valid(lang) { return lang === "en" || lang === "es"; }
  var saved = stored();
  var initial = valid(saved) ? saved :
    ((navigator.language || "").toLowerCase().indexOf("es") === 0 ? "es" : "en");

  btn.hidden = false;
  btn.addEventListener("click", function () {
    var next = btn.dataset.lang === "es" ? "en" : "es";
    apply(next);
    store(next);
  });
  apply(initial);

  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());
})();
