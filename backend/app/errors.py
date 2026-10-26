"""Project-specific exceptions."""


class ElexonError(Exception):
    """The Elexon API could not be reached or returned an unusable response."""


class IngestError(Exception):
    """A row from Elexon could not be parsed into the expected shape."""


class SnapshotError(Exception):
    """The data snapshot file is missing or unreadable."""


class NoDataError(Exception):
    """There is no data to compute the requested result from."""
