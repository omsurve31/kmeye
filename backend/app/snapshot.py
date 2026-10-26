"""Read and write the committed data snapshot (gzip-compressed JSON)."""

import gzip
from pathlib import Path

from pydantic import ValidationError

from app.errors import SnapshotError
from app.schemas import Snapshot


def write_snapshot(snapshot: Snapshot, path: Path) -> None:
    """Write the snapshot so that identical data always gives identical bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.model_dump_json().encode("utf-8")
    # An empty filename and mtime=0 keep the gzip header constant, so reruns do not change the file.
    with (
        path.open("wb") as file,
        gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as compressed_file,
    ):
        compressed_file.write(payload)


def read_snapshot(path: Path) -> Snapshot:
    """Load the snapshot.

    Raises:
        SnapshotError: If the file is missing, is not gzip, or has unexpected content.
    """
    try:
        payload = gzip.decompress(path.read_bytes())
    except FileNotFoundError as error:
        raise SnapshotError(
            f"Snapshot not found at {path}. Build it with: python -m app.ingest"
        ) from error
    except (OSError, EOFError) as error:
        raise SnapshotError(f"Snapshot at {path} is corrupt (not valid gzip)") from error
    try:
        return Snapshot.model_validate_json(payload)
    except ValidationError as error:
        raise SnapshotError(f"Snapshot at {path} is corrupt (unexpected content)") from error
