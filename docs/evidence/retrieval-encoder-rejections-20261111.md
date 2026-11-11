# Two further retrieval encoders rejected before promotion

Progress on [#21](https://github.com/Olli0103/unifi-protect-local-ai/issues/21),
not a search-quality acceptance or a production model change. The failed
[EVA02 preprocessing candidates](retrieval-preprocessing-rejected-20261111.md)
remain separate retained experiments.

## Frozen subjects

| Encoder | Exact upstream revision | Safetensors SHA-256 | Width |
| --- | --- | --- | ---: |
| [PE-Core-L14-336](https://huggingface.co/timm/PE-Core-L-14-336) | `8eff41b3f687e50a323662c2dda5eb3588c6dd35` | `b1fff7093c32a01d98a2d82098f9adf788b30f0efee639916520b3e4302f786b` | 1024 |
| [Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) | `9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda` | `c73fa9caeddeb3ff831d46c085a7a5708343248ca777e90f2d486964464509c1` | 2048 |

Both model cards declare Apache-2.0; that declaration is not a complete
redistribution/rights review. Only pinned safetensors were loaded; no pickle,
remote model code, shared-environment installation or production service was
used. Weights and private inputs remain outside Git and iCloud.

Each run used **one** predetermined profile, CPU FP32/two threads, and the
same retained 70 images: 24 synthetic, one labelled real hallway positive,
and 45 historical train false matches. Ten original synthetic queries
(six positive, four negative) plus the hallway query produce eleven scored
text vectors. One image and one text warmup are excluded from scoring.
Every scored image and query was embedded once; full vectors, ranks and
request timings were retained. This is reused development data, **not an
independent holdout or full-archive native evaluation**.

The fixed k=5/raw-cosine cutoffs **0.25 and 0.2528** were not tuned. At each
cutoff, MRR and nDCG must be at least 0.5 and synthetic negative rejection at
least 75%; the known real positive must reach 0.2528, all four controls over
the 46 real images must stay below 0.25, and vector coverage must be complete.
Native Protect percentages are not these raw cosine values.

## Processing and admission

- **PE-Core:** official 336-pixel bilinear squash, mean/std 0.5 and its own
  32-token tokenizer/context. All planned text was admitted without truncation
  (maximum eight tokens including boundaries); no EVA02 preprocessing reuse.
- **Qwen:** checkpoint-declared built-in `Qwen3VLProcessor`/
  `Qwen2VLImageProcessor`, dynamic aspect-preserving resolution and official
  last-nonpadding-token pooling. One upstream default instruction,
  `Represent the user's input.`, is fixed for images and queries. The existing
  lowercase/short-photo query rule is retained, without a prompt ensemble or
  query-specific instructions. All 82 preprocessing admissions (including the
  text warmup) were frozen by tensor identity before inference; maximum **242**
  tokens including image tokens, instruction and boundaries, below the explicit
  8192 limit. No truncation or remote vision utility was used.

The installed Qwen runtime is Torch 2.14.1 / Transformers 5.20.2, not the
upstream example's Torch 2.8.0. Its built-in local architecture and exact
checkpoint loading had no missing/unexpected/mismatched weights. An initial
attempt stopped **before any forward call or warmup** because Transformers'
loading metadata contains sets that the JSON serializer refused. Its plan,
partial metadata, zero-vector record and harness are retained. The serializer
was corrected and a superseding pre-inference plan frozen; no quality result
or scored model call was retried or erased.

## Results and independent verification

The following MRR/nDCG values are identical at both fixed cutoffs:

| Candidate | MRR@5 | nDCG@5 | Synthetic negatives with results | Real-positive cosine | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| PE-Core-L14 | 0.333333 | 0.294227 | 0/4 | 0.18564695 | Reject: positive ranking and real-positive gates fail |
| Qwen3-VL-2B | 0.833333 | 0.844422 | 4/4 | 0.45274896 | Reject: synthetic and real negative gates fail |

PE-Core's four real negative maxima are 0.1551, 0.1737, 0.1620 and 0.1767:
passing negative controls cannot waive its failed positives. Qwen's real
negative maxima are **0.270439, 0.321651, 0.270533 and 0.345957**: its improved
hallway match cannot waive four false-positive controls. Coverage is complete
for both runs. Neither is a qualified replacement.

Separate standard-library scalar scorers recomputed **all 81 retained
vectors'** query rankings, MRR/nDCG/recall, negative maxima and final gate
verdicts without model calls. Maximum dot-product differences versus NumPy
were 8.33e-17 for PE-Core and 2.22e-16 for Qwen; all ranks and verdicts agree.
PE-Core took about 44 seconds with 5.79 GB peak process RSS; Qwen about
77 seconds with 13.27 GB peak process RSS. These are local process observations,
not total host memory, production throughput or a representative latency study.
The Qwen run attempted no network connection.

Plan SHA-256: PE-Core
`0de8f2f34119cb479edf72a7351ca5d763ac520880e207da282163a5f1505332`;
Qwen scored plan
`3b873632d680f23c3a2019679f15050ebc40e9228386b70fc0f01b02bab5ac39`.
Private vectors/media, local paths and native identifiers are not published.

## Native control and unchanged deployment

A separate read of the original deployed encoder through Protect 7.4.96's
Find Anything UI returned **three matches each** for two already-declared
unrelated queries at the native initial confidence **50**. Both requests
returned HTTP 200. This is a negative-quality **failure**, not a serving outage.
The previously observed automatic broadening to zero was not reproduced in
this run because the initial threshold already returned results. No explicit
auto-broadening switch was found in the inspected controls; that does not prove
its global absence. A keyboard attempt to move the slider had no effect, so
there is no higher-threshold pass. The owned search tab was closed; a failed
stale-reference clear action is retained, not claimed successful.

No production encoder, model endpoint, stored index, threshold, camera scope,
provider setting or device service was changed. No cross-space vector reuse,
query blacklist, post-hoc threshold calibration, native full-archive pass or
fix for Protect's upstream search broadening is claimed. #21 remains open.
