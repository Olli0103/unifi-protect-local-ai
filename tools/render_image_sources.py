"""Render only an explicitly provided same-release source URL, or an unpublished notice."""
import os
from pathlib import Path
import re
import sys

PLACEHOLDER = "@SOURCE_BUNDLE_URL@"


def render(template, url):
    if url:
        if not re.fullmatch(
            r"https://github\.com/Olli0103/unifi-protect-local-ai/releases/download/"
            r"v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|rc)[1-9][0-9]*)?/release\.json", url):
            raise ValueError("source_notice_url_refused")
    else:
        url = "UNPUBLISHED — no source-delivery URL configured; do not distribute this image."
    if template.count(PLACEHOLDER) != 1:
        raise ValueError("source_notice_template_refused")
    return template.replace(PLACEHOLDER, url)


if __name__ == "__main__":
    target = Path(sys.argv[2])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(Path(sys.argv[1]).read_text(), os.environ.get("SOURCE_BUNDLE_URL", "")))
