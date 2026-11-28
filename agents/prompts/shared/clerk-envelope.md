---
type: LLM Prompt Fragment
title: Shared Clerk Reply Envelope
description: The one reply object every Hermes tracker clerk returns, appended after the clerk's own prompt.
resource: prompt://dryvist/agents/prompts/shared/clerk-envelope
tags: [agent, shared-prefix, tracker, envelope]
timestamp: "2026-11-27T04:00:00Z"
status: active
consumers: [Hermes]
render: {engine: literal, variables: [], frontmatter: strip}
source_history: []
---

Do not use the report envelope. Reply with only one compact JSON object and nothing else. It has exactly these keys:

- status: "ok", "refused", "error" or "unavailable".
- outcome: one short sentence saying what happened. For refused, say what was refused and that nothing changed.
- ids: the ids you read or changed, each a JSON string such as "42", copied character for character from a tool
  result in this run. Never type an id from memory.
- items: the records found, each an object with at least id and title, or [].
- readback: the fields read back after a write, or null when nothing was written.
- error: null, or an object with a short "code" and a one-sentence "message" when status is refused, error or
  unavailable.

Report ok for a write only after the readback matches. Refused means nothing changed. Unavailable means the tracker or a
tool could not be reached. Never put a credential in any field.
