# analysis.py — BPM and musical key detection for Bongoo
# by itu-dallasli
#
# Analyzes audio files to detect BPM (tempo) and musical key.
# Uses librosa for audio analysis.

import os


# Key names mapped from chroma index
KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def analyze(audio_path):
    """Analyze an audio file for BPM and musical key.

    Args:
        audio_path: Path to the audio file (MP3/WAV)

    Returns:
        dict {"bpm": float, "key": str} or None on failure
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        print("librosa not installed. Install: pip install librosa")
        return None

    if not os.path.isfile(audio_path):
        print(f"File not found: {audio_path}")
        return None

    try:
        # Load audio (mono, native sample rate)
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # --- BPM Detection ---
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        # tempo may be an array in newer versions
        bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
        bpm = round(bpm, 1)

        # --- Key Detection ---
        # Compute chromagram and find dominant pitch class
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)  # 12 pitch classes

        # Detect major/minor using key profiles (Krumhansl-Schmuckler)
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                         2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                         2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

        import numpy as np
        best_corr = -1
        best_key = "C"
        best_mode = "major"

        for shift in range(12):
            rolled = np.roll(chroma_mean, -shift)
            corr_major = float(np.corrcoef(rolled, major_profile)[0, 1])
            corr_minor = float(np.corrcoef(rolled, minor_profile)[0, 1])

            if corr_major > best_corr:
                best_corr = corr_major
                best_key = KEY_NAMES[shift]
                best_mode = "major"
            if corr_minor > best_corr:
                best_corr = corr_minor
                best_key = KEY_NAMES[shift]
                best_mode = "minor"

        key = f"{best_key} {best_mode}"

        return {"bpm": bpm, "key": key}

    except Exception as e:
        print(f"Analysis failed: {e}")
        return None


def format_result(result):
    """Format analysis result as a readable string."""
    if result is None:
        return "Analysis failed"
    return f"{result['bpm']} BPM — {result['key']}"
