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
                    if tag == "a" or (tag == "link" and a.get("rel") == "canonical") or (
                        tag == "meta"
                    ):
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
        tags = parse(ROOT / "index.html").tags
        html_keys = {a["data-i18n"] for _, a in tags if "data-i18n" in a}
        html_keys |= {a["data-i18n-alt"] for _, a in tags if "data-i18n-alt" in a}
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
                    if url == "/":
                        target = ROOT / "index.html"
                    elif url.startswith("/"):
                        target = ROOT / url.lstrip("/")  # site-absolute
                    else:
                        target = (page.parent / url).resolve()  # relative to the page
                    self.assertTrue(target.exists(), f"{page.name}: {url}")

    def test_lang_and_metadata(self):
        tags = parse(ROOT / "index.html").tags
        self.assertEqual(tags[0], ("html", {"lang": "en"}))
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
        self.assertIn('lang="es"', html)
        self.assertTrue(all("alt" in a for t, a in c.tags if t == "img"))

    def test_touch_icon(self):
        self.assertEqual(self.png_size(ROOT / "assets" / "apple-touch-icon.png"), (180, 180))

    def test_sitemap_and_robots(self):
        import xml.etree.ElementTree as ET

        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text for e in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
        self.assertEqual(locs, ["https://www.burnerator.com/"])
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


if __name__ == "__main__":
    unittest.main()
