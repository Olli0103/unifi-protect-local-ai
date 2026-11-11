# Rejected offline EVA02 preprocessing candidates

Issue #21 remains open. Neither candidate below was promoted, deployed,
reindexed or used to change query thresholds or production settings.

## Frozen experiment

Both runs reuse the original EVA02-L-14 224 checkpoint
`timm/eva02_large_patch14_clip_224.merged2b_s4b_b131k`, upstream revision
`bf4190eb65dd5204ffb03e980108beb1200e0873`, safetensors SHA-256
`00af04296f09f24dcc69559440a80b7a44daf4855a72827e016067e6e571b851`.
The official config declares its CLIP mean/std, not either candidate transform.
No new weights or production models were installed.

Each plan/hash was fixed before inference. CPU-only, two threads, offline
model/cache settings; 70 transformed images comprise the retained 24 synthetic
images, one explicitly labelled real hallway positive and 45 historical
train false matches. There are ten synthetic scored queries (six positive,
four negative), that real positive's text query, a separate baseline text
query and an excluded warmup. The CLAHE output's text count lists eleven
scored queries but omits its separate baseline-query counter; the preserved
execution also contains that baseline call. It must not be described as eleven
total text calls.

Two original-preprocessing baseline image embeddings were checked in each run.
Their maximum component delta was about 1.86e-7 against retained baseline data;
the original real-positive cosine was 0.22373409, matching the earlier
0.22373413 within 1e-6.

The same predeclared gates apply at raw cosine cutoffs 0.25 and 0.2528, k=5:
MRR and nDCG at least 0.5, at least 0.75 synthetic negative rejection, the known
real positive at least 0.2528, every real negative control below 0.25 and full
coverage. Native UI scores are not reinterpreted as these raw cosines.

## One fixed transform per run

- **CLAHE:** uint8 RGB to LAB; CLAHE on L only, clip limit 2.0 and 8x8 grid;
  LAB to RGB, then ordinary shortest-side resize/224 center crop and the same
  normalization. OpenCV-headless 4.11.0.86 was installed only in isolated audit
  dependencies after its official PyPI wheel digest was checked; the shared
  Python environment was not changed.
- **Letterbox:** the retained real positive is 189x360. A square center crop
  retains 52.5% of that image's area and visibly removes part of the person.
  The candidate instead resizes the longest side to 224 and centers on fixed
  mean-color RGB (123,117,104) padding, with the same normalization. No CLAHE
  or changed text prompt, weights, threshold or control set is combined with it.

| Candidate | MRR, both cutoffs | nDCG, both cutoffs | Synthetic negative result rate | Known real-positive cosine | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| CLAHE | 0.666667 | 0.556527 | 0 | 0.2105295 | Reject: known positive fails |
| Letterbox | 0.500000 | 0.411546 | 0 | 0.2261437 | Reject: nDCG and known positive fail |

All four negative controls against the 46 real images stayed below 0.25 in
both runs; coverage was complete. Those successes cannot waive the failed
positive/nDCG gates. The trials took about 25 seconds each with approximately
3 GB peak RSS and did not call any provider or production service.

Plans, input/weight/runtime hashes, vectors, rankings, exact dependency receipt,
failed package-proxy attempt and run outputs are retained privately outside
Git. These are reused development/regression inputs, **not an independent
holdout or full-archive/native quality pass**. No query-specific blacklist,
threshold tuning, production migration or fix for Protect's native automatic
zero-similarity broadening is claimed. Do not repeat these same candidates as
untried work or turn their negative-only success into search acceptance.
