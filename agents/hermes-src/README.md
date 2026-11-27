# Hermes profile souls

`soul.tmpl` renders one `SOUL.md` for each agent definition that has a Hermes prompt at
`agents/prompts/hermes/<name>.md`. A soul is the definition's shared prefix, then that Hermes prompt, then the shared
reply envelope fragment `agents/prompts/shared/clerk-envelope.md`. Every part is static text, so the whole soul can
stay in a model's prompt cache.

## Installation

Run the targets inside the repository dev shell, which provides gomplate, yq and jq: `nix develop`.

## Usage

- `make render-hermes` writes `agents/hermes/<name>.soul.md` and `agents/hermes/manifest.json`.
- `make check-hermes` renders again and fails on any drift, missing file or extra file. `make test` runs it.

The manifest is a sorted list of `{name, path, sha256}`. It also lists `agents/schemas/clerk-envelope.schema.json`, the
JSON Schema that callers use to validate a clerk's reply.

## Consuming the souls

A deployment pins one commit of this repository and the manifest's sha256. It downloads the manifest, checks its
hash, then downloads each listed file and checks that file's hash before it uses it.
