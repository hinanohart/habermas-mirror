# habermas-mirror

A self-hostable, multi-provider reference re-implementation of the deliberation
facilitator pipeline described in **Tessler et al., *AI can help humans find
common ground in democratic deliberation*, Science (2024)** — the so-called
"Habermas Machine".

> **Status: pre-alpha (Phase 0 / repo skeleton).** The pipeline, API, and UI
> land over the next phases. Nothing here is production-ready.

## Why this exists

DeepMind released a [prompted reference][hm-deepmind] of the Habermas Machine
in 2024, but the fine-tuned reward model is not public and the prompted
variant is Gemini-only. `habermas-mirror` aims to give practitioners and
researchers a:

- self-hostable
- LLM-provider-agnostic (via [LiteLLM][litellm])
- minimal-dependency
- Apache-2.0-licensed

reference implementation of the four-stage deliberation pipeline
(*gather opinions → draft group statement → critique → refine*), so the
approach can be reproduced, audited, and extended outside one vendor's
infrastructure.

## Non-goals (deliberately)

This project does **not** claim to:

- "implement Jürgen Habermas's discourse ethics" — the academic literature
  (Volpe 2025, CACM "Ghost in the Habermas Machine", TRISE 2026-03) shows
  that the original Habermas Machine itself is contested as a faithful
  realization of Habermasian theory.
- replace existing deliberation platforms such as [Pol.is][polis],
  [Decidim][decidim], or [Loomio][loomio]. Those serve different scales and
  workflows.
- offer the fine-tuned reward model from the Science paper.

It is an engineering artifact: a faithful, hackable re-implementation of the
*prompted* pipeline, nothing more.

## Acknowledgment

`habermas-mirror` is not affiliated with, endorsed by, or sponsored by
Google DeepMind, Alphabet, or the authors of the original Science paper. We
gratefully cite their published work and the [open prompted reference][hm-deepmind].

## Security model

Participant opinions are inlined verbatim into the LLM prompts that drive
the four-stage pipeline. **Treat every prompt and every model response as
untrusted user input.** The repository does not attempt jailbreak
detection, does not sanitize semantic content, and does not filter
outputs. Operators self-hosting `habermas-mirror` are responsible for
whatever downstream review or moderation their context requires.

Single-provider operation is structurally a single-party attestation, not
a consensus mechanism. See [`docs/BFT_NOTE.md`](./docs/BFT_NOTE.md) for
the honest version.

## License

[Apache License 2.0](./LICENSE). See `LICENSE` for the full text.

## Roadmap (high level)

| Phase | Scope | Status |
|------:|-------|--------|
| 0 | repo skeleton, license, README | done |
| 1 | FastAPI app, LiteLLM wrapper, SQLite, opinion endpoint | done |
| 2 | four-stage facilitator pipeline + prompts | done |
| 3 | minimal React (Vite) UI | done |
| 4 | docs, smoke tests, release artifact | planned |

> **Sunset condition.** `habermas-mirror` is an exploratory engineering
> artifact. If, six months after the first tagged release, the project
> has fewer than 10 GitHub stars AND fewer than 3 forks, it will be
> archived rather than maintained as bit-rot. If DeepMind (or anyone
> else) publishes a more complete self-hostable re-implementation of
> the Habermas Machine, this project will redirect users there.

## Citation

If you use this software in academic work, please cite the upstream
Science paper:

```bibtex
@article{tessler2024habermas,
  title   = {AI can help humans find common ground in democratic deliberation},
  author  = {Tessler, Michael Henry and Bakker, Michiel and Jarrett, Daniel and others},
  journal = {Science},
  year    = {2024},
  doi     = {10.1126/science.adq2852}
}
```

and (optionally) this repository as the re-implementation artifact you used.

[hm-deepmind]: https://github.com/google-deepmind/habermas_machine
[litellm]: https://github.com/BerriAI/litellm
[polis]: https://github.com/compdemocracy/polis
[decidim]: https://github.com/decidim/decidim
[loomio]: https://github.com/loomio/loomio
