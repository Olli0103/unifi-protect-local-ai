# Image sources and licenses

This image contains GPL, LGPL and other third-party components, including the
Debian FFmpeg GPL build, Debian packages, psycopg (LGPL-3.0, when installed)
and bundled LGPL-2.1 libraries. Project code is licensed separately.

Source delivery record: @SOURCE_BUNDLE_URL@

For a published image, the signed release.json binds each immutable image
digest to its source_bundle URL, complete archive SHA-256 (archive_sha256) and ordered parts
with individual SHA-256 values. Download all parts from that same GitHub
release, verify each hash, concatenate in the recorded order and verify the
complete archive hash. The bundle includes the selected upstream originals,
the exact project Git archive (including build/install recipes), and the
four-image inventory inputs. Package matching is not by itself a complete
corresponding-source or rights attestation; publication also requires the
owner's image-license review.

Original license/notice texts are retained at:

- /usr/share/doc/*/copyright and /usr/share/common-licenses/
- Python site-packages/*dist-info/licenses/ and bundled package notice files
- /app/LICENSE and /app/THIRD_PARTY_NOTICES.txt

A development or CI build is not distributable merely because this notice
exists. A missing/unpublished signed release record is not a source offer.
No source-availability warranty or owner approval is inferred from a URL.
