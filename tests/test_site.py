"""Static site checks (stdlib only). Run: python3 -m unittest -v"""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "index.html", ROOT / "404.html"]
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
            self.assertIn("default-src 'none'", csp[0])
            self.assertNotIn("unsafe-inline", csp[0])
            self.assertNotIn("unsafe-eval", csp[0])
            self.assertNotIn("http", csp[0])  # no external origins allowed

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
        css = (ROOT / "assets" / "style.css").read_text()
        self.assertNotRegex(css, r"url\(\s*['\"]?(https?:)?//", "external url() in CSS")
        self.assertNotIn("@import", css)

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
        html_keys = {a["data-i18n"] for _, a in parse(ROOT / "index.html").tags
                     if "data-i18n" in a}
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
                    target = ROOT / url.lstrip("/")
                    if url == "/":
                        target = ROOT / "index.html"
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

    def test_cname(self):
        self.assertEqual((ROOT / "CNAME").read_text().strip(), "www.burnerator.com")
        self.assertTrue((ROOT / ".nojekyll").exists())


if __name__ == "__main__":
    unittest.main()
