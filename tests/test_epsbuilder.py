"""Tests automatiques : python tests/test_epsbuilder.py  (ou pytest)."""
import os
import struct
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["EPSBUILDER_LANG"] = "fr"            # les tests verifient les textes francais

from epsbuilder import audio, hfe, instrument as ins, project  # noqa: E402
from epsbuilder import usbkey  # noqa: E402
from epsbuilder.disk import EnsoniqDisk, TYPE_EPS_INSTRUMENT, quick_summary, system_disk_from  # noqa: E402


def tone(freq, seconds, rate, decay=3.0, harmonics=(1.0, 0.4, 0.2)):
    t = np.arange(int(seconds * rate)) / rate
    x = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harmonics))
    return 0.8 * x / np.max(np.abs(x)) * np.exp(-decay * t)


def pitch_of(x, rate):
    seg = x[: 1 << 14] * np.hanning(min(len(x), 1 << 14))
    sp = np.abs(np.fft.rfft(seg, 1 << 18))
    return np.fft.rfftfreq(1 << 18, 1 / rate)[int(np.argmax(sp))]


def test_hfe_roundtrip():
    rng = np.random.default_rng(1)
    for geom in (hfe.GEOM_DD, hfe.GEOM_HD):
        image = rng.integers(0, 256, geom.image_size, dtype=np.uint8).tobytes()
        assert hfe.hfe_to_image(hfe.image_to_hfe(image)) == image


def test_disk_add_delete():
    disk = EnsoniqDisk.blank(label="TEST")
    assert disk.free_blocks == 1585 and disk.check() == []
    a = bytes(range(256)) * 20
    disk.add_file("UN", 3, a)
    disk.add_file("DEUX", 3, b"\x01" * 512 * 30)
    disk.add_file("TROIS", 3, b"\x02" * 512 * 5)
    disk.delete("DEUX")
    big = bytes([7]) * 512 * 1560          # ne tient qu'en deux morceaux
    disk.add_file("GROS", 3, big)
    assert disk.check() == []
    assert disk.read_file(disk.find("GROS")) == big
    assert disk.read_file(disk.find("UN")) == a
    assert disk.find("GROS").contiguous < 1560
    assert disk.free_blocks == 1585 - 10 - 5 - 1560
    reloaded = EnsoniqDisk(hfe.hfe_to_image(hfe.image_to_hfe(bytes(disk.img))))
    assert reloaded.check() == [] and [e.name for e in reloaded.entries()] == [e.name for e in disk.entries()]


def test_instrument_roundtrip():
    rate = ins.rate_hz(20)
    layer = ins.Layer()
    for root, (lo, hi) in zip((48, 60, 72), ((21, 54), (55, 66), (67, 108))):
        layer.wavesamples.append(ins.Wavesample(f"WS {root}", tone(440 * 2 ** ((root - 69) / 12), 0.3, rate),
                                                rate_code=20, root_key=root, key_lo=lo, key_hi=hi))
    layer.wavesamples[1].loop_mode = ins.LOOP_FORWARD
    layer.wavesamples[1].loop_start, layer.wavesamples[1].loop_end = 1000, 5000
    data = ins.build_instrument(ins.Instrument("ESSAI", [layer]))
    assert len(data) % 512 == 0
    back = ins.parse_instrument(data)
    assert back.name == "ESSAI       " and len(back.layers) == 1
    for a, b in zip(layer.wavesamples, back.layers[0].wavesamples):
        assert (b.root_key, b.key_lo, b.key_hi, b.rate_code, b.loop_mode) == \
               (a.root_key, a.key_lo, a.key_hi, a.rate_code, a.loop_mode)
        assert len(b.samples) == len(a.samples)
        assert np.max(np.abs(b.samples - a.samples)) < 1.5 / 4095       # quantification 13 bits
    assert (back.layers[0].wavesamples[1].loop_start, back.layers[0].wavesamples[1].loop_end) == (1000, 5000)
    # Tous les mots ont leurs 3 bits de poids faible a zero (memoire 13 bits de l'EPS)
    words = np.frombuffer(data, dtype=">u2")
    assert not np.any(words & 7)
    # Reconstruction a l'identique
    assert ins.build_instrument(back) == data


def test_wav_to_disk():
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for note, freq in (("C3", 130.81), ("C5", 523.25)):
            p = os.path.join(tmp, f"son_{note}.wav")
            audio.write_wav(p, np.concatenate([np.zeros(2000), tone(freq, 0.4, 44100)]), 44100)
            paths.append(project.SampleSpec(p, project.note_to_midi(note)))
        inst = project.make_instrument("DEUX SONS", paths)
        disk = EnsoniqDisk.blank()
        project.add_instrument(disk, inst)
        out = os.path.join(tmp, "DSKA0001.hfe")
        disk.save(out)
        disk2 = EnsoniqDisk.load(out)
        assert disk2.check() == []
        entry = disk2.find("DEUX SONS")
        assert entry.file_type == TYPE_EPS_INSTRUMENT
        back = ins.parse_instrument(disk2.read_file(entry))
        ws = back.layers[0].wavesamples
        assert [(w.root_key, w.key_lo, w.key_hi) for w in ws] == [(48, 21, 60), (72, 61, 108)]
        for w, freq in zip(ws, (130.81, 523.25)):
            assert abs(pitch_of(w.samples, w.rate) / freq - 1) < 0.003     # hauteur conservee
            assert abs(np.max(np.abs(w.samples)) - 0.97) < 0.01            # niveau normalise, silence coupe


def test_default_envelope_sustains():
    # Enveloppe d'amplitude par defaut : niveau de maintien au maximum (sinon un son boucle s'eteint).
    from epsbuilder import templates
    amp = [templates.WAVESAMPLE_BLOCK[10 + 2 * (58 + k)] for k in range(22)]
    assert amp[13] == 127 and amp[14] == 127


def test_usb_key_and_system_disk():
    with tempfile.TemporaryDirectory() as tmp:
        system = EnsoniqDisk.blank()
        system.add_file("EPS-1 O.S.", 1, b"\x55" * 512 * 167)
        system.add_file("PIANO", 3, b"\x01" * 512 * 40)
        system.save(os.path.join(tmp, "DSKA0000.hfe"))
        open(os.path.join(tmp, "HXCSDFE.CFG"), "wb").write(b"HXCFECFGV1.0")
        open(os.path.join(tmp, "._DSKA0000.hfe"), "wb").write(b"x")
        assert usbkey.detect_mode(tmp) == usbkey.MODE_HXC
        key = usbkey.UsbKey(tmp)
        slots = key.slots()
        assert [s.number for s in slots] == [0] and slots[0].summary.has_os
        assert slots[0].describe() == "EPS-1 O.S., PIANO"
        assert key.next_free_number() == 1
        clean = system_disk_from(system)
        assert [e.name.strip() for e in clean.entries()] == ["EPS-1 O.S."] and clean.check() == []
        clean.add_file("NOUVEAU", 3, b"\x02" * 512 * 10)
        key.write(clean, key.filename_for(1))
        try:
            key.write(clean, "dska0001.hfe")
            raise AssertionError("ecrasement non signale")
        except usbkey.UsbKeyError:
            pass
        key.write(clean, "dska0001.hfe", overwrite=True)
        assert sorted(n for n in os.listdir(tmp) if n.upper().startswith("DSKA")) == ["DSKA0000.hfe", "DSKA0001.hfe"]
        s = quick_summary(os.path.join(tmp, "DSKA0001.hfe"))
        assert [e.name.strip() for e in s.entries] == ["EPS-1 O.S.", "NOUVEAU"] and s.total_blocks == 1600
        assert s.free_blocks == clean.free_blocks
        assert "001 [OS]" in key.catalog()


def test_percussive_envelope():
    x = tone(440, 0.1, ins.rate_hz(20))
    a = ins.build_instrument(ins.Instrument("A", [ins.Layer(wavesamples=[ins.Wavesample("S", x)])]))
    b = ins.build_instrument(ins.Instrument("A", [ins.Layer(wavesamples=[ins.Wavesample("S", x, envelope=ins.ENV_PERCUSSIVE)])]))
    sustain = lambda d: d[0x370 + 10 + 2 * (58 + 13)]
    assert sustain(a) == 127 and sustain(b) == 0


def test_reorder_and_replace():
    disk = EnsoniqDisk.blank()
    for i, n in enumerate(("OS", "A", "B", "C")):
        disk.add_file(n, 1 if n == "OS" else 3, bytes([i + 1]) * 512 * (5 + i))
    disk.reorder(["OS", "C", "A", "B"])
    assert [e.name.strip() for e in disk.entries()] == ["OS", "C", "A", "B"] and disk.check() == []
    assert disk.read_file(disk.find("C")) == bytes([4]) * 512 * 8
    disk.replace_file("A", "A2", 3, b"\x09" * 512 * 20)
    assert [e.name.strip() for e in disk.entries()] == ["OS", "C", "A2", "B"] and disk.check() == []
    assert disk.read_file(disk.find("A2")) == b"\x09" * 512 * 20
    before = bytes(disk.img)
    for bad in (lambda: disk.replace_file("A2", "B", 3, b"x" * 512),            # nom deja pris
                lambda: disk.replace_file("A2", "A2", 3, b"x" * 512 * 5000),      # trop gros
                lambda: disk.reorder(["OS", "C"])):
        try:
            bad()
            raise AssertionError("erreur attendue")
        except Exception as ex:
            assert type(ex).__name__ == "DiskError"
    assert bytes(disk.img) == before                    # disquette intacte apres un echec


def test_edit_existing_instrument():
    rate = ins.rate_hz(20)
    a = ins.Wavesample("GRAVE", tone(130.81, 0.2, rate), root_key=48, key_lo=21, key_hi=59, envelope=ins.ENV_PERCUSSIVE)
    b = ins.Wavesample("AIGU", tone(523.25, 0.2, rate), root_key=72, key_lo=60, key_hi=108,
                       loop_mode=ins.LOOP_BIDIRECTIONAL, loop_start=100, loop_end=3000)
    original = ins.parse_instrument(ins.build_instrument(ins.Instrument("DUO", [ins.Layer(wavesamples=[a, b])], key_lo=21, key_hi=108)))
    ws = original.layers[0].wavesamples
    specs = [project.SampleSpec(None, 50, 21, 64, False, None, ws[0]),       # note de base et zone changees
             project.SampleSpec(None, 72, 65, 108, True, None, ws[1])]       # boucle conservee telle quelle
    edited = ins.parse_instrument(ins.build_instrument(project.make_instrument("DUO 2", specs, base=original)))
    e = edited.layers[0].wavesamples
    assert (edited.key_lo, edited.key_hi) == (21, 108)
    assert [(w.root_key, w.key_lo, w.key_hi) for w in e] == [(50, 21, 64), (72, 65, 108)]
    assert e[1].loop_mode == ins.LOOP_BIDIRECTIONAL and (e[1].loop_start, e[1].loop_end) == (100, 3000)
    assert np.array_equal(e[0].samples, ws[0].samples) and np.array_equal(e[1].samples, ws[1].samples)
    amp_sustain = lambda w: w.params[10 + 2 * (58 + 13)]
    assert amp_sustain(e[0]) == 0 and amp_sustain(e[1]) == 127             # enveloppes conservees


def test_other_audio_formats():
    try:
        import soundfile
    except ImportError:
        return
    with tempfile.TemporaryDirectory() as tmp:
        x = tone(440, 0.5, 44100, decay=0.0)
        for ext in ("flac", "aiff", "ogg", "mp3"):
            p = os.path.join(tmp, f"la.{ext}")
            soundfile.write(p, np.stack([x, x], axis=1), 44100)
            snd = audio.read_sound(p)
            assert snd.rate == 44100 and abs(len(snd.samples) - len(x)) < 3000, ext
            assert abs(pitch_of(snd.samples[4000:], snd.rate) / 440 - 1) < 0.003, ext
        assert audio.is_audio_file("X.FLAC") and not audio.is_audio_file("x.txt")
        open(os.path.join(tmp, "faux.flac"), "wb").write(b"pas un son")
        try:
            audio.read_sound(os.path.join(tmp, "faux.flac"))
            raise AssertionError("erreur attendue")
        except audio.AudioError:
            pass


def test_sound_processing():
    rate = 44100.0
    quiet = tone(220, 1.0, rate, decay=0.0) * np.where(np.arange(44100) < 22050, 1.0, 0.1)   # fort puis faible
    edit = project.SoundEdit(start=4410, end=39689, fade_in_ms=10, fade_out_ms=10)
    x, code, mode, ls, le = project.process_sound(quiet, rate, edit, 20, normalize=True, trim=True)
    out_rate = ins.rate_hz(code)
    assert code == 20 and abs(len(x) - 35280 * out_rate / rate) < 3 and mode == 0 and ls is None
    assert abs(x[0]) < 1e-9 and abs(x[-1]) < 1e-9 and abs(np.max(np.abs(x)) - 0.97) < 0.01
    # compression : l'ecart entre passage fort et passage faible diminue
    ratio = lambda y: np.max(np.abs(y[:len(y) // 3])) / np.max(np.abs(y[-len(y) // 3:]))
    squeezed = audio.compress(quiet, rate, 80)
    assert ratio(squeezed) < 0.5 * ratio(quiet) and np.max(np.abs(squeezed)) <= np.max(np.abs(quiet)) + 1e-9
    assert np.array_equal(audio.compress(quiet, rate, 0), quiet)
    # resolution
    assert len(np.unique(audio.reduce_bits(quiet, 6))) <= 64 and np.array_equal(audio.reduce_bits(quiet, 13), quiet)
    # frequence propre au son, sans depasser celle du fichier
    x2, code2, *_ = project.process_sound(quiet, rate, project.SoundEdit(rate_code=40), 20, True, False)
    assert code2 == 40 and abs(len(x2) - 44100 * ins.rate_hz(40) / rate) < 3
    assert project.process_sound(quiet, 22050.0, project.SoundEdit(rate_code=12), 20, True, False)[1] == ins.rate_code_for(22050)
    # boucle : positions converties dans le son produit
    edit = project.SoundEdit(start=1000, loop_mode=ins.LOOP_BIDIRECTIONAL, loop_start=11000, loop_end=21000)
    x3, code3, mode3, ls3, le3 = project.process_sound(quiet, rate, edit, 20, True, False)
    k = ins.rate_hz(code3) / rate
    assert mode3 == ins.LOOP_BIDIRECTIONAL and abs(ls3 - 10000 * k) <= 1 and abs(le3 - 20000 * k) <= 1
    # aides au bouclage
    period = 100
    sine = np.sin(2 * np.pi * np.arange(20000) / period)
    assert audio.nearest_zero_crossing(sine, 1230) % period in (0, 1)
    end = audio.best_loop_end(sine, 3000, 12345)
    assert (end + 1 - 3000) % period == 0 and abs(end - 12345) <= period
    assert audio.trim_bounds(np.concatenate([np.zeros(500), sine, np.zeros(700)]))[0] in range(500, 503)


def test_translations_complete():
    """Chaque texte passe a T() a une traduction anglaise, avec les memes variables."""
    import ast
    import glob
    import re
    import subprocess
    from epsbuilder import i18n
    from epsbuilder.translations import EN
    package = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "epsbuilder")
    keys = set()
    for path in glob.glob(os.path.join(package, "*.py")):
        for node in ast.walk(ast.parse(open(path, encoding="utf-8").read())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "T":
                assert isinstance(node.args[0], ast.Constant), f"T() sans texte fixe dans {path}"
                keys.add(node.args[0].value)
    assert len(keys) > 250
    missing = sorted(keys - set(EN))
    assert not missing, f"textes sans traduction : {missing[:5]}"
    fields = lambda s: sorted(re.findall(r"\{[^}]*\}", s))
    assert not [k for k in keys if fields(k) != fields(EN[k])]
    for name in ("MANUEL.md", "MANUAL.md", "LICENCE.txt"):
        assert os.path.getsize(os.path.join(package, name)) > 500
    assert i18n.LANG == "fr" and i18n.T("Supprimer") == "Supprimer" and i18n.number("31.3 kHz") == "31,3 kHz"
    # L'application en anglais, dans un processus separe (la langue se choisit au lancement).
    code = (
        "import os, sys, tempfile\n"
        "from PySide6 import QtCore, QtWidgets\n"
        "QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)\n"
        "QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, tempfile.mkdtemp())\n"
        "from epsbuilder import gui, i18n, disk, usbkey\n"
        "app = QtWidgets.QApplication([])\n"
        "w = gui.MainWindow()\n"
        "texts = [w.to_disk_btn.text(), w.delete_btn.text(), w.table.horizontalHeaderItem(2).text(),\n"
        "         w.sound_editor.title(), w.rate_box.currentText(), w.disk_title.text(), disk.FILE_TYPES[3],\n"
        "         usbkey.Slot('x').title, i18n.number('31.3 kHz')]\n"
        "print('|'.join(texts))\n"
        "w.show_manual()\n"
        "print(w._documents[0].findChild(QtWidgets.QTextBrowser).toPlainText()[:40].replace(chr(10), ' '))\n"
    )
    env = dict(os.environ, EPSBUILDER_LANG="en", QT_QPA_PLATFORM="offscreen",
               PYTHONPATH=os.path.join(package, ".."),
               PYTHONIOENCODING="utf-8")           # la console Windows (cp1252) ne sait pas ecrire « ▶ »
    try:
        import PySide6  # noqa: F401
    except ImportError:
        return
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=120)
    assert out.returncode == 0, out.stderr[-800:]
    first, second = [l for l in out.stdout.splitlines() if l.strip()][-2:]
    assert first == ("Add the instrument to the disk  ▶|Delete|Root note|Selected sound|31.3 kHz (recommended)|"
                     "New blank disk|EPS instrument|x|31.3 kHz"), first
    assert second.startswith("EPS Builder — Manual"), second


def test_notes():
    assert project.note_to_midi("C4") == 60 and project.note_to_midi("A0") == 21
    assert project.note_to_midi("F#3") == 54 and project.note_to_midi("Bb2") == 46
    assert project.midi_to_note(67) == "G4"
    assert project.auto_zones([60]) == [(21, 108)]


def test_gui_smoke():
    """Parcours complet dans l'interface, sans ecran : sons -> instrument -> disquette -> cle."""
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        return
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from epsbuilder import gui
    with tempfile.TemporaryDirectory() as tmp:
        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
        QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, tmp)
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        keydir = os.path.join(tmp, "cle")
        os.mkdir(keydir)
        open(os.path.join(keydir, "HXCSDFE.CFG"), "wb").write(b"HXCFECFGV1.0")
        paths = []
        for note, freq in (("C5", 523.25), ("C3", 130.81)):
            p = os.path.join(tmp, f"orgue_{note}.wav")
            audio.write_wav(p, tone(freq, 0.3, 44100), 44100)
            paths.append(p)
        win = gui.MainWindow()
        win.add_files(paths)
        assert [(s.root, s.lo, s.hi) for s in win.samples] == [(48, 21, 60), (72, 61, 108)]
        assert win.name_edit.text() == "ORGUE"
        win.add_instrument_to_disk()
        assert [e.name.strip() for e in win.disk.entries()] == ["ORGUE"] and win.disk_dirty
        win.set_key_folder(keydir)
        assert win.key.mode == usbkey.MODE_HXC
        win.write_to_key(new=True)
        assert os.listdir(keydir).count("DSKA0000.hfe") == 1 and not win.disk_dirty
        assert [s.describe() for s in win._slots] == ["ORGUE"]
        back = EnsoniqDisk.load(os.path.join(keydir, "DSKA0000.hfe"))
        assert back.check() == [] and bytes(back.img) == bytes(win.disk.img)
        # deuxieme instrument, puis reorganisation
        win.samples = []
        win.name_edit.setText("SECOND")
        win.add_files([paths[0]])
        win.add_instrument_to_disk()
        win.disk_table.selectRow(1)
        win.move_entry(-1)
        assert [e.name.strip() for e in win.disk.entries()] == ["SECOND", "ORGUE"]
        # modification d'un instrument de la disquette : note de base, nom, ajout d'un son
        win.disk_table.selectRow(1)
        win.samples = []
        win.edit_selected()
        assert win.editing_name.strip() == "ORGUE" and len(win.samples) == 2 and not win.auto_zones.isChecked()
        win.samples[0].root = 50
        win.name_edit.setText("ORGUE B")
        win.add_instrument_to_disk()
        assert [e.name.strip() for e in win.disk.entries()] == ["SECOND", "ORGUE B"] and win.disk.check() == []
        again = ins.parse_instrument(win.disk.read_file(win.disk.find("ORGUE B")))
        assert [w.root_key for w in again.layers[0].wavesamples] == [50, 72]
        assert win.editing_name.strip() == "ORGUE B"
        # selection multiple : transposition, boucle et retrait groupes
        win.samples = []
        win.editing_name = win.editing_base = None
        win.auto_zones.setChecked(True)
        win.add_files(paths + [paths[0]])
        assert [s.root for s in win.samples] == [48, 72, 72]
        win.select_items(win.samples[1:])
        assert win.selected_rows() == [1, 2]
        box = win.table.cellWidget(1, 2)
        box.setCurrentIndex(box.findData(60))               # C5 -> C4 sur une ligne de la selection
        app.processEvents()
        assert [s.root for s in win.samples] == [48, 60, 60] and win.selected_rows() == [1, 2]
        win._loop_changed(2, True)
        app.processEvents()
        assert [s.loop for s in win.samples] == [False, True, True]
        win._loop_changed(0, True)                          # ligne hors selection : elle seule
        assert [s.loop for s in win.samples] == [True, True, True]
        win.remove_sample()
        assert [s.root for s in win.samples] == [48]
        # ecoute : son a sa note de base, transposition au clavier, instrument de la disquette
        played = []

        class FakePlayer:
            available = True
            def play(self, samples, rate):
                played.append((np.array(samples), rate))
                return True
            def stop(self):
                pass
        win.player = FakePlayer()
        win.select_items(win.samples)
        win.preview()
        x, rate = played[-1]
        assert abs(pitch_of(x, rate) / 130.81 - 1) < 0.01
        win.play_key(60)                                    # une octave au-dessus de la note de base
        x, rate = played[-1]
        assert abs(pitch_of(x, rate) / 261.63 - 1) < 0.01
        geo = win.keyboard._geometry()
        assert win.keyboard.key_at(geo[4][60] + 1, geo[2] + geo[3] - 2) == 60      # bas d'une touche blanche
        assert win.keyboard.key_at(geo[4][61] + 1, geo[2] + 2) == 61               # touche noire
        win.samples[0].loop = True
        assert len(gui.audition(win.render_item(win.samples[0]))) >= int(2.4 * win.render_item(win.samples[0]).rate)
        # plages : glisser un bord sur le clavier, ou choisir dans la liste
        win.samples = []
        win.auto_zones.setChecked(True)
        win.add_files(paths)
        assert [(s.lo, s.hi) for s in win.samples] == [(21, 60), (61, 108)]
        win.move_zone_edge(0, "hi", 50)                     # la plage voisine suit
        assert [(s.lo, s.hi) for s in win.samples] == [(21, 50), (51, 108)] and not win.auto_zones.isChecked()
        win.move_zone_edge(1, "lo", 70)                     # idem dans l'autre sens
        assert [(s.lo, s.hi) for s in win.samples] == [(21, 69), (70, 108)]
        win.move_zone_edge(0, "hi", 120)                    # on ne peut pas faire disparaitre le voisin
        assert [(s.lo, s.hi) for s in win.samples] == [(21, 107), (108, 108)]
        win.move_zone_edge(0, "hi", 40)
        win.move_zone_edge(1, "lo", 55)                     # la frontiere commune se deplace d'un bloc
        assert [(s.lo, s.hi) for s in win.samples] == [(21, 54), (55, 108)] and win.check_zones() == ""
        win.refresh_samples()
        box = win.table.cellWidget(0, 4)
        box.setCurrentIndex(box.findData(60))               # depuis la liste : chevauchement evite
        app.processEvents()
        assert [(s.lo, s.hi) for s in win.samples] == [(21, 60), (61, 108)]
        assert win.table.cellWidget(1, 3).currentData() == 61
        win.add_files([paths[0]])                           # ajout en zones manuelles : partage de la plage
        assert sorted((s.root, s.lo, s.hi) for s in win.samples) == [(48, 21, 60), (72, 61, 72), (72, 73, 108)]
        assert win.check_zones() == ""
        kb = win.keyboard
        kb.resize(900, 100)
        kb.set_zones([(s.lo, s.hi, s.root, None) for s in win.samples])
        geo = kb._geometry()
        edge_x = geo[4][60] + geo[1]
        assert kb._edge_at(edge_x - 2, 8) in ((0, "hi"), (1, "lo")) and kb._edge_at(edge_x - 2, 60) is None
        assert kb.key_at_x(geo[4][72] + 1) == 72
        win.refresh_keyboard()
        win.disk_table.selectRow(0)
        win.play_disk_instrument()
        assert len(played) == 3 and len(played[-1][0]) > 1000
        # editeur de son : debut, fin, boucle, frequence, reglages groupes, son de la disquette
        win.confirm = lambda *a, **k: True                  # les confirmations sont acceptees
        win.samples = []
        win.editing_name = win.editing_base = None
        win.auto_zones.setChecked(True)
        win.add_files(paths)
        ed = win.sound_editor
        assert ed.edit is None                              # rien de selectionne
        win.select_items([win.samples[0]])
        item = win.samples[0]
        assert ed.edit is item.edit and len(ed.samples) == len(item.samples)
        before_blocks = win.estimated_blocks()[0]
        full = len(win.render_item(item).samples)
        ed._set_position("start", 2205)
        ed._set_position("end", 8819)                       # on garde 0,15 s sur 0,30 s
        assert (item.edit.start, item.edit.end) == (2205, 8819) and item.edited
        short = win.render_item(item)
        assert abs(len(short.samples) - 6615 * short.rate / 44100) < 3 and len(short.samples) < 0.6 * full
        assert win.estimated_blocks()[0] < before_blocks
        ed.loop_box.setCurrentIndex(ed.loop_box.findData(ins.LOOP_FORWARD))
        ed.loop_box.activated.emit(ed.loop_box.currentIndex())
        assert item.loop and win._loop_boxes[0].isChecked() and ed.loop_start.isEnabled()
        ed._set_position("loop_start", 4000)
        ed.auto_loop()
        ws = win.render_item(item)
        assert ws.loop_mode == ins.LOOP_FORWARD and 0 < ws.loop_start < ws.loop_end <= len(ws.samples) - 1
        win.select_items(win.samples)                       # reglage groupe : frequence et resolution
        ed.rate_box.setCurrentIndex(ed.rate_box.findData(40))
        ed.rate_box.activated.emit(ed.rate_box.currentIndex())
        ed._set_group("bits", 8)
        assert [s.edit.rate_code for s in win.samples] == [40, 40] and [s.edit.bits for s in win.samples] == [8, 8]
        assert win.render_item(win.samples[1]).rate_code == 40
        assert len(np.unique(win.render_item(win.samples[1]).samples)) <= 256
        win._reset_sound()
        assert not any(s.edited for s in win.samples) and not win._loop_boxes[0].isChecked()
        win.set_disk(EnsoniqDisk.blank(), "essai son")
        win.name_edit.setText("DECOUPE")
        win.select_items([win.samples[0]])
        ed._set_position("end", 6000)
        win.add_instrument_to_disk()
        win.disk_table.selectRow(0)
        win.edit_selected()                                 # son de la disquette : intact tant qu'on n'y touche pas
        it = win.samples[0]
        assert not it.edited and win.spec_for(it).edit is None
        assert np.array_equal(win.render_item(it).samples, it.ws.samples)
        win.select_items([it])
        n0 = len(it.ws.samples)
        win.sound_editor._set_position("end", n0 // 2)
        win.sound_editor._set_group("compress", 60)
        win.add_instrument_to_disk()
        again = ins.parse_instrument(win.disk.read_file(win.disk.find("DECOUPE")))
        assert len(again.layers[0].wavesamples[0].samples) == n0 // 2 + 1 and win.disk.check() == []
        win.disk_dirty = False
        # glisser-deposer : ordre sur la disquette, copie vers la cle, import depuis la cle
        win.set_disk(EnsoniqDisk.blank(), "essai")
        win.editing_name = win.editing_base = None
        win.samples = []
        win.name_edit.setText("SECOND")
        win.auto_zones.setChecked(True)
        win.add_files([paths[0]])
        win.add_instrument_to_disk()
        win.samples = []
        win.name_edit.setText("ORGUE B")
        win.add_files(paths)
        win.add_instrument_to_disk()
        win.confirm = lambda *a, **k: True                  # les confirmations sont acceptees
        assert [e.name.strip() for e in win.disk.entries()] == ["SECOND", "ORGUE B"]
        win.move_entries_to(["ORGUE B     "], 0)
        assert [e.name.strip() for e in win.disk.entries()] == ["ORGUE B", "SECOND"]
        win.move_entries_to(["ORGUE B     "], -1)           # depose sous les lignes : en dernier
        assert [e.name.strip() for e in win.disk.entries()] == ["SECOND", "ORGUE B"]
        win.disk_table.selectRow(1)
        assert bytes(win.disk_table.mimeData([]).data(gui.MIME_FILES)).decode() == "ORGUE B     "
        win.refresh_key()
        slot0 = win._slots[0]                               # contient ORGUE (ecrit plus haut)
        win.disk_file = None
        assert win.copy_files_to_slot(["SECOND      "], slot0)
        on_key = EnsoniqDisk.load(os.path.join(keydir, slot0.filename))
        assert [e.name.strip() for e in on_key.entries()] == ["ORGUE", "SECOND"] and on_key.check() == []
        assert win.copy_files_to_slot(["ORGUE B     "], None)   # nouvel emplacement
        assert sorted(n for n in os.listdir(keydir) if n.startswith("DSKA")) == ["DSKA0000.hfe", "DSKA0001.hfe"]
        assert [s.describe() for s in win._slots] == ["ORGUE, SECOND", "ORGUE B"]
        win.set_disk(EnsoniqDisk.blank(), "essai")
        assert win.import_from_slot(win._slots[0], ["ORGUE       ", "SECOND      "])
        assert [e.name.strip() for e in win.disk.entries()] == ["ORGUE", "SECOND"] and win.disk_dirty
        win.disk_file = win._slots[1].filename              # un emplacement n'est pas copie sur lui-meme
        assert not win.import_from_slot(win._slots[1]) and not win.copy_files_to_slot(["ORGUE       "], win._slots[1])
        full = EnsoniqDisk.blank()
        full.add_file("GROS", 3, b"\x01" * 512 * 1580)
        win.disk_file = None
        key2 = win.key.write(full, "DSKA0002.hfe")
        win.refresh_key()
        errors = []
        win.error = lambda ex: errors.append(str(ex))
        assert not win.copy_files_to_slot(["ORGUE       "], win._slots[2]) and "pleine" in errors[-1]
        assert bytes(EnsoniqDisk.load(key2).img) == bytes(full.img)    # emplacement plein : rien n'est ecrit
        win.show_manual()                                   # manuel et licence fournis avec l'application
        win.show_licence()
        texts = [d.findChild(QtWidgets.QTextBrowser).toPlainText() for d in win._documents]
        assert "Glisser-déposer" in texts[0] and "MIT License" in texts[1]
        for d in win._documents:
            d.close()
        win.disk_dirty = False
        win.close()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok ", name)
