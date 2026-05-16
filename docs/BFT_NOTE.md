# A note on single-provider operation

`habermas-mirror` runs the four-stage facilitator pipeline through one
LLM call per stage. By default — and in most realistic self-host
deployments — every stage of every session goes to the *same* provider
under the *same* operator's API key.

That is fine for an engineering reference implementation. It is *not* a
consensus mechanism, and it should not be marketed as one.

## Why this matters

The intuition that running the same model "as participant, drafter,
critic, and reviser" gives the system some kind of cross-checking
property does not hold. If a single operator controls all four stages,
the four stages are not independent: they share weights, prompt
formatting, and any biases (deliberate or not) that the provider has
trained or sampled in. A pipeline where one party plays all roles is
structurally equivalent to a single-party attestation — i.e. a single
signature dressed up as a quorum.

This is the same reason a Byzantine-fault-tolerant protocol with all N
participants under one owner offers no fault tolerance: cryptographic
ceremony cannot manufacture independence that is not there.

## What operators can do

If you need stronger guarantees than "one provider's opinion about
itself", the cheapest robust thing to do is:

1. Run the pipeline more than once with different `HABERMAS_MIRROR_MODEL`
   choices (e.g. an OpenAI model for `draft`, an Anthropic model for
   `critique`, a Gemini model for `refine`). The pipeline already
   accepts a per-call `model=` override at the Python level; an HTTP
   knob is on the Phase 3 roadmap.

2. Run the same pipeline under independent operators and compare
   outputs. The `statements` table preserves the full transcript so
   that this comparison is mechanical.

3. Treat the resulting group statement as one input among others into
   whatever offline process the deliberation is feeding — not as the
   final word.

## What we don't claim

`habermas-mirror` does not implement Habermasian discourse ethics, does
not detect strategic action, does not score sincerity, does not
preserve dissent as a first-class object, and does not produce evidence
packs for any regulatory framework. Each of those was considered and
deliberately scoped out of the reference implementation, because the
existing literature in 2026 already covers most of them better.

See the README for the rest of the non-goals.

## On the dissent-preservation scope cut

For the record: the first-session exploration explicitly listed
"dissent preservation + reject-consensus right, **first-class in MVP**"
as the mitigation for the *manipulative-consensus* risk Volpe (2025)
raises against the original Habermas Machine. When the scope was
narrowed to A' — a self-hostable engineering re-implementation of the
prompted pipeline, with no academic novelty claim — that mitigation
was demoted from "must-have" to "non-goal" without a separate
discussion. A later audit flagged this as a silent drift relative to
the original exploration memo.

This document is the audit-trail record of that demotion. The acceptable
operator-level mitigation today is the same as for single-provider
operation more generally: run the pipeline more than once with
heterogeneous models, treat the resulting group statement as one input
among others, and preserve the underlying opinions (which are not
discarded by this pipeline) so any later dissent-focused tool can be
attached on top.
