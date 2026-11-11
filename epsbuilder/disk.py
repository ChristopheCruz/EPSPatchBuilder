"""Systeme de fichiers des disquettes Ensoniq (EPS, EPS-16+, ASR-10).

Blocs de 512 octets :
  0        inutilise (motif 6D B6)
  1        identification du support ("ID")
  2        bloc systeme : nombre de blocs libres ("OS")
  3-4      repertoire principal, 39 entrees de 26 octets ("DR")
  5...     table d'allocation, 170 entrees de 3 octets par bloc ("FB")
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .i18n import T
from . import hfe

BLOCK = 512
DIR_BLOCK = 3
DIR_ENTRIES = 39
ENTRY_SIZE = 26
FAT_BLOCK = 5
FAT_PER_BLOCK = 170
FAT_FREE, FAT_END, FAT_BAD = 0, 1, 2

TYPE_OS = 1
OS_TYPES = (1, 28, 34)
TYPE_EPS_INSTRUMENT = 3
FILE_TYPES = {
    1: T("Systeme (OS)"), 2: T("Sous-repertoire"), 3: T("Instrument EPS"), 4: T("Banque EPS"),
    5: T("Sequence EPS"), 6: T("Morceau EPS"), 7: T("SysEx"), 8: T("Repertoire parent"), 9: T("Macro"),
    23: T("Banque EPS-16+"), 24: T("Instrument EPS-16+"), 25: T("Effet EPS-16+"),
    26: T("Sequence EPS-16+"), 27: T("Morceau EPS-16+"), 28: T("OS EPS-16+"),
    30: T("Banque ASR"), 31: T("Effet ASR"), 32: T("Sequence ASR"), 33: T("Morceau ASR"),
    34: T("OS ASR"), 35: T("Piste audio ASR"),
}


class DiskError(Exception):
    pass


@dataclass
class DirEntry:
    index: int
    type_info: int
    file_type: int
    name: str
    blocks: int
    contiguous: int
    first_block: int

    @property
    def type_name(self) -> str:
        return FILE_TYPES.get(self.file_type, f"Type {self.file_type}")


def clean_name(name: str) -> str:
    """Nom Ensoniq : 12 caracteres ASCII majuscules, complete par des espaces."""
    out = "".join(c if 32 <= ord(c) < 127 else " " for c in name.upper())
    return out[:12].ljust(12)


class EnsoniqDisk:
    def __init__(self, image: bytes):
        self.geom = hfe.geometry_for_image_size(len(image))
        self.img = bytearray(image)
        self.total_blocks = len(image) // BLOCK
        self.fat_blocks = -(-self.total_blocks // FAT_PER_BLOCK)
        self.first_data_block = FAT_BLOCK + self.fat_blocks
        if self.img[BLOCK + 38: BLOCK + 40] != b"ID" or self.img[2 * BLOCK + 28: 2 * BLOCK + 30] != b"OS":
            raise DiskError(T("Cette image n'est pas une disquette Ensoniq formatee"))

    # ------------------------------------------------------------------ creation / fichiers
    @classmethod
    def blank(cls, hd: bool = False, label: str = "") -> "EnsoniqDisk":
        geom = hfe.GEOM_HD if hd else hfe.GEOM_DD
        total = geom.blocks
        img = bytearray(b"\x6d\xb6" * (geom.image_size // 2))
        fat_blocks = -(-total // FAT_PER_BLOCK)
        first_data = FAT_BLOCK + fat_blocks
        # Bloc 1 : identification
        b1 = bytearray(BLOCK)
        b1[0:4] = bytes([0x00, 0x80, 0x01, 0x00])
        b1[4:6] = geom.sectors.to_bytes(2, "big")
        b1[6:8] = geom.sides.to_bytes(2, "big")
        b1[8:10] = geom.tracks.to_bytes(2, "big")
        b1[10:14] = BLOCK.to_bytes(4, "big")
        b1[14:18] = total.to_bytes(4, "big")
        b1[18:20] = bytes([0x1E, 0x02])
        if label:
            b1[30] = 0xFF
            b1[31:38] = clean_name(label)[:7].encode("ascii")
        b1[38:40] = b"ID"
        if not label:
            # Comme le formatage de l'EPS : l'enregistrement de 40 octets est repete dans tout le bloc.
            b1 = bytearray((bytes(b1[:40]) * 13)[:500] + bytes(12))
        img[BLOCK:2 * BLOCK] = b1
        # Bloc 2 : systeme
        b2 = bytearray(BLOCK)
        b2[0:4] = (total - first_data).to_bytes(4, "big")
        b2[28:30] = b"OS"
        img[2 * BLOCK:3 * BLOCK] = b2
        # Blocs 3-4 : repertoire
        d = bytearray(2 * BLOCK)
        d[-2:] = b"DR"
        img[3 * BLOCK:5 * BLOCK] = d
        # Table d'allocation
        for i in range(fat_blocks):
            fb = bytearray(BLOCK)
            fb[-2:] = b"FB"
            img[(FAT_BLOCK + i) * BLOCK:(FAT_BLOCK + i + 1) * BLOCK] = fb
        disk = cls(bytes(img))
        for n in range(first_data):
            disk._fat_set(n, FAT_END)
        return disk

    @classmethod
    def load(cls, path: str) -> "EnsoniqDisk":
        with open(path, "rb") as f:
            data = f.read()
        if data[:8] == b"HXCPICFE":
            data = hfe.hfe_to_image(data)
        return cls(data)

    def save(self, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()
        data = hfe.image_to_hfe(bytes(self.img), self.geom) if ext == ".hfe" else bytes(self.img)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)

    # ------------------------------------------------------------------ FAT
    def _fat_pos(self, n: int) -> int:
        return (FAT_BLOCK + n // FAT_PER_BLOCK) * BLOCK + (n % FAT_PER_BLOCK) * 3

    def _fat_get(self, n: int) -> int:
        p = self._fat_pos(n)
        return int.from_bytes(self.img[p:p + 3], "big")

    def _fat_set(self, n: int, v: int) -> None:
        p = self._fat_pos(n)
        self.img[p:p + 3] = v.to_bytes(3, "big")

    def _count_free(self) -> int:
        return sum(1 for n in range(self.first_data_block, self.total_blocks) if self._fat_get(n) == FAT_FREE)

    @property
    def free_blocks(self) -> int:
        return int.from_bytes(self.img[2 * BLOCK:2 * BLOCK + 4], "big")

    def _set_free(self, n: int) -> None:
        self.img[2 * BLOCK:2 * BLOCK + 4] = n.to_bytes(4, "big")

    @property
    def label(self) -> str:
        if self.img[BLOCK + 30] != 0xFF:
            return ""
        return self.img[BLOCK + 31:BLOCK + 38].decode("latin1").rstrip()

    # ------------------------------------------------------------------ repertoire
    def _entry_pos(self, i: int) -> int:
        return DIR_BLOCK * BLOCK + i * ENTRY_SIZE

    def entries(self) -> list[DirEntry]:
        out = []
        for i in range(DIR_ENTRIES):
            e = self.img[self._entry_pos(i):self._entry_pos(i) + ENTRY_SIZE]
            if e[1] == 0:
                continue
            out.append(DirEntry(i, e[0], e[1], e[2:14].decode("latin1"),
                                int.from_bytes(e[14:16], "big"), int.from_bytes(e[16:18], "big"),
                                int.from_bytes(e[18:22], "big")))
        return out

    def find(self, name: str) -> DirEntry | None:
        key = clean_name(name)
        for e in self.entries():
            if e.name == key:
                return e
        return None

    def _chain(self, entry: DirEntry) -> list[int]:
        chain, n = [], entry.first_block
        while len(chain) < entry.blocks:
            if not (self.first_data_block <= n < self.total_blocks):
                raise DiskError(T("Chaine de blocs corrompue pour {0!r}").format(entry.name))
            chain.append(n)
            nxt = self._fat_get(n)
            if nxt == FAT_END:
                break
            n = nxt
        if len(chain) != entry.blocks:
            raise DiskError(T("Chaine de blocs incomplete pour {0!r}").format(entry.name))
        return chain

    def read_file(self, entry: DirEntry) -> bytes:
        return b"".join(bytes(self.img[n * BLOCK:(n + 1) * BLOCK]) for n in self._chain(entry))

    def _allocate(self, count: int) -> list[int]:
        free = [n for n in range(self.first_data_block, self.total_blocks) if self._fat_get(n) == FAT_FREE]
        if len(free) < count:
            raise DiskError(T("Disquette pleine : {0} blocs demandes, {1} libres").format(count, len(free)))
        # On cherche d'abord une plage contigue (premier emplacement qui convient).
        run_start, run_len = None, 0
        prev = None
        for n in free:
            if prev is not None and n == prev + 1:
                run_len += 1
            else:
                run_start, run_len = n, 1
            if run_len == count:
                return list(range(run_start, run_start + count))
            prev = n
        return free[:count]

    def add_file(self, name: str, file_type: int, data: bytes, type_info: int = 0,
                 slot: int | None = None) -> DirEntry:
        name = clean_name(name)
        if self.find(name):
            raise DiskError(T("Un fichier nomme {0!r} existe deja sur la disquette").format(name.strip()))
        if slot is not None and self.img[self._entry_pos(slot) + 1] != 0:
            slot = None
        if slot is None:
            slot = next((i for i in range(DIR_ENTRIES) if self.img[self._entry_pos(i) + 1] == 0), None)
        if slot is None:
            raise DiskError(T("Repertoire plein (39 fichiers maximum)"))
        if len(data) % BLOCK:
            data = data + bytes(BLOCK - len(data) % BLOCK)
        count = len(data) // BLOCK
        if count == 0 or count > 0xFFFF:
            raise DiskError(T("Taille de fichier invalide"))
        blocks = self._allocate(count)
        for k, n in enumerate(blocks):
            self.img[n * BLOCK:(n + 1) * BLOCK] = data[k * BLOCK:(k + 1) * BLOCK]
            self._fat_set(n, blocks[k + 1] if k + 1 < count else FAT_END)
        contiguous = 1
        while contiguous < count and blocks[contiguous] == blocks[contiguous - 1] + 1:
            contiguous += 1
        e = bytearray(ENTRY_SIZE)
        e[0] = type_info
        e[1] = file_type
        e[2:14] = name.encode("ascii")
        e[14:16] = count.to_bytes(2, "big")
        e[16:18] = contiguous.to_bytes(2, "big")
        e[18:22] = blocks[0].to_bytes(4, "big")
        p = self._entry_pos(slot)
        self.img[p:p + ENTRY_SIZE] = e
        self._set_free(self.free_blocks - count)
        return DirEntry(slot, type_info, file_type, name, count, contiguous, blocks[0])

    def delete(self, name: str) -> None:
        entry = self.find(name)
        if entry is None:
            raise DiskError(T("Fichier introuvable : {0!r}").format(name))
        chain = self._chain(entry)
        for n in chain:
            self._fat_set(n, FAT_FREE)
        p = self._entry_pos(entry.index)
        self.img[p:p + ENTRY_SIZE] = bytes(ENTRY_SIZE)
        self._set_free(self.free_blocks + len(chain))

    def replace_file(self, old_name: str, new_name: str, file_type: int, data: bytes) -> DirEntry:
        """Remplace un fichier en gardant sa place dans le repertoire. En cas d'echec, la disquette
        est laissee telle qu'elle etait."""
        old = self.find(old_name)
        if old is None:
            raise DiskError(T("Fichier introuvable : {0!r}").format(old_name))
        other = self.find(new_name)
        if other is not None and other.index != old.index:
            raise DiskError(T("Un autre fichier s'appelle deja {0!r}").format(clean_name(new_name).strip()))
        backup = bytes(self.img)
        try:
            self.delete(old_name)
            return self.add_file(new_name, file_type, data, old.type_info, slot=old.index)
        except DiskError:
            self.img[:] = backup
            raise

    def reorder(self, names: list[str]) -> None:
        """Reecrit le repertoire dans l'ordre donne (tous les fichiers doivent etre cites une fois)."""
        current = {e.name: e for e in self.entries()}
        wanted = [clean_name(n) for n in names]
        if sorted(wanted) != sorted(current):
            raise DiskError(T("La liste ne correspond pas au contenu de la disquette"))
        records = [bytes(self.img[self._entry_pos(current[n].index):self._entry_pos(current[n].index) + ENTRY_SIZE])
                   for n in wanted]
        for i in range(DIR_ENTRIES):
            p = self._entry_pos(i)
            self.img[p:p + ENTRY_SIZE] = records[i] if i < len(records) else bytes(ENTRY_SIZE)

    def check(self) -> list[str]:
        """Controle de coherence ; retourne la liste des anomalies (vide si tout va bien)."""
        problems = []
        if self.img[5 * BLOCK - 2:5 * BLOCK] != b"DR":
            problems.append(T("signature DR absente"))
        for i in range(self.fat_blocks):
            if self.img[(FAT_BLOCK + i + 1) * BLOCK - 2:(FAT_BLOCK + i + 1) * BLOCK] != b"FB":
                problems.append(T("signature FB absente (bloc {0})").format(FAT_BLOCK + i))
        used = {}
        for e in self.entries():
            try:
                for n in self._chain(e):
                    if n in used:
                        problems.append(T("bloc {0} partage entre {1!r} et {2!r}").format(n, used[n], e.name))
                    used[n] = e.name
            except DiskError as ex:
                problems.append(str(ex))
        marked = {n for n in range(self.first_data_block, self.total_blocks) if self._fat_get(n) != FAT_FREE}
        if marked != set(used):
            problems.append(T("{0} blocs alloues sans fichier (ou l'inverse)").format(len(marked ^ set(used))))
        if self._count_free() != self.free_blocks:
            problems.append(T("compteur de blocs libres faux ({0} annonces, {1} reels)").format(self.free_blocks, self._count_free()))
        return problems


@dataclass
class DiskSummary:
    label: str
    free_blocks: int
    total_blocks: int
    entries: list[DirEntry]

    @property
    def has_os(self) -> bool:
        return any(e.file_type in OS_TYPES for e in self.entries)


def quick_summary(path: str) -> DiskSummary:
    """Lit seulement le debut d'une image (repertoire) : rapide, pour lister une cle USB."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] == b"HXCPICFE":
        head = hfe.hfe_to_image(data, max_tracks=1)
        total = (len(head) // BLOCK) * data[9]           # blocs par piste x nombre de pistes
    else:
        head, total = data[:20 * BLOCK], len(data) // BLOCK
    if len(head) < 5 * BLOCK or head[BLOCK + 38:BLOCK + 40] != b"ID" or head[2 * BLOCK + 28:2 * BLOCK + 30] != b"OS":
        raise DiskError(T("Image non formatee Ensoniq"))
    entries = []
    for i in range(DIR_ENTRIES):
        e = head[DIR_BLOCK * BLOCK + i * ENTRY_SIZE:DIR_BLOCK * BLOCK + (i + 1) * ENTRY_SIZE]
        if e[1]:
            entries.append(DirEntry(i, e[0], e[1], e[2:14].decode("latin1"), int.from_bytes(e[14:16], "big"),
                                    int.from_bytes(e[16:18], "big"), int.from_bytes(e[18:22], "big")))
    label = head[BLOCK + 31:BLOCK + 38].decode("latin1").rstrip() if head[BLOCK + 30] == 0xFF else ""
    return DiskSummary(label, int.from_bytes(head[2 * BLOCK:2 * BLOCK + 4], "big"), total, entries)


def system_disk_from(source: EnsoniqDisk) -> EnsoniqDisk:
    """Copie d'une disquette systeme dont on ne garde que l'OS (pour y ajouter ses propres instruments)."""
    if not any(e.file_type in OS_TYPES for e in source.entries()):
        raise DiskError(T("Cette disquette ne contient pas le systeme (OS)"))
    disk = EnsoniqDisk(bytes(source.img))
    for e in disk.entries():
        if e.file_type not in OS_TYPES:
            disk.delete(e.name)
    # Le bloc systeme d'une disquette OS d'origine ne contient rien apres la signature « OS » ;
    # on efface les residus eventuels pour retrouver cet etat.
    disk.img[2 * BLOCK + 30:3 * BLOCK] = bytes(BLOCK - 30)
    return disk
