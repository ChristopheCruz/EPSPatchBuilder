# Debugging report: BCR2000 → Ensoniq EPS over SysEx

Session of 12–13 November 2026, on real hardware.

**Outcome so far.** The EPS side is understood and verified by read-back: the message format is
right, and writes to a numbered wavesample work. The BCR2000 side is verified up to its MIDI
output: it sends well-formed messages. The current preset (`EPS_BCR2000_I1_L1_WS1`) was built
from these findings but **has not yet been confirmed end to end** (BCR2000 knob → audible or
read-back change on the EPS). Two limits are structural: the BCR2000 can only send values 0–63
in a form the EPS accepts, and "all wavesamples" writes are not reliable.

## Setup

| Item | Detail |
|---|---|
| Sampler | Ensoniq EPS (classic), sound loaded in instrument slot 1 |
| Controller | Behringer BCR2000, MIDI OUT A |
| Interface | M-Audio MIDISPORT 2x2 |
| Tools | MIDI-OX (send `.syx`, monitor input), Behringer B-Control Edit for the first load attempt |
| Reference | *Ensoniq Performance Sampler External Command Specification*, 12 June 1989; *B-Control MIDI Implementation* 1.2.6 |

## What is confirmed

Each line was observed on the machines, most of them by reading the value back with GET PARAMETER.

### EPS

1. **SysEx header and word format.** `F0 0F 03 0n`, then a command byte, then 12-bit words sent
   as two 6-bit bytes. Confirmed by every exchange below.
2. **VIRTUAL BUTTON PRESS (40h) works.** `F0 0F 03 00 40 00 13 F7` switches the EPS to Edit,
   `… 00 14 F7` to Load. Button numbers are the decimal values of the specification table.
3. **GET PARAMETER (08h) works.** The EPS answers with an ACK, then a PUT PARAMETER carrying
   the value:

   ```
   sent      F0 0F 03 00 08 00 00 00 00 00 01 14 01 F7
   received  F0 0F 03 00 01 00 00 F7
             F0 0F 03 00 11 00 00 00 00 00 01 14 01 00 00 00 00 F7     (Filter 1 Cutoff = 0)
   ```

4. **Values above 63 use two 6-bit bytes.** The EPS reports volume 127 as `01 3F` and 85 as
   `01 15`.
5. **PUT PARAMETER (11h) to a numbered wavesample works, silently.** Volume = 0 and Filter 1
   Cutoff = 0 on instrument 1, layer 1, wavesample 1 were both read back as 0. The EPS sends no
   reply on success.
6. **The EPS transmits its own front-panel edits in the same format.** Switching MIDI SYS-EX to
   ON on the panel produced `F0 0F 03 00 11 00 00 00 00 00 00 30 05 00 00 00 01 F7` (page 12,
   item 5, value 1). Editing a parameter by hand is therefore a way to capture reference
   messages.
7. **A value sent as one 7-bit byte is ignored.** Cutoff = 100 sent as `00 00 00 64` (instead of
   `00 00 01 24`) left the cutoff unchanged, with no error reply.
8. **Status codes seen.**

   | Reply | Code | When |
   |---|---|---|
   | `… 01 00 00 F7` | 00 ACK | Before the answer to a GET |
   | `… 01 00 05 F7` | 05 INVALID INSTRUMENT | GET on an empty instrument slot |
   | `… 01 00 17 F7` | 17 NAK | PUT on an empty instrument slot; also PUT "all wavesamples" in one case below |
   | `… 01 00 07 F7` | 07 LAYER IN USE | Seen once, unexplained (see open questions) |

9. **ERROR 144 – REBOOT?** appeared twice when the EPS was flooded with MIDI data. The Ensoniq
   service manual lists excessive MIDI data as a cause. A reboot clears RAM, so the sound must
   be reloaded.

### BCR2000

1. **BCL value tokens are a fixed list:** `val`, `val0.6`, `val0`, `val0.3`, `val4.7`,
   `val8.11`, `val12.13`, `val7.13`, `val1.7`. The first preset used `val6.11 val0.5`, which is
   not in the list, so its encoders had no valid output.
2. **The preset loads over MIDI from a plain `.syx` dump** once two conditions are met: a delay
   between SysEx messages (200 ms worked) and no MIDI loop through the computer.
3. **`Er22` on the BCR2000 display** is BCL error 22, invalid message index: a line was lost or
   repeated during the transfer.
4. **The BCR2000 sends well-formed messages.** Captured from MIDI OUT A:
   `F0 0F 03 00 11 00 00 00 00 00 00 10 0C 00 00 00 60 F7` (18 bytes, correct addressing).
5. **Default transmission interval is 2 ms.** At that rate a turned encoder floods the EPS.
   The preset now sets `.txinterval 100`, the maximum the BCR2000 accepts.
6. **Encoders start at 0 after a preset load.** Turning left sends nothing; to send 0, turn right
   first and come back.

## Problems met, in order

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | Filter cutoff messages made no audible difference | The sound's Filter Env2 Amounts are +127, so ENV2 already holds both filters open | Lower Env2 Amount first, or check by read-back instead of by ear |
| 2 | BCR2000 did nothing after loading the preset | Invalid BCL tokens `val6.11 val0.5`; the BCR2000 was still sending factory Control Changes | Use valid tokens only |
| 3 | `Er22` during preset upload | Lines lost in transfer | Delay between SysEx messages |
| 4 | MIDI-OX "SysEx: No Buffers Available", input flooded with Channel Aftertouch | MIDI loop: MIDI-OX routed its input back to its output, so BCR2000 replies went back to the BCR2000 | Remove the input→output routing in MIDI-OX, or unplug the return cable during upload |
| 5 | EPS "ERROR 144 – REBOOT?" (twice) | Flood of SysEx: MIDI loop, then BCR2000 at 2 ms interval | `.txinterval 100`, lower encoder resolution, turn slowly |
| 6 | BCR2000 messages reached the EPS but changed nothing | Three causes stacked: values above 63 sent as one byte (ignored), "all wavesamples" addressing (unreliable), and pitch-group encoders with no audible effect on this sound | Cap values at 63, address wavesample 1, test with filter or volume |
| 7 | Every request answered with status 17 then 05 | Test files were addressed to instrument slot 3, which was empty. The slot number had been misread from a one-character reply; the sound was in slot 1 | Address the slot that holds the sound; `03_scan_instruments_1_to_8.syx` shows which slots are loaded |
| 8 | Volume "all wavesamples" had no effect in the first tests | Not fully explained. The EPS appears to have been in Load mode in each failing case (see below) | Use Edit mode and a numbered wavesample |

## "All wavesamples" writes are unreliable

Wavesample number 0 is documented as "all wavesamples of the layer". Observed results (the
front-panel column is reconstructed from the order of the tests, it was not noted at the time):

| Write (wavesample 0) | EPS front panel at that moment | Result |
|---|---|---|
| Filter Env2 Amount, cutoffs | Not recorded | Audibly applied |
| Volume = 0 | Edit mode, Filter page shown | Applied (read back 0) |
| Filter 1 Cutoff = 60 | Edit mode, Filter page shown | Refused, status 17, twice |
| Filter 1 Cutoff = 60 | Load mode | No error, not applied (read back 0) |
| Volume = 0 / 127 | Load mode | No audible effect, twice |

Writes to wavesample 1 worked in every attempt that was read back (three out of three).

Two patterns fit these results but are **not proven**:

- PUT PARAMETER may only be applied while the EPS is in Edit mode.
- An "all wavesamples" write may be refused when its parameter is on the page currently shown.

## The 0–63 limit

The EPS wants a value as `(value >> 6, value & 63)`. BCL has no token that extracts bits 0–5 or
bit 6 alone, and no arithmetic. Every combination of the valid tokens leaves a gap of invalid
bytes in the middle of the travel, so a continuous 0–127 encoder cannot be written in BCL. The
preset therefore caps every encoder at 63 and sends `$00 $00 $00 val`.

Not usable from the BCR2000 alone for the same reason: negative values of the bipolar
parameters, whose encoding was not tested.

## State of the files

| File | State |
|---|---|
| `EPS_BCR2000_I1_L1_WS1.bcl` / `.syx` | Current preset. Instrument 1, layer 1, wavesample 1, values 0–63, 100 ms interval. Not yet confirmed end to end |
| `gen_eps_bcl.py` | Generates that preset for any instrument, layer, wavesample, base channel |
| `debug/make_debug_sysex.py`, `debug/sysex/` | Single-message test files for the EPS |
| `EPS_BCR2000_I1_L1.*`, `…_7bit_variant.*` | Removed: invalid tokens, "all wavesamples" addressing, values above 63 sent as one byte |

## How to debug

Cabling: computer MIDI OUT → EPS MIDI IN, EPS MIDI OUT → computer MIDI IN. In MIDI-OX, make
sure no input port is routed to the output port. Send one file at a time and wait about three
seconds between two sends: the EPS refuses a command that arrives while it is processing one.

1. **EPS settings.** Edit / MIDI: MIDI SYS-EX = ON, base channel 1. Check again after a power
   cycle. Put the EPS in Edit mode.
2. **Is SysEx accepted?** Send `01_button_EDIT.syx`, then `02_button_LOAD.syx`; the display
   must follow. Go back to Edit mode afterwards.
3. **Which slots are loaded?** Send `03_scan_instruments_1_to_8.syx` with at least 300 ms
   between messages. A loaded slot answers ACK plus an 18-byte message; an empty one answers
   status 05.
4. **Write, then read back.** Send `20_volume_000.syx`, then `10_GET_volume.syx`. The answer
   must end with `00 00 00 00 F7`. Restore with `22_volume_127.syx`.
5. **Check the BCR2000 alone.** Connect its MIDI OUT A to the computer and turn Filter 1
   Cutoff. Expected: `F0 0F 03 00 11 00 00 00 00 00 01 14 01 00 00 00 xx F7`. Control Change
   messages mean the EPS preset is not the active one.
6. **Then connect the BCR2000 to the EPS** and compare with a read-back from the computer.

The files in `debug/sysex/` are for instrument 1, layer 1, wavesample 1, base channel 1.
`make_debug_sysex.py` regenerates them for another target.

## Corrections to earlier assumptions

- The first preset syntax (`val6.11 val0.5`) was written from memory and was wrong.
- Wavesample volume was used as an "unmistakable" audible test before any write had been
  verified; it failed for reasons unrelated to the message format.
- A guess that "all wavesamples" volume writes are relative offsets was disproved by read-back.
- A guess that SYS-EX had reset to OFF after the ERROR 144 reboots is not supported: virtual
  buttons still worked after them. SYS-EX did have to be set again after a full power cycle.

## Open questions

1. Does the current preset work end to end? First thing to test.
2. Are PUT PARAMETER writes ignored outside Edit mode? Test: `20_volume_000.syx` then
   `10_GET_volume.syx` with the EPS in Load mode.
3. What exactly makes an "all wavesamples" write succeed, fail with 17, or be ignored?
4. How fast can the EPS take successive writes? The specification asks for 2 s between
   commands; the BCR2000 cannot go slower than 100 ms.
5. How are negative values encoded?
6. Status 05 then 07 was returned once for two messages addressed to the loaded slot 1, sent
   less than half a second apart. Not reproduced.
7. Why the very first volume writes to wavesample 1 had no audible effect (never read back).

## Recommended next step

A small bridge program on the computer, between the BCR2000 and the EPS: the BCR2000 sends
plain Control Changes and the program translates them into exact EPS messages. It removes the
structural limits above: full 0–127 range and negative values, one write per wavesample instead
of the unreliable "all", a send rate matched to the EPS, a choice of instrument slot at run
time, and read-back of EPS values to drive the BCR2000 LED rings. Its cost is that the BCR2000
no longer controls the EPS without a computer.
