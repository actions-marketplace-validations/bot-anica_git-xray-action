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
| **Price** | $0 | **$9/month per org** |

### Get a License

1. **Purchase** at [git-xray.lemonsqueezy.com](https://git-xray.lemonsqueezy.com)
2. **Add the key** to your repo → Settings → Secrets → `GIT_XRAY_LICENSE_KEY`
3. **Update your workflow**:

```yaml
      - uses: bot-anica/git-xray-action@v1
        with:
          license-key: ${{ secrets.GIT_XRAY_LICENSE_KEY }}
```

That's it — bus factor and coupling analysis will activate on the next PR.

> Don't have a Lemon Squeezy account? Email **bot.anica.dev@gmail.com** and we'll generate a key for you directly.

---

## Options

```yaml
- uses: bot-anica/git-xray-action@v1
  with:
    # License key for private repos (not needed for public repos)
    license-key: ${{ secrets.GIT_XRAY_LICENSE_KEY }}

    # Max results per analysis section (default: 5)
    top: 5

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
