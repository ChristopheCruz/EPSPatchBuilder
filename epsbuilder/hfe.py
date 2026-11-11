"""Lecture et ecriture du format HFE (HxC Floppy Emulator) pour disquettes Ensoniq.

Geometrie Ensoniq : 80 pistes, 2 faces, secteurs de 512 octets numerotes a partir de 0,
MFM. 10 secteurs/piste a 250 kbit/s (EPS, EPS-16+ : 800 Ko) ou 20 secteurs/piste a
500 kbit/s (ASR-10 HD : 1600 Ko).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

SECTOR_SIZE = 512
BITREV = bytes(int(f"{i:08b}"[::-1], 2) for i in range(256))

IFMODE_GENERIC_SHUGART_DD = 7
IFMODE_IBMPC_HD = 1  # utilise par les images ASR HD


@dataclass(frozen=True)
class Geometry:
    tracks: int
    sides: int
    sectors: int
    bitrate: int          # kbit/s
    interface_mode: int
    gap3: int
    track_bytes: int      # octets de donnees (avant MFM) par face et par piste
    skew: int             # decalage du premier secteur entre deux faces consecutives

    @property
    def blocks(self) -> int:
        return self.tracks * self.sides * self.sectors

    @property
    def image_size(self) -> int:
        return self.blocks * SECTOR_SIZE


# Valeurs relevees sur une image HFE creee par un EPS (gap, longueur de piste, decalage).
GEOM_DD = Geometry(80, 2, 10, 250, IFMODE_GENERIC_SHUGART_DD, 40, 6320, 2)
GEOM_HD = Geometry(80, 2, 20, 500, IFMODE_GENERIC_SHUGART_DD, 40, 12640, 2)


def geometry_for_image_size(size: int) -> Geometry:
    for g in (GEOM_DD, GEOM_HD):
        if g.image_size == size:
            return g
    raise ValueError(f"Taille d'image non reconnue : {size} octets (attendu 819200 ou 1638400)")


def crc16(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


# --------------------------------------------------------------------------- MFM
def _build_mfm_table():
    # table[bit_precedent][octet] -> 16 cellules
    table = [[0] * 256, [0] * 256]
    for prev in (0, 1):
        for byte in range(256):
            p = prev
            v = 0
            for i in range(7, -1, -1):
                d = (byte >> i) & 1
                c = 1 if (p == 0 and d == 0) else 0
                v = (v << 2) | (c << 1) | d
                p = d
            table[prev][byte] = v
    return table


_MFM = _build_mfm_table()
_SYNC_A1 = 0x4489  # A1 avec horloge manquante


class _TrackWriter:
    def __init__(self):
        self.cells = bytearray()
        self.prev = 0

    def data(self, payload: bytes):
        prev = self.prev
        out = self.cells
        t0, t1 = _MFM
        for b in payload:
            v = (t1 if prev else t0)[b]
            out.append(v >> 8)
            out.append(v & 0xFF)
            prev = b & 1
        self.prev = prev

    def sync_a1(self, n=3):
        for _ in range(n):
            self.cells += _SYNC_A1.to_bytes(2, "big")
        self.prev = 1


def encode_track(geom: Geometry, track: int, side: int, sectors: list[bytes], first_sector: int = 0) -> bytes:
    """Retourne le flux MFM (cellules, MSB en premier) d'une face de piste."""
    tw = _TrackWriter()
    tw.data(b"\x4e" * 160)
    n = geom.sectors
    for k in range(n):
        r = (first_sector + k) % n
        tw.data(b"\x00" * 12)
        tw.sync_a1()
        idf = bytes([0xFE, track, side, r, 2])
        tw.data(idf + crc16(b"\xa1\xa1\xa1" + idf).to_bytes(2, "big"))
        tw.data(b"\x4e" * 22)
        tw.data(b"\x00" * 12)
        tw.sync_a1()
        body = b"\xfb" + sectors[r]
        tw.data(body + crc16(b"\xa1\xa1\xa1" + body).to_bytes(2, "big"))
        tw.data(b"\x4e" * geom.gap3)
    used = len(tw.cells) // 2
    if used > geom.track_bytes:
        raise ValueError("Piste trop longue")
    tw.data(b"\x4e" * (geom.track_bytes - used))
    return bytes(tw.cells)


def first_sector_of(geom: Geometry, track: int, side: int) -> int:
    # Meme decalage que le logiciel HxC (compteur sur 8 bits), pour produire des fichiers
    # identiques a ceux qu'il genere.
    return (-((geom.skew * (track * geom.sides + side)) & 0xFF)) % geom.sectors


# --------------------------------------------------------------------------- ecriture
def image_to_hfe(image: bytes, geom: Geometry | None = None) -> bytes:
    geom = geom or geometry_for_image_size(len(image))
    if len(image) != geom.image_size:
        raise ValueError("Taille d'image incorrecte")
    header = bytearray(b"\xff" * 512)
    header[0:8] = b"HXCPICFE"
    struct.pack_into("<BBBBHHBBH", header, 8, 0, geom.tracks, geom.sides, 0, geom.bitrate, 0,
                     geom.interface_mode, 1, 1)
    track_len = geom.track_bytes * 2 * 2          # cellules (x2) pour deux faces (x2)
    blocks_per_track = -(-track_len // 512)
    lut = bytearray(b"\xff" * 512)
    body = bytearray()
    spt = geom.sectors
    for t in range(geom.tracks):
        struct.pack_into("<HH", lut, t * 4, 2 + t * blocks_per_track, track_len)
        sides = []
        for s in range(2):
            if s < geom.sides:
                base = (t * geom.sides + s) * spt * SECTOR_SIZE
                secs = [image[base + i * SECTOR_SIZE: base + (i + 1) * SECTOR_SIZE] for i in range(spt)]
                cells = encode_track(geom, t, s, secs, first_sector_of(geom, t, s))
            else:
                cells = bytes(geom.track_bytes * 2)
            sides.append(cells.translate(BITREV))
        # Le dernier bloc est complete par le motif du gap (comme le fait le logiciel HxC).
        pad = blocks_per_track * 256 - len(sides[0])
        sides = [sd + sd[-2:] * (pad // 2) for sd in sides]
        blk = bytearray(blocks_per_track * 512)
        for i in range(blocks_per_track):
            for s in range(2):
                chunk = sides[s][i * 256:(i + 1) * 256]
                blk[i * 512 + s * 256: i * 512 + s * 256 + len(chunk)] = chunk
        body += blk
    return bytes(header) + bytes(lut) + bytes(body)


# --------------------------------------------------------------------------- lecture
def _decode_side(cells: bytes):
    bits = "".join(f"{b:08b}" for b in cells)
    wrap = bits + bits[:8192]
    sync = "0100010010001001" * 3
    found = {}
    pos = 0
    pending = None

    def rd(p, n):
        seg = wrap[p:p + n * 16]
        if len(seg) < n * 16:
            return None
        return int(seg[1::2], 2).to_bytes(n, "big")

    while True:
        i = wrap.find(sync, pos)
        if i < 0 or i >= len(bits):
            break
        p = i + 48
        mark = rd(p, 1)
        if mark is None:
            break
        if mark[0] == 0xFE:
            body = rd(p, 7)
            if body and crc16(b"\xa1\xa1\xa1" + body) == 0:
                pending = body[1:5]
            else:
                pending = None
        elif mark[0] in (0xFB, 0xF8) and pending is not None:
            size = 128 << pending[3]
            body = rd(p, 1 + size + 2)
            if body and crc16(b"\xa1\xa1\xa1" + body) == 0:
                found.setdefault(pending[2], body[1:1 + size])
            pending = None
        pos = p
    return found


def hfe_to_image(data: bytes, max_tracks: int | None = None) -> bytes:
    """Decode un fichier HFE (v1) et retourne l'image brute, secteurs dans l'ordre.

    max_tracks limite la lecture aux premieres pistes (lecture rapide du repertoire)."""
    if data[:8] != b"HXCPICFE":
        raise ValueError("Ce fichier n'est pas un HFE v1 (signature HXCPICFE absente)")
    _rev, ntrk, nside, enc, _br, _rpm, _if, _dnu, lut_off = struct.unpack_from("<BBBBHHBBH", data, 8)
    if enc not in (0, 0xFF):
        raise ValueError(f"Encodage HFE non gere : {enc}")
    image = bytearray()
    spt = None
    for t in range(ntrk if max_tracks is None else min(ntrk, max_tracks)):
        off, ln = struct.unpack_from("<HH", data, lut_off * 512 + t * 4)
        raw = data[off * 512: off * 512 + -(-ln // 512) * 512]
        side_len = ln // 2
        for s in range(nside):
            cells = bytearray()
            for b in range(0, len(raw), 512):
                cells += raw[b + s * 256: b + s * 256 + 256]
            cells = bytes(cells[:side_len]).translate(BITREV)
            secs = _decode_side(cells)
            if spt is None:
                spt = len(secs)
                if spt not in (10, 20):
                    raise ValueError(f"Nombre de secteurs inattendu : {spt}")
            for r in range(spt):
                if r not in secs or len(secs[r]) != SECTOR_SIZE:
                    raise ValueError(f"Secteur illisible : piste {t}, face {s}, secteur {r}")
                image += secs[r]
    return bytes(image)
