#!/usr/bin/env python3
import os, shutil, subprocess, tempfile
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

# === Settings ===
VOICE_MAIN = Path.home() / ".local/share/piper/voices/ru_RU-irina-medium.onnx"
if not VOICE_MAIN.exists():
    VOICE_MAIN = Path.home() / ".local/share/piper/voices/ru_RU-irina-medium.onnx"  # fallback stays the same
VOICE_CFG  = Path(str(VOICE_MAIN) + ".json")

PIPER_BIN_CANDIDATES  = ["/usr/local/bin/piper", "/opt/piper-tts/piper", "piper"]
PLAYER_CANDIDATES     = ["play", "aplay", "paplay"]
SOX_BIN_CANDIDATES    = ["sox"]

# Use a unified audio format so sox doesn't complain
TARGET_SR   = 22050
TARGET_CH   = 1
TARGET_BITS = 16

def which(cands):
    for c in cands:
        full = shutil.which(c)
        if full:
            return full
        if Path(c).exists():
            return c
    return None

PIPER = which(PIPER_BIN_CANDIDATES)
PLAYER = which(PLAYER_CANDIDATES)
SOX    = which(SOX_BIN_CANDIDATES)

def get_battery():
    if psutil is None:
        return None
    try:
        b = psutil.sensors_battery()
        return None if b is None else round(b.percent)
    except Exception:
        return None

def piper_say(text: str, wav_path: str, *, length=0.97, noise=0.30, noise_w=0.60, pause=0.38):
    if not PIPER or not Path(PIPER).exists():
        raise RuntimeError("Piper not found")
    if not VOICE_MAIN.exists():
        raise RuntimeError(f"Model not found: {VOICE_MAIN}")
    args = [
        PIPER, "--model", str(VOICE_MAIN),
        "--output_file", wav_path,
        "--sentence_silence", str(pause),
        "--length_scale", str(length),
        "--noise_scale",  str(noise),
        "--noise_w",      str(noise_w),
        "--output_sample_rate", str(TARGET_SR),   # <<< key for compatibility
    ]
    if VOICE_CFG.exists():
        args[1:1] = ["--config", str(VOICE_CFG)]
    subprocess.run(args, input=text.encode("utf-8"),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def sox_pitch(in_wav: str, out_wav: str, cents: int = 0, gain_db: float = 0.0):
    chain = [SOX, in_wav, out_wav]
    if cents:
        chain += ["pitch", str(cents)]
    if gain_db:
        chain += ["gain", str(gain_db)]
    subprocess.run(chain, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def sox_concat_with_pause(wav_a: str, wav_b: str, out_wav: str, pause_ms: int = 280):
    """
    Concatenate A + pause + B. All files must be 22_050 Hz, mono, 16-bit.
    """
    # Generate silence in the exact same format
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        silence = tmp.name
    subprocess.run([
        SOX, "-n",
        "-r", str(TARGET_SR),
        "-c", str(TARGET_CH),
        "-b", str(TARGET_BITS),
        silence, "trim", "0", str(pause_ms/1000)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Concatenate files of the same format
    subprocess.run([SOX, wav_a, silence, wav_b, out_wav],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    try:
        os.remove(silence)
    except Exception:
        pass

def speak(phrase1: str, phrase2: str):
    if not PLAYER:
        raise RuntimeError("No player found (sox/aplay/paplay). Install sox or use aplay.")
    if not SOX:
        raise RuntimeError("sox not found. Install the sox package for pitch and concatenation effects.")

    with tempfile.TemporaryDirectory() as td:
        a_raw = os.path.join(td, "a_raw.wav")
        b_raw = os.path.join(td, "b_raw.wav")
        a_fx  = os.path.join(td, "a_fx.wav")
        b_fx  = os.path.join(td, "b_fx.wav")
        out   = os.path.join(td, "out.wav")

        # Phrase 1: calm tone, slightly lower pitch
        piper_say(phrase1, a_raw, length=0.98, noise=0.28, noise_w=0.58, pause=0.40)
        sox_pitch(a_raw, a_fx, cents=-30)

        # Phrase 2: informative, a bit more energetic, slightly higher pitch
        piper_say(phrase2, b_raw, length=0.95, noise=0.30, noise_w=0.60, pause=0.36)
        sox_pitch(b_raw, b_fx, cents=+25)

        # Concatenate with a pause using the same format
        sox_concat_with_pause(a_fx, b_fx, out, pause_ms=280)

        # Gentle “radio” tone
        if Path(PLAYER).name == "play":
            subprocess.run([PLAYER, out, "bass", "+2", "treble", "-1", "gain", "-1"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run([PLAYER, out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    batt = get_battery()
    p1 = "Я ухожу на покой, мой господин!"
    p2 = f"Уровень заряда батареи: {batt} процентов." if batt is not None else "До скорой встречи"
    speak(p1, p2)

if __name__ == "__main__":
    main()
