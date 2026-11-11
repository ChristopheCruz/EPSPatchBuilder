"""Lecture de fichiers WAV et preparation des sons (mono, frequence, niveau)."""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass

import numpy as np

from .i18n import T


class AudioError(Exception):
    pass


@dataclass
class Sound:
    samples: np.ndarray            # float64 mono, [-1, 1]
    rate: float
    root_key: int | None = None    # note MIDI lue dans le fichier (bloc « smpl »), si presente
    loop_start: int | None = None
    loop_end: int | None = None

    @property
    def duration(self) -> float:
        return len(self.samples) / self.rate


def read_wav(path: str) -> Sound:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise AudioError(T("{0} : ce n'est pas un fichier WAV").format(path))
    pos, fmt, pcm, smpl = 12, None, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            fmt = body
        elif cid == b"data":
            pcm = body
        elif cid == b"smpl":
            smpl = body
        pos += 8 + size + (size & 1)
    if fmt is None or pcm is None or len(fmt) < 16:
        raise AudioError(T("{0} : fichier WAV incomplet").format(path))
    tag, channels, rate, _, align, bits = struct.unpack_from("<HHIIHH", fmt, 0)
    if tag == 0xFFFE and len(fmt) >= 26:          # WAVE_FORMAT_EXTENSIBLE
        tag = struct.unpack_from("<H", fmt, 24)[0]
    if channels < 1 or rate < 1:
        raise AudioError(T("{0} : en-tete WAV invalide").format(path))
    width = bits // 8
    frames = len(pcm) // (width * channels)
    pcm = pcm[:frames * width * channels]
    if tag == 1 and width == 1:
        x = (np.frombuffer(pcm, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif tag == 1 and width == 2:
        x = np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
    elif tag == 1 and width == 3:
        b = np.frombuffer(pcm, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / float(1 << 23)
    elif tag == 1 and width == 4:
        x = np.frombuffer(pcm, dtype="<i4").astype(np.float64) / float(1 << 31)
    elif tag == 3 and width == 4:
        x = np.frombuffer(pcm, dtype="<f4").astype(np.float64)
    elif tag == 3 and width == 8:
        x = np.frombuffer(pcm, dtype="<f8").astype(np.float64)
    else:
        raise AudioError(T("{0} : format WAV non gere (code {1}, {2} bits)").format(path, tag, bits))
    x = x.reshape(-1, channels).mean(axis=1)        # mixage mono
    sound = Sound(x, float(rate))
    if smpl is not None and len(smpl) >= 36:
        unity = struct.unpack_from("<I", smpl, 12)[0]
        loops = struct.unpack_from("<I", smpl, 28)[0]
        if 0 <= unity <= 127:
            sound.root_key = unity
        if loops >= 1 and len(smpl) >= 60:
            start, end = struct.unpack_from("<II", smpl, 36 + 8)
            if 0 <= start < end < len(x):
                sound.loop_start, sound.loop_end = start, end
    return sound


# Formats lus directement, puis par la bibliotheque soundfile, puis par ffmpeg s'il est installe.
SOUNDFILE_EXTENSIONS = (".aif", ".aiff", ".aifc", ".flac", ".ogg", ".oga", ".mp3", ".au", ".snd", ".caf", ".w64", ".voc")
FFMPEG_EXTENSIONS = (".m4a", ".aac", ".wma", ".opus", ".mp4", ".webm", ".amr", ".ape", ".wv")
AUDIO_EXTENSIONS = (".wav",) + SOUNDFILE_EXTENSIONS + FFMPEG_EXTENSIONS


def is_audio_file(path: str) -> bool:
    return path.lower().endswith(AUDIO_EXTENSIONS)


def _read_with_soundfile(path: str) -> Sound:
    try:
        import soundfile
    except ImportError as ex:
        raise AudioError(T("La bibliotheque « soundfile » n'est pas installee : seuls les WAV sont lisibles")) from ex
    try:
        data, rate = soundfile.read(path, dtype="float64", always_2d=True)
    except Exception as ex:
        raise AudioError(T("{0} : lecture impossible ({1})").format(os.path.basename(path), ex)) from ex
    return Sound(data.mean(axis=1), float(rate))


def _read_with_ffmpeg(path: str) -> Sound:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise AudioError(T("{0} : ce format demande le programme ffmpeg, qui n'est pas installe. Convertissez "
                           "le fichier en WAV, FLAC ou MP3, ou installez ffmpeg.").format(os.path.basename(path)))
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        flags = {"creationflags": 0x08000000} if os.name == "nt" else {}      # pas de fenetre console
        result = subprocess.run([exe, "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-c:a", "pcm_s24le", tmp],
                                capture_output=True, timeout=300, **flags)
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            raise AudioError(T("{0} : conversion impossible ({1})").format(os.path.basename(path), detail[-1] if detail else 'erreur ffmpeg'))
        return read_wav(tmp)
    except subprocess.TimeoutExpired as ex:
        raise AudioError(T("{0} : conversion trop longue").format(os.path.basename(path))) from ex
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def read_sound(path: str) -> Sound:
    """Lit un fichier audio de n'importe quel format pris en charge et le convertit en mono."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        try:
            return read_wav(path)
        except AudioError:
            try:                                   # WAV compresse (ADPCM, etc.)
                return _read_with_soundfile(path)
            except AudioError:
                pass
            raise
    if ext in FFMPEG_EXTENSIONS:
        return _read_with_ffmpeg(path)
    try:
        return _read_with_soundfile(path)
    except AudioError:
        if shutil.which("ffmpeg"):
            return _read_with_ffmpeg(path)
        raise


def write_wav(path: str, samples: np.ndarray, rate: float) -> None:
    pcm = np.clip(np.rint(np.asarray(samples) * 32767.0), -32768, 32767).astype("<i2").tobytes()
    r = int(round(rate))
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
                + struct.pack("<IHHIIHH", 16, 1, 1, r, r * 2, 2, 16) + b"data" + struct.pack("<I", len(pcm)) + pcm)


def resample(x: np.ndarray, src_rate: float, dst_rate: float, zero_crossings: int = 24) -> np.ndarray:
    """Reechantillonnage a bande limitee (sinus cardinal fenetre Kaiser)."""
    x = np.asarray(x, dtype=np.float64)
    if abs(src_rate - dst_rate) < 1e-6 or len(x) == 0:
        return x.copy()
    ratio = dst_rate / src_rate
    cutoff = min(1.0, ratio) * 0.96            # marge avant la frequence de Nyquist
    half = int(np.ceil(zero_crossings / cutoff))
    n_out = int(np.floor(len(x) * ratio))
    padded = np.concatenate([np.zeros(half + 1), x, np.zeros(half + 2)])
    out = np.empty(n_out)
    taps = np.arange(-half, half + 1)
    beta = 9.0
    i0 = np.i0(beta)
    for a in range(0, n_out, 4096):
        t = np.arange(a, min(a + 4096, n_out)) / ratio
        base = np.floor(t).astype(np.int64)
        frac = t - base
        d = taps[None, :] - frac[:, None]                       # distance en echantillons source
        w = np.clip(1.0 - (d / (half + 1)) ** 2, 0.0, None)
        kernel = cutoff * np.sinc(cutoff * d) * np.i0(beta * np.sqrt(w)) / i0
        idx = base[:, None] + taps[None, :] + half + 1
        out[a:a + len(t)] = np.einsum("ij,ij->i", padded[idx], kernel)
    return out


def trim_silence(x: np.ndarray, threshold_db: float = -60.0) -> tuple[np.ndarray, int]:
    """Supprime le silence au debut et a la fin. Retourne le son et le nombre d'echantillons retires au debut."""
    if len(x) == 0:
        return x, 0
    level = np.max(np.abs(x))
    if level <= 0:
        return x, 0
    loud = np.nonzero(np.abs(x) > level * 10 ** (threshold_db / 20.0))[0]
    return x[loud[0]:loud[-1] + 1], int(loud[0])


def normalize(x: np.ndarray, peak: float = 0.97) -> np.ndarray:
    level = float(np.max(np.abs(x))) if len(x) else 0.0
    return x if level <= 0 else x * (peak / level)


def trim_bounds(x: np.ndarray, threshold_db: float = -60.0) -> tuple[int, int]:
    """Premier et dernier echantillon audibles (bornes incluses)."""
    if len(x) == 0:
        return 0, 0
    level = np.max(np.abs(x))
    if level <= 0:
        return 0, len(x) - 1
    loud = np.nonzero(np.abs(x) > level * 10 ** (threshold_db / 20.0))[0]
    return int(loud[0]), int(loud[-1])


def compress(x: np.ndarray, rate: float, amount: int) -> np.ndarray:
    """Compression de dynamique. amount de 0 (aucune) a 100 (forte) : les passages forts sont
    attenues, ce qui permet de remonter le niveau d'ensemble (a faire suivre d'une normalisation)."""
    x = np.asarray(x, dtype=np.float64)
    amount = max(0, min(100, int(amount)))
    if amount == 0 or len(x) == 0:
        return x.copy()
    peak = float(np.max(np.abs(x)))
    if peak <= 0:
        return x.copy()
    threshold = peak * 10 ** (-(amount * 0.30) / 20.0)        # jusqu'a -30 dB sous la crete
    ratio = 1.0 + amount * 0.07                               # jusqu'a 8:1
    hop = max(1, int(rate * 0.002))                           # suivi d'enveloppe par pas de 2 ms
    blocks = -(-len(x) // hop)
    padded = np.zeros(blocks * hop)
    padded[:len(x)] = np.abs(x)
    env = padded.reshape(blocks, hop).max(axis=1)
    attack = np.exp(-1.0 / (0.005 * rate / hop))
    release = np.exp(-1.0 / (0.120 * rate / hop))
    smooth = np.empty(blocks)
    level = env[0]                                            # pas de surcharge sur l'attaque
    for i, value in enumerate(env):
        coeff = attack if value > level else release
        level = coeff * level + (1.0 - coeff) * value
        smooth[i] = level
    over = np.maximum(smooth, threshold) / threshold
    gain = over ** (1.0 / ratio - 1.0)
    centers = (np.arange(blocks) + 0.5) * hop
    return x * np.interp(np.arange(len(x)), centers, gain)


def reduce_bits(x: np.ndarray, bits: int) -> np.ndarray:
    """Reduit la resolution (effet « lo-fi »). L'EPS classique travaille sur 13 bits."""
    if bits >= 13:
        return np.asarray(x, dtype=np.float64)
    steps = float(1 << (max(2, bits) - 1))
    return np.clip(np.rint(np.asarray(x, dtype=np.float64) * steps) / steps, -1.0, 1.0 - 1.0 / steps)


def apply_fades(x: np.ndarray, rate: float, fade_in_ms: float, fade_out_ms: float) -> np.ndarray:
    x = np.array(x, dtype=np.float64)
    n_in = min(len(x), int(rate * max(0.0, fade_in_ms) / 1000.0))
    n_out = min(len(x), int(rate * max(0.0, fade_out_ms) / 1000.0))
    if n_in > 1:
        x[:n_in] *= np.linspace(0.0, 1.0, n_in)
    if n_out > 1:
        x[-n_out:] *= np.linspace(1.0, 0.0, n_out)
    return x


def nearest_zero_crossing(x: np.ndarray, pos: int, search: int = 2000) -> int:
    """Passage par zero montant le plus proche de pos (pos si aucun n'est trouve)."""
    lo, hi = max(1, pos - search), min(len(x) - 1, pos + search)
    if hi <= lo:
        return pos
    seg = x[lo - 1:hi + 1]
    idx = np.nonzero((seg[:-1] < 0) & (seg[1:] >= 0))[0] + lo
    return int(idx[np.argmin(np.abs(idx - pos))]) if len(idx) else pos


def best_loop_end(x: np.ndarray, loop_start: int, loop_end: int, search: int = 3000, window: int = 96) -> int:
    """Cherche pres de loop_end le point ou la suite du son ressemble le plus au debut de la boucle,
    pour que le raccord s'entende le moins possible."""
    n = len(x)
    if loop_start < 0 or loop_start + window >= n:
        return loop_end
    lo = max(loop_start + window, loop_end - search)
    hi = min(n - window - 2, loop_end + search)
    if hi <= lo:
        return loop_end
    ref = x[loop_start:loop_start + window]
    # Le son rejoue x[loop_start...] juste apres x[e] : on compare donc x[e+1 : e+1+window] a ref.
    cand = np.lib.stride_tricks.sliding_window_view(x[lo + 1:hi + 1 + window], window)
    cost = np.sum((cand - ref) ** 2, axis=1)
    cost = cost + 1e-9 * np.abs(np.arange(len(cost)) + lo - loop_end)      # a egalite, le plus proche
    return int(lo + np.argmin(cost))
