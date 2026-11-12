# BCR2000 preset for the Ensoniq EPS

A Behringer BCR2000 preset that edits the sound parameters of an **Ensoniq EPS (classic)** in real
time over MIDI System Exclusive, plus a printable A4 overlay that labels the encoders.

> **Status: untested on hardware.** The preset was generated from Ensoniq's official SysEx
> specification and checked by decoding its own output, but it has not yet been run against a
> real BCR2000 or EPS. See [What still needs checking](#what-still-needs-checking).

## Files

| File | Purpose |
|---|---|
| `EPS_BCR2000_I1_L1.bcl` | Main preset as BCL text: instrument 1, layer 1, all wavesamples |
| `EPS_BCR2000_I1_L1.syx` | The same preset as a SysEx dump, to send without an editor |
| `EPS_BCR2000_I1_L1_7bit_variant.bcl` / `.syx` | Fallback preset if the BCR2000 rejects the 6-bit value split |
| `gen_eps_bcl.py` | Generator, to target another instrument, layer, wavesample or base channel |
| `overlay/bcr2000_overlay_a4.pdf` | Printable overlay, two A4 landscape sheets |
| `overlay/bcr2000_overlay_a4.html` | Source of the overlay, to edit the labels |

## How it works

The EPS has no CC or NRPN per parameter. It is edited with the **PUT PARAMETER** command (`11h`)
of its External Command Specification. Every encoder of the preset sends one 18-byte message:

```
F0 0F 03 0n 11  [instrument] [layer] [wavesample] [parameter] [value hi] [value lo]  F7
```

- `0n` is the EPS base MIDI channel (`00` = channel 1).
- Each field is a 12-bit word sent as two 6-bit bytes, high byte first.
- Instrument 0-7, layer 0-7, wavesample 1-127. **Wavesample 0 edits every wavesample of the layer.**
- Parameter number = page × 256 + item. On the wire: first byte = page × 4, second byte = item.
- The value is a 24-bit number, right justified, sent as two 12-bit words.
- The EPS sends no reply unless the parameter number or value is invalid.

Example, Filter 1 Cutoff = 100 on instrument 1, layer 1, all wavesamples:

```
F0 0F 03 00 11 00 00 00 00 00 00 14 01 00 00 01 24 F7
```

Parameter pages: 1-3 = ENV1-ENV3, 4 = Pitch, 5 = Filter, 6 = Volume, 7 = LFO, 8 = Wavesample,
9 = Layer, 10 = Instrument, 12 = MIDI, 13 = System, 14 = Edit.

## Mapping

Numbers in brackets are (page, item). The buttons are not used.

**Push encoders (top row, four encoder groups)**

| # | Group 1: Pitch | Group 2: LFO | Group 3: ENV2 (filter) levels | Group 4: ENV3 (amp) levels |
|---|---|---|---|---|
| 1 | Fine Tune (4,10) + | LFO Wave (7,1) | Level 0 Hard (2,1) | Level 0 Hard (3,1) |
| 2 | LFO Amount (4,2) | LFO Speed (7,2) | Level 1 Hard (2,11) | Level 1 Hard (3,11) |
| 3 | Env1 Amount (4,3) + | LFO Depth (7,3) | Level 2 Hard (2,12) | Level 2 Hard (3,12) |
| 4 | Random Amount (4,12) + | LFO Delay (7,4) | Level 3 Hard (2,13) | Level 3 Hard (3,13) |
| 5 | Random Freq (4,5) | LFO Mode (7,5) | Level 4 Hard (2,14) | Level 4 Hard (3,14) |
| 6 | Bend Range (4,6) | LFO Mod Source (7,7) | 2nd Release Level (2,23) + | 2nd Release Level (3,23) + |
| 7 | Pitch Mod Amount (4,11) + | Amp Mod Source (6,7) | Env Mode (2,8) | Env Mode (3,8) |
| 8 | Pitch Mod Source (4,7) | Amp Mod Amount (6,10) | Filter Mode (5,0) | Filter 1 Mod Source (5,7) |

**The three fixed encoder rows**

| # | Row 1: Filter / Amp | Row 2: ENV2 times | Row 3: ENV3 times |
|---|---|---|---|
| 1 | Filter 1 Cutoff (5,1) | Time 1 (2,3) | Time 1 (3,3) |
| 2 | Filter 2 Cutoff (5,11) | Time 2 (2,19) | Time 2 (3,19) |
| 3 | Filter 1 Env2 Amount (5,2) + | Time 3 (2,20) | Time 3 (3,20) |
| 4 | Filter 2 Env2 Amount (5,12) + | Time 4 (2,21) | Time 4 (3,21) |
| 5 | Filter 1 Kbd Amount (5,3) + | Time 5 (2,22) | Time 5 (3,22) |
| 6 | Filter 1 Mod Amount (5,14) + | 2nd Release Time (2,4) | 2nd Release Time (3,4) |
| 7 | Wavesample Volume (6,1) | Attack Time Vel (2,5) | Attack Time Vel (3,5) |
| 8 | Pan (6,2) | Kbd Scaling (2,6) | Kbd Scaling (3,6) |

`+` marks a parameter that the specification defines as -127 to +127. The preset only sends the
positive half (0 to +127), see below.

Not mapped: ENV1 (pitch envelope), the "Soft" envelope levels, loop points, key ranges, root key
and the layer parameters (glide, velocity window).

## Setup

1. On the EPS: Edit / MIDI, set **MIDI SYS-EX = ON** and base channel 1.
2. Load an instrument into instrument slot 1.
3. Send the preset to the BCR2000, either way:
   - open the `.bcl` file in [BC Manager](https://mountainutilities.eu) and send it from there
     (BC Manager also reports any line the BCR2000 rejects), or
   - send the `.syx` file with any MIDI dump program such as MIDI-OX or SysEx Librarian. If the
     transfer fails, add a short delay between SysEx messages in that program.

   The preset lands in the edit buffer without overwriting a memory slot; press STORE on the
   BCR2000 to keep it.
4. Connect BCR2000 MIDI OUT to EPS MIDI IN.
5. Start with Filter 1 Cutoff while holding a note.

To target something else:

```
python gen_eps_bcl.py OUTPUT_DIR INSTRUMENT LAYER WAVESAMPLE BASE_CHANNEL
python gen_eps_bcl.py . 2 1 0 1      # instrument 2, layer 1, all wavesamples, base channel 1
```

The generator writes both the `.bcl` and the `.syx` of each preset. A `.syx` file is the BCL text
with one line per SysEx message (`F0 00 20 32 7F 15 20 <index MSB> <index LSB> <line> F7`),
comments removed.

## What still needs checking

- **BCL value syntax.** The EPS wants the value as two 6-bit bytes, written here as
  `val6.11 val0.5`. It is not confirmed that the BCR2000 accepts this bit range. If BC Manager
  rejects the main file, or the encoders send nothing after loading the main `.syx`, use the
  `7bit_variant` files: they send `$00 val`, which is exact for values 0 to 63 and unverified
  above that.
- **Message rate.** With a one-way cable, the specification asks the sender to wait 2 seconds
  between commands. That is probably conservative, but turn the encoders slowly at first and see
  whether the EPS keeps up.
- **Negative values.** The specification does not say how negative values are encoded, so the
  bipolar parameters are limited to 0 to +127 for now.

Known limits:

- With "all wavesamples", Volume and Pan give every wavesample of the layer the same value, which
  flattens any per-wavesample balance.
- The EPS does not report its current values, so the BCR2000 LED rings do not reflect the loaded
  sound, and a parameter jumps to the encoder position as soon as the encoder is turned.

## Overlay

`overlay/bcr2000_overlay_a4.pdf` holds two A4 landscape sheets: one piece for the push-encoder
row and the two button rows, one piece for the three fixed encoder rows. The PDF is printed from
`overlay/bcr2000_overlay_a4.html`; edit that file and print it to PDF from a browser to change
the labels.

- Print at **100 %** ("actual size", no fit-to-page). Each sheet has a 100 mm check line.
- The dimensions (28.6 mm encoder pitch, 26 mm holes) were taken from the BCR2000 overlay
  template of the Mixxx manual, not measured on a device. Print a test on plain paper and check
  the holes against the encoders before cutting the final one.
- The overlay covers the eight encoder columns, not the right-hand section of the BCR2000
  (display and function keys), which the preset does not use.

## Sources

- *Ensoniq Performance Sampler External Command Specification*, June 12, 1989 (MKB2). A scan is
  available in the [epstool repository](https://github.com/mikewolak/epstool) under `references/`.
- BCL language: *BC MIDI Implementation* and the BC Manager manual,
  [Mountain Utilities](https://mountainutilities.eu).
- Overlay dimensions: Behringer BCR2000 overlay template in the [Mixxx manual repository](https://github.com/mixxxdj/manual) (`source/_static/controllers/`).
