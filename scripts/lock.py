#!/usr/bin/env python3
"""Write or verify vendor/LOCK.json, the checksum record of the vendored AIDOC-AP core.

  python3 scripts/lock.py verify
  python3 scripts/lock.py write --tag v1.2 --commit <sha>   (only via scripts/fetch_core.sh)
"""
import argparse
import json
import sys

from common import LOCK, vendor_digest, verify_lock

REPOSITORY = "https://github.com/certain-project/aidoc-ap"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--tag", required=True)
    w.add_argument("--commit", required=True)
    sub.add_parser("verify")
    args = ap.parse_args()

    if args.cmd == "write":
        LOCK.write_text(json.dumps(
            {"repository": REPOSITORY, "tag": args.tag, "commit": args.commit, "files": vendor_digest()},
            indent=2) + "\n")
        print(f"wrote {LOCK.name} for {args.tag} ({args.commit[:7]})")
        return 0

    problems = verify_lock()
    for p in problems:
        print("ERROR:", p)
    if not problems:
        lock = json.loads(LOCK.read_text())
        print(f"vendored core matches LOCK ({lock['tag']}, {lock['commit'][:7]}, {len(lock['files'])} files)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
