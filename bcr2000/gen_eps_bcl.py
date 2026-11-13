#!/usr/bin/env python3
"""Generate a Behringer BCR2000 preset that edits Ensoniq EPS (classic) parameters over SysEx.

Every encoder sends one PUT PARAMETER command (11h), as described in the
"Ensoniq Performance Sampler External Command Specification" (June 12, 1989):

    F0 0F 03 0n 11 | instrument | layer | wavesample | parameter | value (2 words) | F7

Each field is a 12-bit word sent as two 6-bit bytes, high byte first.

What was learned on a real EPS and BCR2000 (see DEBUG_REPORT.md) and is built in here:

* Value range 0-63 only. The EPS needs values 64-127 as two 6-bit bytes, and BCL has no token
  that splits a value that way (its tokens are val, val0, val0.3, val4.7, val8.11, val12.13,
  val7.13, val1.7). A value sent as one 7-bit byte is ignored by the EPS, so every encoder is
  capped at 63 and sends "$00 val".
* One wavesample, not "all". Writes to wavesample 0 (all wavesamples of the layer) were
  applied, refused or ignored depending on the state of the EPS front panel. Writes to a
  numbered wavesample worked every time. The default target is wavesample 1.
* Slow output. The BCR2000 default transmission interval is 2 ms, which floods the EPS
  (ERROR 144). The preset sets the global interval to 100 ms, the maximum.

Usage:
    python gen_eps_bcl.py [OUTPUT_DIR] [INSTRUMENT 1-8] [LAYER 1-8] [WAVESAMPLE 0-127] [BASE_CHANNEL 1-16]

Writes EPS_BCR2000_I<i>_L<l>_WS<w>.bcl (BCL text) and .syx (the same BCL, one line per SysEx
message, for any MIDI dump program):
    F0 00 20 32 7F 15 20 <line index MSB> <line index LSB> <BCL line as ASCII> F7
(7F = any device ID, 15 = BCR2000, 20 = BCL message).
"""
import os
import sys

VALUE_CAP = 63        # highest value the BCR2000 can send in a form the EPS accepts
TX_INTERVAL_MS = 100  # BCR2000 global transmission interval: 2, 5, 10, 20, 50 or 100

# (name, page, item, max value, bipolar in the specification?)
# The parameter number is page * 256 + item (section 9 of the specification).
PARAMS = {
    # Push-encoder group 1: PITCH
    1: ("Fine Tune", 4, 10, 127, True), 2: ("Pitch LFO Amount", 4, 2, 127, False),
    3: ("Pitch Env1 Amount", 4, 3, 127, True), 4: ("Pitch Random Amount", 4, 12, 127, True),
    5: ("Pitch Random Freq", 4, 5, 127, False), 6: ("Bend Range", 4, 6, 13, False),
    7: ("Pitch Mod Amount", 4, 11, 127, True), 8: ("Pitch Mod Source", 4, 7, 15, False),
    # Push-encoder group 2: LFO / AMP MOD
    9: ("LFO Wave", 7, 1, 6, False), 10: ("LFO Speed", 7, 2, 99, False),
    11: ("LFO Depth", 7, 3, 127, False), 12: ("LFO Delay", 7, 4, 99, False),
    13: ("LFO Mode", 7, 5, 2, False), 14: ("LFO Mod Source", 7, 7, 15, False),
    15: ("Amp Mod Source", 6, 7, 15, False), 16: ("Amp Mod Amount", 6, 10, 127, False),
    # Push-encoder group 3: ENV2 (filter) levels
    17: ("ENV2 Level 0 Hard", 2, 1, 127, False), 18: ("ENV2 Level 1 Hard", 2, 11, 127, False),
    19: ("ENV2 Level 2 Hard", 2, 12, 127, False), 20: ("ENV2 Level 3 Hard", 2, 13, 127, False),
    21: ("ENV2 Level 4 Hard", 2, 14, 127, False), 22: ("ENV2 2nd Release Level", 2, 23, 127, True),
    23: ("ENV2 Mode", 2, 8, 2, False), 24: ("Filter Mode", 5, 0, 3, False),
    # Push-encoder group 4: ENV3 (amp) levels
    25: ("ENV3 Level 0 Hard", 3, 1, 127, False), 26: ("ENV3 Level 1 Hard", 3, 11, 127, False),
    27: ("ENV3 Level 2 Hard", 3, 12, 127, False), 28: ("ENV3 Level 3 Hard", 3, 13, 127, False),
    29: ("ENV3 Level 4 Hard", 3, 14, 127, False), 30: ("ENV3 2nd Release Level", 3, 23, 127, True),
    31: ("ENV3 Mode", 3, 8, 2, False), 32: ("Filter 1 Mod Source", 5, 7, 15, False),
    # Fixed row 1: FILTER / AMP
    33: ("Filter 1 Cutoff", 5, 1, 127, False), 34: ("Filter 2 Cutoff", 5, 11, 127, False),
    35: ("Filter 1 Env2 Amount", 5, 2, 127, True), 36: ("Filter 2 Env2 Amount", 5, 12, 127, True),
    37: ("Filter 1 Kbd Amount", 5, 3, 127, True), 38: ("Filter 1 Mod Amount", 5, 14, 127, True),
    39: ("Wavesample Volume", 6, 1, 127, False), 40: ("Pan", 6, 2, 17, False),
    # Fixed row 2: ENV2 times
    41: ("ENV2 Time 1", 2, 3, 99, False), 42: ("ENV2 Time 2", 2, 19, 99, False),
    43: ("ENV2 Time 3", 2, 20, 99, False), 44: ("ENV2 Time 4", 2, 21, 99, False),
    45: ("ENV2 Time 5", 2, 22, 99, False), 46: ("ENV2 2nd Release Time", 2, 4, 127, False),
    47: ("ENV2 Attack Time Vel", 2, 5, 99, False), 48: ("ENV2 Kbd Scaling", 2, 6, 127, False),
    # Fixed row 3: ENV3 times
    49: ("ENV3 Time 1", 3, 3, 99, False), 50: ("ENV3 Time 2", 3, 19, 99, False),
    51: ("ENV3 Time 3", 3, 20, 99, False), 52: ("ENV3 Time 4", 3, 21, 99, False),
    53: ("ENV3 Time 5", 3, 22, 99, False), 54: ("ENV3 2nd Release Time", 3, 4, 127, False),
    55: ("ENV3 Attack Time Vel", 3, 5, 99, False), 56: ("ENV3 Kbd Scaling", 3, 6, 127, False),
}



def word12(value):
    """A 12-bit word as two 6-bit MIDI bytes, high byte first."""
    assert 0 <= value < 4096
    return [value >> 6, value & 63]


def header(base_channel, instrument, layer, wavesample, page, item):
    """Everything before the value: SysEx head, command, edit context, parameter number."""
    return ([0xF0, 0x0F, 0x03, base_channel - 1, 0x11]
            + word12(instrument - 1) + word12(layer - 1) + word12(wavesample)
            + word12(page * 256 + item))


def preset_name(instrument, layer, wavesample):
    target = "ALL" if wavesample == 0 else f"WS{wavesample}"
    return f"EPS I{instrument} L{layer} {target} 0-{VALUE_CAP}"


def build(base_channel, instrument, layer, wavesample):
    target = "all wavesamples (unreliable)" if wavesample == 0 else f"wavesample {wavesample}"
    lines = [
        "; Ensoniq EPS (classic) - BCR2000 preset, SysEx PUT PARAMETER",
        f"; Target: instrument {instrument}, layer {layer}, {target}. EPS base channel = {base_channel}.",
        f"; Values 0-{VALUE_CAP} only. Global transmission interval set to {TX_INTERVAL_MS} ms.",
        "; No $store: the preset lands in the BCR2000 edit buffer. Press STORE to keep it.",
        "$rev R1",
        "$global",
        f"  .txinterval {TX_INTERVAL_MS}",
        "$preset",
        "  .name '%-24s'" % preset_name(instrument, layer, wavesample),
        "  .snapshot off",
        "  .request off",
        "  .egroups 4",
        "  .fkeys on",
        "  .lock off",
        "  .init",
    ]
    for number in range(1, 57):
        name, page, item, maximum, bipolar = PARAMS[number]
        top = min(maximum, VALUE_CAP)
        resolution = 48 if maximum >= 99 else (24 if maximum >= 13 else 12)
        head = " ".join(f"${b:02X}" for b in header(base_channel, instrument, layer, wavesample, page, item))
        notes = []
        if maximum > VALUE_CAP:
            notes.append(f"EPS range 0-{maximum}")
        if bipolar:
            notes.append("bipolar on the EPS, positive side only")
        note = f" [{'; '.join(notes)}]" if notes else ""
        lines += [
            f"$encoder {number} ; {name} ({page},{item}) 0-{top}{note}",
            "  .showvalue on",
            f"  .mode {'bar' if maximum >= 99 else '1dot'}",
            f"  .resolution {resolution} {resolution} {resolution} {resolution}",
            "  .default 0",
            f"  .minmax 0 {top}",
            f"  .tx {head} $00 $00 $00 val $F7",
        ]
    lines.append("$end")
    return lines


def to_sysex(lines):
    """Wrap BCL lines as BCR2000 SysEx messages, comments and blank lines removed."""
    data = bytearray()
    index = 0
    for line in lines:
        text = line.split(";")[0].rstrip()
        if not text.strip():
            continue
        payload = text.encode("ascii")
        assert all(byte < 0x80 for byte in payload)
        data += bytes([0xF0, 0x00, 0x20, 0x32, 0x7F, 0x15, 0x20, (index >> 7) & 0x7F, index & 0x7F])
        data += payload + b"\xF7"
        index += 1
    return bytes(data)


def self_check(base_channel, instrument, layer, wavesample):
    """Simulate every encoder's output and decode it back the way the specification describes."""
    # Specification example: "Free System Blocks" (page 13, item 0) is sent as $34 $00.
    assert word12(13 * 256 + 0) == [0x34, 0x00]
    assert sorted(PARAMS) == list(range(1, 57))
    assert len({(p[1], p[2]) for p in PARAMS.values()}) == 56, "duplicate parameter"
    for name, page, item, maximum, _ in PARAMS.values():
        for value in {0, 1, min(maximum, VALUE_CAP)}:
            message = header(base_channel, instrument, layer, wavesample, page, item) + [0, 0, 0, value, 0xF7]
            assert len(message) == 18 and all(b < 64 for b in message[5:-1]), name
            data = message[5:-1]
            words = [data[i] * 64 + data[i + 1] for i in range(0, len(data), 2)]
            assert words[:3] == [instrument - 1, layer - 1, wavesample], name
            assert (words[3] >> 8, words[3] & 255) == (page, item), name
            assert words[4] * 4096 + words[5] == value, name


def main():
    args = sys.argv[1:]
    out_dir = args[0] if len(args) > 0 else "."
    instrument = int(args[1]) if len(args) > 1 else 1
    layer = int(args[2]) if len(args) > 2 else 1
    wavesample = int(args[3]) if len(args) > 3 else 1
    base_channel = int(args[4]) if len(args) > 4 else 1
    if not (1 <= instrument <= 8 and 1 <= layer <= 8 and 0 <= wavesample <= 127 and 1 <= base_channel <= 16):
        sys.exit("instrument 1-8, layer 1-8, wavesample 0-127 (0 = all, unreliable), base channel 1-16")

    self_check(base_channel, instrument, layer, wavesample)
    os.makedirs(out_dir, exist_ok=True)
    lines = build(base_channel, instrument, layer, wavesample)
    base = f"EPS_BCR2000_I{instrument}_L{layer}_" + ("ALL" if wavesample == 0 else f"WS{wavesample}")
    path = os.path.join(out_dir, base + ".bcl")
    with open(path, "w", newline="\r\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("wrote", path)
    path = os.path.join(out_dir, base + ".syx")
    with open(path, "wb") as handle:
        handle.write(to_sysex(lines))
    print("wrote", path)


if __name__ == "__main__":
    main()
