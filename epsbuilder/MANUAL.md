# EPS Builder — Manual

EPS Builder turns your audio files into instruments for the **Ensoniq EPS** sampler, stores
them on virtual floppy disks and manages the USB stick of a **Gotek** drive (HxC or
FlashFloppy firmware). Instruments are written in the EPS classic format, which the EPS-16+
and the ASR-10 can also read.

The window reads from left to right: **1. Instrument**, **2. Disk**, **3. USB stick**.

## In short

1. Drag audio files into the "Instrument" list.
2. Check the root note of each sound and give the instrument a name.
3. Click "Add the instrument to the disk".
4. Click "Write to a new slot" to send it to the USB stick.
5. Eject the stick, plug it into the Gotek, boot the EPS from the slot that holds the OS,
   then select the new slot and load the instrument.

## 1. Instrument

### Adding sounds

Drag your files into the list or use "Add sounds…". Supported formats: WAV, AIFF, FLAC, MP3,
OGG. M4A, AAC, WMA and Opus need the *ffmpeg* program to be installed on the computer.
Stereo sounds are mixed down to mono.

The **root note** is the note at which the sound plays at its original pitch. It is read from
the file name (`piano_C3.wav`, `bass F#1.flac`); otherwise it is C4, middle C. Correct it in
the "Root note" column.

### Key ranges

Each sound covers a range of notes, shown in colour above the keyboard.

- **Automatic zones**: the keyboard is split halfway between the root notes.
- **By hand**: drag the edge of a coloured band on the keyboard, or pick the notes in the
  "Zone: from … to" columns. The neighbouring range adjusts by itself. Any manual change
  turns automatic zones off.

### Multiple selection

Ctrl + click or Shift + click selects several sounds. "Remove", the "Loop" box and the root
note then apply to the whole selection (changing the root note shifts every selected sound by
the same interval). The same goes for the sample rate, resolution, compression, fades and loop
type in the sound editor.

### Adjusting a sound

The "Selected sound" panel shows the waveform of the first selected sound.

| Setting | Effect |
|---|---|
| **Start / End** | The part of the sound that is kept. Drag the **S** (start) and **E** (end) markers or type the times. The greyed parts are removed, which saves space. |
| **Fade in / out** | Gradual start or end, to avoid a click when cutting in the middle of a sound. |
| **Sample rate** | Sample rate of this sound. Lower: less space, duller sound. By default, the instrument's rate. |
| **Resolution** | The EPS records at 13 bits. A lower value gives a "lo-fi" grain; the space used does not change. |
| **Compression** | Tames the loud passages and raises the overall level. |
| **Loop** | No loop, loop forward, back and forth, or loop then release. The **L** markers delimit the part that repeats while the key is held. |
| **Zero crossings** | Snaps the loop edges to the nearest zero crossing, to reduce clicks. |
| **Auto splice** | Searches near the loop end for the point where the splice is least audible. |
| **Reset** | Cancels the settings of the selected sounds. |

"Trim silence" removes the silence at the start and end of imported sounds as long as you have
not set their start and end by hand. "Normalize level" brings each imported sound to full level.

### Instrument settings

- **Name**: 12 characters at most.
- **Sample rate**: default for imported sounds. 31.3 kHz is a good compromise; at that rate a
  disk holds about 12 seconds of sound.
- **Envelope**: "Sustained sound" keeps the volume for as long as the key is held;
  "Percussive sound" lets it decay to silence, like a piano.

### Listening

- "Listen" plays the selected sound as it will be in the EPS, at its root note.
- Clicking a key of the keyboard plays the instrument on that note.

Listening works on Windows.

## 2. Disk

An EPS disk holds 1585 blocks, about 790 KB, and 39 files at most. The bar shows the space
used.

| Button | Purpose |
|---|---|
| **Blank** | New empty disk. |
| **With OS…** | New disk containing the EPS operating system, copied from an existing disk. It will be able to boot the machine. |
| **Open… / Save as…** | Reads or writes a `.hfe` image (Gotek) or a `.img` raw image. |
| **Edit the instrument** | Loads the instrument into the editor (double-click). Its sounds keep their settings; edit it, then click "Update the instrument on the disk". Only single-layer instruments can be edited. |
| **Listen** | Plays the sounds of the instrument one after the other. |
| **Up / Down** | Changes the order of the instruments. You can also drag them in the list. The OS stays first. |
| **Export as WAV…** | Saves every sound on the disk as a WAV file. |
| **Delete** | Removes the file from the disk. |

Until the disk is written to the USB stick or saved, its title shows "modified".

## 3. Gotek USB stick

Choose the stick in the list ("Browse…" for any folder). The firmware is detected
automatically:

- **HxC**: images are named `DSKA0000.hfe`, `DSKA0001.hfe`… The number is the one you select
  on the Gotek.
- **FlashFloppy**: file names are free.

| Action | Effect |
|---|---|
| **Open** (or double-click) | Loads the slot into the "Disk" section. |
| **Write to a new slot** | Writes the current disk to the first free slot. |
| **Replace the slot** | Replaces the selected slot, after confirmation. |
| **Catalogue…** | Saves the list of all slots and their contents to a text file. |

Every write is read back and checked. **Always eject the stick** from Windows before removing
it.

### Drag and drop

- An instrument from the disk dropped **onto a slot** is copied into it. Dropped below the
  last row, it creates a new slot. The stick is modified at once, after confirmation.
- A slot dropped **onto the disk** offers to import its instruments.

### Editing an existing slot

Open it, make your changes (add, delete, reorder, edit an instrument), then click "Replace the
slot".

## On the EPS

1. Set the Gotek to the slot that holds the OS (usually 000) and switch the EPS on.
2. Once the EPS has booted, select the slot you want on the Gotek.
3. Press LOAD, then INSTRUMENT, choose the instrument and confirm.

## Troubleshooting

| Message or symptom | Cause and fix |
|---|---|
| **OS NOT ON DISK** at power-on | The Gotek is on a slot without the OS. Go back to the slot that holds the OS. |
| **KBD FAILED – TRY AGAIN** | Keyboard calibration failed: switch on again without touching the keys. If it persists, it is a keyboard contact fault, unrelated to the USB stick. |
| **DISK DRIVE NOT READY** | A Gotek setting (jumpers, disk change delay), not a fault in the file. |
| The sound stops while the key is held | Choose the "Sustained sound" envelope and turn the loop on. |
| Click on every loop pass | Use "Zero crossings" or "Auto splice", or move the L markers. |
| "Too big for the disk" | Shorten the sounds (start, end), lower the sample rate, or spread them over two disks. |

## Limits

- EPS classic format only (13 bits, 800 KB disks). The native EPS-16+ and ASR-10 formats are
  not written.
- One layer per created instrument.
- Detailed envelopes, the filter and the LFO are set on the EPS itself.

## License

EPS Builder is free software released under the MIT license: you may use, copy, modify and
redistribute it freely, including for commercial purposes, provided the copyright notice is
kept.
