# BCR2000 preset for the Ensoniq EPS

A Behringer BCR2000 preset that edits the sound parameters of an **Ensoniq EPS (classic)** in real
time over MIDI System Exclusive, plus a printable A4 overlay that labels the encoders.

> **Status: partly verified on hardware.** The message format and writes to a numbered
> wavesample are confirmed on a real EPS, and the BCR2000 is confirmed to send well-formed
> messages. The current preset has not yet been confirmed end to end. Two limits are known:
> values 0–63 only, and one wavesample at a time. See [DEBUG_REPORT.md](DEBUG_REPORT.md).

## Files

| File | Purpose |
|---|---|
| `EPS_BCR2000_I1_L1_WS1.bcl` | Preset as BCL text: instrument 1, layer 1, wavesample 1 |
| `EPS_BCR2000_I1_L1_WS1.syx` | The same preset as a SysEx dump, to send without an editor |
| `gen_eps_bcl.py` | Generator, to target another instrument, layer, wavesample or base channel |
| `DEBUG_REPORT.md` | What was tested on the machines, what works, what does not, and how to debug |
| `debug/sysex/` | Single-message test files for the EPS (buttons, read, write) |
| `debug/make_debug_sysex.py` | Regenerates the test files for another target |
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
- Instrument 0-7, layer 0-7, wavesample 1-127.
- Parameter number = page × 256 + item. On the wire: first byte = page × 4, second byte = item.
- The value is a 24-bit number, right justified, sent as two 12-bit words.
- The EPS sends no reply on success, and a status reply on error.

Example, Filter 1 Cutoff = 60 on instrument 1, layer 1, wavesample 1:

```
F0 0F 03 00 11 00 00 00 00 00 01 14 01 00 00 00 3C F7
```

Parameter pages: 1-3 = ENV1-ENV3, 4 = Pitch, 5 = Filter, 6 = Volume, 7 = LFO, 8 = Wavesample,
9 = Layer, 10 = Instrument, 12 = MIDI, 13 = System, 14 = Edit.

## Limits

- **Values 0–63 only.** The EPS needs values 64–127 as two 6-bit bytes, and the BCR2000 preset
  language cannot split a value that way. Every encoder is capped at 63.
- **One wavesample.** The preset addresses wavesample 1. Wavesample 0 ("all wavesamples of the
  layer") exists in the specification but gave inconsistent results on the test machine.
- **Positive values only** for the parameters that are bipolar on the EPS (marked `+` below).
- **No feedback.** The EPS does not report its values to the BCR2000, so the LED rings do not
  reflect the loaded sound. After a preset load every encoder is at 0: turning left sends
  nothing, and a parameter jumps to the encoder value at the first step to the right.
- **A fixed target.** Instrument slot, layer and wavesample are written into the preset.

A bridge program on a computer would remove the first three; see the end of the debug report.

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

Not mapped: ENV1 (pitch envelope), the "Soft" envelope levels, loop points, key ranges, root key
and the layer parameters (glide, velocity window).

## Setup

1. **EPS.** Edit / MIDI: MIDI SYS-EX = ON and base channel 1; check both again after a power
   cycle. Load the sound into instrument slot 1 and stay in Edit mode.
2. **Send the preset to the BCR2000**, either way:
   - open the `.bcl` file in [BC Manager](https://mountainutilities.eu) and send it from there, or
   - send the `.syx` file with a MIDI dump program such as MIDI-OX, with a delay between SysEx
     messages (200 ms worked) and no MIDI loop: nothing may route the BCR2000 replies back to
     the BCR2000. `Er22` on its display means a line was lost; resend from the start.
3. **Press STORE on the BCR2000**, pick a preset number, press STORE again. Until then the
   preset is in a temporary buffer.
4. Connect BCR2000 MIDI OUT A to EPS MIDI IN.
5. Turn slowly. The preset sets the BCR2000 global transmission interval to 100 ms (factory
   value 2 ms) so that the EPS is not flooded; this setting applies to all BCR2000 presets and
   can be changed back in its global menu (EDIT + STORE, push encoder 8).

On sounds made with EPS Builder, both Filter Env2 Amounts start at +127 and hold the filters
open, so the cutoffs seem to do nothing. Lower Filter 1 Env2 Amount first (turn right, then
fully left), then use Filter 1 Cutoff.

If the EPS shows `ERROR 144 – REBOOT?`, it received too much MIDI data. Accept the reboot and
reload the sound.

To target something else:

```
python gen_eps_bcl.py OUTPUT_DIR INSTRUMENT LAYER WAVESAMPLE BASE_CHANNEL
python gen_eps_bcl.py . 2 1 1 1      # instrument 2, layer 1, wavesample 1, base channel 1
```

A `.syx` preset is the BCL text with one line per SysEx message
(`F0 00 20 32 7F 15 20 <index MSB> <index LSB> <line> F7`), comments removed.

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
- BCL language: [*B-Control MIDI Implementation* 1.2.6](https://zwizwa.be/darcs/bcr2000/doc/BC.MIDI.Implementation.pdf)
  and the BC Manager manual, [Mountain Utilities](https://mountainutilities.eu).
- Overlay dimensions: Behringer BCR2000 overlay template in the
  [Mixxx manual repository](https://github.com/mixxxdj/manual) (`source/_static/controllers/`).
