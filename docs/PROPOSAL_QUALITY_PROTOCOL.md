# Proposal Quality Protocol

This protocol turns community feedback into testable engineering proposals.

## Why this exists

High-quality proposals need more than "this feels better."  
For roadmap decisions, each proposal should include:

1. **Mechanism**: how a concrete change in LogForge should alter behavior.
2. **Prediction**: what observable output/metric should change.
3. **Falsification**: what observation would show the proposal is wrong.

If any of the three is missing, the proposal is not ready for prioritization.

## Required proposal contract

For feature discussions and issues, maintainers should ask for:

- **Current context**: exact workflow/repo context where pain happens.
- **Target layer**: CLI/config, parser, classifier, generator, renderer, CI, or docs.
- **Mechanism**: "changing X to Z in layer Y should cause behavior B because ..."
- **Prediction**: "after change, running command C should produce measurable result R."
- **Falsification**: "if output O still occurs under condition T, proposal fails."

## Triage states

- **Ready**: mechanism + prediction + falsification are all present.
- **Needs mechanism**: idea exists but no causal explanation.
- **Needs prediction**: no measurable expected behavior.
- **Needs falsification**: no disconfirming condition.

Use labels to keep the queue explicit (for example: `needs mechanism`).

## Example (LogForge-specific)

Weak proposal:

> "Use a different summary style. It should feel smarter."

Testable proposal:

> "In classifier fallback prompts, add explicit scope hints when commit scope exists.  
> Mechanism: better prompt constraints reduce `misc` over-classification for scoped commits.  
> Prediction: on fixture set X, `misc` entries drop from 18% to under 10%.  
> Falsification: if `misc` stays >= 18% or misclassification rises in `fix` group, reject."

## Maintainer workflow

1. Intake issue/discussion.
2. If proposal is incomplete, request the missing contract fields.
3. Add `needs mechanism` (or equivalent) until complete.
4. Move to roadmap only when proposal is falsifiable and measurable.
5. After implementation, compare observed result vs prediction and close the loop.
