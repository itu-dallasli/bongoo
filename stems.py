# stems.py — Audio stem separation for Bongoo
# by itu-dallasli
#
# Separates audio into vocals, drums, bass, and other using AI models.
# Supports two models: Open-Unmix (light) and Demucs (heavy, best quality).

import os
import shutil
import traceback

_torchaudio_patched = False

def _patch_torchaudio_save():
    """Replace torchaudio.save with a soundfile-based fallback.
    Fixes 'torchcodec is required' errors in newer torchaudio versions.
    """
    global _torchaudio_patched
    if _torchaudio_patched:
        return

    try:
        import torchaudio
        import soundfile as sf

        _original_save = torchaudio.save

        def _sf_save(uri, src, sample_rate, **kwargs):
            """Save audio using soundfile instead of torchcodec."""
            import numpy as np
            # src: (channels, samples) tensor -> (samples, channels) numpy
            data = src.cpu().numpy().T
            sf.write(str(uri), data, sample_rate)

        torchaudio.save = _sf_save
        _torchaudio_patched = True
        print("Patched torchaudio.save → soundfile backend")
    except ImportError:
        print("Warning: could not patch torchaudio (soundfile missing)")



def separate(input_path, output_dir=None, model="openunmix"):
    """Separate an audio file into stems.

    Args:
        input_path:  Path to the input audio file (MP3/WAV)
        output_dir:  Output directory (default: same dir as input + _stems)
        model:       "openunmix" (light, ~150MB) or "demucs" (heavy, ~1.5GB)

    Returns:
        dict with stem paths {"vocals": path, "drums": path, ...}
        or None on failure
    """
    if not os.path.isfile(input_path):
        print(f"File not found: {input_path}")
        return None

    if output_dir is None:
        base = os.path.splitext(input_path)[0]
        output_dir = base + "_stems"
    os.makedirs(output_dir, exist_ok=True)

    basename = os.path.splitext(os.path.basename(input_path))[0]

    if model == "demucs":
        return _separate_demucs(input_path, output_dir, basename)
    else:
        return _separate_openunmix(input_path, output_dir, basename)


def _separate_demucs(input_path, output_dir, basename):
    """Separate using Meta's Demucs model (best quality, heavy)."""
    try:
        import demucs.separate
    except ImportError:
        print("Demucs not installed. Install: pip install demucs")
        return None

    try:
        # Monkey-patch torchaudio.save to use soundfile (avoids torchcodec)
        _patch_torchaudio_save()

        # Demucs outputs to: output_dir/htdemucs/basename/{vocals,drums,bass,other}.wav
        demucs.separate.main([
            "--two-stems", "vocals",
            "-n", "htdemucs",
            "-o", output_dir,
            input_path
        ])

        stem_dir = os.path.join(output_dir, "htdemucs", basename)
        return _collect_stems(stem_dir, output_dir, basename)
    except Exception as e:
        print(f"Demucs separation failed: {e}")
        traceback.print_exc()
        return None


def _separate_openunmix(input_path, output_dir, basename):
    """Separate using Open-Unmix model (lighter, faster).
    Uses torch.hub to load the pre-trained umxhq model.
    Uses soundfile for audio I/O (avoids torchcodec dependency).
    """
    try:
        import torch
    except ImportError:
        print("PyTorch not installed. Install: pip install torch")
        return None

    try:
        import soundfile as sf
    except ImportError:
        print("soundfile not installed. Install: pip install soundfile")
        return None

    try:
        print(f"Loading audio: {input_path}")
        # Use soundfile to read audio (works with WAV, FLAC, OGG; for MP3 needs ffmpeg conversion)
        try:
            data, sample_rate = sf.read(input_path, dtype="float32")
        except RuntimeError:
            # soundfile can't read MP3 directly — convert via ffmpeg first
            import subprocess, tempfile
            tmp_wav = os.path.join(output_dir, "_temp_input.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-ar", "44100", tmp_wav],
                capture_output=True
            )
            data, sample_rate = sf.read(tmp_wav, dtype="float32")
            os.remove(tmp_wav)

        # data shape: (samples,) for mono or (samples, channels) for stereo
        waveform = torch.from_numpy(data).float()
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(1).repeat(1, 2)  # mono → stereo
        # shape: (samples, channels) → (channels, samples)
        waveform = waveform.T

        # Add batch dimension: (channels, samples) → (batch, channels, samples)
        audio = waveform.unsqueeze(0)

        device = "cuda" if torch.cuda.is_available() else "cpu"

        print("Loading Open-Unmix model (umxhq)...")
        separator = torch.hub.load(
            "sigsep/open-unmix-pytorch", "umxhq",
            device=device
        )
        separator.eval()

        print("Separating stems...")
        with torch.no_grad():
            estimates = separator(audio.to(device))
            # estimates shape: (batch, sources, channels, samples)

        source_names = ["vocals", "drums", "bass", "other"]
        stems = {}

        for i, stem_name in enumerate(source_names):
            if i < estimates.shape[1]:
                stem_audio = estimates[0, i].cpu().numpy().T  # (samples, channels)
                stem_path = os.path.join(output_dir, f"{basename}_{stem_name}.wav")
                sf.write(stem_path, stem_audio, sample_rate)
                stems[stem_name] = stem_path
                print(f"  Saved: {stem_name} → {os.path.basename(stem_path)}")

        return stems if stems else None

    except Exception as e:
        print(f"Open-Unmix separation failed: {e}")
        traceback.print_exc()
        return None


def _collect_stems(stem_dir, output_dir, basename):
    """Move stems from demucs output structure to flat output dir."""
    stems = {}
    # --two-stems produces: vocals.wav + no_vocals.wav
    # full mode produces: vocals.wav, drums.wav, bass.wav, other.wav
    for stem_name in ["vocals", "no_vocals", "drums", "bass", "other"]:
        src = os.path.join(stem_dir, f"{stem_name}.wav")
        # Rename no_vocals to a friendlier name
        out_name = "backing_track" if stem_name == "no_vocals" else stem_name
        dst = os.path.join(output_dir, f"{basename}_{out_name}.wav")
        if os.path.isfile(src):
            shutil.move(src, dst)
            stems[out_name] = dst

    # Clean up demucs directory structure
    htdemucs_dir = os.path.join(output_dir, "htdemucs")
    if os.path.isdir(htdemucs_dir):
        shutil.rmtree(htdemucs_dir, ignore_errors=True)

    return stems if stems else None
