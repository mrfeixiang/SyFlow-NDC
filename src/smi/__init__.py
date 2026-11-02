"""Small-molecule inhibitor Go/No-Go module.

Decision unit: indication × protein target × compound × assay batch.
Runtime gates live in ``src.smi.schemas.gate``. This package does not
change the nanobody-drug conjugate gates in ``src.schemas.gate``.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
