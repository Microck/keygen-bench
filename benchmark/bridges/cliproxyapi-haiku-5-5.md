# CLIProxyAPI 7.3.16 with Claude Haiku 5.5

The Anthropic OAuth route (`provider: anthropic_oauth`) reaches Claude through a local
[CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) bridge. The bridge only forwards models in its
model catalog. Claude Haiku 5.5 (`claude-haiku-5-5`) shipped on 2026-10-07, before any CLIProxyAPI release or
the upstream catalog listed it, so requests failed with `unknown provider for model claude-haiku-5-5`. Aliases
(`oauth-model-alias`, per-auth `model_aliases`) only rename models the catalog already knows, so they do not help.

The Haiku runs used CLIProxyAPI v7.3.16 (commit `c404af96`, the same release as the other `anthropic_oauth`
campaigns) rebuilt with one change: the catalog comes from
[router-for-me/models#80](https://github.com/router-for-me/models/pull/80), which adds `claude-haiku-5-5`.
Request handling is unchanged. The catalog is both embedded and tried first on refresh; once that PR merges and
its branch is deleted, refresh falls through to the upstream catalog.

Build (Go 1.26, linux/arm64):

```sh
git clone --depth 1 --branch v7.3.16 https://github.com/router-for-me/CLIProxyAPI.git && cd CLIProxyAPI
curl -fsSL https://raw.githubusercontent.com/tandetat/models/feat/claude-haiku-5-5/models.json \
  -o internal/registry/models/models.json
git apply cliproxyapi-haiku-5-5.diff
CGO_ENABLED=1 go build -buildvcs=false -ldflags="-s -w -X main.Version=7.3.16+haiku55 -X main.Commit=c404af96" \
  -o cli-proxy-api-haiku55 ./cmd/server/
```

The campaigns record this bridge as `CLIProxyAPI 7.3.16+c404af96+haiku55-catalog` with executable SHA-256
`fe039be2082706333b0f754fd93c38afca923702162fe1e0d6ab2dada2bf4d90`; readiness pilots hash the actual executable
(`native_readiness.py --bridge-executable`). A rebuild with different build dates or toolchains gives a
different hash. Remove this note once a CLIProxyAPI release lists Claude Haiku 5.5.
