# Acceptance seed files

A seed file creates tracker records before an acceptance suite runs. Put each file at
`<suite>.yaml` in this directory as a YAML list of steps. A suite without a file needs no seeds.

## Installation

Nothing to install. The loader `agents/judges/acceptance_seed.py` runs in the repository's dev shell.

## Usage

`make acceptance-sets` loads a suite's seed file before each run of that suite. To load one by hand:

```sh
nix develop -c python3 agents/judges/acceptance_seed.py <suite> <run_id>
```

## Seed steps

Each step runs in order and has:

- `method`: `PUT`, `POST`, `GET`, or `DELETE`.
- `path`: an API path; placeholders are allowed.
- `json`: optional request body; placeholders are allowed in nested strings.
- `key`: optional name that saves the response `id` for later steps.

A step that holds only `reset: NAME` deletes every task in the project whose title is in environment
variable `NAME`. It refuses a project whose title does not start with `Acceptance`.

Placeholders:

- `${RUN}`: current run id.
- `${env:NAME}`: non-empty environment variable `NAME`.
- `${project:NAME}`: project id whose title matches environment variable `NAME`.
- `${view:NAME}`: kanban view id for that project.
- `${bucket:NAME:Title}`: bucket id with that title in the project's kanban view.
- `${label:Title}`: matching label id, creating the label when absent. `Title` may use `${RUN}`.
- `${user:NAME}`: user id whose username matches environment variable `NAME`.
- `${id:KEY}`: id saved by an earlier step under `KEY`.
- `${date:+7d}`, `${date:-2d}`, `${date:+3h}`: UTC time offset by days or hours.

A whole-string id placeholder becomes an integer; an id placeholder inside longer text becomes text.
The loader reads `ACCEPTANCE_SEED_URL` and `ACCEPTANCE_SEED_TOKEN` from the environment.
The URL value is the tracker base; the loader appends the API path.
