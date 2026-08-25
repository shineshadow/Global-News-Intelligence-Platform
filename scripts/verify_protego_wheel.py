"""Verify the exact Owner-approved Protego v1 distribution artifact."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_FILENAME = "protego-0.6.2-py3-none-any.whl"
EXPECTED_SHA256 = "714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff"


def verify(path: Path) -> None:
    if path.name != EXPECTED_FILENAME:
        raise ValueError(f"Expected wheel filename {EXPECTED_FILENAME!r}.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("Protego wheel SHA-256 does not match Owner approval.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    arguments = parser.parse_args()
    verify(arguments.wheel)
    print(f"verified {EXPECTED_FILENAME} sha256:{EXPECTED_SHA256}")


if __name__ == "__main__":
    main()
