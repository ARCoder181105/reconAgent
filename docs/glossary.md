# ReconAgent — Glossary

> Locked term definitions. Do not redefine mid-project. If a term's meaning must change, treat it as a decision change (see `decisions.md` re-litigation policy).

## Payment / Gateway

| Term | Meaning |
|---|---|
| **UTR** | Unique Transaction Reference — the reference number assigned by the receiving bank to a single NEFT/RTGS/IMPS transfer; intended to uniquely identify the transfer across the Indian banking system. |
| **MDR** | Merchant Discount Rate — the fee the gateway (Razorpay) charges the merchant per transaction, commonly ~2% depending on payment method. |
| **GST on fees** | 18% tax charged on the MDR fee. |
| **Settlement** | A group of captured payments, netted (customer payments minus fees, tax, refunds, adjustments), transferred from the gateway to the merchant's bank account. |
| **Settlement batch** | The set of captured payments grouped into one settlement cycle. |
| **Razorpay settlement id** | `setl_...` — the gateway's identifier for a settlement. |
| **Refund / chargeback** | Money returned to customer / dispute reversal; may be netted into a batch or appear as a standalone bank debit. |
| **On-hold / partial settlement** | A settlement where risk holds pull some payments out; batch composition differs from the expected payment list. |

## Reconciliation

| Term | Meaning |
|---|---|
| **Reconciliation** | Confirming that each gateway settlement batch arrived at the bank as the correct credit, correct amount, correct reason. |
| **Exact match** | Full UTR substring found + amount match (Stage 1). |
| **Fuzzy UTR match** | UTR matched by edit-distance / truncation-aware scoring (Stage 2). |
| **Amount + date match** | No usable UTR; single candidate within date window (Stage 3). |
| **Batch-sum match** | One bank credit equals the sum of multiple settlement records (many-to-one, Stage 4). |
| **LLM tie-break** | Stage 5 plausibility judgment on otherwise-unresolved records (last resort). |
| **Orphan** | A bank line with no corresponding settlement record (and vice versa). |

## Exception Handling

| Term | Meaning |
|---|---|
| **Exception** | A record the engine could not consistently match; routed to human review with reason code, confidence, and ranked candidates. |
| **Reason code** | Canonical failure classifier (`NO_CANDIDATE`, `MULTIPLE_CANDIDATES`, etc.) — see `taxonomy.md`. |
| **Confidence tier** | Auto-match / Review queue / Hard exception banding — see `taxonomy.md`. |
| **Candidates** | Top 1–3 closest proposed matches, with scores, shown to a human reviewer. |
| **Exception clustering** | Grouping hard exceptions sharing a root cause (reason code + string heuristics) to reduce review fatigue. |

## Governance (Maker-Checker)

| Term | Meaning |
|---|---|
| **Maker** | Junior accountant who proposes a resolution (confirm/reject/override) on an exception. Maker action does NOT close the books. |
| **Checker** | Senior controller who signs off (approve) or rejects a maker's proposal with reason. Exception closes only after approval. |
| **Pending approval** | Derived state: maker proposed, awaiting checker sign-off. |
| **Closed books / verified** | State after checker approval — the only state counted in `verified_rate`. |

## Persistence

| Term | Meaning |
|---|---|
| **Event sourcing** | Pattern where state is never mutated in place; every change appends an immutable event, and current state is a projection of the event log. |
| **Event** | An immutable append-only record of an action (`CREATED`, `MAKER_PROPOSED`, `CHECKER_APPROVED`, `CHECKER_REJECTED`). |
| **Projection** | The derived current view (e.g. exception status) read from the event log. |
| **System of record** | The authoritative source (here: the `exception_events` append-only log). |

## Metrics

| Term | Meaning |
|---|---|
| **Match rate** | `auto_matched / total_records` — engine confidence. |
| **Verified rate** | `records_closed / total_records` — books actually closed after Maker-Checker. |
| **Precision** | TP / (TP + FP). |
| **Recall** | TP / (TP + FN). |
| **False positive** | Engine auto-matched a pair the answer key says is wrong — the most dangerous failure mode. |
| **False negative** | Engine escalated a record the answer key says had a confident correct match. |
| **Hidden answer key** | Synthetic ground-truth mapping, generated with the data but never seen by the matcher; used only for scoring. |
| **Ground truth** | The known-correct settlement↔bank-line mapping from the answer key. |
