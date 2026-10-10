# Post-collection construct audit

The frozen 32-chain set was scored without deletion. Inspection of every L2
answer emission then identified two residual construction artifacts that were
not caught by the automatic lexical filters or preliminary AI-assisted review:

- `HP09`: the retained title `Cat's Eye` directly cues the gold animal `cat`.
- `HP23`: the retained evidence explicitly lists Philosophy, Politics and
  Economics, so the gold number `three` can still be obtained by counting.

These chains remain in the full 32-chain results. A separately labelled,
post-collection sensitivity analysis excludes them and reports results on the
remaining 30 chains. The exclusions are based only on the visible prompt and
the prespecified construct (whether necessary evidence is missing), not on
whether the model answer matches the gold answer.

No additional chain was substituted and no model response was rerun after this
audit. This preserves the complete audit trail and prevents silent
outcome-dependent sample replacement.
