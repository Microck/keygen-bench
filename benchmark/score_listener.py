#!/usr/bin/env python3
"""AI listener: Meta Audiobox Aesthetics ratings of the canonical FT2 render.

    python benchmark/score_listener.py identity
    python benchmark/score_listener.py predict /absolute/canonical.wav

The model was trained on human 1-10 ratings of speech, sound and music clips
(Tjandra et al. 2025, arXiv:2502.05139; weights CC-BY-4.0). It returns four
ratings: content enjoyment (CE), content usefulness (CU), production
complexity (PC) and production quality (PQ). The benchmark score uses CE only.

This file runs in its own Python environment (benchmark/requirements-listener.txt)
so PyTorch never loads inside the evaluator process, whose loaded native
libraries are hashed for provenance. score.py starts it as a subprocess.
Inference is pinned to the CPU, one fixed model revision and verified weights.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys

REPO = "facebook/audiobox-aesthetics"
REVISION = "9b1dd8e5df9af7216e836a98974fe3b82c56ded6"
WEIGHTS_SHA256 = "a5a3c2412649cc2384ec525ffd5180ce6c4778f43bed6108e0a1303de04d014e"
# Bounds inference cost: the model averages 10 s windows, and nearly all
# submissions establish their material well within two minutes.
MAX_SECONDS = 120
AXES = {"CE": "content_enjoyment", "CU": "content_usefulness",
        "PC": "production_complexity", "PQ": "production_quality"}


def _weights_path() -> str:
    from huggingface_hub import hf_hub_download
    return hf_hub_download(REPO, "model.safetensors", revision=REVISION)


def identity() -> dict:
    with open(_weights_path(), "rb") as stream:
        weights = hashlib.file_digest(stream, "sha256").hexdigest()
    if weights != WEIGHTS_SHA256:
        raise RuntimeError(f"listener weights {weights} do not match the pinned {WEIGHTS_SHA256}")
    import torch
    return {"model": REPO, "revision": REVISION, "weights_sha256": weights, "device": "cpu",
            "max_seconds": MAX_SECONDS, "torch": torch.__version__,
            "torchaudio": importlib.metadata.version("torchaudio"),
            "audiobox_aesthetics": importlib.metadata.version("audiobox_aesthetics")}


def predict(wav_path: str) -> dict:
    import numpy as np
    import torch
    from scipy.io import wavfile
    from audiobox_aesthetics.infer import AesPredictor
    from audiobox_aesthetics.model.aes import AesMultiOutput, Normalize

    class PinnedPredictor(AesPredictor):
        # The package loads the latest Hub revision on whatever accelerator is
        # present. Pin both; the inference arithmetic in forward() is unchanged.
        def setup_model(self):
            self.device = torch.device("cpu")
            self.model = AesMultiOutput.from_pretrained(REPO, revision=REVISION).to(self.device).eval()
            self.target_transform = {axis: Normalize(mean=self.model.target_transform[axis]["mean"],
                                                     std=self.model.target_transform[axis]["std"])
                                     for axis in AXES}

    ident = identity()
    rate, pcm = wavfile.read(wav_path, mmap=True)
    if pcm.dtype != np.int16 or pcm.ndim not in (1, 2):
        raise ValueError("expected signed-16 mono or stereo PCM")
    clip = np.asarray(pcm[: rate * MAX_SECONDS], dtype=np.float32) / 32768.0
    wav = torch.from_numpy(clip)
    wav = wav[None, :] if wav.ndim == 1 else wav.T.contiguous()
    raw = PinnedPredictor(checkpoint_pth=None).forward([{"path": wav, "sample_rate": rate}])[0]
    return {"ratings": {AXES[key]: raw[key] for key in AXES},
            "analyzed_seconds": len(clip) / rate, "identity": ident}


def main() -> None:
    if sys.argv[1:2] == ["identity"] and len(sys.argv) == 2:
        result = identity()
    elif sys.argv[1:2] == ["predict"] and len(sys.argv) == 3:
        result = predict(sys.argv[2])
    else:
        raise SystemExit(__doc__)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
