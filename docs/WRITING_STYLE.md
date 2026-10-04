# Writing style

I keep the repository voice close to the style used by mature infrastructure projects: concise project scope, explicit boundaries, short operational sections and separate deep-dive documentation.

The repository is still owner-led, so human-facing prose uses my voice rather than sounding like an assistant giving me instructions.

## Voice

When I describe my decisions or workflow, I use first-person singular:

```text
I use...
I keep...
I require...
I treat...
I consider...
I do not...
```

When I describe system behavior or a technical invariant, I use neutral declarative language:

```text
The deployment path verifies...
The transaction is accepted only after...
A failed precondition returns PRE_MUTATION_REFUSAL.
```

I avoid reader-directed wording such as:

```text
you should...
you need to...
please run...
make sure you...
your environment...
```

Commands remain commands, but the surrounding prose describes how I use them instead of instructing a reader.

## Structure

I prefer:

- a short project definition first;
- explicit scope and non-goals;
- one clear source of truth for deeper contracts;
- short command blocks;
- evidence and failure semantics close to the behavior they describe;
- links to detailed runbooks instead of duplicating them in README;
- focused sections instead of conversational filler.

## Contracts and standards

I keep normative technical language such as `MUST`, `SHOULD` and terminal-state names when it defines machine or transaction behavior.

I do not rewrite standard legal or community texts merely to force first-person voice. `LICENSE` and standard code-of-conduct language remain authoritative in their normal form.

## Contributions and templates

Contribution and issue templates use neutral prompts or my acceptance criteria. They do not address me as if another person were operating the repository.

## Repository rule

New human-facing documentation follows this style unless a file has a stronger external standard or machine-readable contract that requires different wording.
