#!/usr/bin/env python3
"""Static blog builder for burnerator.com ("The blacksmith's logbook").

Sources:  content/posts/<YYYY-MM-DD-slug>/en.md (required) and es.md (optional).
Outputs:  blog/index.html, blog/<slug>/index.html, blog/<slug>/es/index.html,
          blog/feed.xml (Atom, English), sitemap.xml.
Outputs are committed (GitHub Pages serves them as-is, no build step there).

  .venv/bin/python scripts/build.py           # (re)generate
  .venv/bin/python scripts/build.py --check   # fail if committed output is stale (CI)

Security: raw HTML in Markdown is escaped (markdown-it html=False); images must be local;
links must be https, site-relative or anchors; external links get rel="noopener";
every page carries a strict CSP; front matter is HTML-escaped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "content" / "posts"
SITE = "https://www.burnerator.com"
LANGS = ("en", "es")
SLUG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
REQUIRED = ("title", "date", "summary")

CSP_STATIC = ("default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; "
              "form-action 'none'")
CSP_SCRIPT = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
              "base-uri 'none'; form-action 'none'")

UI = {
    "en": {"logbook": "The blacksmith's logbook", "read": "min read", "back": "All articles",
           "home": "Home", "says": "The blacksmith says", "other": "Leer en español",
           "published": "Published", "tags": "Tags"},
    "es": {"logbook": "El cuaderno del herrero", "read": "min de lectura",
           "back": "Todos los artículos", "home": "Inicio", "says": "El herrero dice",
           "other": "Read in English", "published": "Publicado", "tags": "Etiquetas"},
}


class BuildError(Exception):
    pass


@dataclass
class Post:
    slug: str
    lang: str
    meta: dict
    body_md: str
    html: str = ""
    words: int = 0
    langs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def date(self) -> dt.date:
        return dt.date.fromisoformat(self.meta["date"])

    @property
    def url(self) -> str:
        return f"/blog/{self.slug}/" + ("" if self.lang == "en" else f"{self.lang}/")

    @property
    def minutes(self) -> int:
        return max(1, round(self.words / 200))


# ---------------------------------------------------------------- markdown

def _md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": True})
    md.enable("table")

    def link_open(self, tokens, idx, options, env):
        tok = tokens[idx]
        href = tok.attrGet("href") or ""
        _check_href(href, env)
        if href.startswith("https://"):
            tok.attrSet("rel", "noopener")
        return self.renderToken(tokens, idx, options, env)

    def image(self, tokens, idx, options, env):
        tok = tokens[idx]
        src = tok.attrGet("src") or ""
        if re.match(r"^([a-z][a-z0-9+.-]*:|//)", src, re.I):
            raise BuildError(f"{env['where']}: only local images are allowed: {src}")
        tok.attrSet("loading", "lazy")
        return self.image(tokens, idx, options, env)

    md.add_render_rule("link_open", link_open)
    md.add_render_rule("image", image)
    return md


def _check_href(href: str, env: dict) -> None:
    if href.startswith(("https://", "/", "#")) and not href.startswith("//"):
        return
    # relative links only to the post's own data files (copied next to the page)
    if re.fullmatch(r"(\.\./)?[a-z0-9-]+\.json", href):
        return
    raise BuildError(f"{env['where']}: link must be https, site-relative or #anchor: {href}")


def parse_front_matter(text: str, where: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise BuildError(f"{where}: missing front matter")
    try:
        head, body = text[4:].split("\n---\n", 1)
    except ValueError:
        raise BuildError(f"{where}: unterminated front matter") from None
    meta = {}
    for line in head.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise BuildError(f"{where}: bad front matter line: {line!r}")
        meta[key.strip()] = value.strip()
    for k in REQUIRED:
        if not meta.get(k):
            raise BuildError(f"{where}: front matter needs '{k}'")
    dt.date.fromisoformat(meta["date"])
    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    return meta, body


def load_posts() -> list[Post]:
    posts: list[Post] = []
    if not POSTS.exists():
        return posts
    md = _md()
    for d in sorted(POSTS.iterdir()):
        if not d.is_dir():
            continue
        if not SLUG_RE.match(d.name):
            raise BuildError(f"bad post folder name: {d.name} (YYYY-MM-DD-slug)")
        if not (d / "en.md").exists():
            raise BuildError(f"{d.name}: en.md is required")
        langs = tuple(lang for lang in LANGS if (d / f"{lang}.md").exists())
        for lang in langs:
            where = f"{d.name}/{lang}.md"
            meta, body = parse_front_matter((d / f"{lang}.md").read_text(encoding="utf-8"), where)
            p = Post(d.name, lang, meta, body, langs=langs)
            p.html = md.render(body, {"where": where})
            p.words = len(re.findall(r"\w+", body))
            posts.append(p)
    return posts


# ---------------------------------------------------------------- templates

def e(s: str) -> str:
    return html.escape(s, quote=True)


def shell(*, lang: str, title: str, description: str, canonical: str, body: str,
          scripts: bool = False, alternates: dict[str, str] | None = None,
          title_es: str | None = None) -> str:
    alt = "".join(
        f'\n  <link rel="alternate" hreflang="{code}" href="{SITE}{href}">'
        for code, href in (alternates or {}).items()
    )
    script = '\n  <script src="/assets/main.js" defer></script>' if scripts else ""
    title_es = f' data-title-es="{e(title_es)}"' if title_es else ""
    return f"""<!doctype html>
<html lang="{lang}"{title_es}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{CSP_SCRIPT if scripts else CSP_STATIC}">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:url" content="{SITE}{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:image" content="{SITE}/assets/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="{SITE}{canonical}">{alt}
  <link rel="alternate" type="application/atom+xml" title="Burnerator blog" href="/blog/feed.xml">
  <link rel="icon" href="/assets/img/favicon-32.png" type="image/png" sizes="32x32">
  <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
  <link rel="stylesheet" href="/assets/style.css">{script}
</head>
<body>
  <a class="skip" href="#main" data-i18n="skip">{"Skip to content" if lang == "en" else "Saltar al contenido"}</a>
  <header class="top">
    <a class="brand" href="/">
      <img src="/assets/img/favicon-64.png" alt="" width="32" height="32">
      <span>burnerator</span>
    </a>
    <nav>
      <a href="/#what" data-i18n="nav.what">{"What" if lang == "en" else "Qué"}</a>
      <a href="/#projects" data-i18n="nav.projects">{"Projects" if lang == "en" else "Proyectos"}</a>
      <a href="/blog/" aria-current="page" data-i18n="nav.blog">Blog</a>
      <a href="/#join" data-i18n="nav.join">{"Join" if lang == "en" else "Únete"}</a>
    </nav>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="foot">
    <p><span class="p">$</span> <span data-i18n="foot.p">{"made with curiosity, coffee and a bit of AI" if lang == "en"
       else "hecho con curiosidad, café y un poco de IA"}</span> · <span>© Burnerator</span></p>
    <p class="small"><a href="/blog/feed.xml">RSS / Atom</a></p>
  </footer>
</body>
</html>
"""


def render_post(p: Post) -> str:
    ui = UI[p.lang]
    m = p.meta
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in m["tags"])
    other = [lang for lang in p.langs if lang != p.lang]
    switch = ""
    if other:
        o = other[0]
        href = f"/blog/{p.slug}/" + ("" if o == "en" else f"{o}/")
        switch = f'<a class="lang-link" href="{href}" hreflang="{o}" lang="{o}">{UI[p.lang]["other"]}</a>'
    says = m.get("mascot_says", "")
    mascot = ""
    if says:
        mascot = f"""
      <aside class="mascot-says" aria-label="{e(ui['says'])}">
        <img class="mascot mascot-sm" src="/assets/img/mascot-240.png" width="96" height="96" alt="">
        <div class="bubble"><strong>{e(ui['says'])}:</strong> {e(says)}</div>
      </aside>"""
    body = f"""    <article class="post">
      <p class="kicker"><a href="/blog/">// {e(ui['logbook'])}</a></p>
      <h1>{e(m['title'])}</h1>
      <p class="post-meta">{e(ui['published'])} <time datetime="{p.date.isoformat()}">{p.date.isoformat()}</time> · {p.minutes} {e(ui['read'])} {switch}</p>
      <div class="post-tags" aria-label="{e(ui['tags'])}">{tags}</div>
      <div class="prose">
{p.html}      </div>{mascot}
      <p class="post-back"><a class="btn" href="/blog/">← {e(ui['back'])}</a></p>
    </article>"""
    alternates = {lang: f"/blog/{p.slug}/" + ("" if lang == "en" else f"{lang}/")
                  for lang in p.langs}
    return shell(lang=p.lang, title=f"{m['title']} · Burnerator", description=m["summary"],
                 canonical=p.url, body=body, alternates=alternates if len(p.langs) > 1 else None)


def render_index(posts: list[Post]) -> str:
    by_slug: dict[str, dict[str, Post]] = {}
    for p in posts:
        by_slug.setdefault(p.slug, {})[p.lang] = p
    items = []
    for slug in sorted(by_slug, reverse=True):
        versions = by_slug[slug]
        en = versions["en"]
        tags = "".join(f'<span class="tag">{e(t)}</span>' for t in en.meta["tags"])
        blocks = []
        for lang, p in versions.items():
            hidden = "" if lang == "en" else " hidden"
            blocks.append(
                f'<div class="post-card-body" data-show-lang="{lang}" lang="{lang}"{hidden}>'
                f'<h2><a href="{p.url}">{e(p.meta["title"])}</a></h2>'
                f'<p>{e(p.meta["summary"])}</p></div>'
            )
        items.append(
            f'      <li class="post-card"><time datetime="{en.date.isoformat()}">'
            f'{en.date.isoformat()}</time>{"".join(blocks)}<div class="post-tags">{tags}</div></li>'
        )
    listing = "\n".join(items) or '      <li class="post-card soon" data-i18n="blog.empty">The first article is cooling on the anvil.</li>'
    body = f"""    <section class="section blog-hero">
      <div class="oops">
        <img class="mascot" src="/assets/img/mascot-240.png" srcset="/assets/img/mascot-240.png 1x, /assets/img/mascot-480.png 2x" width="200" height="200" alt="The Burnerator blacksmith robot, proudly holding its hammer" data-i18n-alt="blog.mascot">
        <div class="bubble">
          <h1 data-i18n="blog.title">The blacksmith's logbook</h1>
          <p class="say" data-i18n="blog.lead">Everything we heat up, hammer and measure: benchmarks, experiments and lessons learned, explained in plain words.</p>
        </div>
      </div>
    </section>
    <section class="section">
      <ul class="posts">
{listing}
      </ul>
    </section>"""
    return shell(lang="en", title="Blog · Burnerator", canonical="/blog/", body=body,
                 title_es="Blog · Burnerator · El cuaderno del herrero",
                 description="Benchmarks, experiments and lessons learned by the Burnerator "
                             "forge: AI explained in plain words.", scripts=True)


def render_feed(posts: list[Post]) -> str:
    en = sorted((p for p in posts if p.lang == "en"), key=lambda p: (p.date, p.slug), reverse=True)
    updated = en[0].date.isoformat() if en else "2026-11-17"
    entries = "".join(f"""
  <entry>
    <title>{xml_escape(p.meta['title'])}</title>
    <link href="{SITE}{p.url}"/>
    <id>{SITE}{p.url}</id>
    <updated>{p.date.isoformat()}T00:00:00Z</updated>
    <summary>{xml_escape(p.meta['summary'])}</summary>
  </entry>""" for p in en)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Burnerator · The blacksmith's logbook</title>
  <link href="{SITE}/blog/"/>
  <link rel="self" href="{SITE}/blog/feed.xml"/>
  <id>{SITE}/blog/</id>
  <updated>{updated}T00:00:00Z</updated>
  <author><name>Burnerator</name></author>{entries}
</feed>
"""


def render_sitemap(posts: list[Post]) -> str:
    latest = max((p.date for p in posts), default=dt.date(2026, 11, 17)).isoformat()
    urls = [("/", latest), ("/blog/", latest)]
    urls += [(p.url, p.date.isoformat()) for p in sorted(posts, key=lambda p: (p.slug, p.lang))]
    body = "".join(f"""
  <url>
    <loc>{SITE}{loc}</loc>
    <lastmod>{mod}</lastmod>
  </url>""" for loc, mod in urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}
</urlset>
"""


# ---------------------------------------------------------------- build

def outputs() -> dict[str, str]:
    posts = load_posts()
    files = {"blog/index.html": render_index(posts), "blog/feed.xml": render_feed(posts),
             "sitemap.xml": render_sitemap(posts)}
    for d in sorted(POSTS.iterdir()) if POSTS.exists() else []:
        for data in sorted(d.glob("*.json")):  # published alongside the article
            import json

            json.loads(data.read_text(encoding="utf-8"))  # must be valid JSON
            files[f"blog/{d.name}/{data.name}"] = data.read_text(encoding="utf-8")
    for p in posts:
        rel = f"blog/{p.slug}/index.html" if p.lang == "en" else f"blog/{p.slug}/{p.lang}/index.html"
        files[rel] = render_post(p)
    return files


def generated_on_disk() -> set[str]:
    blog = ROOT / "blog"
    found = {str(f.relative_to(ROOT)) for f in blog.rglob("*") if f.is_file()} if blog.exists() else set()
    return found | ({"sitemap.xml"} if (ROOT / "sitemap.xml").exists() else set())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if committed output is stale")
    args = ap.parse_args(argv)
    try:
        files = outputs()
    except BuildError as exc:
        print(f"build: {exc}", file=sys.stderr)
        return 1
    if args.check:
        stale = [rel for rel, text in files.items()
                 if not (ROOT / rel).exists() or (ROOT / rel).read_text(encoding="utf-8") != text]
        extra = sorted(generated_on_disk() - set(files))
        if stale or extra:
            print("build: generated files are stale; run scripts/build.py", file=sys.stderr)
            for rel in stale + extra:
                print(f"  {rel}", file=sys.stderr)
            return 1
        print(f"build: OK ({len(files)} generated files up to date)")
        return 0
    for rel in generated_on_disk() - set(files):  # removed posts
        (ROOT / rel).unlink()
    for rel, text in files.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"build: wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
