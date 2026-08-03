from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app.services.artifact_inspection_sandbox import (
    BubblewrapClamAVScanner,
    BubblewrapInspectionSandbox,
)

EICAR_TEST_BYTES = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$"
    b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


async def _run() -> None:
    scanner = BubblewrapClamAVScanner(BubblewrapInspectionSandbox())
    if not await scanner.ready():
        raise RuntimeError("Artifact inspection sandbox is not ready.")

    with tempfile.TemporaryDirectory(prefix="gni-inspection-smoke-") as directory:
        root = Path(directory)
        clean_path = root / "clean.txt"
        clean_path.write_bytes(b"GNI Artifact inspection sandbox smoke test.\n")
        clean = await scanner.scan(clean_path)
        if not clean.clean:
            raise RuntimeError("ClamAV rejected the clean smoke payload.")

        eicar_path = root / "eicar.com"
        eicar_path.write_bytes(EICAR_TEST_BYTES)
        infected = await scanner.scan(eicar_path)
        if infected.clean or infected.reason_code != "clamav_malware_match":
            raise RuntimeError("ClamAV did not reject the EICAR smoke payload.")

    print(
        "artifact inspection smoke passed: "
        f"{clean.scanner_name} engine={clean.scanner_version} "
        f"signatures={clean.signature_version}"
    )


if __name__ == "__main__":
    asyncio.run(_run())
