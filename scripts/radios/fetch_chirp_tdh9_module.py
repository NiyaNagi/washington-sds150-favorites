"""Fetch the TIDRADIO TD-H9 test driver from CHIRP issue #12216.

The TD-H9 is not in any released CHIRP build.  Support exists only as a
drop-in replacement ``tdh8.py`` attached to the tracking issue, which CHIRP
normally loads through *Help > Load module from issue*.

This script downloads that module for use by the programming bridge.  It is
deliberately a fetch script rather than a vendored copy, for the same reason
``scripts/fetch_hpe_fixtures.py`` exists: CHIRP is licensed GPL-3.0 and this
project is MIT, so its source must not be committed here.  The download lands
in a git-ignored directory and is attributed on every run.

Usage::

    python scripts/radios/fetch_chirp_tdh9_module.py [--attachment 15609]

Pin the attachment id.  The module's memory layout has changed during
development and its author warns that saved ``.img`` files may not survive a
version change, so the module that produced an image should be kept with it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ISSUE_URL = "https://chirpmyradio.com/issues/12216"
ATTACHMENT_URL = "https://chirpmyradio.com/attachments/download/{id}/tdh8.py"

#: Attachment 15609 ("beta 072729.01") is the last build whose TD-H9 support
#: was confirmed on hardware in the issue thread, on firmware 1.0.32 and
#: 1.0.33, including uploading channels from CHIRP CSV plans.  Later
#: attachments carry TD-H8 Gen 4 work in the same file.
DEFAULT_ATTACHMENT = 15609
KNOWN_ATTACHMENTS = {
    15542: "070326.01 - first TD-H9 support",
    15543: "070526.01 - Bluetooth toggle fix",
    15600: "072726.01 - fixes the Settings tab crash",
    15609: "072729.01 - removes the NOAA name lock on channels 189-199",
    15685: "081726.04 - TD-H8 Gen 4 work",
    15686: "081726.05 - TD-H8 Gen 4 work, per-mode frequency ranges",
}

DEST_DIR = Path(".chirp-modules")
LICENCE_NOTE = """\
This directory holds third-party CHIRP driver modules downloaded on demand.

CHIRP is licensed GPL-3.0. Its source is NOT part of this repository and must
not be committed. These files are fetched for local use only.

Source: {issue}
"""


def fetch(attachment_id: int, dest_dir: Path) -> Path:
    url = ATTACHMENT_URL.format(id=attachment_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "README.txt").write_text(
        LICENCE_NOTE.format(issue=ISSUE_URL), encoding="utf-8"
    )

    request = urllib.request.Request(url, headers={"User-Agent": "wasds150-fetch"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        data = response.read()

    if b"TDH9" not in data and b"tdh9" not in data.lower():
        raise SystemExit(
            f"downloaded file from {url} does not look like the TD-H9 driver"
        )

    target = dest_dir / f"tdh8_{attachment_id}.py"
    target.write_bytes(data)

    digest = hashlib.sha256(data).hexdigest()
    (dest_dir / f"tdh8_{attachment_id}.json").write_text(
        json.dumps(
            {
                "attachment_id": attachment_id,
                "description": KNOWN_ATTACHMENTS.get(attachment_id, "unknown"),
                "url": url,
                "issue": ISSUE_URL,
                "sha256": digest,
                "bytes": len(data),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "licence": "GPL-3.0 (CHIRP); not redistributed by this project",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Fetched attachment {attachment_id} ({len(data)} bytes)")
    print(f"  {KNOWN_ATTACHMENTS.get(attachment_id, 'unknown build')}")
    print(f"  sha256 {digest}")
    print(f"  -> {target}")
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attachment", type=int, default=DEFAULT_ATTACHMENT,
        help=f"Attachment id from issue 12216 (default {DEFAULT_ATTACHMENT})",
    )
    parser.add_argument("--dest", default=str(DEST_DIR), help="Destination directory")
    parser.add_argument(
        "--list", action="store_true", help="List the known attachment ids and exit"
    )
    args = parser.parse_args(argv)

    if args.list:
        for key in sorted(KNOWN_ATTACHMENTS):
            marker = " (default)" if key == DEFAULT_ATTACHMENT else ""
            print(f"{key}  {KNOWN_ATTACHMENTS[key]}{marker}")
        return 0

    fetch(args.attachment, Path(args.dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
