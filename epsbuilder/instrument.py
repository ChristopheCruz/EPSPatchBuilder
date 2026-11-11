"""Format instrument de l'Ensoniq EPS classique (type de fichier 3).

Un instrument est une suite de blocs alignes sur 16 octets :
    bloc instrument (656 octets) -> blocs layer (224 octets) -> blocs wavesample
    (288 octets de parametres suivis des echantillons).

Chaque bloc commence par un en-tete de 5 mots (taille, pointeur retour, chainage) puis
contient ses parametres tels qu'ils sont decrits dans la specification Ensoniq
"EPS External Command Specification" (un parametre par mot de 16 bits, valeur dans
l'octet de poids fort). La memoire de l'EPS classique fait 13 bits de large : les 3 bits
de poids faible de chaque mot sont toujours nuls, y compris pour les echantillons.

L'EPS-16+ et l'ASR-10 relisent ce format.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np

from .i18n import T
from . import templates

INST_SIZE = 0x290
LAYER_SIZE = 0xE0
WS_PARAM_SIZE = 0x120
HDR = 10                     # en-tete de bloc : 5 mots
FIRST_KEY = 21               # la table de clavier couvre 88 touches a partir du la0 (MIDI 21)
LAST_KEY = 108
MAX_LAYERS = 8
MAX_WAVESAMPLES = 127
GUARD_WORDS = 4              # echantillons de garde apres la fin du son
CLOCK_HZ = 625000.0          # periode d'echantillonnage = n x 1,6 microseconde

LOOP_FORWARD_NO_LOOP, LOOP_BACKWARD_NO_LOOP, LOOP_FORWARD, LOOP_BIDIRECTIONAL, LOOP_AND_RELEASE = range(5)
LOOP_MODE_NAMES = [T("Sans boucle"), T("Sans boucle, a l'envers"), T("Boucle avant"), T("Boucle aller-retour"),
                   T("Boucle puis relachement")]

# Numeros de mots (specification Ensoniq, sections 7.1 a 7.3)
I_SIZE_BLOCKS, I_KEY_LO, I_KEY_HI = 15, 26, 27
I_LAYER_OFFSETS, I_WS_OFFSETS = 45, 61
L_VEL_LO, L_VEL_HI, L_KEYMAP = 15, 16, 19
W_COPY_WS, W_COPY_LAYER, W_ROOT_KEY, W_FINE_TUNE, W_VOLUME, W_LOOP_MODE = 12, 13, 80, 86, 99, 114
W_START, W_END, W_LOOP_START, W_LOOP_END, W_RATE, W_KEY_LO, W_KEY_HI = 115, 119, 123, 127, 131, 132, 133


W_AMP_ENV = 58
ENV_SUSTAIN, ENV_PERCUSSIVE = "sustain", "percussive"
# Enveloppe d'amplitude « percussive » : le son decroit jusqu'au silence meme touche enfoncee
# (valeurs d'un piano electrique regle sur un EPS). L'enveloppe « tenue » est celle du modele.
AMP_ENV_PERCUSSIVE = (0, 70, 127, 26, 60, 127, 26, 58, 100, 47, 55, 52, 74, 0, 0, 0, 1, 0, 30, 0, 0, 0)


class InstrumentError(Exception):
    pass


def rate_code_for(hz: float) -> int:
    """Code de frequence EPS (12 = 52,1 kHz ... 127 = 4,9 kHz) le plus proche de hz."""
    return max(12, min(127, int(round(CLOCK_HZ / hz))))


def rate_hz(code: int) -> float:
    return CLOCK_HZ / code


# --------------------------------------------------------------------------- modele
@dataclass
class Wavesample:
    name: str
    samples: np.ndarray                 # float dans [-1, 1], mono
    rate_code: int = 20                 # 20 -> 31 250 Hz
    root_key: int = 60                  # note MIDI jouee a la hauteur d'origine
    key_lo: int = FIRST_KEY
    key_hi: int = LAST_KEY
    loop_mode: int = LOOP_FORWARD_NO_LOOP
    loop_start: int | None = None       # en echantillons
    loop_end: int | None = None
    volume: int | None = None           # 0-127 ; None = valeur par defaut de l'EPS
    envelope: str = ENV_SUSTAIN         # ENV_SUSTAIN ou ENV_PERCUSSIVE (ignore si params est fourni)
    params: bytes | None = None         # bloc de parametres complet (instrument relu)

    @property
    def rate(self) -> float:
        return rate_hz(self.rate_code)


@dataclass
class Layer:
    name: str = "UNNAMEDLAYER"
    wavesamples: list[Wavesample] = field(default_factory=list)
    vel_lo: int = 0
    vel_hi: int = 127


@dataclass
class Instrument:
    name: str
    layers: list[Layer] = field(default_factory=list)
    key_lo: int = 36                    # etendue jouable de l'instrument (clavier de l'EPS : do1-do6)
    key_hi: int = 96

    def all_wavesamples(self) -> list[Wavesample]:
        return [ws for layer in self.layers for ws in layer.wavesamples]


# --------------------------------------------------------------------------- codage
def _name_words(name: str) -> bytes:
    name = "".join(c if 32 <= ord(c) < 127 else " " for c in name.upper())[:12].ljust(12)
    return b"".join(bytes([ord(c), 0]) for c in name)


def _put_param(buf: bytearray, base: int, word: int, value: int) -> None:
    struct.pack_into(">H", buf, base + HDR + 2 * word, (value & 0xFF) << 8)


def _put_size(buf: bytearray, base: int, size: int) -> None:
    struct.pack_into(">HH", buf, base, (size & 0xFFF) << 4, (size >> 12) << 4)


def _put_offset(buf: bytearray, pos: int, offset: int) -> None:
    struct.pack_into(">HH", buf, pos, (offset >> 12) << 8, (offset & 0xFFF) << 4)


def _put_position(buf: bytearray, base: int, word: int, sample_index: int) -> None:
    """Position dans le son : champ de 32 bits cale a gauche (index << 9), un octet par mot."""
    raw = sample_index << 9
    for k in range(4):
        _put_param(buf, base, word + k, (raw >> (24 - 8 * k)) & 0xFF)


def encode_samples(samples: np.ndarray) -> bytes:
    """Flottants [-1, 1] -> mots de 16 bits gros-boutistes, 13 bits utiles cales a gauche."""
    x = np.clip(np.rint(np.asarray(samples, dtype=np.float64) * 4095.0), -4096, 4095).astype(np.int16)
    return (x << 3).astype(">i2").tobytes()


def decode_samples(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=">i2").astype(np.float64) / 32768.0 * (32768.0 / (4095.0 * 8))


def _align16(n: int) -> int:
    return (n + 15) & ~15


def build_instrument(inst: Instrument) -> bytes:
    """Construit le fichier instrument (multiple de 512 octets) pret a etre ecrit sur disquette."""
    if not 1 <= len(inst.layers) <= MAX_LAYERS:
        raise InstrumentError(T("Un instrument contient de 1 a 8 layers"))
    all_ws = inst.all_wavesamples()
    if not all_ws:
        raise InstrumentError(T("L'instrument ne contient aucun son"))
    if len(all_ws) > MAX_WAVESAMPLES:
        raise InstrumentError(T("Un instrument contient au maximum 127 sons"))

    out = bytearray(templates.INSTRUMENT_BLOCK)
    out[HDR:HDR + 24] = _name_words(inst.name)
    # Remise a zero des tables de pointeurs (layers et wavesamples)
    for w in range(I_LAYER_OFFSETS, I_WS_OFFSETS + 2 * 128):
        struct.pack_into(">H", out, HDR + 2 * w, 0)

    ws_number = 0
    for li, layer in enumerate(inst.layers):
        if not layer.wavesamples:
            raise InstrumentError(T("Le layer {0} est vide").format(li + 1))
        layer_pos = len(out)
        numbers = list(range(ws_number + 1, ws_number + 1 + len(layer.wavesamples)))
        lb = bytearray(templates.LAYER_BLOCK)
        _put_size(lb, 0, LAYER_SIZE)
        struct.pack_into(">H", lb, 4, (HDR + 2 * (I_LAYER_OFFSETS + 2 * li)) << 4)   # pointeur retour
        struct.pack_into(">HH", lb, 6, numbers[0] << 8, numbers[-1] << 8)           # premier / dernier son
        lb[HDR:HDR + 24] = _name_words(layer.name)
        _put_param(lb, 0, L_VEL_LO, layer.vel_lo)
        _put_param(lb, 0, L_VEL_HI, layer.vel_hi)
        keymap = [0] * 88
        for n, ws in zip(numbers, layer.wavesamples):
            if not (0 <= ws.key_lo <= ws.key_hi <= 127):
                raise InstrumentError(T("Zone de clavier invalide pour {0!r}").format(ws.name))
            for key in range(max(ws.key_lo, FIRST_KEY), min(ws.key_hi, LAST_KEY) + 1):
                if keymap[key - FIRST_KEY]:
                    raise InstrumentError(T("Les zones de clavier se chevauchent sur la note {0} ({1!r})").format(key, ws.name))
                keymap[key - FIRST_KEY] = n
        for k, n in enumerate(keymap):
            _put_param(lb, 0, L_KEYMAP + k, n)
        _put_offset(out, HDR + 2 * (I_LAYER_OFFSETS + 2 * li), layer_pos)
        out += lb

        for idx, (n, ws) in enumerate(zip(numbers, layer.wavesamples)):
            count = len(ws.samples)
            if count < 8:
                raise InstrumentError(T("Le son {0!r} est trop court").format(ws.name))
            if not 12 <= ws.rate_code <= 127:
                raise InstrumentError(T("Code de frequence d'echantillonnage hors limites (12 a 127)"))
            looped = ws.loop_mode in (LOOP_FORWARD, LOOP_BIDIRECTIONAL, LOOP_AND_RELEASE)
            loop_start = ws.loop_start if (looped and ws.loop_start is not None) else 0
            loop_end = ws.loop_end if (looped and ws.loop_end is not None) else count - 1
            if not (0 <= loop_start < loop_end <= count - 1):
                raise InstrumentError(T("Points de boucle invalides pour {0!r}").format(ws.name))
            # Echantillons de garde : la suite de la boucle si le son boucle, sinon la derniere valeur.
            data_words = (count + GUARD_WORDS + 7) & ~7
            extra = data_words - count
            if looped:
                loop = np.asarray(ws.samples[loop_start:loop_end + 1])
                guard = np.resize(np.roll(loop, -((count - 1 - loop_start) % len(loop)) - 1), extra)
            else:
                guard = np.full(extra, ws.samples[-1])
            data = encode_samples(np.concatenate([np.asarray(ws.samples, dtype=np.float64), guard]))

            ws_pos = len(out)
            wb = bytearray(ws.params if ws.params is not None else templates.WAVESAMPLE_BLOCK)
            size = WS_PARAM_SIZE + len(data)
            if size >= 1 << 20:
                raise InstrumentError(T("Le son {0!r} est trop long (plus de 1 Mo)").format(ws.name))
            _put_size(wb, 0, size)
            struct.pack_into(">H", wb, 4, (HDR + 2 * (I_WS_OFFSETS + 2 * n)) << 4)   # pointeur retour
            nxt = numbers[idx + 1] if idx + 1 < len(numbers) else 0
            prv = numbers[idx - 1] if idx > 0 else 0
            struct.pack_into(">HH", wb, 6, nxt << 8, prv << 8)                       # chainage dans le layer
            wb[HDR:HDR + 24] = _name_words(ws.name)
            _put_param(wb, 0, W_COPY_WS, 0)
            _put_param(wb, 0, W_COPY_LAYER, 0)
            _put_param(wb, 0, W_ROOT_KEY, ws.root_key)
            if ws.params is None:
                _put_param(wb, 0, W_FINE_TUNE, 0)
                if ws.envelope == ENV_PERCUSSIVE:
                    for k, value in enumerate(AMP_ENV_PERCUSSIVE):
                        _put_param(wb, 0, W_AMP_ENV + k, value)
            if ws.volume is not None:
                _put_param(wb, 0, W_VOLUME, ws.volume)
            _put_param(wb, 0, W_LOOP_MODE, ws.loop_mode)
            _put_position(wb, 0, W_START, 0)
            _put_position(wb, 0, W_END, count - 1)
            _put_position(wb, 0, W_LOOP_START, loop_start)
            _put_position(wb, 0, W_LOOP_END, loop_end)
            _put_param(wb, 0, W_RATE, ws.rate_code)
            _put_param(wb, 0, W_KEY_LO, ws.key_lo)
            _put_param(wb, 0, W_KEY_HI, ws.key_hi)
            _put_offset(out, HDR + 2 * (I_WS_OFFSETS + 2 * n), ws_pos)
            out += wb + data
            assert len(out) % 16 == 0
        ws_number = numbers[-1]

    total = (len(out) + 511) & ~511
    out += bytes(total - len(out))
    _put_size(out, 0, total)
    struct.pack_into(">H", out, HDR + 2 * I_SIZE_BLOCKS, (total // 512) & 0xFFF8)
    _put_param(out, 0, I_KEY_LO, inst.key_lo)
    _put_param(out, 0, I_KEY_HI, inst.key_hi)
    return bytes(out)


# --------------------------------------------------------------------------- lecture
def _word(b: bytes, pos: int) -> int:
    return struct.unpack_from(">H", b, pos)[0]


def _get_size(b: bytes, base: int) -> int:
    return ((_word(b, base + 2) >> 4) << 12) | (_word(b, base) >> 4)


def _get_offset(b: bytes, pos: int) -> int:
    return (_word(b, pos) << 4) + (_word(b, pos + 2) >> 4)


def _get_name(b: bytes, base: int) -> str:
    return bytes(b[base + HDR + 2 * i] for i in range(12)).decode("latin1")


def _get_position(b: bytes, base: int, word: int) -> int:
    raw = 0
    for k in range(4):
        raw = (raw << 8) | b[base + HDR + 2 * (word + k)]
    return raw >> 9


def parse_instrument(data: bytes) -> Instrument:
    """Relit un instrument EPS. Les sons « copies » (qui partagent les echantillons d'un autre
    son) sont relus avec les echantillons de l'original."""
    if len(data) < INST_SIZE or _get_size(data, 0) > len(data) + 511:
        raise InstrumentError(T("Ce fichier n'est pas un instrument EPS valide"))
    P = lambda base, w: data[base + HDR + 2 * w]
    ws_offsets = {n: _get_offset(data, HDR + 2 * (I_WS_OFFSETS + 2 * n)) for n in range(1, 128)}
    ws_offsets = {n: o for n, o in ws_offsets.items() if o}

    def ws_data(n: int, depth: int = 0) -> bytes:
        o = ws_offsets[n]
        src = P(o, W_COPY_WS)
        if src and src in ws_offsets and depth < 4:
            return ws_data(src, depth + 1)
        return data[o + WS_PARAM_SIZE:o + _get_size(data, o)]

    inst = Instrument(_get_name(data, 0), key_lo=P(0, I_KEY_LO), key_hi=P(0, I_KEY_HI))
    for li in range(MAX_LAYERS):
        lo = _get_offset(data, HDR + 2 * (I_LAYER_OFFSETS + 2 * li))
        if not lo:
            continue
        layer = Layer(_get_name(data, lo), [], P(lo, L_VEL_LO), P(lo, L_VEL_HI))
        seen = []
        for k in range(88):
            n = P(lo, L_KEYMAP + k)
            if n and n not in seen and n in ws_offsets:
                seen.append(n)
        for n in seen:
            o = ws_offsets[n]
            raw = ws_data(n)
            start = _get_position(data, o, W_START)
            end = min(_get_position(data, o, W_END), len(raw) // 2 - 1)
            if end <= start:
                start, end = 0, len(raw) // 2 - 1
            count = end + 1 - start
            samples = decode_samples(raw[start * 2:(end + 1) * 2])
            keys = [k + FIRST_KEY for k in range(88) if P(lo, L_KEYMAP + k) == n]
            layer.wavesamples.append(Wavesample(
                name=_get_name(data, o), samples=samples, rate_code=P(o, W_RATE) or 20,
                root_key=P(o, W_ROOT_KEY), key_lo=keys[0], key_hi=keys[-1],
                loop_mode=P(o, W_LOOP_MODE),
                loop_start=max(0, min(_get_position(data, o, W_LOOP_START) - start, count - 2)),
                loop_end=max(1, min(_get_position(data, o, W_LOOP_END) - start, count - 1)),
                params=bytes(data[o:o + WS_PARAM_SIZE])))
        if layer.wavesamples:
            inst.layers.append(layer)
    return inst
