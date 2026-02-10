# Git X-Ray Action

Analyze every pull request for deployment risk. Get instant feedback on hotspot files, bus factor warnings, and missing coupled files — before you merge.

## What it does

On every PR, Git X-Ray posts a comment with:

- **Risk Score** (0-100) — overall deployment risk assessment
- **Hotspot Detection** — flags if the PR touches files that change most frequently (where bugs statistically concentrate)
- **Bus Factor Warnings** — alerts when only 1-2 people have ever worked on the code being changed
- **Missing Coupled Files** — detects files that usually change together but weren't included in the PR

## Quick Setup

Add this to `.github/workflows/xray.yml`:

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
          fetch-depth: 0  # Required: full history for analysis

      - uses: bot-anica/git-xray-action@v1
```

That's it. Every PR will now get a risk analysis comment.

## Example Comment

> ## 🟡 Git X-Ray — PR Risk Analysis
>
> | | |
> |---|---|
> | **Risk Level** | 🟡 **MODERATE** (38/100) |
> | **Files Changed** | 5 |
> | **Hotspot Files** | 2 |
> | **Warnings** | 1 |
>
> ### 🔥 Hotspot Files in This PR
>
> | File | Repo Rank | Risk | Churn |
> |------|-----------|------|-------|
> | `src/api/handlers.py` | #1 of 342 | ▓▓▓▓▓▓▓▓░░ | +2,340/-1,892 |
> | `src/core/engine.py` | #3 of 342 | ▓▓▓▓▓░░░░░ | +1,203/-987 |
>
> ### 🔗 Possibly Missing Files
>
> | Missing File | Paired With | Coupling | Co-Commits |
> |-------------|-------------|----------|------------|
> | `src/api/user_handler.py` | `src/models/user.py` | 95% | 38 |

## Options

```yaml
- uses: bot-anica/git-xray-action@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}  # default, usually not needed
    license-key: ${{ secrets.GIT_XRAY_LICENSE_KEY }}  # for private repos
    top: 5  # max results per section (default: 5)
```

## Pricing

**Public repos**: Free, full analysis, forever.

**Private repos**:

| Feature | Free | Pro ($9/mo) |
|---------|------|-------------|
| Risk score | Yes | Yes |
| Hotspot detection | Yes | Yes |
| Bus factor warnings | — | Yes |
| Missing coupled files | — | Yes |

Purchase a license at [git-xray.lemonsqueezy.com](https://git-xray.lemonsqueezy.com) (coming soon).

After purchase, add the key to your repo's secrets as `GIT_XRAY_LICENSE_KEY`.

## Requirements

- `actions/checkout` with `fetch-depth: 0` (the action needs full git history)
- Repository must have at least 20 commits for meaningful analysis

## How it works

Git X-Ray runs a single `git log --numstat` pass over the full repository history. All analysis happens inside the GitHub Actions runner — no code or data is sent to any external service.

The analysis is powered by [git-xray-cli](https://pypi.org/project/git-xray-cli/), an open-source (MIT) git repository analysis engine.

## Links

- [git-xray-cli](https://github.com/bot-anica/git-xray) — the open-source analysis engine (MIT)
- [Report an issue](https://github.com/bot-anica/git-xray-action/issues)
