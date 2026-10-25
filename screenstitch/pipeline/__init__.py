"""ScreenStitch processing pipeline."""

from screenstitch.pipeline.register import (
    RegistrationError,
    RegistrationResult,
    register,
    register_fallback,
)
from screenstitch.pipeline.mask import (
    MaskResult,
    compute_disagreement_masks,
)
from screenstitch.pipeline.reconstruct import (
    ReconstructionResult,
    reconstruct,
)
from screenstitch.pipeline.blend import (
    BlendResult,
    blend,
)

__all__ = [
    "register",
    "register_fallback",
    "RegistrationResult",
    "RegistrationError",
    "compute_disagreement_masks",
    "MaskResult",
    "reconstruct",
    "ReconstructionResult",
    "blend",
    "BlendResult",
]
