# burnerator.com

Landing page of **Burnerator**, a forge for ideas and open-source projects. A group of friends
playing with new technologies, the geek way. AI-assisted. AI for dummies.

Live at <https://www.burnerator.com> (GitHub Pages, branch `main`, root).

## Stack

Plain HTML + CSS + a tiny vanilla JS file for the EN/ES toggle. No build step, no frameworks,
no third-party scripts, fonts or trackers. Works without JavaScript (English).

## Security

- Strict Content-Security-Policy (`default-src 'none'`, no inline code, no external origins).
- No cookies or analytics; language preference is kept in `localStorage` only.
- Gates: `scripts/check.sh` (site tests: CSP, no inline code, no third-party resources,
  i18n completeness, links, a11y basics) and `scripts/check_secrets.sh` (gitleaks over the full
  history, no `.env`, only GitHub noreply emails). Both run in the `pre-push` hook (on the exact
  commit pushed, in a clean worktree) and in CI. `main` is protected: PR + green CI.

## Contributing

```bash
git config core.hooksPath .githooks
git config user.email "<id>+<login>@users.noreply.github.com"   # never a personal email
python3 -m http.server 8000                                      # preview at http://localhost:8000
./scripts/check.sh && ./scripts/check_secrets.sh
```

Branch → PR → green CI → squash merge. Translations live in `assets/main.js` (`ES`); English is
the HTML itself. Every `data-i18n` key must exist in both (tested).
