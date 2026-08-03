#!/usr/bin/python3
from __future__ import annotations

import sys
import time
from pathlib import Path

if "--version" in sys.argv:
    print("ClamAV 1.4.3/27777/Test")
    raise SystemExit(0)

artifact = Path(sys.argv[-1])
payload = artifact.read_bytes()
if b"TIMEOUT" in payload:
    time.sleep(10)
if b"SCANNER_ERROR" in payload:
    print("scanner failed")
    raise SystemExit(2)
if b"EICAR" in payload:
    print(f"{artifact}: Win.Test.EICAR_HDB-1 FOUND")
    raise SystemExit(1)
raise SystemExit(0)
