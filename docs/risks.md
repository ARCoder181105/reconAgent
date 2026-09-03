# ReconAgent — Risks

> Known risks, impact, likelihood, mitigation, status. Owner = the single human maintainer. Reduce/retire risks as work proceeds; update status here, never delete.

| Risk | Impact | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| Subset-sum combinatorial explosion in Stage 4 | Pipeline hang / blowup | Medium | Bound candidate pool per date window; never scan whole dataset per bank line (constraints.md) | Mitigation defined |
| Gemini rate limit / downtime in Stage 5 | Stage 5 unavailable | Medium | Async offload; on failure fall back to Stage 4 result with lower confidence; never break pipeline | Mitigation defined |
| LLM returns non-JSON / chatty text | Downstream parser breaks | Medium | Structured output mode (fixed JSON schema); validate + reject non-conforming | Mitigation defined |
| Silent false-positive match | Financial-control failure, low score | Low (by design) | 3x FP penalty; confidence tiers; LLM never sole authority | Mitigation defined |
| Synthetic data too easy/too hard → unmeasurable demo | Poor judged accuracy | Medium | Hidden answer key + 70/20/10 mix; score honestly | Mitigation defined |
| Scope creep (ChromaDB, Prometheus, cross-border) | Half-built features | Medium | scope.md + re-litigation policy in decisions.md | Active guard |
| Single-owner bus risk / context loss | Slow dev | High | This docs set + onboarding.md | Active guard |
| SQLite write contention in prototype | Lock timeouts | Low | Prototype scale; single user; document Postgres path | No action yet |
| Judging misreads Maker-Checker as complexity | Lower perceived clarity | Medium | Reinforce in demo narrative: controls, not complexity (assumptions A13) | Monitor |

## Escalation

Any risk rated High impact + High likelihood: stop, tell the human, adjust plan via tasks.md before proceeding.
