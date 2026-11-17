"""Static site checks (stdlib only). Run: python3 -m unittest -v"""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
ALLOWED_LINK_HOSTS = {"github.com", "www.burnerator.com"}


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict]] = []
        self.ids: set[str] = set()
        self.inline_script = False
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "script":
            self._in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script and data.strip():
            self.inline_script = True


def parse(path: Path) -> Collector:
    c = Collector()
    c.feed(path.read_text(encoding="utf-8"))
    return c


class TestSecurity(unittest.TestCase):
    def test_csp_present_and_strict(self):
        for page in PAGES:
            csp = [a.get("content", "") for t, a in parse(page).tags
                   if t == "meta" and a.get("http-equiv", "").lower() == "content-security-policy"]
            self.assertEqual(len(csp), 1, page.name)
            directives = {d.split()[0]: d.split()[1:] for d in csp[0].split(";") if d.strip()}
            self.assertEqual(directives.get("default-src"), ["'none'"])
            self.assertEqual(directives.get("base-uri"), ["'none'"])
            self.assertEqual(directives.get("form-action"), ["'none'"])
            allowed = {"'self'", "'none'", "data:"}
            for name, sources in directives.items():
                self.assertTrue(set(sources) <= allowed, f"{page.name}: {name} {sources}")
            self.assertNotIn("data:", directives.get("script-src", []))

    def test_no_inline_code_or_styles(self):
        for page in PAGES:
            c = parse(page)
            self.assertFalse(c.inline_script, f"inline <script> in {page.name}")
            for tag, a in c.tags:
                self.assertNotIn("style", a, f"inline style on <{tag}> in {page.name}")
                self.assertFalse([k for k in a if k.startswith("on")],
                                 f"inline handler on <{tag}> in {page.name}")
                self.assertNotEqual(tag, "style", f"<style> block in {page.name}")
        js = (ROOT / "assets" / "main.js").read_text()
        self.assertNotRegex(
            js, r"\.(inner|outer)HTML\s*=|insertAdjacentHTML|document\.write|\beval\(|new Function"
        )

    def test_no_third_party_resources(self):
        for page in PAGES:
            for tag, a in parse(page).tags:
                for attr in ("src", "href"):
                    url = a.get(attr, "")
                    if not url.startswith(("http://", "https://", "//")):
                        continue
                    own_link = tag == "link" and a.get("rel") in ("canonical", "alternate")
                    if tag == "a":
                        # navigation links load nothing; they must be https + noopener
                        self.assertTrue(url.startswith("https://"), url)
                        self.assertIn("noopener", a.get("rel", ""), url)
                    elif own_link or tag == "meta":
                        host = re.sub(r"^(https?:)?//", "", url).split("/")[0]
                        self.assertIn(host, ALLOWED_LINK_HOSTS, url)
                        self.assertTrue(url.startswith("https://"), url)
                    else:
                        self.fail(f"external resource <{tag} {attr}={url}> in {page.name}")
        for css_file in sorted(ROOT.rglob("*.css")):
            if ".git" in css_file.parts:
                continue
            css = css_file.read_text()
            self.assertNotRegex(css, r"url\(\s*['\"]?(https?:)?//", f"external url() in {css_file}")
            self.assertNotIn("@import", css, str(css_file))

    def test_external_links_are_noopener(self):
        for tag, a in parse(ROOT / "index.html").tags:
            if tag == "a" and a.get("href", "").startswith("https://"):
                self.assertIn("noopener", a.get("rel", ""), a["href"])

    def test_no_tracking_or_secrets_patterns(self):
        blob = "".join(p.read_text() for p in ROOT.rglob("*") if p.is_file()
                       and ".git" not in p.parts and p.suffix in {".html", ".js", ".css"})
        for bad in ("google-analytics", "gtag(", "googletagmanager", "fonts.googleapis",
                    "facebook.net", "document.cookie", "@gmail.com", "gruposantander"):
            self.assertNotIn(bad, blob)


class TestContent(unittest.TestCase):
    def test_i18n_keys_match_both_languages(self):
        html_keys = set()
        for page in (ROOT / "index.html", ROOT / "blog" / "index.html"):
            tags = parse(page).tags
            html_keys |= {a["data-i18n"] for _, a in tags if "data-i18n" in a}
            html_keys |= {a["data-i18n-alt"] for _, a in tags if "data-i18n-alt" in a}
        # keys only emitted in some states (e.g. empty blog) live in the generator
        html_keys |= set(re.findall(r'data-i18n(?:-alt)?="([a-z0-9.]+)"',
                                    (ROOT / "scripts" / "build.py").read_text()))
        js = (ROOT / "assets" / "main.js").read_text()
        es_block = js[js.index("var ES = {"): js.index("};", js.index("var ES = {"))]
        es_keys = set(re.findall(r'^\s*"([a-z0-9.]+)":', es_block, re.M))
        self.assertEqual(html_keys - es_keys, set(), "keys missing Spanish translation")
        self.assertEqual(es_keys - html_keys, set(), "Spanish keys not used in HTML")

    def test_internal_links_and_assets_exist(self):
        for page in PAGES:
            c = parse(page)
            for tag, a in c.tags:
                for attr in ("href", "src"):
                    url = a.get(attr)
                    if not url or url.startswith(("http", "mailto:")):
                        continue
                    if url.startswith("#"):
                        if page.name == "index.html":
                            self.assertIn(url[1:], c.ids, f"missing anchor {url}")
                        continue
                    path = url.split("#", 1)[0]
                    if path.startswith("/"):
                        target = ROOT / path.lstrip("/")  # site-absolute
                    else:
                        target = (page.parent / path).resolve()  # relative to the page
                    if path.endswith("/") or target.is_dir():
                        target = target / "index.html"
                    self.assertTrue(target.exists(), f"{page.name}: {url}")

    def test_lang_and_metadata(self):
        tags = parse(ROOT / "index.html").tags
        self.assertEqual(tags[0][0], "html")
        self.assertEqual(tags[0][1].get("lang"), "en")
        names = {a.get("name") for t, a in tags if t == "meta"}
        self.assertTrue({"viewport", "description"} <= names)

    def test_images_have_alt(self):
        for page in PAGES:
            for tag, a in parse(page).tags:
                if tag == "img":
                    self.assertIn("alt", a, page.name)

    def test_js_validates_stored_language(self):
        js = (ROOT / "assets" / "main.js").read_text()
        self.assertIn('lang === "en" || lang === "es"', js)

    def test_blinking_stops_within_5s(self):
        css = (ROOT / "assets" / "style.css").read_text()
        m = re.search(r"\.cursor \{[^}]*animation: blink ([0-9.]+)s steps\(1\) (\d+)", css)
        self.assertIsNotNone(m)
        self.assertLess(float(m.group(1)) * int(m.group(2)), 5)

    def test_404_has_heading_and_home_link(self):
        c = parse(ROOT / "404.html")
        self.assertIn("h1", [t for t, _ in c.tags])
        self.assertIn("/", [a.get("href") for t, a in c.tags if t == "a"])

    def test_cname(self):
        self.assertEqual((ROOT / "CNAME").read_text().strip(), "www.burnerator.com")
        self.assertTrue((ROOT / ".nojekyll").exists())


class TestDiscoverability(unittest.TestCase):
    @staticmethod
    def png_size(path: Path) -> tuple[int, int]:
        import struct

        head = path.read_bytes()[:24]
        assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
        return struct.unpack(">II", head[16:24])

    def test_social_card(self):
        metas = {a.get("property") or a.get("name"): a.get("content")
                 for t, a in parse(ROOT / "index.html").tags if t == "meta"}
        self.assertEqual(metas["og:image"], "https://www.burnerator.com/assets/og.png")
        self.assertEqual(metas["twitter:card"], "summary_large_image")
        self.assertTrue(metas.get("og:image:alt"))
        self.assertEqual(self.png_size(ROOT / "assets" / "og.png"), (1200, 630))
        self.assertLess((ROOT / "assets" / "og.png").stat().st_size, 1_000_000)

    def test_brand_images(self):
        for name, size in (("img/favicon-32.png", (32, 32)), ("img/favicon-64.png", (64, 64)),
                           ("img/mascot-240.png", (240, 240)),
                           ("img/mascot-480.png", (480, 480))):
            self.assertEqual(self.png_size(ROOT / "assets" / name), size, name)
            self.assertLess((ROOT / "assets" / name).stat().st_size, 400_000, name)

    def test_404_mascot_speaks_both_languages(self):
        html = (ROOT / "404.html").read_text()
        c = parse(ROOT / "404.html")
        self.assertIn("/assets/img/mascot-240.png", [a.get("src") for t, a in c.tags])
        self.assertTrue(all(a.get("alt") for t, a in c.tags if t == "img"))
        # non-empty message in each language, and a translated way home
        en = re.search(r'<p class="say">([^<]+)</p>', html)
        es = re.search(r'<p class="say-es" lang="es">([^<]+)</p>', html)
        self.assertTrue(en and en.group(1).strip(), "missing English message")
        self.assertTrue(es and es.group(1).strip(), "missing Spanish message")
        home = re.search(r'<a class="btn primary" href="/">(.+?)</a>', html, re.S)
        self.assertTrue(home, "missing home link")
        self.assertRegex(home.group(1), r'Back to the forge.*<span lang="es">[^<]+</span>')

    def test_touch_icon(self):
        self.assertEqual(self.png_size(ROOT / "assets" / "apple-touch-icon.png"), (180, 180))

    def test_sitemap_and_robots(self):
        import xml.etree.ElementTree as ET

        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text for e in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
        self.assertIn("https://www.burnerator.com/", locs)
        self.assertIn("https://www.burnerator.com/blog/", locs)
        posts = sorted((ROOT / "blog").glob("*/index.html"))
        for post in posts:
            self.assertIn(f"https://www.burnerator.com/blog/{post.parent.name}/", locs)
        self.assertTrue(all(loc.startswith("https://www.burnerator.com/") for loc in locs))
        self.assertIn("Sitemap: https://www.burnerator.com/sitemap.xml",
                      (ROOT / "robots.txt").read_text())

    def test_security_txt_valid_and_not_expired(self):
        from datetime import UTC, datetime

        txt = (ROOT / ".well-known" / "security.txt").read_text()
        fields = dict(line.split(": ", 1) for line in txt.splitlines()
                      if line and not line.startswith("#"))
        self.assertEqual(
            fields["Contact"],
            "https://github.com/Burnerator/burnerator.github.io/security/advisories/new",
        )
        self.assertEqual(fields["Canonical"],
                         "https://www.burnerator.com/.well-known/security.txt")
        expires = datetime.fromisoformat(fields["Expires"].replace("Z", "+00:00"))
        days_left = (expires - datetime.now(UTC)).days
        self.assertGreater(days_left, 30, "security.txt expires soon: renew it")
        self.assertLessEqual(days_left, 366, "RFC 9116: Expires should be < 1 year")

    def test_design_sources_not_indexed(self):
        for page in (ROOT / "design").glob("*.html"):
            names = {a.get("name"): a.get("content") for t, a in parse(page).tags if t == "meta"}
            self.assertEqual(names.get("robots"), "noindex", page.name)


class TestBlog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import build  # noqa: F401
        except ModuleNotFoundError as exc:  # markdown-it-py missing
            raise unittest.SkipTest(f"build deps not installed: {exc}") from exc
        cls.build = build

    def test_generated_output_is_up_to_date(self):
        self.assertEqual(self.build.main(["--check"]), 0)

    def test_raw_html_in_markdown_is_escaped(self):
        md = self.build._md()
        out = md.render("<script>alert(1)</script> <img src=x onerror=y>", {"where": "t"})
        self.assertNotIn("<script", out)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;script&gt;", out)

    def test_external_images_and_unsafe_links_rejected(self):
        md = self.build._md()
        for bad in ("![x](https://evil.example/p.png)", "![x](//evil.example/p.png)",
                    "[x](http://plain.example)", "[x](//evil.example)"):
            with self.assertRaises(self.build.BuildError, msg=bad):
                md.render(bad, {"where": "t"})
        # markdown-it itself refuses javascript:/data: URLs (rendered as plain text)
        for dangerous in ("[x](javascript:alert(1))", "[x](data:text/html,hi)"):
            self.assertNotIn("href", md.render(dangerous, {"where": "t"}))
        ok = md.render("[a](https://example.com) [b](/blog/) [c](#x) ![i](/assets/og.png)",
                       {"where": "t"})
        self.assertIn('rel="noopener"', ok)

    def test_front_matter_is_escaped(self):
        meta, body = self.build.parse_front_matter(
            "---\ntitle: <b>x</b>\ndate: 2026-01-01\nsummary: s\n---\nbody", "t")
        p = self.build.Post("2026-01-01-x", "en", meta, body, langs=("en",))
        p.html = ""
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", self.build.render_post(p))

    def test_feed_is_valid_atom(self):
        import xml.etree.ElementTree as ET

        root = ET.parse(ROOT / "blog" / "feed.xml").getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2005/Atom}feed")
        posts = list((ROOT / "blog").glob("*/index.html"))
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        self.assertEqual(len(entries), len(posts))

    def test_translations_link_each_other(self):
        for es in (ROOT / "blog").glob("*/es/index.html"):
            en = es.parent.parent / "index.html"
            for page in (en, es):
                alts = {a.get("hreflang") for t, a in parse(page).tags
                        if t == "link" and a.get("rel") == "alternate" and a.get("hreflang")}
                self.assertEqual(alts, {"en", "es"}, page)
            self.assertEqual(parse(es).tags[0], ("html", {"lang": "es"}))

    def test_results_data_published_and_linked(self):
        import json

        for page in (ROOT / "blog").glob("*/index.html"):
            data = page.parent / "results.json"
            if not data.exists():
                continue
            d = json.loads(data.read_text())
            self.assertTrue(d["prompts"] and d["runs"] and d["harness"]["commit"])
            self.assertRegex(d["harness"]["commit"], r"^[0-9a-f]{40}$")
            hrefs = [a.get("href") for t, a in parse(page).tags if t == "a"]
            self.assertIn("results.json", hrefs)
            text = data.read_text()
            for bad in ("nvapi-", "/Users/", "@gmail", "Bearer "):
                self.assertNotIn(bad, text)

    def test_language_aware_links_and_titles(self):
        js = (ROOT / "assets" / "main.js").read_text()
        self.assertIn("data-href-", js)
        self.assertIn("data-title-es", js)
        home = parse(ROOT / "index.html").tags
        teaser = [a for t, a in home if t == "a" and a.get("data-href-es")]
        for a in teaser:  # language-specific links must point to existing pages
            target = ROOT / a["data-href-es"].lstrip("/") / "index.html"
            self.assertTrue(target.exists(), a["data-href-es"])
        for page in (ROOT / "index.html", ROOT / "blog" / "index.html"):
            self.assertTrue(parse(page).tags[0][1].get("data-title-es"), page)

    def test_front_matter_has_no_draft_flag(self):
        """Narrow guard only: a `draft` key in front matter must never be committed.
        The real control is process: articles enter the repo only after maintainer review."""
        for md in (ROOT / "content" / "posts").glob("*/*.md"):
            head = md.read_text().split("\n---\n", 1)[0]
            self.assertNotRegex(head, r"(?m)^draft\s*:", md)

    def test_preview_script_is_allowlist_and_fails_loudly(self):
        sh = (ROOT / "scripts" / "preview.sh").read_text()
        self.assertNotIn("rsync", sh)
        self.assertNotIn("|| true", sh)
        self.assertIn("for item in index.html", sh)
        self.assertIn("--bind 127.0.0.1", sh)

    def test_every_post_has_the_mascot(self):
        for page in (ROOT / "blog").glob("**/index.html"):
            if page.parent.name == "blog":
                continue
            srcs = [a.get("src") for t, a in parse(page).tags if t == "img"]
            self.assertIn("/assets/img/mascot-240.png", srcs, page)


if __name__ == "__main__":
    unittest.main()
