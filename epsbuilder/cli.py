"""Interface en ligne de commande.

Exemples :
    python -m epsbuilder info DSKA0000.hfe
    python -m epsbuilder build -o DSKA0001.hfe -n "MON PIANO" piano_C2.wav@C2 piano_C4.wav@C4
    python -m epsbuilder build -o DSKA0001.hfe --base DSKA0001.hfe -n "BASSE" basse.wav@E1
    python -m epsbuilder extract DSKA0000.hfe dossier_wav
"""
from __future__ import annotations

import argparse
import os
import sys

from .i18n import T
from . import __version__, audio, instrument as ins, project
from .disk import DiskError, EnsoniqDisk, TYPE_EPS_INSTRUMENT


def cmd_info(args) -> int:
    disk = EnsoniqDisk.load(args.image)
    kind = T("HD 1600 Ko (ASR-10)") if disk.geom.sectors == 20 else T("DD 800 Ko (EPS / EPS-16+)")
    print(T("Disquette {0}, nom « {1} », {2} blocs libres sur {3}").format(kind, disk.label, disk.free_blocks, disk.total_blocks - disk.first_data_block))
    for e in disk.entries():
        print(f"{e.index + 1:2d}. {e.name}  {e.type_name:16s} {e.blocks:5d} blocs")
        if e.file_type == TYPE_EPS_INSTRUMENT and args.detail:
            try:
                for line in project.describe_instrument(ins.parse_instrument(disk.read_file(e))):
                    print(line)
            except Exception as ex:  # instrument illisible : on continue la liste
                print(T("     (lecture impossible : {0})").format(ex))
    problems = disk.check()
    for p in problems:
        print(T("ANOMALIE :"), p)
    return 1 if problems else 0


def cmd_build(args) -> int:
    specs = []
    for item in args.wav:
        path, _, note = item.partition("@")
        specs.append(project.SampleSpec(path, project.note_to_midi(note) if note else None, loop=args.loop))
    disk = EnsoniqDisk.load(args.base) if args.base else EnsoniqDisk.blank(hd=args.hd, label=args.label)
    inst = project.make_instrument(args.name, specs, rate_hz=args.rate, normalize=not args.no_normalize,
                                   trim=not args.no_trim)
    blocks = project.add_instrument(disk, inst)
    disk.save(args.output)
    words = sum(len(w.samples) for w in inst.all_wavesamples())
    print(T("Instrument « {0} » : {1} blocs ({2} Ko), {3} echantillons").format(inst.name.upper()[:12], blocks, blocks * 512 // 1024, words))
    for line in project.describe_instrument(inst):
        print(line)
    print(T("Disquette ecrite : {0} ({1} blocs libres)").format(args.output, disk.free_blocks))
    return 0


def cmd_extract(args) -> int:
    disk = EnsoniqDisk.load(args.image)
    os.makedirs(args.folder, exist_ok=True)
    count = 0
    for e in disk.entries():
        if e.file_type != TYPE_EPS_INSTRUMENT:
            continue
        inst = ins.parse_instrument(disk.read_file(e))
        for li, layer in enumerate(inst.layers, 1):
            for wi, ws in enumerate(layer.wavesamples, 1):
                name = f"{e.name.strip()}_L{li}_{wi:02d}_{project.midi_to_note(ws.root_key)}.wav".replace(" ", "_")
                audio.write_wav(os.path.join(args.folder, name), ws.samples, ws.rate)
                count += 1
    print(T("{0} fichier(s) WAV ecrit(s) dans {1}").format(count, args.folder))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="epsbuilder", description=T("EPS Builder {0}").format(__version__))
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("info", help=T("affiche le contenu d'une image de disquette (.hfe ou .img)"))
    a.add_argument("image")
    a.add_argument("-d", "--detail", action="store_true", help=T("detaille les sons de chaque instrument"))
    a.set_defaults(func=cmd_info)

    a = sub.add_parser("build", help=T("cree un instrument a partir de fichiers WAV et l'ecrit sur une disquette"))
    a.add_argument("wav", nargs="+", help=T("fichier audio (WAV, AIFF, FLAC, MP3, OGG...), suivi au besoin de @NOTE (ex. "
                                            "piano.wav@C3)"))
    a.add_argument("-o", "--output", required=True, help=T("image a ecrire (.hfe ou .img)"))
    a.add_argument("-n", "--name", required=True, help=T("nom de l'instrument (12 caracteres)"))
    a.add_argument("--base", help=T("image existante a completer (sinon disquette vierge)"))
    a.add_argument("--rate", type=float, default=project.DEFAULT_RATE_HZ,
                   help=T("frequence d'echantillonnage dans l'EPS en Hz (defaut 31250)"))
    a.add_argument("--loop", action="store_true", help=T("boucler les sons"))
    a.add_argument("--hd", action="store_true", help=T("disquette HD 1600 Ko (ASR-10)"))
    a.add_argument("--label", default="", help=T("nom de la disquette (7 caracteres)"))
    a.add_argument("--no-normalize", action="store_true", help=T("ne pas ajuster le niveau"))
    a.add_argument("--no-trim", action="store_true", help=T("ne pas couper les silences"))
    a.set_defaults(func=cmd_build)

    a = sub.add_parser("extract", help=T("exporte en WAV les sons des instruments d'une disquette"))
    a.add_argument("image")
    a.add_argument("folder")
    a.set_defaults(func=cmd_extract)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (DiskError, ins.InstrumentError, audio.AudioError, ValueError, OSError) as ex:
        print(T("Erreur : {0}").format(ex), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
