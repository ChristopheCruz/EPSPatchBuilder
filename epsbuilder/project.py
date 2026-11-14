"""Fonctions de haut niveau : fichiers WAV -> instrument -> disquette."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace

from .i18n import T
from . import audio, instrument as ins
from .disk import EnsoniqDisk, TYPE_EPS_INSTRUMENT

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d)$")
_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

DEFAULT_RATE_HZ = 31250.0


def note_to_midi(text: str) -> int:
    """« C4 », « F#3 », « Bb2 » ou un numero MIDI. Convention : C4 = 60."""
    text = text.strip()
    if text.isdigit():
        value = int(text)
    else:
        m = _NOTE_RE.match(text)
        if not m:
            raise ValueError(T("Note invalide : {0!r} (exemples : C4, F#3, 60)").format(text))
        value = _SEMITONE[m.group(1).upper()] + {"#": 1, "b": -1, "": 0}[m.group(2)] + 12 * (int(m.group(3)) + 1)
    if not 0 <= value <= 127:
        raise ValueError(T("Note hors limites : {0!r}").format(text))
    return value


def midi_to_note(key: int) -> str:
    return f"{NOTE_NAMES[key % 12]}{key // 12 - 1}"


@dataclass
class SoundEdit:
    """Reglages d'un son. Les positions sont en echantillons du son d'origine."""
    start: int | None = None           # None : automatique (silence coupe si l'option est active)
    end: int | None = None             # dernier echantillon garde ; None : automatique
    rate_code: int | None = None       # None : frequence de l'instrument
    bits: int = 13                     # resolution (13 = maximum de l'EPS classique)
    compress: int = 0                  # compression de dynamique, 0 a 100
    fade_in_ms: float = 0.0
    fade_out_ms: float = 0.0
    loop_mode: int = ins.LOOP_FORWARD_NO_LOOP
    loop_start: int | None = None      # None : debut du son
    loop_end: int | None = None        # None : fin du son

    @property
    def looped(self) -> bool:
        return self.loop_mode >= ins.LOOP_FORWARD


def process_sound(samples, rate: float, edit: SoundEdit, default_code: int, normalize: bool, trim: bool,
                  allow_upsample: bool = False):
    """Applique les reglages a un son. Retourne (echantillons, code de frequence, mode de boucle,
    debut de boucle, fin de boucle), les positions etant dans le son produit."""
    n = len(samples)
    auto = audio.trim_bounds(samples) if trim else (0, n - 1)
    a = auto[0] if edit.start is None else max(0, min(int(edit.start), n - 2))
    b = auto[1] if edit.end is None else max(a + 1, min(int(edit.end), n - 1))
    b = max(b, min(a + 15, n - 1))
    x = samples[a:b + 1]
    if edit.compress > 0:
        x = audio.compress(x, rate, edit.compress)
    code = edit.rate_code or default_code
    if not allow_upsample:
        code = ins.rate_code_for(min(ins.rate_hz(code), rate))
    out_rate = ins.rate_hz(code)
    ratio = out_rate / rate
    x = audio.resample(x, rate, out_rate)
    x = audio.apply_fades(x, out_rate, edit.fade_in_ms, edit.fade_out_ms)
    if normalize:
        x = audio.normalize(x)
    x = audio.reduce_bits(x, edit.bits)
    mode, ls, le = edit.loop_mode, None, None
    if edit.looped and len(x) > 16:
        src_ls = a if edit.loop_start is None else edit.loop_start
        src_le = b if edit.loop_end is None else edit.loop_end
        ls = max(0, min(int(round((src_ls - a) * ratio)), len(x) - 2))
        le = max(ls + 1, min(int(round((src_le - a) * ratio)), len(x) - 1))
    elif edit.looped:
        mode = ins.LOOP_FORWARD_NO_LOOP
    return x, code, mode, ls, le


@dataclass
class SampleSpec:
    path: str
    root_key: int | None = None        # None : lue dans le WAV si possible, sinon C4
    key_lo: int | None = None          # None : zones reparties automatiquement
    key_hi: int | None = None
    loop: bool = False                 # boucler (points lus dans le WAV, sinon tout le son)
    name: str | None = None
    wavesample: ins.Wavesample | None = None   # son deja present dans un instrument (edition)
    edit: SoundEdit | None = None      # reglages detailles (debut, fin, boucle, compression...)
    sound: audio.Sound | None = None   # son deja lu (evite de relire le fichier)


def auto_zones(roots: list[int]) -> list[tuple[int, int]]:
    """Repartit le clavier entre les sons : chaque frontiere est a mi-chemin entre deux notes de base."""
    order = sorted(range(len(roots)), key=lambda i: roots[i])
    zones = [None] * len(roots)
    lo = ins.FIRST_KEY
    for pos, i in enumerate(order):
        if pos + 1 < len(order):
            hi = (roots[i] + roots[order[pos + 1]]) // 2
            hi = max(lo, min(hi, ins.LAST_KEY - (len(order) - pos - 1)))
        else:
            hi = ins.LAST_KEY
        zones[i] = (lo, hi)
        lo = hi + 1
    return zones


@dataclass
class LayerSpec:
    """Un layer de l'instrument a construire."""
    specs: list[SampleSpec]
    name: str = "UNNAMEDLAYER"
    vel_lo: int = 0
    vel_hi: int = 127
    patches: frozenset[int] | None = None      # None : reglage par defaut de l'EPS
    base: ins.Layer | None = None              # layer d'origine (instrument relu) : emplacement et reglages
    slot: int | None = None                    # emplacement 0-7 ; None : celui du layer d'origine, sinon le premier libre


def _loop_only(edit: SoundEdit, src: ins.Wavesample) -> bool:
    """Les reglages ne touchent que la boucle d'un son deja present (rien a recalculer)."""
    n = len(src.samples)
    return (edit.start in (None, 0) and edit.end in (None, n - 1) and edit.rate_code in (None, src.rate_code)
            and edit.bits == 13 and edit.compress == 0 and not edit.fade_in_ms and not edit.fade_out_ms)


def make_wavesamples(specs: list[SampleSpec], rate_hz: float | None = DEFAULT_RATE_HZ, normalize: bool = True,
                     trim: bool = True, envelope: str = ins.ENV_SUSTAIN) -> list[ins.Wavesample]:
    """Les sons d'un layer.

    Chaque element est soit un fichier audio (converti a rate_hz, 52 kHz au plus, None = frequence
    du fichier), soit un son deja present dans un instrument (spec.wavesample). Sans reglages
    (spec.edit), ce dernier est repris tel quel ; avec, il est retravaille en gardant ses autres
    parametres.
    """
    if not specs:
        raise ValueError(T("Aucun son"))
    sounds, roots = [], []
    for spec in specs:
        if spec.wavesample is not None:
            snd = None
            root = spec.root_key if spec.root_key is not None else spec.wavesample.root_key
        else:
            snd = spec.sound if spec.sound is not None else audio.read_sound(spec.path)
            root = spec.root_key if spec.root_key is not None else (snd.root_key if snd.root_key is not None else 60)
        sounds.append(snd)
        roots.append(root)
    zones = auto_zones(roots)
    out: list[ins.Wavesample] = []
    for spec, snd, root, zone in zip(specs, sounds, roots, zones):
        key_lo = spec.key_lo if spec.key_lo is not None else zone[0]
        key_hi = spec.key_hi if spec.key_hi is not None else zone[1]
        if spec.wavesample is not None:
            src = spec.wavesample
            ws = replace(src, name=spec.name or src.name, root_key=root, key_lo=key_lo, key_hi=key_hi)
            if spec.edit is not None and _loop_only(spec.edit, src):
                # Seule la boucle change : le son garde ses echantillons (et leur partage eventuel).
                ws.loop_mode = spec.edit.loop_mode
                if spec.edit.looped:
                    n = len(src.samples)
                    ls = 0 if spec.edit.loop_start is None else max(0, min(int(spec.edit.loop_start), n - 2))
                    le = n - 1 if spec.edit.loop_end is None else max(ls + 1, min(int(spec.edit.loop_end), n - 1))
                    ws.loop_start, ws.loop_end = ls, le
            elif spec.edit is not None:
                # Son de la disquette retravaille : niveau conserve, sauf apres compression.
                x, code, mode, ls, le = process_sound(src.samples, src.rate, spec.edit, src.rate_code,
                                                      normalize=spec.edit.compress > 0, trim=False,
                                                      allow_upsample=True)
                ws.samples, ws.rate_code, ws.loop_mode, ws.loop_start, ws.loop_end = x, code, mode, ls, le
                ws.detach()                            # nouveaux echantillons, propres a ce son
            else:
                was_looped = src.loop_mode >= ins.LOOP_FORWARD
                if spec.loop and not was_looped:
                    ws.loop_mode = ins.LOOP_FORWARD
                    if not (src.loop_start is not None and src.loop_end is not None and 0 <= src.loop_start < src.loop_end):
                        ws.loop_start, ws.loop_end = 0, len(src.samples) - 1
                elif not spec.loop and was_looped:
                    ws.loop_mode = ins.LOOP_FORWARD_NO_LOOP
            out.append(ws)
            continue
        edit = spec.edit
        if edit is None:
            edit = SoundEdit(loop_mode=ins.LOOP_FORWARD if spec.loop else ins.LOOP_FORWARD_NO_LOOP,
                             loop_start=snd.loop_start, loop_end=snd.loop_end)
        default_code = ins.rate_code_for(rate_hz) if rate_hz else ins.rate_code_for(min(snd.rate, 52100.0))
        x, code, mode, ls, le = process_sound(snd.samples, snd.rate, edit, default_code, normalize, trim)
        out.append(ins.Wavesample(
            name=(spec.name or os.path.splitext(os.path.basename(spec.path))[0]),
            samples=x, rate_code=code, root_key=root, envelope=envelope, key_lo=key_lo, key_hi=key_hi,
            loop_mode=mode, loop_start=ls, loop_end=le))
    return out


def make_layered_instrument(name: str, layers: list[LayerSpec], rate_hz: float | None = DEFAULT_RATE_HZ,
                            normalize: bool = True, trim: bool = True, envelope: str = ins.ENV_SUSTAIN,
                            base: ins.Instrument | None = None) -> ins.Instrument:
    """Cree un instrument de 1 a 8 layers. base : instrument d'origine (modification) dont on
    conserve l'etendue et les reglages generaux ; chaque LayerSpec.base garde ceux de son layer."""
    if not layers:
        raise ValueError(T("Aucun layer"))
    if len(layers) > ins.MAX_LAYERS:
        raise ins.InstrumentError(T("Un instrument contient de 1 a 8 layers"))
    built = []
    for spec in layers:
        if not spec.specs:
            raise ins.InstrumentError(T("Le layer « {0} » est vide").format(spec.name.strip()))
        ws = make_wavesamples(spec.specs, rate_hz, normalize, trim, envelope)
        b = spec.base
        slot = spec.slot if spec.slot is not None else (b.slot if b is not None else None)
        built.append(ins.Layer(spec.name, ws, spec.vel_lo, spec.vel_hi, spec.patches, slot,
                               b.params if b is not None else None))
    every = [w for layer in built for w in layer.wavesamples]
    if len(every) > ins.MAX_WAVESAMPLES:
        raise ins.InstrumentError(T("Un instrument contient au maximum 127 sons"))
    if base is not None:
        return ins.Instrument(name, built, key_lo=base.key_lo, key_hi=base.key_hi, params=base.params)
    lo = min(w.key_lo for w in every)
    hi = max(w.key_hi for w in every)
    return ins.Instrument(name, built, key_lo=min(36, max(lo, ins.FIRST_KEY)), key_hi=max(96, min(hi, ins.LAST_KEY)))


def make_instrument(name: str, specs: list[SampleSpec], rate_hz: float | None = DEFAULT_RATE_HZ,
                    normalize: bool = True, trim: bool = True,
                    envelope: str = ins.ENV_SUSTAIN, base: ins.Instrument | None = None) -> ins.Instrument:
    """Cree un instrument a un layer (voir make_wavesamples). base : instrument d'origine dont on
    conserve l'etendue, les reglages et le premier layer."""
    first = base.layers[0] if base is not None and base.layers else None
    layer = LayerSpec(specs)
    if first is not None:
        layer = LayerSpec(specs, first.name, first.vel_lo, first.vel_hi, first.patches, first)
    return make_layered_instrument(name, [layer], rate_hz, normalize, trim, envelope, base)


def add_instrument(disk: EnsoniqDisk, inst: ins.Instrument) -> int:
    """Ecrit l'instrument sur la disquette ; retourne sa taille en blocs."""
    data = ins.build_instrument(inst)
    disk.add_file(inst.name, TYPE_EPS_INSTRUMENT, data)
    return len(data) // 512


def describe_instrument(inst: ins.Instrument) -> list[str]:
    lines = []
    for li, layer in enumerate(inst.layers, 1):
        lines.append(T("  Layer {0} ({1}), velocite {2}-{3}").format(li, layer.name.strip(), layer.vel_lo, layer.vel_hi))
        for ws in layer.wavesamples:
            loop = ins.LOOP_MODE_NAMES[ws.loop_mode] if ws.loop_mode < 5 else f"mode {ws.loop_mode}"
            extra = f" [{ws.loop_start}-{ws.loop_end}]" if ws.loop_mode >= 2 else ""
            lines.append(T("    {0:12s} {1:7d} ech. {2:7.0f} Hz ({3:5.2f} s)  base {4:4s} zone {5}-{6}  {7}{8}").format(ws.name.strip(), len(ws.samples), ws.rate, len(ws.samples) / ws.rate, midi_to_note(ws.root_key), midi_to_note(ws.key_lo), midi_to_note(ws.key_hi), loop, extra))
    return lines
