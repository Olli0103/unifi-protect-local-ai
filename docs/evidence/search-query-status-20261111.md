# Search transport and query outcomes — 11 November 2026

## Native finding and bounded recovery

Five bounded native Protect 7.4.96 search requests initially returned HTTP 500.
The Key's search transport remained connected and its transport error was empty.
The selected existing encoder was stopped; another running encoder had a different
model revision and was not a valid substitute. This establishes a diagnostic gap:
a connected search transport does not establish successful query encoding.

The exact selected encoder was recovered with its existing checkpoint, encoding
contract and index profile unchanged. The first readiness reader used the wrong
JSON level and the owned start was rolled back. The corrected reader verified the
nested encoding declaration. The first cold native request exceeded its client
deadline; that attempt remains failed. Four other native requests and an explicit
follow-up returned HTTP 200. Previously identified false matches remained, so
retrieval quality is still unaccepted. The production identity/pairing projection
was unchanged. No model replacement, reindex, threshold change, new camera scope
or paid provider was introduced. Private receipts remain outside the repository.

## Source correction and limits

The search runtime now records a bounded last completed request outcome separately
from connection state. Text and image failures remain explicit; an echo is not a
successful search. The existing authenticated processing observation exposes only
fixed labels and nonnegative counters, never query contents, URLs or error bodies.
Historical failures remain counted after a later successful response. Missing
legacy observations remain unknown. Viewing the page performs no inference.

Synthetic tests exercise an actual loopback encoder reply, failed reply with no
fake vector, subsequent recovery, image outcomes, invalid/private observations,
and the existing read-only authenticated UI. The existing desktop/mobile Chrome
harness checks visible failure followed by recovery while failure counts remain.
Exact platform totals belong in the PR receipts. These checks do not establish
native deployment of this presentation, retrieval relevance, saved results or
host-reboot recovery. Issues #21 and #24 remain open for those wider criteria.
