# Git X-Ray Action

> Know the risk before you merge.

Git X-Ray analyzes every pull request against your full git history and posts a risk report as a PR comment — automatically.

It detects **hotspot files** (where bugs concentrate), **bus factor risks** (knowledge silos), and **missing coupled files** (things you probably forgot to change).

Zero config. No external services. All analysis runs inside your GitHub Actions runner.

---

## Setup (2 minutes)

Create `.github/workflows/xray.yml`:

```yaml
name: Git X-Ray
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: bot-anica/git-xray-action@v1
```

That's it. Open a PR and you'll see the report.

---

## What You Get

Every PR gets a comment like this:

> ## 🟠 Git X-Ray — PR Risk Analysis
>
> | | |
> |---|---|
> | **Risk Level** | 🟠 **HIGH** (52/100) |
> | **Files Changed** | 12 |
> | **Hotspot Files** | 3 |
> | **Warnings** | 2 |
>
> ### 🔥 Hotspot Files in This PR
>
> These files change most frequently in the repo — statistically where bugs concentrate.
>
> | File | Repo Rank | Risk | Churn |
> |------|-----------|------|-------|
> | `src/api/handlers.py` | #1 of 342 | ▓▓▓▓▓▓▓░ | +2,340/-1,892 |
> | `src/core/engine.py` | #3 of 342 | ▓▓▓▓▓░░░ | +1,203/-987 |
> | `src/models/user.py` | #12 of 342 | ▓▓▓░░░░░ | +540/-320 |
>
> ### ⚠️ Bus Factor Warnings
>
> These areas have concentrated knowledge — if key contributors leave, the code becomes risky.
>
> | Area | Risk | Key Contributor |
> |------|------|-----------------|
> | `src/api/` | 🔴 CRITICAL | **dave** (91% of commits) |
>
> ### 🔗 Possibly Missing Files
>
> These files usually change together with files in this PR but weren't included.
>
> | Missing File | Paired With | Coupling | Co-Commits |
> |-------------|-------------|----------|------------|
> | `tests/test_handlers.py` | `src/api/handlers.py` | 87% | 45 |

---

## AI Risk Summary (Pro)

Pro users get a natural-language risk summary on every PR — powered by AI.

> **🧠 AI Risk Summary**
>
> This PR touches `src/api/handlers.py`, the #1 hotspot in the repo with 2,340 lines of churn. Only Dave has worked on `src/api/` (bus factor: 1) — consider getting his review. The test file `tests/test_handlers.py` usually changes with the handler but isn't included here.

The AI API key is included with your Pro license — no extra setup beyond adding the secret (see [Get a License](#get-a-license)).

---

## How It Works

1. Runs `git log --numstat` on the full repo history (single pass, fast)
2. Cross-references changed PR files against historical patterns
3. Calculates a risk score (0–100) based on hotspots, bus factor, and coupling
4. Posts a markdown comment on the PR (updates on subsequent pushes, no spam)

**Privacy**: No code or data leaves your GitHub Actions runner. Ever.

Powered by [git-xray-cli](https://github.com/bot-anica/git-xray), an open-source (MIT) analysis engine.

---

## Pricing

**Public repos** — free, full analysis, forever.

**Private repos** — hotspot detection is free. Unlock the full suite with a license:

| | Free | Pro |
|---|:---:|:---:|
| Risk score (0–100) | ✅ | ✅ |
| Hotspot detection | ✅ | ✅ |
| Bus factor warnings | — | ✅ |
| Missing coupled files | — | ✅ |
| AI risk summary | — | ✅ |
| **Price** | $0 | **$9/month per org** |

### Get a License

1. **[Purchase Git X-Ray Pro](https://checkout.freemius.com/product/24238/plan/40293/)** ($8.99/month or $89.99/year)
2. **Check your email** — you'll receive two keys: `GIT_XRAY_LICENSE_KEY` and `AI_API_KEY`
3. **Add both keys** to your repo → Settings → Secrets and variables → Actions
4. **Update your workflow**:

```yaml
      - uses: bot-anica/git-xray-action@v1
        with:
          license-key: ${{ secrets.GIT_XRAY_LICENSE_KEY }}
          ai-api-key: ${{ secrets.AI_API_KEY }}
```

That's it — full analysis (bus factor, coupling, and AI risk summary) activates on the next PR.

> Questions? Email **support@anica.space**

---

## Options

```yaml
- uses: bot-anica/git-xray-action@v1
  with:
    # License key for private repos (not needed for public repos)
    license-key: ${{ secrets.GIT_XRAY_LICENSE_KEY }}

    # Max results per analysis section (default: 5)
    top: 5

    # AI-powered risk summary (optional — no key = no AI, no error)
    ai-api-key: ${{ secrets.AI_API_KEY }}

    # GitHub token — uses the default token, override only if needed
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

---

## Requirements

- `actions/checkout` with `fetch-depth: 0` (full git history needed)
- At least 20 commits in the repository for meaningful analysis

---

## Links

- [git-xray-cli](https://github.com/bot-anica/git-xray) — the open-source analysis engine (MIT)
- [Report an issue](https://github.com/bot-anica/git-xray-action/issues)
- [Email support](mailto:bot.anica.dev@gmail.com)
