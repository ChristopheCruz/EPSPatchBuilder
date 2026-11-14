"""Gestion de la cle USB du Gotek : emplacements, ecriture sure, catalogue.

Deux modes :
  - HxC « indexe » : les images s'appellent DSKA0000.HFE, DSKA0001.HFE... et se choisissent
    par leur numero sur le Gotek ;
  - FlashFloppy : les noms de fichiers sont libres.
"""
from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field

from .i18n import T
from .disk import DiskError, DiskSummary, EnsoniqDisk, quick_summary

MODE_HXC, MODE_FLASHFLOPPY = "hxc", "flashfloppy"
_SLOT_RE = re.compile(r"^DSKA(\d{4})\.HFE$", re.IGNORECASE)
MAX_SLOT = 9999
TRASH_DIR = "CORBEILLE_EPS"          # emplacements supprimes : deplaces ici, jamais effaces
_TEMP_PREFIX = "~EPSB"               # noms provisoires pendant un echange d'emplacements


class UsbKeyError(Exception):
    pass


@dataclass
class Slot:
    filename: str
    number: int | None = None            # numero d'emplacement (mode HxC)
    summary: DiskSummary | None = None
    error: str = ""

    @property
    def title(self) -> str:
        return f"{self.number:03d}" if self.number is not None else self.filename

    def describe(self) -> str:
        if self.error:
            return f"({self.error})"
        names = [e.name.strip() for e in self.summary.entries]
        return ", ".join(names) if names else T("(vide)")


def list_removable_drives() -> list[tuple[str, str]]:
    """Lecteurs amovibles (Windows) : liste de (chemin, libelle)."""
    drives = []
    if sys.platform != "win32":
        return drives
    import ctypes
    import string
    kernel32 = ctypes.windll.kernel32
    mask = kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if not mask & (1 << i):
            continue
        root = f"{letter}:\\"
        if kernel32.GetDriveTypeW(root) != 2:          # DRIVE_REMOVABLE
            continue
        name = ctypes.create_unicode_buffer(261)
        fs = ctypes.create_unicode_buffer(261)
        ok = kernel32.GetVolumeInformationW(root, name, 261, None, None, None, fs, 261)
        label = f"{letter}: {name.value or T('Cle USB')}" + (f" ({fs.value})" if ok and fs.value else "")
        drives.append((root, label))
    return drives


def detect_mode(folder: str) -> str | None:
    try:
        names = {n.upper() for n in os.listdir(folder)}
    except OSError:
        return None
    if "HXCSDFE.CFG" in names:
        return MODE_HXC
    if "FF.CFG" in names or "FF" in names:
        return MODE_FLASHFLOPPY
    return None


@dataclass
class UsbKey:
    folder: str
    mode: str = MODE_HXC
    _cache: dict = field(default_factory=dict, repr=False)

    def _summary(self, path: str) -> tuple[DiskSummary | None, str]:
        try:
            st = os.stat(path)
            key = (path, st.st_mtime_ns, st.st_size)
            if key not in self._cache:
                self._cache[key] = quick_summary(path)
            return self._cache[key], ""
        except (DiskError, ValueError) as ex:
            return None, str(ex)
        except OSError as ex:
            return None, T("lecture impossible : {0}").format(ex.strerror or ex)

    def slots(self) -> list[Slot]:
        try:
            names = sorted(os.listdir(self.folder), key=str.upper)
        except OSError as ex:
            raise UsbKeyError(T("Cle inaccessible : {0}").format(ex.strerror or ex)) from ex
        out = []
        for name in names:
            if name.startswith((".", _TEMP_PREFIX)) or not name.upper().endswith(".HFE"):
                continue
            if not os.path.isfile(os.path.join(self.folder, name)):
                continue
            m = _SLOT_RE.match(name)
            if self.mode == MODE_HXC and not m:
                continue
            summary, error = self._summary(os.path.join(self.folder, name))
            out.append(Slot(name, int(m.group(1)) if (m and self.mode == MODE_HXC) else None, summary, error))
        if self.mode == MODE_HXC:
            out.sort(key=lambda s: s.number)
        return out

    def next_free_number(self) -> int:
        used = {s.number for s in self.slots()}
        for n in range(MAX_SLOT + 1):
            if n not in used:
                return n
        raise UsbKeyError(T("Plus aucun emplacement libre"))

    def filename_for(self, number: int) -> str:
        return f"DSKA{number:04d}.hfe"

    def existing_name(self, filename: str) -> str | None:
        """Nom reel d'un fichier de la cle, sans tenir compte de la casse."""
        try:
            for name in os.listdir(self.folder):
                if name.upper() == filename.upper():
                    return name
        except OSError:
            pass
        return None

    def write(self, disk: EnsoniqDisk, filename: str, overwrite: bool = False) -> str:
        """Ecrit l'image sur la cle (fichier temporaire, puis remplacement), et la relit pour controle."""
        if not filename.upper().endswith(".HFE"):
            filename += ".hfe"
        if any(c in filename for c in '\\/:*?"<>|'):
            raise UsbKeyError(T("Nom de fichier invalide"))
        existing = self.existing_name(filename)
        if existing and not overwrite:
            raise UsbKeyError(T("{0} existe deja sur la cle").format(existing))
        path = os.path.join(self.folder, existing or filename)
        problems = disk.check()
        if problems:
            raise UsbKeyError(T("Disquette incoherente, ecriture annulee : ") + " ; ".join(problems))
        try:
            disk.save(path)
            check = EnsoniqDisk.load(path)
        except OSError as ex:
            raise UsbKeyError(T("Ecriture impossible : {0}").format(ex.strerror or ex)) from ex
        if bytes(check.img) != bytes(disk.img):
            raise UsbKeyError(T("Le fichier relu sur la cle differe de l'original : cle defectueuse ?"))
        return path

    # ------------------------------------------------------------------ gestion des emplacements
    def _path(self, filename: str) -> str:
        return os.path.join(self.folder, filename)

    def _rename(self, old: str, new: str) -> None:
        try:
            os.rename(self._path(old), self._path(new))
        except OSError as ex:
            raise UsbKeyError(T("Renommage impossible : {0}").format(ex.strerror or ex)) from ex

    def _temp_name(self) -> str:
        n = 0
        while self.existing_name(f"{_TEMP_PREFIX}{n}.hfe"):
            n += 1
        return f"{_TEMP_PREFIX}{n}.hfe"

    def _check_name(self, filename: str) -> str:
        filename = filename.strip()
        if not filename.upper().endswith(".HFE"):
            filename += ".hfe"
        if filename.upper() == ".HFE" or any(c in filename for c in '\\/:*?"<>|') or filename.startswith((".", _TEMP_PREFIX)):
            raise UsbKeyError(T("Nom de fichier invalide"))
        if self.mode == MODE_HXC and not _SLOT_RE.match(filename):
            raise UsbKeyError(T("En mode HxC, les images s'appellent DSKA0000.HFE, DSKA0001.HFE…"))
        return filename

    def move(self, slot: Slot, number: int) -> int | None:
        """Mode HxC : donne le numero demande a l'emplacement. Si ce numero est deja pris, les deux
        emplacements echangent leurs numeros. Retourne le numero libere (None si aucun)."""
        if self.mode != MODE_HXC or slot.number is None:
            raise UsbKeyError(T("Seuls les emplacements numérotés (mode HxC) peuvent changer de numéro"))
        if not 0 <= number <= MAX_SLOT:
            raise UsbKeyError(T("Numéro d'emplacement hors limites (0 à {0})").format(MAX_SLOT))
        if number == slot.number:
            return None
        if self.existing_name(slot.filename) is None:
            raise UsbKeyError(T("{0} n'existe plus sur la clé").format(slot.filename))
        target = self.existing_name(self.filename_for(number))
        if target is None:
            self._rename(slot.filename, self.filename_for(number))
            return slot.number
        temp = self._temp_name()                       # echange en trois renommages, sans rien ecraser
        self._rename(target, temp)
        try:
            self._rename(slot.filename, self.filename_for(number))
        except UsbKeyError:
            self._rename(temp, target)
            raise
        self._rename(temp, self.filename_for(slot.number))
        return None

    def rename(self, slot: Slot, filename: str) -> str:
        """Mode FlashFloppy : change le nom du fichier image. Retourne le nouveau nom."""
        filename = self._check_name(filename)
        existing = self.existing_name(filename)
        if existing and existing.upper() != slot.filename.upper():
            raise UsbKeyError(T("{0} existe deja sur la cle").format(existing))
        if existing == filename:
            return filename
        if existing:                                   # seule la casse change (FAT ne distingue pas)
            temp = self._temp_name()
            self._rename(slot.filename, temp)
            self._rename(temp, filename)
        else:
            self._rename(slot.filename, filename)
        return filename

    def trash_folder(self) -> str:
        return self._path(TRASH_DIR)

    def delete(self, slot: Slot) -> str:
        """Deplace l'image dans la corbeille de la cle (rien n'est efface). Retourne son chemin."""
        if self.existing_name(slot.filename) is None:
            raise UsbKeyError(T("{0} n'existe plus sur la clé").format(slot.filename))
        trash = self.trash_folder()
        stem, ext = os.path.splitext(slot.filename)
        dest = os.path.join(trash, f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}{ext}")
        k = 1
        while os.path.exists(dest):
            dest = os.path.join(trash, f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}_{k}{ext}")
            k += 1
        try:
            os.makedirs(trash, exist_ok=True)
            os.replace(self._path(slot.filename), dest)
        except OSError as ex:
            raise UsbKeyError(T("Suppression impossible : {0}").format(ex.strerror or ex)) from ex
        return dest

    def add_blank(self, filename: str, hd: bool = False, label: str = "") -> str:
        """Nouvel emplacement contenant une disquette vierge."""
        return self.write(EnsoniqDisk.blank(hd=hd, label=label), self._check_name(filename))

    def add_from_file(self, path: str, filename: str) -> str:
        """Nouvel emplacement a partir d'une image (.hfe ou .img) de l'ordinateur."""
        try:
            disk = EnsoniqDisk.load(path)
        except (DiskError, ValueError) as ex:
            raise UsbKeyError(T("{0} : image illisible ({1})").format(os.path.basename(path), ex)) from ex
        except OSError as ex:
            raise UsbKeyError(T("lecture impossible : {0}").format(ex.strerror or ex)) from ex
        return self.write(disk, self._check_name(filename))

    def compact(self) -> list[tuple[str, str]]:
        """Mode HxC : renumerote les emplacements 000, 001, 002… dans leur ordre actuel, sans trou.
        Retourne la liste des renommages (ancien nom, nouveau nom)."""
        if self.mode != MODE_HXC:
            raise UsbKeyError(T("Seuls les emplacements numérotés (mode HxC) peuvent changer de numéro"))
        slots = self.slots()
        moves = [(s.filename, self.filename_for(i)) for i, s in enumerate(slots) if s.number != i]
        # Deux temps : d'abord des noms provisoires, puis les noms definitifs (aucun ecrasement possible).
        temps = []
        for old, _new in moves:
            temp = self._temp_name()
            self._rename(old, temp)
            temps.append(temp)
        for temp, (_old, new) in zip(temps, moves):
            self._rename(temp, new)
        return moves

    def catalog(self) -> str:
        lines = [T("Catalogue de la cle {0}").format(self.folder), ""]
        for slot in self.slots():
            if slot.error:
                lines.append(f"{slot.title}  {slot.describe()}")
                continue
            s = slot.summary
            extra = " [OS]" if s.has_os else ""
            lines.append(T("{0}{1}  ({2} blocs libres)").format(slot.title, extra, s.free_blocks))
            for e in s.entries:
                lines.append(T("      {0}  {1}, {2} blocs").format(e.name, e.type_name, e.blocks))
        return "\n".join(lines) + "\n"
