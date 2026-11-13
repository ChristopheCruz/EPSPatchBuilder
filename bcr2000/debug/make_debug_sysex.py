#!/usr/bin/env python3
"""Generate the single-message SysEx files used to debug the EPS side without the BCR2000.

Send them one at a time from a MIDI dump program (MIDI-OX, SysEx Librarian), with the EPS
MIDI OUT connected back to the computer so that its replies can be read.

Usage:
    python make_debug_sysex.py [OUTPUT_DIR] [INSTRUMENT 1-8] [LAYER 1-8] [WAVESAMPLE 1-127] [BASE_CHANNEL 1-16]

Message formats (Ensoniq EPS External Command Specification, June 12, 1989):
    VIRTUAL BUTTON  F0 0F 03 0n 40 | button                                  | F7
    GET PARAMETER   F0 0F 03 0n 08 | inst | layer | ws | parameter           | F7
    PUT PARAMETER   F0 0F 03 0n 11 | inst | layer | ws | parameter | value*2 | F7
Each field is a 12-bit word sent as two 6-bit bytes, high byte first.
"""
import os
import sys

args = sys.argv[1:]
OUT = args[0] if len(args) > 0 else "sysex"
INST = int(args[1]) if len(args) > 1 else 1
LAYER = int(args[2]) if len(args) > 2 else 1
WS = int(args[3]) if len(args) > 3 else 1
CHANNEL = int(args[4]) if len(args) > 4 else 1

HEAD = [0xF0, 0x0F, 0x03, CHANNEL - 1]


def word12(value):
    assert 0 <= value < 4096
    return [value >> 6, value & 63]


def value24(value):
    """A parameter value: 24 bits, right justified, as two 12-bit words."""
    return word12(value >> 12) + word12(value & 0xFFF)


def context(ws, inst=None):
    return word12((INST if inst is None else inst) - 1) + word12(LAYER - 1) + word12(ws)


def put(ws, page, item, value_bytes):
    return bytes(HEAD + [0x11] + context(ws) + word12(page * 256 + item) + value_bytes + [0xF7])


def get(ws, page, item, inst=None):
    return bytes(HEAD + [0x08] + context(ws, inst) + word12(page * 256 + item) + [0xF7])


def button(number):
    return bytes(HEAD + [0x40] + word12(number) + [0xF7])


VOLUME, CUTOFF1, CUTOFF2, F1_ENV2, F2_ENV2, MASTER_TUNE = (6, 1), (5, 1), (5, 11), (5, 2), (5, 12), (13, 2)

FILES = {
    # --- Does the EPS accept SysEx at all? Visible on its display, no sound needed.
    "01_button_EDIT.syx": button(19),
    "02_button_LOAD.syx": button(20),
    # --- Which instrument slots are loaded? Eight GET requests, one per slot.
    "03_scan_instruments_1_to_8.syx": b"".join(get(WS, *VOLUME, inst=i) for i in range(1, 9)),
    # --- Read a value back. The EPS answers ACK (F0 0F 03 0n 01 00 00 F7) then a PUT PARAMETER.
    "10_GET_volume.syx": get(WS, *VOLUME),
    "11_GET_cutoff1.syx": get(WS, *CUTOFF1),
    "12_GET_master_tune.syx": get(0, *MASTER_TUNE),
    # --- Writes to one wavesample: worked every time on the test machine.
    "20_volume_000.syx": put(WS, *VOLUME, value24(0)),
    "21_volume_100.syx": put(WS, *VOLUME, value24(100)),
    "22_volume_127.syx": put(WS, *VOLUME, value24(127)),
    "23_cutoff1_000.syx": put(WS, *CUTOFF1, value24(0)),
    "24_cutoff1_060.syx": put(WS, *CUTOFF1, value24(60)),
    "25_cutoff1_127.syx": put(WS, *CUTOFF1, value24(127)),
    "26_cutoff2_127.syx": put(WS, *CUTOFF2, value24(127)),
    "27_filter1_env2_amount_000.syx": put(WS, *F1_ENV2, value24(0)),
    "28_filter2_env2_amount_000.syx": put(WS, *F2_ENV2, value24(0)),
    "29_filter1_env2_amount_127.syx": put(WS, *F1_ENV2, value24(127)),
    # --- System parameter: instrument, layer and wavesample are irrelevant.
    "30_master_tune_127.syx": put(0, *MASTER_TUNE, value24(127)),
    "31_master_tune_000.syx": put(0, *MASTER_TUNE, value24(0)),
    # --- Known problem cases, kept to reproduce them.
    # Wavesample 0 = all wavesamples of the layer: applied, refused (status 17) or ignored,
    # depending on the state of the EPS front panel.
    "40_volume_000_all_wavesamples.syx": put(0, *VOLUME, value24(0)),
    "41_cutoff1_060_all_wavesamples.syx": put(0, *CUTOFF1, value24(60)),
    # Value 100 sent as one 7-bit byte (00 00 00 64) instead of two 6-bit bytes (00 00 01 24):
    # the EPS ignores it. This is the form the BCR2000 would have to use above 63.
    "42_cutoff1_100_as_one_7bit_byte_INVALID.syx": put(WS, *CUTOFF1, [0, 0, 0, 100]),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, data in FILES.items():
        with open(os.path.join(OUT, name), "wb") as handle:
            handle.write(data)
        print(f"{name:46s}", " ".join(f"{b:02X}" for b in data))


if __name__ == "__main__":
    main()
