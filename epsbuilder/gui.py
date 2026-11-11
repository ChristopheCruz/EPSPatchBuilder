"""Interface graphique d'EPS Builder (PySide6)."""
from __future__ import annotations

import os
import re
import sys
import tempfile
from copy import copy
from dataclasses import astuple, dataclass, field

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from . import i18n
from .i18n import T
from . import __version__, audio, instrument as ins, project, usbkey
from .project import SoundEdit
from .soundedit import SoundEditor
from .disk import DiskError, EnsoniqDisk, OS_TYPES, TYPE_EPS_INSTRUMENT, system_disk_from

ERRORS = (DiskError, ins.InstrumentError, audio.AudioError, usbkey.UsbKeyError, ValueError, OSError)

RATES = [(12, T("52,1 kHz (qualité maximale)")), (14, T("44,6 kHz")), (16, T("39,1 kHz")), (20, T("31,3 kHz (conseillé)")),
         (24, T("26,0 kHz")), (32, T("19,5 kHz")), (40, T("15,6 kHz (économe)"))]
ZONE_COLORS = ["#4C8BF5", "#F2994A", "#27AE60", "#BB6BD9", "#EB5757", "#2D9CDB", "#F2C94C", "#6FCF97"]
_NOTE_IN_NAME = re.compile(r"(?<![A-Za-z])([A-Ga-g][#b]?-?\d)(?![A-Za-z0-9])")
NOTE_CHOICES = [(k, project.midi_to_note(k)) for k in range(ins.FIRST_KEY, ins.LAST_KEY + 1)]


@dataclass
class SampleItem:
    """Un son de l'instrument en cours : fichier audio a convertir, ou son deja present sur la disquette."""
    path: str | None
    sound: audio.Sound | None
    root: int
    lo: int = ins.FIRST_KEY
    hi: int = ins.LAST_KEY
    ws: ins.Wavesample | None = None
    edit: SoundEdit = field(default_factory=SoundEdit)        # reglages du son (debut, fin, boucle...)
    initial: SoundEdit = field(default_factory=SoundEdit)     # reglages de depart, pour « Reinitialiser »
    auto: tuple[int, int] = (0, 0)                            # debut et fin sans les silences

    @classmethod
    def from_file(cls, path: str, sound: audio.Sound, root: int) -> "SampleItem":
        looped = sound.loop_start is not None
        edit = SoundEdit(loop_mode=ins.LOOP_FORWARD if looped else ins.LOOP_FORWARD_NO_LOOP,
                         loop_start=sound.loop_start, loop_end=sound.loop_end)
        return cls(path, sound, root, edit=edit, initial=copy(edit), auto=audio.trim_bounds(sound.samples))

    @classmethod
    def from_wavesample(cls, ws: ins.Wavesample) -> "SampleItem":
        n = len(ws.samples)
        looped = ws.loop_mode >= ins.LOOP_FORWARD
        edit = SoundEdit(start=0, end=n - 1, rate_code=ws.rate_code, loop_mode=ws.loop_mode,
                         loop_start=ws.loop_start if looped else None, loop_end=ws.loop_end if looped else None)
        return cls(None, None, ws.root_key, ws.key_lo, ws.key_hi, ws, edit, copy(edit), (0, n - 1))

    @property
    def name(self) -> str:
        if self.ws is not None:
            return self.ws.name.strip()
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def samples(self):
        return self.ws.samples if self.ws is not None else self.sound.samples

    @property
    def rate(self) -> float:
        return self.ws.rate if self.ws is not None else self.sound.rate

    @property
    def loop(self) -> bool:
        return self.edit.looped

    @loop.setter
    def loop(self, on: bool):
        if on and not self.edit.looped:
            self.edit.loop_mode = ins.LOOP_FORWARD
        elif not on:
            self.edit.loop_mode = ins.LOOP_FORWARD_NO_LOOP

    @property
    def edited(self) -> bool:
        return self.edit != self.initial

    def kept(self, trim: bool) -> tuple[int, int]:
        """Debut et fin du son garde, en echantillons d'origine."""
        n = len(self.samples)
        auto = self.auto if (trim and self.ws is None) else (0, n - 1)
        a = auto[0] if self.edit.start is None else max(0, min(self.edit.start, n - 2))
        b = auto[1] if self.edit.end is None else max(a + 1, min(self.edit.end, n - 1))
        return a, b

    @property
    def duration(self) -> float:
        return len(self.samples) / self.rate

    @property
    def origin(self) -> str:
        where = T("Son de la disquette") if self.ws is not None else self.path
        return T("{0}\n{1:.0f} Hz, {2} échantillons").format(where, self.rate, len(self.samples))


def guess_root(path: str, sound: audio.Sound) -> int:
    """Note de base : lue dans le nom du fichier (« piano_C3.wav »), sinon dans le WAV, sinon C4."""
    stem = os.path.splitext(os.path.basename(path))[0]
    for text in reversed(_NOTE_IN_NAME.findall(stem)):
        try:
            key = project.note_to_midi(text)
        except ValueError:
            continue
        if ins.FIRST_KEY <= key <= ins.LAST_KEY:
            return key
    if sound.root_key is not None and ins.FIRST_KEY <= sound.root_key <= ins.LAST_KEY:
        return sound.root_key
    return 60


# --------------------------------------------------------------------------- ecoute
class Player:
    """Joue un son sur la carte son du PC (Windows). Le son est ecrit dans un fichier temporaire."""
    available = sys.platform == "win32"

    def __init__(self):
        self.path = os.path.join(tempfile.gettempdir(), f"epsbuilder_ecoute_{os.getpid()}.wav")

    def play(self, samples, rate: float) -> bool:
        if not self.available or len(samples) == 0:
            return False
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
        if not 8000 <= rate <= 96000:              # frequences inhabituelles : on ramene a 44,1 kHz
            samples, rate = audio.resample(samples, rate, 44100.0), 44100.0
        audio.write_wav(self.path, samples, rate)
        winsound.PlaySound(self.path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        return True

    def stop(self):
        if self.available:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        try:
            os.remove(self.path)
        except OSError:
            pass


def audition(ws: ins.Wavesample, seconds: float = 2.5):
    """Extrait a ecouter : tel que l'EPS le jouera (13 bits). Un son boucle est prolonge par sa boucle."""
    import numpy as np
    x = ins.decode_samples(ins.encode_samples(ws.samples))
    limit = int(6.0 * ws.rate)
    if ws.loop_mode >= ins.LOOP_FORWARD and ws.loop_start is not None and ws.loop_end is not None \
            and 0 <= ws.loop_start < ws.loop_end < len(x):
        loop = x[ws.loop_start:ws.loop_end + 1]
        if ws.loop_mode == ins.LOOP_BIDIRECTIONAL:
            loop = np.concatenate([loop, loop[-2:0:-1]])
        want = max(int(seconds * ws.rate), ws.loop_end + 1)
        repeats = -(-(want - ws.loop_end - 1) // len(loop))
        x = np.concatenate([x[:ws.loop_end + 1]] + [loop] * min(repeats, 20000))[:want].copy()
        fade = min(len(x), int(0.04 * ws.rate))
        x[-fade:] *= np.linspace(1.0, 0.0, fade)
    return x[:limit]


# --------------------------------------------------------------------------- clavier
class KeyboardView(QtWidgets.QWidget):
    """Clavier de 88 touches montrant la zone et la note de base de chaque son."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zones: list[tuple[int, int, int, QtGui.QColor]] = []      # lo, hi, note de base, couleur
        self._drag = None
        self.setMouseTracking(True)
        self.setMinimumHeight(100)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def set_zones(self, zones):
        self.zones = zones
        self.update()

    keyClicked = QtCore.Signal(int)
    WHITE = (0, 2, 4, 5, 7, 9, 11)

    def _geometry(self):
        whites = [k for k in range(ins.FIRST_KEY, ins.LAST_KEY + 1) if k % 12 in self.WHITE]
        w = self.width() / len(whites)
        top = 22
        h = self.height() - top - 14
        xpos = {k: i * w for i, k in enumerate(whites)}
        for k in range(ins.FIRST_KEY, ins.LAST_KEY + 1):
            if k not in xpos:
                xpos[k] = xpos[k - 1] + w * 0.65
        return whites, w, top, h, xpos

    def key_at(self, x: float, y: float) -> int | None:
        whites, w, top, h, xpos = self._geometry()
        if not (top <= y <= top + h):
            return None
        if y <= top + h * 0.6:                       # les touches noires passent devant
            for k in range(ins.FIRST_KEY, ins.LAST_KEY + 1):
                if k % 12 not in self.WHITE and xpos[k] <= x <= xpos[k] + w * 0.7:
                    return k
        for k in whites:
            if xpos[k] <= x < xpos[k] + w:
                return k
        return None

    zoneEdgeMoved = QtCore.Signal(int, str, int)      # numero du son, "lo" ou "hi", note
    zoneEditFinished = QtCore.Signal()
    BAND = 18                                         # hauteur de la bande des zones
    GRAB = 6                                          # distance de prise d'un bord, en pixels

    def key_at_x(self, x: float) -> int:
        """Note situee a l'abscisse x (touches noires comprises)."""
        whites, w, top, h, xpos = self._geometry()
        x = max(0.0, min(x, self.width() - 1))
        for k in range(ins.FIRST_KEY, ins.LAST_KEY + 1):
            if k % 12 not in self.WHITE and xpos[k] <= x <= xpos[k] + w * 0.7:
                return k
        for k in whites:
            if xpos[k] <= x < xpos[k] + w:
                return k
        return ins.LAST_KEY

    def _edge_at(self, x: float, y: float):
        """Bord de zone sous la souris : (numero du son, "lo" ou "hi"), sinon None."""
        if y > self.BAND + 3:
            return None
        whites, w, top, h, xpos = self._geometry()
        width_of = lambda k: w if k % 12 in self.WHITE else w * 0.7
        best = None
        for i, (lo, hi, _root, _color) in enumerate(self.zones):
            lo, hi = max(lo, ins.FIRST_KEY), min(hi, ins.LAST_KEY)
            if lo > hi:
                continue
            for side, ex in (("hi", xpos[hi] + width_of(hi)), ("lo", xpos[lo])):
                d = abs(x - ex)
                if d <= self.GRAB and (best is None or d < best[0]):
                    best = (d, i, side)
        return (best[1], best[2]) if best else None

    def mousePressEvent(self, event):
        pos = event.position()
        self._drag = self._edge_at(pos.x(), pos.y())
        if self._drag is None:
            key = self.key_at(pos.x(), pos.y())
            if key is not None:
                self.keyClicked.emit(key)

    def mouseMoveEvent(self, event):
        pos = event.position()
        drag = getattr(self, "_drag", None)
        if drag is not None and event.buttons() & Qt.LeftButton:
            self.zoneEdgeMoved.emit(drag[0], drag[1], self.key_at_x(pos.x()))
            return
        over_edge = self._edge_at(pos.x(), pos.y()) is not None
        self.setCursor(Qt.SizeHorCursor if over_edge else Qt.PointingHandCursor)

    def mouseReleaseEvent(self, _event):
        if getattr(self, "_drag", None) is not None:
            self._drag = None
            self.zoneEditFinished.emit()

    def paintEvent(self, _event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        whites, w, top, h, xpos = self._geometry()
        band = self.BAND - 2
        width_of = lambda k: w if k % 12 in self.WHITE else w * 0.7
        # bandes de zones
        for lo, hi, root, color in self.zones:
            lo, hi = max(lo, ins.FIRST_KEY), min(hi, ins.LAST_KEY)
            if lo > hi:
                continue
            x0, x1 = xpos[lo], xpos[hi] + width_of(hi)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QtCore.QRectF(x0 + 1, 2, x1 - x0 - 2, band), 4, 4)
            # poignees aux deux bords : on les fait glisser pour changer la plage
            p.setBrush(QtGui.QColor(255, 255, 255, 190))
            if x1 - x0 > 14:
                p.drawRect(QtCore.QRectF(x0 + 3, 5, 2, band - 6))
                p.drawRect(QtCore.QRectF(x1 - 5, 5, 2, band - 6))
        # touches blanches
        p.setPen(QtGui.QPen(QtGui.QColor("#8A8F98"), 1))
        for k in whites:
            p.setBrush(QtGui.QColor("#FFFFFF"))
            p.drawRect(QtCore.QRectF(xpos[k], top, w, h))
        # touches noires
        for k in range(ins.FIRST_KEY, ins.LAST_KEY + 1):
            if k in whites:
                continue
            p.setBrush(QtGui.QColor("#23262B"))
            p.drawRect(QtCore.QRectF(xpos[k], top, w * 0.7, h * 0.6))
        # notes de base
        for lo, hi, root, color in self.zones:
            if not ins.FIRST_KEY <= root <= ins.LAST_KEY:
                continue
            black = root not in whites
            cx = xpos[root] + width_of(root) / 2
            cy = top + (h * 0.45 if black else h * 0.82)
            p.setPen(QtGui.QPen(QtGui.QColor("#FFFFFF"), 1.5))
            p.setBrush(color)
            p.drawEllipse(QtCore.QPointF(cx, cy), 4.5, 4.5)
        # reperes des do
        p.setPen(QtGui.QColor("#5A6068"))
        font = p.font()
        font.setPointSizeF(7.5)
        p.setFont(font)
        for k in whites:
            if k % 12 == 0:
                p.drawText(QtCore.QRectF(xpos[k] - 6, top + h + 1, w + 12, 12), Qt.AlignCenter, project.midi_to_note(k))
        p.end()


class SampleTable(QtWidgets.QTableWidget):
    filesDropped = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(0, 7, parent)
        self.setAcceptDrops(True)
        self.setHorizontalHeaderLabels(["", T("Son"), T("Note de base"), T("Zone : de"), T("à"), T("Boucle"), T("Durée")])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)     # Ctrl / Maj : plusieurs sons
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for col, width in ((0, 26), (2, 104), (3, 88), (4, 88), (5, 60), (6, 84)):
            hh.setSectionResizeMode(col, QtWidgets.QHeaderView.Fixed)
            self.setColumnWidth(col, width)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if audio.is_audio_file(u.toLocalFile())]
        if paths:
            self.filesDropped.emit(paths)
            e.acceptProposedAction()


MIME_FILES = "application/x-epsbuilder-files"      # fichiers de la disquette ouverte (noms, un par ligne)
MIME_SLOT = "application/x-epsbuilder-slot"        # emplacement de la cle (nom du fichier image)


class DragTable(QtWidgets.QTableWidget):
    """Table dont on peut faire glisser les lignes, et qui recoit celles de l'autre table."""
    MIME_OUT = ""
    MIME_IN: tuple[str, ...] = ()
    dropped = QtCore.Signal(str, str, int)         # type, contenu, ligne visee (-1 : en dehors des lignes)

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        self.payload = lambda: ""                  # fourni par la fenetre : contenu a faire glisser

    def mimeTypes(self):
        return [self.MIME_OUT]

    def mimeData(self, _items):
        data = QtCore.QMimeData()
        data.setData(self.MIME_OUT, self.payload().encode("utf-8"))
        return data

    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def _accepted(self, event):
        return next((m for m in self.MIME_IN if event.mimeData().hasFormat(m)), None)

    def dragEnterEvent(self, event):
        if self._accepted(event):
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, event):
        mime = self._accepted(event)
        if not mime:
            event.ignore()
            return
        row = self.rowAt(int(event.position().y()))
        text = bytes(event.mimeData().data(mime)).decode("utf-8")
        event.setDropAction(Qt.CopyAction)
        event.accept()
        # Traitement differe : on laisse le glisser-deposer se terminer avant d'ouvrir une boite de dialogue.
        QtCore.QTimer.singleShot(0, lambda: self.dropped.emit(mime, text, row))


class DiskTable(DragTable):
    MIME_OUT = MIME_FILES
    MIME_IN = (MIME_FILES, MIME_SLOT)              # reorganisation interne, ou import depuis la cle


class KeyTable(DragTable):
    MIME_OUT = MIME_SLOT
    MIME_IN = (MIME_FILES,)                        # copie d'instruments vers un emplacement


def note_combo(value: int) -> QtWidgets.QComboBox:
    box = QtWidgets.QComboBox()
    for key, label in NOTE_CHOICES:
        box.addItem(label, key)
    box.setCurrentIndex(max(0, min(value - ins.FIRST_KEY, len(NOTE_CHOICES) - 1)))
    box.setMaxVisibleItems(18)
    return box


# --------------------------------------------------------------------------- fenetre principale
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("EPS Builder {0}").format(__version__))
        self.resize(1320, 900)
        self.settings = QtCore.QSettings("EPSBuilder", "EPSBuilder")
        self.samples: list[SampleItem] = []
        self.disk = EnsoniqDisk.blank()
        self.disk_name = T("Nouvelle disquette vierge")
        self.disk_dirty = False
        self.key: usbkey.UsbKey | None = None
        self.editing_name: str | None = None          # instrument de la disquette en cours de modification
        self.editing_base: ins.Instrument | None = None
        self.disk_file: str | None = None             # fichier de la cle dont vient la disquette ouverte
        self._slots: list = []
        self.player = Player()
        self._render_cache: dict = {}
        self._filling = False

        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_instrument_panel())
        right = QtWidgets.QSplitter(Qt.Vertical)
        right.addWidget(self._build_disk_panel())
        right.addWidget(self._build_key_panel())
        right.setStretchFactor(0, 2)
        right.setStretchFactor(1, 3)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([730, 550])
        self.setCentralWidget(splitter)
        self._build_menu()
        self.statusBar().showMessage(T("Glissez des fichiers audio dans la liste pour commencer."))

        self.refresh_samples()
        self.refresh_disk()
        self.refresh_drives()

    # ------------------------------------------------------------------ construction
    def _build_menu(self):
        m = self.menuBar().addMenu(T("&Fichier"))
        m.addAction(T("Nouvelle disquette vierge"), self.new_blank_disk)
        m.addAction(T("Nouvelle disquette avec OS…"), self.new_system_disk)
        m.addSeparator()
        m.addAction(T("Ouvrir une image de disquette…"), self.open_disk, QtGui.QKeySequence.Open)
        m.addAction(T("Enregistrer l'image sous…"), self.save_disk_as, QtGui.QKeySequence.SaveAs)
        m.addSeparator()
        m.addAction(T("Quitter"), self.close, QtGui.QKeySequence.Quit)
        lang = self.menuBar().addMenu("&Langue / Language")
        group = QtGui.QActionGroup(self)
        for code, label in i18n.LANGUAGES.items():
            action = lang.addAction(label)
            action.setCheckable(True)
            action.setChecked(code == i18n.LANG)
            action.triggered.connect(lambda _checked=False, c=code: self.choose_language(c))
            group.addAction(action)
        h = self.menuBar().addMenu(T("&Aide"))
        h.addAction(T("Manuel"), self.show_manual, QtGui.QKeySequence.HelpContents)
        h.addAction(T("Licence"), self.show_licence)
        h.addSeparator()
        h.addAction(T("À propos"), self.about)

    def choose_language(self, code: str):
        if code == i18n.LANG:
            return
        i18n.set_language(code)
        QtWidgets.QMessageBox.information(
            self, "EPS Builder",
            "La langue changera au prochain lancement de l'application.\n"
            "The language will change the next time the application starts.")

    def _build_instrument_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox(T("1. Instrument"))
        lay = QtWidgets.QVBoxLayout(box)

        self.edit_banner = QtWidgets.QFrame()
        self.edit_banner.setStyleSheet("QFrame{background:#FFF4D6;border:1px solid #E5C76B;border-radius:4px;} "
                                       "QLabel{border:none;background:transparent;color:#5C4A00;}")
        bl = QtWidgets.QHBoxLayout(self.edit_banner)
        bl.setContentsMargins(8, 4, 4, 4)
        self.edit_label = QtWidgets.QLabel()
        self.edit_label.setWordWrap(True)
        bl.addWidget(self.edit_label, 1)
        new_btn = QtWidgets.QPushButton(T("Nouvel instrument"))
        new_btn.setToolTip(T("Abandonne la modification et vide l'éditeur."))
        new_btn.clicked.connect(self.new_instrument)
        bl.addWidget(new_btn)
        lay.addWidget(self.edit_banner)

        form = QtWidgets.QHBoxLayout()
        self.name_edit = QtWidgets.QLineEdit(T("NOUVEAU"))
        self.name_edit.setMaxLength(12)
        self.name_edit.setMaximumWidth(170)
        self.name_edit.setValidator(QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(r"[ -~]{0,12}")))
        self.name_edit.textEdited.connect(lambda t: self.name_edit.setText(t.upper()))
        form.addWidget(QtWidgets.QLabel(T("Nom :")))
        form.addWidget(self.name_edit)
        form.addSpacing(12)
        self.rate_box = QtWidgets.QComboBox()
        for code, label in RATES:
            self.rate_box.addItem(label, code)
        self.rate_box.setCurrentIndex(3)
        self.rate_box.currentIndexChanged.connect(self.refresh_estimate)
        form.addWidget(QtWidgets.QLabel(T("Fréquence :")))
        form.addWidget(self.rate_box)
        form.addSpacing(12)
        self.env_box = QtWidgets.QComboBox()
        self.env_box.addItem(T("Son tenu"), ins.ENV_SUSTAIN)
        self.env_box.addItem(T("Son percussif (décroît)"), ins.ENV_PERCUSSIVE)
        form.addWidget(QtWidgets.QLabel(T("Enveloppe :")))
        form.addWidget(self.env_box)
        form.addStretch(1)
        lay.addLayout(form)

        self.table = SampleTable()
        self.table.filesDropped.connect(self.add_files)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setToolTip(T("Ctrl ou Maj + clic pour sélectionner plusieurs sons : retirer, boucler ou\nchanger "
                                "la note de base s'applique alors à toute la sélection."))
        lay.addWidget(self.table, 2)

        self.empty_hint = QtWidgets.QLabel(T("Glissez ici vos fichiers audio (WAV, AIFF, FLAC, MP3, OGG…), ou utilisez « Ajouter "
                                             "des sons… ».\nLa note de base est reconnue dans le nom du fichier (ex. "
                                             "piano_C3.wav).\nCtrl ou Maj + clic : sélectionner plusieurs sons pour les régler "
                                             "ensemble."))
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("color:#6B7280; padding:6px;")
        lay.addWidget(self.empty_hint)

        row = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton(T("Ajouter des sons…"))
        self.add_btn.clicked.connect(self.browse_samples)
        self.remove_btn = QtWidgets.QPushButton(T("Retirer"))
        self.remove_btn.clicked.connect(self.remove_sample)
        self.play_btn = QtWidgets.QPushButton(T("Écouter"))
        self.play_btn.setToolTip(T("Joue le son sélectionné tel qu'il sera dans l'EPS (fréquence choisie, 13 bits),\nà "
                                   "sa note de base. Cliquez sur le clavier pour l'entendre sur une autre note."))
        self.play_btn.clicked.connect(self.preview)
        self.auto_zones = QtWidgets.QCheckBox(T("Zones automatiques"))
        self.auto_zones.setChecked(True)
        self.auto_zones.setToolTip(T("Répartit le clavier à mi-chemin entre les notes de base."))
        self.auto_zones.toggled.connect(lambda _on: self.refresh_samples())
        self.normalize = QtWidgets.QCheckBox(T("Ajuster le niveau"))
        self.normalize.setChecked(True)
        self.trim = QtWidgets.QCheckBox(T("Couper les silences"))
        self.trim.setChecked(True)
        self.trim.setToolTip(T("Retire le silence au début et à la fin des sons importés,\ntant que leur début et "
                               "leur fin n'ont pas été réglés à la main."))
        self.trim.toggled.connect(lambda _on: (self.show_in_editor(force=True), self.refresh_estimate()))
        for wdg in (self.add_btn, self.remove_btn, self.play_btn):
            row.addWidget(wdg)
        row.addStretch(1)
        for wdg in (self.auto_zones, self.normalize, self.trim):
            row.addWidget(wdg)
        lay.addLayout(row)

        self.sound_editor = SoundEditor(RATES)
        self.sound_editor.changed.connect(self._sound_edited)
        self.sound_editor.group_setting.connect(self._group_setting)
        self.sound_editor.reset_requested.connect(self._reset_sound)
        lay.addWidget(self.sound_editor, 1)
        self._shown: SampleItem | None = None

        self.keyboard = KeyboardView()
        self.keyboard.setToolTip(T("Cliquez sur une touche pour écouter l'instrument à cette note.\nFaites glisser le "
                                   "bord d'une bande de couleur pour changer la plage d'un son."))
        self.keyboard.setCursor(Qt.PointingHandCursor)
        self.keyboard.keyClicked.connect(self.play_key)
        self.keyboard.zoneEdgeMoved.connect(self.move_zone_edge)
        self.keyboard.zoneEditFinished.connect(lambda: self.refresh_samples())
        lay.addWidget(self.keyboard)

        bottom = QtWidgets.QHBoxLayout()
        self.estimate = QtWidgets.QLabel()
        bottom.addWidget(self.estimate, 1)
        self.to_disk_btn = QtWidgets.QPushButton(T("Ajouter l'instrument à la disquette  ▶"))
        self.to_disk_btn.setDefault(True)
        self.to_disk_btn.setMinimumHeight(34)
        self.to_disk_btn.clicked.connect(self.add_instrument_to_disk)
        bottom.addWidget(self.to_disk_btn)
        lay.addLayout(bottom)
        return box

    def _build_disk_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox(T("2. Disquette"))
        lay = QtWidgets.QVBoxLayout(box)
        self.disk_title = QtWidgets.QLabel()
        self.disk_title.setStyleSheet("font-weight:600;")
        lay.addWidget(self.disk_title)
        self.disk_table = DiskTable(0, 3)
        self.disk_table.payload = lambda: "\n".join(e.name for e in self.selected_entries())
        self.disk_table.dropped.connect(self._dropped_on_disk)
        self.disk_table.setToolTip(T("Glissez un instrument pour changer l'ordre, ou vers un emplacement de la clé pour "
                                     "l'y copier.\nGlissez ici un emplacement de la clé pour en importer les instruments."))
        self.disk_table.setHorizontalHeaderLabels([T("Nom"), T("Type"), T("Blocs")])
        self.disk_table.verticalHeader().setVisible(False)
        self.disk_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.disk_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.disk_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.disk_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.disk_table.setColumnWidth(1, 150)
        self.disk_table.setColumnWidth(2, 60)
        self.disk_table.itemSelectionChanged.connect(self._update_buttons)
        self.disk_table.itemDoubleClicked.connect(lambda *_: self.edit_selected())
        lay.addWidget(self.disk_table, 1)
        self.disk_bar = QtWidgets.QProgressBar()
        self.disk_bar.setTextVisible(True)
        lay.addWidget(self.disk_bar)
        row = QtWidgets.QHBoxLayout()
        for label, slot in ((T("Vierge"), self.new_blank_disk), (T("Avec OS…"), self.new_system_disk),
                            (T("Ouvrir…"), self.open_disk), (T("Enregistrer sous…"), self.save_disk_as)):
            b = QtWidgets.QPushButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        row2 = QtWidgets.QHBoxLayout()
        self.edit_btn = QtWidgets.QPushButton(T("Modifier l'instrument"))
        self.edit_btn.setToolTip(T("Charge l'instrument sélectionné dans l'éditeur (double-clic)."))
        self.edit_btn.clicked.connect(self.edit_selected)
        self.listen_btn = QtWidgets.QPushButton(T("Écouter"))
        self.listen_btn.setToolTip(T("Fait entendre les sons de l'instrument sélectionné, l'un après l'autre."))
        self.listen_btn.clicked.connect(self.play_disk_instrument)
        self.up_btn = QtWidgets.QPushButton(T("▲ Monter"))
        self.up_btn.clicked.connect(lambda: self.move_entry(-1))
        self.down_btn = QtWidgets.QPushButton(T("▼ Descendre"))
        self.down_btn.clicked.connect(lambda: self.move_entry(1))
        self.export_btn = QtWidgets.QPushButton(T("Exporter en WAV…"))
        self.export_btn.clicked.connect(self.export_wav)
        self.delete_btn = QtWidgets.QPushButton(T("Supprimer"))
        self.delete_btn.clicked.connect(self.delete_file)
        for b in (self.edit_btn, self.listen_btn, self.up_btn, self.down_btn):
            row2.addWidget(b)
        row2.addStretch(1)
        row2.addWidget(self.export_btn)
        row2.addWidget(self.delete_btn)
        lay.addLayout(row2)
        lay.addLayout(row)
        return box

    def _build_key_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QGroupBox(T("3. Clé USB du Gotek"))
        lay = QtWidgets.QVBoxLayout(box)
        row = QtWidgets.QHBoxLayout()
        self.drive_box = QtWidgets.QComboBox()
        self.drive_box.setMinimumWidth(170)
        self.drive_box.activated.connect(self._drive_chosen)
        browse = QtWidgets.QPushButton(T("Parcourir…"))
        browse.clicked.connect(self.browse_key)
        refresh = QtWidgets.QPushButton(T("Actualiser"))
        refresh.clicked.connect(self.refresh_drives)
        self.mode_box = QtWidgets.QComboBox()
        self.mode_box.addItem(T("HxC (emplacements numérotés)"), usbkey.MODE_HXC)
        self.mode_box.addItem(T("FlashFloppy (noms libres)"), usbkey.MODE_FLASHFLOPPY)
        self.mode_box.activated.connect(self._mode_chosen)
        row.addWidget(self.drive_box, 1)
        row.addWidget(browse)
        row.addWidget(refresh)
        row.addWidget(self.mode_box)
        lay.addLayout(row)
        self.key_table = KeyTable(0, 3)
        self.key_table.payload = lambda: (self.selected_slot().filename if self.selected_slot() else "")
        self.key_table.dropped.connect(self._dropped_on_key)
        self.key_table.setToolTip(T("Double-clic : ouvrir l'emplacement.\nGlissez un emplacement vers la disquette pour "
                                    "en importer les instruments.\nDéposez ici un instrument de la disquette pour le "
                                    "copier dans un emplacement (sous les lignes : nouvel emplacement)."))
        self.key_table.setHorizontalHeaderLabels([T("Emplacement"), T("Contenu"), T("Libre")])
        self.key_table.verticalHeader().setVisible(False)
        self.key_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.key_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.key_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.key_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.key_table.setColumnWidth(0, 96)
        self.key_table.setColumnWidth(2, 70)
        self.key_table.itemSelectionChanged.connect(self._update_buttons)
        self.key_table.itemDoubleClicked.connect(lambda *_: self.open_slot())
        lay.addWidget(self.key_table, 1)
        row = QtWidgets.QHBoxLayout()
        self.open_slot_btn = QtWidgets.QPushButton(T("Ouvrir"))
        self.open_slot_btn.setToolTip(T("Charge cet emplacement dans la partie « Disquette »."))
        self.open_slot_btn.clicked.connect(self.open_slot)
        self.catalog_btn = QtWidgets.QPushButton(T("Catalogue…"))
        self.catalog_btn.clicked.connect(self.save_catalog)
        self.write_sel_btn = QtWidgets.QPushButton(T("Remplacer l'emplacement"))
        self.write_sel_btn.clicked.connect(lambda: self.write_to_key(new=False))
        self.write_new_btn = QtWidgets.QPushButton(T("Écrire dans un nouvel emplacement"))
        self.write_new_btn.setMinimumHeight(34)
        self.write_new_btn.clicked.connect(lambda: self.write_to_key(new=True))
        row.addWidget(self.open_slot_btn)
        row.addWidget(self.catalog_btn)
        row.addStretch(1)
        row.addWidget(self.write_sel_btn)
        row.addWidget(self.write_new_btn)
        lay.addLayout(row)
        return box

    # ------------------------------------------------------------------ utilitaires
    def error(self, ex: Exception | str):
        QtWidgets.QMessageBox.warning(self, "EPS Builder", str(ex))

    def confirm(self, text: str, detail: str = "") -> bool:
        box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, "EPS Builder", text, parent=self)
        if detail:
            box.setInformativeText(detail)
        yes = box.addButton(T("Continuer"), QtWidgets.QMessageBox.AcceptRole)
        box.addButton(T("Annuler"), QtWidgets.QMessageBox.RejectRole)
        box.exec()
        return box.clickedButton() is yes

    def last_dir(self, key: str) -> str:
        return self.settings.value(key, os.path.expanduser("~"))

    def keep_dir(self, key: str, path: str):
        self.settings.setValue(key, os.path.dirname(path) if os.path.isfile(path) else path)

    def _update_buttons(self):
        has_sample = bool(self.samples)
        rows = self.selected_rows()
        self.remove_btn.setEnabled(bool(rows))
        self.remove_btn.setText(T("Retirer ({0})").format(len(rows)) if len(rows) > 1 else T("Retirer"))
        self.play_btn.setEnabled(bool(rows))
        self.to_disk_btn.setEnabled(has_sample)
        entry = self.selected_entry()
        self.delete_btn.setEnabled(entry is not None)
        self.edit_btn.setEnabled(entry is not None and entry.file_type == TYPE_EPS_INSTRUMENT)
        self.listen_btn.setEnabled(entry is not None and entry.file_type == TYPE_EPS_INSTRUMENT)
        self.up_btn.setEnabled(self.can_move(-1))
        self.down_btn.setEnabled(self.can_move(1))
        editing = self.editing_name is not None
        self.edit_banner.setVisible(editing)
        if editing:
            self.edit_label.setText(
                f"<b>Modification de « {self.editing_name.strip()} »</b> — les sons déjà présents gardent leurs "
                "réglages ; fréquence, niveau, silences et enveloppe ne concernent que les sons ajoutés.")
        self.to_disk_btn.setText(T("Mettre à jour l'instrument sur la disquette  ▶") if editing
                                 else T("Ajouter l'instrument à la disquette  ▶"))
        self.export_btn.setEnabled(any(e.file_type == TYPE_EPS_INSTRUMENT for e in self.disk.entries()))
        has_key = self.key is not None
        slot = self.selected_slot()
        self.open_slot_btn.setEnabled(slot is not None and not slot.error)
        self.write_sel_btn.setEnabled(slot is not None)
        self.write_new_btn.setEnabled(has_key)
        self.catalog_btn.setEnabled(has_key and self.key_table.rowCount() > 0)

    # ------------------------------------------------------------------ sons
    def browse_samples(self):
        patterns = " ".join("*" + ext for ext in audio.AUDIO_EXTENSIONS)
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, T("Ajouter des sons"), self.last_dir("wav_dir"),
                                                          T("Fichiers audio ({0});;Tous les fichiers (*)").format(patterns))
        if paths:
            self.keep_dir("wav_dir", paths[0])
            self.add_files(paths)

    def add_files(self, paths: list[str]):
        problems = []
        for path in paths:
            try:
                sound = audio.read_sound(path)
                if len(sound.samples) < 16:
                    raise audio.AudioError(T("{0} : son trop court").format(os.path.basename(path)))
                item = SampleItem.from_file(path, sound, guess_root(path, sound))
                if not self.auto_zones.isChecked():
                    self.place_new_item(item)
                self.samples.append(item)
            except ERRORS as ex:
                problems.append(str(ex))
        if len(self.samples) > ins.MAX_WAVESAMPLES:
            del self.samples[ins.MAX_WAVESAMPLES:]
            problems.append(T("Un instrument contient au maximum 127 sons."))
        self.samples.sort(key=lambda s: s.root)
        if self.name_edit.text() in ("", T("NOUVEAU")) and self.samples:
            stem = _NOTE_IN_NAME.sub("", self.samples[0].name).strip(" _-") or self.samples[0].name
            self.name_edit.setText(stem.upper()[:12])
        self.refresh_samples()
        if problems:
            self.error("\n".join(problems))

    def selected_rows(self) -> list[int]:
        model = self.table.selectionModel()
        rows = sorted({i.row() for i in model.selectedRows()}) if model else []
        return [r for r in rows if r < len(self.samples)]

    def select_items(self, items: list[SampleItem]):
        """Reselectionne des sons apres une reconstruction de la liste."""
        self.table.clearSelection()
        model = self.table.selectionModel()
        wanted = {id(i) for i in items}
        for row, item in enumerate(self.samples):
            if id(item) in wanted:
                model.select(self.table.model().index(row, 0),
                             QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)

    def place_new_item(self, item: SampleItem) -> None:
        """Zones manuelles : donne une plage a un nouveau son sans chevaucher les autres. S'il tombe dans
        la plage d'un son existant, celle-ci est partagee a mi-chemin entre les deux notes de base."""
        host = next((s for s in self.samples if s.lo <= item.root <= s.hi), None)
        if host is None:
            taken = {k for s in self.samples for k in range(s.lo, s.hi + 1)}
            lo = hi = item.root
            while lo - 1 >= ins.FIRST_KEY and lo - 1 not in taken:
                lo -= 1
            while hi + 1 <= ins.LAST_KEY and hi + 1 not in taken:
                hi += 1
            item.lo, item.hi = lo, hi
        elif host.lo == host.hi:
            item.lo = item.hi = item.root              # plus de place : chevauchement signale a l'ecriture
        elif item.root >= host.root:
            cut = max(host.lo, min((host.root + item.root) // 2, host.hi - 1))
            item.lo, item.hi, host.hi = cut + 1, host.hi, cut
        else:
            cut = max(host.lo, min((host.root + item.root) // 2, host.hi - 1))
            item.lo, item.hi, host.lo = host.lo, cut, cut + 1

    def remove_sample(self):
        rows = self.selected_rows()
        if rows:
            self.samples = [s for r, s in enumerate(self.samples) if r not in rows]
            self.refresh_samples()

    def _group_for(self, row: int) -> list[SampleItem]:
        """Les sons concernes par une modification faite sur une ligne : toute la selection si la
        ligne en fait partie, sinon cette ligne seule."""
        rows = self.selected_rows()
        if row in rows and len(rows) > 1:
            return [self.samples[r] for r in rows]
        return [self.samples[row]]

    def apply_auto_zones(self):
        if self.auto_zones.isChecked() and self.samples:
            for item, (lo, hi) in zip(self.samples, project.auto_zones([s.root for s in self.samples])):
                item.lo, item.hi = lo, hi

    def refresh_samples(self, keep: list[SampleItem] | None = None):
        if not isinstance(keep, list):
            keep = [self.samples[r] for r in self.selected_rows()]
        self.apply_auto_zones()
        self._filling = True
        for r in range(self.table.rowCount()):             # les anciens controles disparaissent tout de suite
            for c in (2, 3, 4, 5):
                old = self.table.cellWidget(r, c)
                if old is not None:
                    self.table.removeCellWidget(r, c)
                    old.hide()
                    old.setParent(None)
                    old.deleteLater()
        self.table.setRowCount(len(self.samples))
        self._loop_boxes = []
        for row, item in enumerate(self.samples):
            color = QtGui.QColor(ZONE_COLORS[row % len(ZONE_COLORS)])
            chip = QtWidgets.QTableWidgetItem()
            chip.setBackground(color)
            self.table.setItem(row, 0, chip)
            name = QtWidgets.QTableWidgetItem(item.name)
            name.setToolTip(item.origin)
            self.table.setItem(row, 1, name)
            root = note_combo(item.root)
            root.currentIndexChanged.connect(lambda _i, r=row, b=root: self._root_changed(r, b))
            self.table.setCellWidget(row, 2, root)
            for col, attr in ((3, "lo"), (4, "hi")):
                box = note_combo(getattr(item, attr))
                box.setToolTip(T("Modifier la plage désactive les zones automatiques.\nLa plage voisine s'ajuste pour "
                                 "ne pas se chevaucher."))
                box.currentIndexChanged.connect(lambda _i, r=row, a=attr, b=box: self._zone_changed(r, a, b))
                self.table.setCellWidget(row, col, box)
            loop = QtWidgets.QCheckBox()
            loop.setChecked(item.loop)
            self._loop_boxes.append(loop)
            loop.setToolTip(T("Le son se répète tant que la touche est enfoncée.\nPoints de boucle lus dans le WAV "
                              "s'ils existent, sinon tout le son."))
            loop.toggled.connect(lambda on, r=row: self._loop_changed(r, on))
            holder = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setAlignment(Qt.AlignCenter)
            hl.addWidget(loop)
            self.table.setCellWidget(row, 5, holder)
            dur = QtWidgets.QTableWidgetItem(f"{item.duration:.2f} s")
            dur.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 6, dur)
        self.select_items(keep)
        self._filling = False
        self.show_in_editor()
        self.empty_hint.setVisible(not self.samples)
        self.refresh_keyboard()
        self.refresh_estimate()
        self._update_buttons()

    def refresh_keyboard(self):
        self.keyboard.set_zones([(s.lo, s.hi, s.root, QtGui.QColor(ZONE_COLORS[i % len(ZONE_COLORS)]))
                                 for i, s in enumerate(self.samples)])

    def _root_changed(self, row: int, box: QtWidgets.QComboBox):
        if self._filling or row >= len(self.samples):
            return
        group = self._group_for(row)
        shift = box.currentData() - self.samples[row].root
        for item in group:                       # selection multiple : meme transposition pour tous
            item.root = max(ins.FIRST_KEY, min(ins.LAST_KEY, item.root + shift))
        if self.auto_zones.isChecked():
            self.samples.sort(key=lambda s: s.root)
        if self.auto_zones.isChecked() or len(group) > 1:
            # L'ordre ou plusieurs lignes changent : on reconstruit la liste apres l'evenement.
            QtCore.QTimer.singleShot(0, lambda: self.refresh_samples(group if len(group) > 1 else None))
        else:
            self.refresh_keyboard()

    def set_zone_edge(self, index: int, side: str, key: int) -> None:
        """Deplace le bas ("lo") ou le haut ("hi") de la plage d'un son. La plage voisine suit le
        mouvement si elle etait accolee, et recule si elle serait recouverte ; elle garde au moins une note."""
        if not 0 <= index < len(self.samples):
            return
        if self.auto_zones.isChecked():                     # une retouche a la main fige les zones
            self.auto_zones.blockSignals(True)
            self.auto_zones.setChecked(False)
            self.auto_zones.blockSignals(False)
        item = self.samples[index]
        others = [s for s in self.samples if s is not item]
        if side == "hi":
            right = min((s for s in others if s.lo > item.lo), key=lambda s: s.lo, default=None)
            limit = right.hi - 1 if right else ins.LAST_KEY
            key = max(item.lo, min(key, limit))
            if right and (right.lo <= key or right.lo == item.hi + 1):
                right.lo = key + 1
            item.hi = key
        else:
            left = max((s for s in others if s.hi < item.hi), key=lambda s: s.hi, default=None)
            limit = left.lo + 1 if left else ins.FIRST_KEY
            key = min(item.hi, max(key, limit))
            if left and (left.hi >= key or left.hi == item.lo - 1):
                left.hi = key - 1
            item.lo = key

    def move_zone_edge(self, index: int, side: str, key: int):
        self.set_zone_edge(index, side, key)
        self.refresh_keyboard()
        item = self.samples[index] if 0 <= index < len(self.samples) else None
        if item:
            self.statusBar().showMessage(T("« {0} » : de {1} à {2}").format(item.name, project.midi_to_note(item.lo), project.midi_to_note(item.hi)), 3000)

    def _zone_changed(self, row: int, attr: str, box: QtWidgets.QComboBox):
        if self._filling or row >= len(self.samples):
            return
        self.set_zone_edge(row, attr, box.currentData())
        # Une plage voisine a pu bouger, ou la valeur a ete bornee : on reaffiche la liste.
        QtCore.QTimer.singleShot(0, lambda: self.refresh_samples())

    def _loop_changed(self, row: int, on: bool):
        if self._filling or row >= len(self.samples):
            return
        group = self._group_for(row)
        for item in group:                       # selection multiple : meme reglage pour tous
            item.loop = on
        self.sync_loop_boxes()
        self.show_in_editor(force=True)
        self.refresh_estimate()

    # ------------------------------------------------------------------ reglage du son selectionne
    def _selection_changed(self):
        if not self._filling:
            self.show_in_editor()
        self._update_buttons()

    def show_in_editor(self, force: bool = False):
        """Affiche dans l'editeur de son le premier son selectionne."""
        rows = self.selected_rows()
        item = self.samples[rows[0]] if rows else None
        if item is self._shown and not force:
            return
        self._shown = item
        if item is None:
            self.sound_editor.set_sound(None, None, 1.0, (0, 0), "")
        else:
            n = len(item.samples)
            auto = item.auto if (self.trim.isChecked() and item.ws is None) else (0, n - 1)
            self.sound_editor.set_sound(item.edit, item.samples, item.rate, auto, item.name)

    def sync_loop_boxes(self):
        self._filling = True
        for box, item in zip(self._loop_boxes, self.samples):
            box.setChecked(item.loop)
        self._filling = False

    def _sound_edited(self):
        self.sync_loop_boxes()
        self.refresh_estimate()

    def _group_setting(self, name: str, value):
        """Un reglage commun (frequence, resolution, compression, fondus, type de boucle) s'applique
        aussi aux autres sons selectionnes."""
        for row in self.selected_rows():
            item = self.samples[row]
            if item is not self._shown:
                setattr(item.edit, name, value)

    def _reset_sound(self):
        for row in self.selected_rows():
            self.samples[row].edit = copy(self.samples[row].initial)
        self.show_in_editor(force=True)
        self._sound_edited()

    def rate_code(self) -> int:
        return self.rate_box.currentData()

    def output_length(self, item: SampleItem) -> tuple[int, float]:
        """Nombre d'echantillons et frequence du son une fois converti."""
        a, b = item.kept(self.trim.isChecked())
        if item.ws is not None:
            rate = ins.rate_hz(item.edit.rate_code or item.ws.rate_code)
        else:
            rate = ins.rate_hz(ins.rate_code_for(min(ins.rate_hz(item.edit.rate_code or self.rate_code()), item.rate)))
        return int((b - a + 1) * rate / item.rate), rate

    def estimated_blocks(self) -> tuple[int, float]:
        total_bytes, seconds = ins.INST_SIZE + ins.LAYER_SIZE, 0.0
        for item in self.samples:
            n, rate = self.output_length(item)
            total_bytes += ins.WS_PARAM_SIZE + 2 * ((n + ins.GUARD_WORDS + 7) & ~7)
            seconds += n / rate
        return -(-total_bytes // 512), seconds

    def refresh_estimate(self):
        if not self.samples:
            self.estimate.setText("")
            return
        blocks, seconds = self.estimated_blocks()
        free = self.disk.free_blocks
        if self.editing_name is not None:
            old = self.disk.find(self.editing_name)
            free += old.blocks if old else 0
        text = (T("{0} son(s), {1:.1f} s — environ {2} blocs ({3} Ko) pour {4} blocs libres sur la disquette.").format(len(self.samples), seconds, blocks, blocks // 2, free))
        if blocks > free:
            text = f"<span style='color:#C0392B'><b>Trop gros pour la disquette.</b> {text}</span>"
        self.estimate.setText(text)

    def specs(self) -> list[project.SampleSpec]:
        return [self.spec_for(s) for s in self.samples]

    def spec_for(self, item: SampleItem) -> project.SampleSpec:
        if item.ws is not None:
            # Son de la disquette : repris tel quel tant qu'aucun reglage n'a ete touche.
            return project.SampleSpec(None, item.root, item.lo, item.hi, item.loop, None, item.ws,
                                      copy(item.edit) if item.edited else None)
        return project.SampleSpec(item.path, item.root, item.lo, item.hi, item.loop, item.name, None,
                                  copy(item.edit), item.sound)

    def check_zones(self) -> str:
        used = {}
        for s in self.samples:
            if s.lo > s.hi:
                return T("« {0} » : le bas de la zone est au-dessus du haut.").format(s.name)
            for k in range(s.lo, s.hi + 1):
                if k in used:
                    return (T("Les zones de « {0} » et « {1} » se chevauchent sur la note {2}.").format(used[k], s.name, project.midi_to_note(k)))
                used[k] = s.name
        return ""

    def build_instrument(self) -> ins.Instrument | None:
        name = self.name_edit.text().strip()
        if not name:
            self.error(T("Donnez un nom à l'instrument."))
            return None
        problem = self.check_zones()
        if problem:
            self.error(problem)
            return None
        return project.make_instrument(name, self.specs(), rate_hz=ins.rate_hz(self.rate_code()),
                                       normalize=self.normalize.isChecked(), trim=self.trim.isChecked(),
                                       envelope=self.env_box.currentData(),
                                       base=self.editing_base if self.editing_name is not None else None)

    def render_item(self, item: SampleItem) -> ins.Wavesample:
        """Le son tel qu'il sera ecrit dans l'instrument (conversion gardee en memoire)."""
        key = (id(item), astuple(item.edit), self.rate_code(), self.normalize.isChecked(), self.trim.isChecked())
        if key not in self._render_cache:
            if len(self._render_cache) > 64:
                self._render_cache.clear()
            inst = project.make_instrument("X", [self.spec_for(item)], rate_hz=ins.rate_hz(self.rate_code()),
                                           normalize=self.normalize.isChecked(), trim=self.trim.isChecked())
            self._render_cache[key] = inst.layers[0].wavesamples[0]
        return self._render_cache[key]

    def play_item(self, item: SampleItem, key: int | None = None):
        """Joue un son, a sa note de base ou transpose sur la touche demandee."""
        if not self.player.available:
            self.statusBar().showMessage(T("L'écoute n'est disponible que sous Windows."), 6000)
            return
        try:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            ws = self.render_item(item)
            ratio = 2.0 ** (((key if key is not None else item.root) - item.root) / 12.0)
            self.player.play(audition(ws), ws.rate * ratio)
            note = project.midi_to_note(key if key is not None else item.root)
            self.statusBar().showMessage(T("Écoute : « {0} » sur {1}").format(item.name, note), 4000)
        except ERRORS as ex:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.error(ex)
        finally:
            while QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()

    def preview(self):
        rows = self.selected_rows()
        if rows:
            self.play_item(self.samples[rows[0]])

    def item_for_key(self, key: int) -> SampleItem | None:
        return next((s for s in self.samples if s.lo <= key <= s.hi), None)

    def play_key(self, key: int):
        item = self.item_for_key(key)
        if item is None:
            self.statusBar().showMessage(T("Aucun son sur la note {0}.").format(project.midi_to_note(key)), 4000)
        else:
            self.play_item(item, key)

    def play_disk_instrument(self):
        """Fait entendre l'un apres l'autre les sons de l'instrument selectionne sur la disquette."""
        entry = self.selected_entry()
        if entry is None or entry.file_type != TYPE_EPS_INSTRUMENT:
            return
        if not self.player.available:
            self.statusBar().showMessage(T("L'écoute n'est disponible que sous Windows."), 6000)
            return
        try:
            import numpy as np
            inst = ins.parse_instrument(self.disk.read_file(entry))
            sounds = inst.all_wavesamples()
            rate = sounds[0].rate
            parts = []
            for ws in sounds[:16]:
                x = audition(ws, seconds=1.5)[:int(2.0 * ws.rate)].copy()
                fade = min(len(x), int(0.03 * ws.rate))
                x[-fade:] *= np.linspace(1.0, 0.0, fade)
                parts += [audio.resample(x, ws.rate, rate), np.zeros(int(0.25 * rate))]
            self.player.play(np.concatenate(parts), rate)
            self.statusBar().showMessage(T("Écoute de « {0} » : {1} son(s), chacun à sa hauteur d'origine.").format(entry.name.strip(), len(sounds)), 6000)
        except ERRORS as ex:
            self.error(ex)

    def add_instrument_to_disk(self):
        try:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            inst = self.build_instrument()
            if inst is None:
                return
            data = ins.build_instrument(inst)
            QtWidgets.QApplication.restoreOverrideCursor()
            target = None                                  # fichier a remplacer, s'il y en a un
            if self.editing_name is not None and self.disk.find(self.editing_name):
                target = self.editing_name
            elif self.disk.find(inst.name):
                if not self.confirm(T("« {0} » existe déjà sur la disquette.").format(inst.name.upper()), T("Le remplacer ?")):
                    return
                target = inst.name
            if target is not None:
                self.disk.replace_file(target, inst.name, TYPE_EPS_INSTRUMENT, data)
                verb = T("mis à jour sur")
            else:
                self.disk.add_file(inst.name, TYPE_EPS_INSTRUMENT, data)
                verb = T("ajouté à")
            self.disk_dirty = True
            if self.editing_name is not None:
                self.load_into_editor(inst.name)           # l'editeur repart de la version enregistree
            self.refresh_disk()
            self.statusBar().showMessage(T("Instrument « {0} » {1} la disquette.").format(inst.name.upper().strip(), verb), 8000)
        except ERRORS as ex:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.error(ex)
        finally:
            while QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()

    # ------------------------------------------------------------------ modification d'un instrument
    def new_instrument(self):
        if self.samples and not self.confirm(T("Vider l'éditeur d'instrument ?"),
                                             T("Les sons listés seront retirés de l'éditeur. La disquette n'est pas modifiée.")):
            return
        self.samples = []
        self.editing_name = self.editing_base = None
        self.name_edit.setText(T("NOUVEAU"))
        self.auto_zones.setChecked(True)
        self.refresh_samples()

    def load_into_editor(self, name: str) -> bool:
        entry = self.disk.find(name)
        if entry is None:
            return False
        inst = ins.parse_instrument(self.disk.read_file(entry))
        if len(inst.layers) != 1:
            raise ins.InstrumentError(
                T("« {0} » contient {1} layers. L'éditeur ne gère pour l'instant que les instruments à "
                  "un seul layer ; celui-ci peut être déplacé, supprimé ou exporté en WAV.").format(entry.name.strip(), len(inst.layers)))
        self.samples = [SampleItem.from_wavesample(ws)
                        for ws in sorted(inst.layers[0].wavesamples, key=lambda w: w.key_lo)]
        self.editing_name, self.editing_base = entry.name, inst
        self.name_edit.setText(entry.name.strip())
        self.auto_zones.blockSignals(True)
        self.auto_zones.setChecked(False)                  # on conserve les zones telles qu'elles sont
        self.auto_zones.blockSignals(False)
        self.refresh_samples()
        return True

    def edit_selected(self):
        entry = self.selected_entry()
        if entry is None or entry.file_type != TYPE_EPS_INSTRUMENT:
            return
        if self.samples and self.editing_name != entry.name and not self.confirm(
                T("Charger « {0} » dans l'éditeur ?").format(entry.name.strip()),
                T("Les sons actuellement listés dans l'éditeur seront retirés.")):
            return
        try:
            self.load_into_editor(entry.name)
            self.statusBar().showMessage(
                T("« {0} » chargé : modifiez-le, puis « Mettre à jour l'instrument sur la disquette ».").format(entry.name.strip()), 10000)
        except ERRORS as ex:
            self.error(ex)

    def can_move(self, delta: int) -> bool:
        entries = self.disk.entries()
        i = self.disk_table.currentRow()
        j = i + delta
        return (0 <= i < len(entries) and 0 <= j < len(entries)
                and entries[i].file_type not in OS_TYPES and entries[j].file_type not in OS_TYPES)

    def move_entry(self, delta: int):
        if not self.can_move(delta):
            return
        names = [e.name for e in self.disk.entries()]
        i = self.disk_table.currentRow()
        names[i], names[i + delta] = names[i + delta], names[i]
        try:
            self.disk.reorder(names)
            self.disk_dirty = True
            self.refresh_disk()
            self.disk_table.selectRow(i + delta)
        except ERRORS as ex:
            self.error(ex)

    # ------------------------------------------------------------------ disquette
    def selected_entry(self):
        row = self.disk_table.currentRow()
        entries = self.disk.entries()
        return entries[row] if 0 <= row < len(entries) else None

    def selected_entries(self) -> list:
        model = self.disk_table.selectionModel()
        rows = sorted({i.row() for i in model.selectedRows()}) if model else []
        entries = self.disk.entries()
        return [entries[r] for r in rows if r < len(entries)]

    # ------------------------------------------------------------------ glisser-deposer
    def _dropped_on_disk(self, mime: str, text: str, row: int):
        if mime == MIME_FILES:
            self.move_entries_to([n for n in text.split("\n") if n], row)
        elif mime == MIME_SLOT and self.key is not None:
            slot = next((s for s in self._slots if s.filename == text), None)
            if slot is not None:
                self.import_from_slot(slot)

    def _dropped_on_key(self, _mime: str, text: str, row: int):
        names = [n for n in text.split("\n") if n]
        slot = self._slots[row] if 0 <= row < len(self._slots) else None
        if names and self.key is not None:
            self.copy_files_to_slot(names, slot)

    def move_entries_to(self, names: list[str], row: int):
        """Reorganisation par glisser-deposer : les fichiers passent devant la ligne visee. L'OS reste en tete."""
        entries = self.disk.entries()
        moved = [e.name for e in entries if e.name in names and e.file_type not in OS_TYPES]
        if not moved:
            return
        before = entries[row].name if 0 <= row < len(entries) else None
        if before in moved:
            return
        rest = [e.name for e in entries if e.name not in moved]
        pos = rest.index(before) if before in rest else len(rest)
        order = rest[:pos] + moved + rest[pos:]
        types = {e.name: e.file_type for e in entries}
        order = [n for n in order if types[n] in OS_TYPES] + [n for n in order if types[n] not in OS_TYPES]
        if order == [e.name for e in entries]:
            return
        try:
            self.disk.reorder(order)
            self.disk_dirty = True
            self.refresh_disk()
            self.disk_table.clearSelection()
            for r, e in enumerate(self.disk.entries()):
                if e.name in moved:
                    self.disk_table.selectionModel().select(
                        self.disk_table.model().index(r, 0),
                        QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
        except ERRORS as ex:
            self.error(ex)

    def transfer(self, source: EnsoniqDisk, names: list[str], target: EnsoniqDisk, target_label: str) -> list[str] | None:
        """Copie des fichiers d'une disquette a une autre. Retourne les noms copies, ou None si annule.
        target n'est modifiee que si tout a pu etre copie."""
        trial = EnsoniqDisk(bytes(target.img))
        copied = []
        for name in names:
            entry = source.find(name)
            if entry is None or entry.file_type in OS_TYPES:
                continue
            data = source.read_file(entry)
            if trial.find(name):
                if not self.confirm(T("« {0} » existe déjà dans {1}.").format(name.strip(), target_label), T("Le remplacer ?")):
                    continue
                trial.replace_file(name, name, entry.file_type, data)
            else:
                trial.add_file(name, entry.file_type, data, entry.type_info)
            copied.append(name.strip())
        if not copied:
            return None
        target.img[:] = trial.img
        return copied

    def new_slot_name(self) -> tuple[str, str] | None:
        """Nom de fichier et libelle d'un nouvel emplacement sur la cle (None si annule)."""
        if self.key.mode == usbkey.MODE_HXC:
            number = self.key.next_free_number()
            return self.key.filename_for(number), T("emplacement {0}").format(f"{number:03d}")
        entries = [e for e in self.disk.entries() if e.file_type not in OS_TYPES]
        default = (entries[0].name.strip() if entries else T("DISQUETTE")).replace(" ", "_")
        filename, ok = QtWidgets.QInputDialog.getText(self, T("Nouveau fichier"), T("Nom du fichier sur la clé :"),
                                                      text=default + ".hfe")
        filename = filename.strip()
        if not ok or not filename:
            return None
        if not filename.upper().endswith(".HFE"):
            filename += ".hfe"
        if self.key.existing_name(filename):
            self.error(T("« {0} » existe déjà sur la clé. Choisissez un autre nom, ou sélectionnez ce fichier "
                         "et utilisez « Remplacer l'emplacement ».").format(filename))
            return None
        return filename, filename

    def copy_files_to_slot(self, names: list[str], slot) -> bool:
        """Copie des instruments de la disquette ouverte dans un emplacement de la cle (slot None : nouveau)."""
        names = [n for n in names if self.disk.find(n) and self.disk.find(n).file_type not in OS_TYPES]
        if not names or self.key is None:
            return False
        listing = ", ".join(n.strip() for n in names)
        try:
            if slot is None:
                chosen = self.new_slot_name()
                if chosen is None:
                    return False
                filename, title = chosen
                if not self.confirm(T("Créer l'{0} avec : {1} ?").format(title, listing) if self.key.mode == usbkey.MODE_HXC
                                    else T("Créer {0} avec : {1} ?").format(title, listing),
                                    T("Une disquette vierge sera créée sur la clé avec ces instruments.")):
                    return False
                target, overwrite = EnsoniqDisk.blank(), False
            else:
                if slot.error:
                    self.error(T("L'emplacement {0} est illisible : {1}").format(slot.title, slot.error))
                    return False
                if self.disk_file and slot.filename.upper() == self.disk_file.upper():
                    self.statusBar().showMessage(T("Cet emplacement est la disquette déjà ouverte : utilisez « Remplacer l'emplacement "
                                                   "» pour y écrire vos modifications."), 9000)
                    return False
                filename, title = slot.filename, T("emplacement {0}").format(slot.title)
                if not self.confirm(T("Copier {0} dans l'{1} ?").format(listing, title),
                                    T("Contenu actuel : {0}\nLa clé sera modifiée immédiatement.").format(slot.describe())):
                    return False
                target, overwrite = EnsoniqDisk.load(os.path.join(self.key.folder, filename)), True
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            QtWidgets.QApplication.restoreOverrideCursor()
            copied = self.transfer(self.disk, names, target, T("l'{0}").format(title))
            if not copied:
                return False
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            self.key.write(target, filename, overwrite=overwrite)
            QtWidgets.QApplication.restoreOverrideCursor()
            self.refresh_key()
            self.statusBar().showMessage(T("{0} copié(s) dans l'{1} et vérifié(s) sur la clé.").format(', '.join(copied), title), 10000)
            return True
        except ERRORS as ex:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.error(ex)
            return False
        finally:
            while QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()

    def choose_files(self, title: str, entries: list) -> list[str]:
        """Boite de choix : quels fichiers importer."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(T("Importer"))
        lay = QtWidgets.QVBoxLayout(dialog)
        lay.addWidget(QtWidgets.QLabel(title))
        boxes = []
        for e in entries:
            box = QtWidgets.QCheckBox(T("{0}   ({1}, {2} blocs)").format(e.name.strip(), e.type_name, e.blocks))
            box.setChecked(True)
            boxes.append(box)
            lay.addWidget(box)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).setText(T("Importer"))
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).setText(T("Annuler"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        lay.addWidget(buttons)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return []
        return [e.name for e, box in zip(entries, boxes) if box.isChecked()]

    def import_from_slot(self, slot, names: list[str] | None = None) -> bool:
        """Copie des instruments d'un emplacement de la cle vers la disquette ouverte."""
        if slot.error:
            self.error(T("L'emplacement {0} est illisible : {1}").format(slot.title, slot.error))
            return False
        if self.disk_file and slot.filename.upper() == self.disk_file.upper():
            self.statusBar().showMessage(T("Cet emplacement est déjà la disquette ouverte."), 6000)
            return False
        try:
            source = EnsoniqDisk.load(os.path.join(self.key.folder, slot.filename))
            candidates = [e for e in source.entries() if e.file_type not in OS_TYPES]
            if not candidates:
                self.statusBar().showMessage(T("L'emplacement {0} ne contient aucun instrument.").format(slot.title), 6000)
                return False
            if names is None:
                names = [candidates[0].name] if len(candidates) == 1 else self.choose_files(
                    T("Fichiers de l'emplacement {0} à copier sur la disquette :").format(slot.title), candidates)
            copied = self.transfer(source, names, self.disk, T("la disquette")) if names else None
            if not copied:
                return False
            self.disk_dirty = True
            self.refresh_disk()
            self.statusBar().showMessage(T("{0} importé(s) de l'emplacement {1}.").format(', '.join(copied), slot.title), 8000)
            return True
        except ERRORS as ex:
            self.error(ex)
            return False

    def refresh_disk(self):
        entries = self.disk.entries()
        self.disk_table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            self.disk_table.setItem(row, 0, QtWidgets.QTableWidgetItem(e.name.rstrip()))
            self.disk_table.setItem(row, 1, QtWidgets.QTableWidgetItem(e.type_name))
            n = QtWidgets.QTableWidgetItem(str(e.blocks))
            n.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.disk_table.setItem(row, 2, n)
        total = self.disk.total_blocks - self.disk.first_data_block
        used = total - self.disk.free_blocks
        self.disk_bar.setRange(0, total)
        self.disk_bar.setValue(used)
        self.disk_bar.setFormat(T("{0} blocs utilisés sur {1} — {2} libres ({3} Ko)").format(used, total, self.disk.free_blocks, self.disk.free_blocks // 2))
        self.disk_title.setText(self.disk_name + (T(" — modifiée") if self.disk_dirty else ""))
        self.refresh_estimate()
        self._update_buttons()

    def can_discard_disk(self) -> bool:
        return (not self.disk_dirty) or self.confirm(
            T("La disquette en cours a été modifiée et n'est pas encore écrite."), T("Abandonner ces modifications ?"))

    def set_disk(self, disk: EnsoniqDisk, name: str):
        self.disk, self.disk_name, self.disk_dirty = disk, name, False
        self.disk_file = None
        self.editing_name = self.editing_base = None      # l'editeur garde ses sons, comme un nouvel instrument
        self.refresh_disk()

    def new_blank_disk(self):
        if self.can_discard_disk():
            self.set_disk(EnsoniqDisk.blank(), T("Nouvelle disquette vierge"))

    def new_system_disk(self):
        if not self.can_discard_disk():
            return
        source = None
        if self.key is not None:
            try:
                for slot in self.key.slots():
                    if slot.summary and slot.summary.has_os:
                        source = os.path.join(self.key.folder, slot.filename)
                        break
            except usbkey.UsbKeyError:
                pass
        if source is None:
            source, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, T("Choisir une disquette contenant l'OS"), self.last_dir("img_dir"),
                T("Images de disquette (*.hfe *.img)"))
            if not source:
                return
        try:
            disk = system_disk_from(EnsoniqDisk.load(source))
            self.set_disk(disk, T("Nouvelle disquette avec OS (copié de {0})").format(os.path.basename(source)))
            self.statusBar().showMessage(T("L'OS a été copié ; cette disquette pourra démarrer l'EPS."), 8000)
        except ERRORS as ex:
            self.error(ex)

    def open_disk(self):
        if not self.can_discard_disk():
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, T("Ouvrir une image de disquette"), self.last_dir("img_dir"),
                                                        T("Images de disquette (*.hfe *.img)"))
        if path:
            self.load_disk_file(path)

    def load_disk_file(self, path: str):
        try:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            disk = EnsoniqDisk.load(path)
            self.keep_dir("img_dir", path)
            self.set_disk(disk, os.path.basename(path))
        except ERRORS as ex:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.error(ex)
        finally:
            while QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()

    def save_disk_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, T("Enregistrer l'image"), os.path.join(self.last_dir("img_dir"), "disquette.hfe"),
            T("Image HFE pour Gotek (*.hfe);;Image brute (*.img)"))
        if not path:
            return
        try:
            self.disk.save(path)
            self.keep_dir("img_dir", path)
            self.disk_name, self.disk_dirty = os.path.basename(path), False
            self.refresh_disk()
        except ERRORS as ex:
            self.error(ex)

    def delete_file(self):
        entry = self.selected_entry()
        if entry is None:
            return
        detail = T("Sans l'OS, cette disquette ne pourra plus démarrer l'EPS.") if entry.file_type in OS_TYPES else ""
        if self.confirm(T("Supprimer « {0} » de la disquette ?").format(entry.name.rstrip()), detail):
            try:
                self.disk.delete(entry.name)
                if entry.name == self.editing_name:
                    self.editing_name = self.editing_base = None
                self.disk_dirty = True
                self.refresh_disk()
            except ERRORS as ex:
                self.error(ex)

    def export_wav(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, T("Dossier pour les fichiers WAV"), self.last_dir("wav_dir"))
        if not folder:
            return
        count, problems = 0, []
        for e in self.disk.entries():
            if e.file_type != TYPE_EPS_INSTRUMENT:
                continue
            try:
                inst = ins.parse_instrument(self.disk.read_file(e))
                for li, layer in enumerate(inst.layers, 1):
                    for wi, ws in enumerate(layer.wavesamples, 1):
                        name = f"{e.name.strip()}_L{li}_{wi:02d}_{project.midi_to_note(ws.root_key)}.wav"
                        name = re.sub(r'[\\/:*?"<>| ]', "_", name)
                        audio.write_wav(os.path.join(folder, name), ws.samples, ws.rate)
                        count += 1
            except ERRORS as ex:
                problems.append(f"{e.name.strip()} : {ex}")
        self.statusBar().showMessage(T("{0} fichier(s) WAV exporté(s) dans {1}").format(count, folder), 8000)
        if problems:
            self.error("\n".join(problems))

    # ------------------------------------------------------------------ cle USB
    def refresh_drives(self):
        current = self.key.folder if self.key else self.settings.value("key_folder", "")
        self.drive_box.clear()
        for root, label in usbkey.list_removable_drives():
            self.drive_box.addItem(label, root)
        if current and self.drive_box.findData(current) < 0 and os.path.isdir(current):
            self.drive_box.addItem(current, current)
        if self.drive_box.count() == 0:
            self.drive_box.addItem(T("Aucune clé détectée"), "")
        index = self.drive_box.findData(current) if current else -1
        if index < 0:
            # Par defaut : la premiere cle qui ressemble a une cle de Gotek.
            for i in range(self.drive_box.count()):
                if usbkey.detect_mode(self.drive_box.itemData(i) or "?"):
                    index = i
                    break
        self.drive_box.setCurrentIndex(max(index, 0))
        self.set_key_folder(self.drive_box.currentData() or "")

    def _drive_chosen(self, _index: int):
        self.set_key_folder(self.drive_box.currentData() or "")

    def _mode_chosen(self, _index: int):
        if self.key:
            self.key.mode = self.mode_box.currentData()
            self.settings.setValue("key_mode", self.key.mode)
            self.refresh_key()

    def browse_key(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, T("Dossier ou clé USB du Gotek"),
                                                            self.settings.value("key_folder", ""))
        if folder:
            folder = os.path.normpath(folder)
            if self.drive_box.findData(folder) < 0:
                self.drive_box.addItem(folder, folder)
            self.drive_box.setCurrentIndex(self.drive_box.findData(folder))
            self.set_key_folder(folder)

    def set_key_folder(self, folder: str):
        if not folder or not os.path.isdir(folder):
            self.key = None
            self.key_table.setRowCount(0)
            self._update_buttons()
            return
        mode = usbkey.detect_mode(folder) or self.settings.value("key_mode", usbkey.MODE_HXC)
        self.mode_box.setCurrentIndex(max(0, self.mode_box.findData(mode)))
        self.key = usbkey.UsbKey(folder, mode)
        self.settings.setValue("key_folder", folder)
        self.refresh_key()

    def refresh_key(self):
        self._slots = []
        if self.key is None:
            self.key_table.setRowCount(0)
            self._update_buttons()
            return
        try:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            self._slots = self.key.slots()
        except usbkey.UsbKeyError as ex:
            self.statusBar().showMessage(str(ex), 8000)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        self.key_table.setRowCount(len(self._slots))
        bold = self.font()
        bold.setBold(True)
        for row, slot in enumerate(self._slots):
            title = QtWidgets.QTableWidgetItem(slot.title + ("  OS" if slot.summary and slot.summary.has_os else ""))
            title.setFont(bold)
            self.key_table.setItem(row, 0, title)
            content = QtWidgets.QTableWidgetItem(slot.describe())
            content.setToolTip(slot.describe().replace(", ", "\n"))
            if slot.error or not (slot.summary and slot.summary.entries):
                content.setForeground(QtGui.QColor("#8A8F98"))
            self.key_table.setItem(row, 1, content)
            free = QtWidgets.QTableWidgetItem("" if slot.error else T("{0} Ko").format(slot.summary.free_blocks // 2))
            free.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.key_table.setItem(row, 2, free)
        self._update_buttons()

    def selected_slot(self):
        row = self.key_table.currentRow()
        return self._slots[row] if 0 <= row < len(self._slots) else None

    def open_slot(self):
        slot = self.selected_slot()
        if slot is None or slot.error or not self.can_discard_disk():
            return
        self.load_disk_file(os.path.join(self.key.folder, slot.filename))
        self.disk_name = T("Emplacement {0}").format(slot.title) if slot.number is not None else slot.filename
        self.disk_file = slot.filename
        self.refresh_disk()

    def write_to_key(self, new: bool):
        if self.key is None:
            return
        try:
            if new:
                chosen = self.new_slot_name()
                if chosen is None:
                    return
                filename, title = chosen
                overwrite = False
            else:
                slot = self.selected_slot()
                if slot is None:
                    return
                filename, title = slot.filename, T("emplacement {0}").format(slot.title)
                detail = T("Contenu actuel : {0}\nIl sera définitivement remplacé.").format(slot.describe())
                if slot.summary and slot.summary.has_os and not any(e.file_type in OS_TYPES for e in self.disk.entries()):
                    detail += (T("\n\nATTENTION : cet emplacement contient l'OS et la nouvelle disquette ne le contient "
                                 "pas. Si c'est votre disquette de démarrage, l'EPS ne démarrera plus dessus."))
                if not self.confirm(T("Remplacer l'{0} ?").format(title), detail):
                    return
                overwrite = True
            if not self.disk.entries():
                if not self.confirm(T("La disquette est vide."), T("L'écrire quand même sur la clé ?")):
                    return
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            self.key.write(self.disk, filename, overwrite=overwrite)
            QtWidgets.QApplication.restoreOverrideCursor()
            self.disk_dirty = False
            self.disk_name = title[0].upper() + title[1:]
            self.disk_file = self.key.existing_name(filename if filename.upper().endswith(".HFE") else filename + ".hfe")
            self.refresh_disk()
            self.refresh_key()
            for row, slot in enumerate(self._slots):
                if slot.filename.upper() == (filename if filename.upper().endswith(".HFE") else filename + ".hfe").upper():
                    self.key_table.selectRow(row)
            self.statusBar().showMessage(
                T("Disquette écrite et vérifiée : {0}. Éjectez la clé avant de la retirer.").format(title), 12000)
        except ERRORS as ex:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.error(ex)
        finally:
            while QtWidgets.QApplication.overrideCursor():
                QtWidgets.QApplication.restoreOverrideCursor()

    def save_catalog(self):
        if self.key is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, T("Enregistrer le catalogue"), os.path.join(self.last_dir("img_dir"), "catalogue_cle_EPS.txt"),
            T("Texte (*.txt)"))
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.key.catalog())
                self.statusBar().showMessage(T("Catalogue enregistré : {0}").format(path), 8000)
            except ERRORS as ex:
                self.error(ex)

    # ------------------------------------------------------------------ divers
    def show_document(self, filename: str, title: str, markdown: bool):
        """Affiche un document fourni avec l'application (manuel, licence)."""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as ex:
            self.error(T("Document introuvable : {0}\n{1}").format(path, ex))
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(820, 720)
        lay = QtWidgets.QVBoxLayout(dialog)
        view = QtWidgets.QTextBrowser()
        view.setOpenExternalLinks(True)
        if markdown:
            view.setMarkdown(text)
        else:
            view.setPlainText(text)
        lay.addWidget(view)
        close = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        close.button(QtWidgets.QDialogButtonBox.Close).setText(T("Fermer"))
        close.rejected.connect(dialog.reject)
        lay.addWidget(close)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.show()                                     # non bloquant : le manuel reste ouvert a cote
        self._documents = getattr(self, "_documents", []) + [dialog]

    def show_manual(self):
        self.show_document("MANUEL.md" if i18n.LANG == "fr" else "MANUAL.md", T("Manuel d'EPS Builder"), markdown=True)

    def show_licence(self):
        self.show_document("LICENCE.txt", T("Licence"), markdown=False)

    def about(self):
        QtWidgets.QMessageBox.about(
            self, T("À propos"),
            f"<b>EPS Builder {__version__}</b><br>Création d'instruments et de disquettes pour Ensoniq EPS, "
            "lisibles aussi par l'EPS-16+ et l'ASR-10.<br><br>Les instruments sont écrits au format "
            "EPS classique (13 bits), sur des disquettes de 800 Ko.<br><br>"
            "Logiciel libre sous licence MIT — © 2026 Christophe CRUZ.")

    def closeEvent(self, event):
        if self.can_discard_disk():
            self.player.stop()
            event.accept()
        else:
            event.ignore()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
