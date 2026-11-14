"""Traduction anglaise des textes de l'application. Cle : texte francais d'origine."""

EN = {
    "La bibliotheque « soundfile » n'est pas installee : seuls les WAV sont lisibles":
        "The “soundfile” library is not installed: only WAV files can be read",
    "{0} : ce n'est pas un fichier WAV":
        "{0}: not a WAV file",
    "{0} : fichier WAV incomplet":
        "{0}: incomplete WAV file",
    "{0} : en-tete WAV invalide":
        "{0}: invalid WAV header",
    "{0} : ce format demande le programme ffmpeg, qui n'est pas installe. Convertissez le fichier en WAV, FLAC ou MP3, ou installez ffmpeg.":
        "{0}: this format needs the ffmpeg program, which is not installed. Convert the file to WAV, FLAC or MP3, or install ffmpeg.",
    "{0} : lecture impossible ({1})":
        "{0}: cannot be read ({1})",
    "{0} : conversion impossible ({1})":
        "{0}: cannot be converted ({1})",
    "{0} : conversion trop longue":
        "{0}: conversion took too long",
    "{0} : format WAV non gere (code {1}, {2} bits)":
        "{0}: unsupported WAV format (code {1}, {2} bits)",
    "HD 1600 Ko (ASR-10)":
        "HD 1600 KB (ASR-10)",
    "DD 800 Ko (EPS / EPS-16+)":
        "DD 800 KB (EPS / EPS-16+)",
    "ANOMALIE :":
        "PROBLEM:",
    "affiche le contenu d'une image de disquette (.hfe ou .img)":
        "show the contents of a disk image (.hfe or .img)",
    "detaille les sons de chaque instrument":
        "list the sounds of each instrument",
    "cree un instrument a partir de fichiers WAV et l'ecrit sur une disquette":
        "create an instrument from audio files and write it to a disk",
    "fichier audio (WAV, AIFF, FLAC, MP3, OGG...), suivi au besoin de @NOTE (ex. piano.wav@C3)":
        "audio file (WAV, AIFF, FLAC, MP3, OGG...), optionally followed by @NOTE (e.g. piano.wav@C3)",
    "image a ecrire (.hfe ou .img)":
        "image to write (.hfe or .img)",
    "nom de l'instrument (12 caracteres)":
        "instrument name (12 characters)",
    "image existante a completer (sinon disquette vierge)":
        "existing image to add to (otherwise a blank disk)",
    "frequence d'echantillonnage dans l'EPS en Hz (defaut 31250)":
        "sample rate in the EPS, in Hz (default 31250)",
    "boucler les sons":
        "loop the sounds",
    "disquette HD 1600 Ko (ASR-10)":
        "HD 1600 KB disk (ASR-10)",
    "nom de la disquette (7 caracteres)":
        "disk label (7 characters)",
    "ne pas ajuster le niveau":
        "do not normalize the level",
    "ne pas couper les silences":
        "do not trim silence",
    "exporte en WAV les sons des instruments d'une disquette":
        "export the sounds of a disk's instruments as WAV",
    "Disquette {0}, nom « {1} », {2} blocs libres sur {3}":
        "{0} disk, label “{1}”, {2} blocks free out of {3}",
    "Instrument « {0} » : {1} blocs ({2} Ko), {3} echantillons":
        "Instrument “{0}”: {1} blocks ({2} KB), {3} samples",
    "Disquette ecrite : {0} ({1} blocs libres)":
        "Disk written: {0} ({1} blocks free)",
    "{0} fichier(s) WAV ecrit(s) dans {1}":
        "{0} WAV file(s) written to {1}",
    "EPS Builder {0}":
        "EPS Builder {0}",
    "Erreur : {0}":
        "Error: {0}",
    "     (lecture impossible : {0})":
        "     (cannot be read: {0})",
    "Systeme (OS)":
        "System (OS)",
    "Sous-repertoire":
        "Sub-directory",
    "Instrument EPS":
        "EPS instrument",
    "Banque EPS":
        "EPS bank",
    "Sequence EPS":
        "EPS sequence",
    "Morceau EPS":
        "EPS song",
    "SysEx":
        "SysEx",
    "Repertoire parent":
        "Parent directory",
    "Macro":
        "Macro",
    "Banque EPS-16+":
        "EPS-16+ bank",
    "Instrument EPS-16+":
        "EPS-16+ instrument",
    "Effet EPS-16+":
        "EPS-16+ effect",
    "Sequence EPS-16+":
        "EPS-16+ sequence",
    "Morceau EPS-16+":
        "EPS-16+ song",
    "OS EPS-16+":
        "EPS-16+ OS",
    "Banque ASR":
        "ASR bank",
    "Effet ASR":
        "ASR effect",
    "Sequence ASR":
        "ASR sequence",
    "Morceau ASR":
        "ASR song",
    "OS ASR":
        "ASR OS",
    "Piste audio ASR":
        "ASR audio track",
    "Image non formatee Ensoniq":
        "Image is not Ensoniq formatted",
    "Cette disquette ne contient pas le systeme (OS)":
        "This disk does not contain the system (OS)",
    "Cette image n'est pas une disquette Ensoniq formatee":
        "This image is not a formatted Ensoniq disk",
    "Repertoire plein (39 fichiers maximum)":
        "Directory full (39 files at most)",
    "Taille de fichier invalide":
        "Invalid file size",
    "La liste ne correspond pas au contenu de la disquette":
        "The list does not match the contents of the disk",
    "signature DR absente":
        "DR signature missing",
    "Chaine de blocs incomplete pour {0!r}":
        "Incomplete block chain for {0!r}",
    "Disquette pleine : {0} blocs demandes, {1} libres":
        "Disk full: {0} blocks needed, {1} free",
    "Un fichier nomme {0!r} existe deja sur la disquette":
        "A file named {0!r} already exists on the disk",
    "Fichier introuvable : {0!r}":
        "File not found: {0!r}",
    "Un autre fichier s'appelle deja {0!r}":
        "Another file is already named {0!r}",
    "{0} blocs alloues sans fichier (ou l'inverse)":
        "{0} blocks allocated without a file (or the reverse)",
    "compteur de blocs libres faux ({0} annonces, {1} reels)":
        "wrong free block count ({0} declared, {1} actual)",
    "Chaine de blocs corrompue pour {0!r}":
        "Corrupt block chain for {0!r}",
    "signature FB absente (bloc {0})":
        "FB signature missing (block {0})",
    "bloc {0} partage entre {1!r} et {2!r}":
        "block {0} shared between {1!r} and {2!r}",
    "52,1 kHz (qualité maximale)":
        "52.1 kHz (best quality)",
    "44,6 kHz":
        "44.6 kHz",
    "39,1 kHz":
        "39.1 kHz",
    "31,3 kHz (conseillé)":
        "31.3 kHz (recommended)",
    "26,0 kHz":
        "26.0 kHz",
    "19,5 kHz":
        "19.5 kHz",
    "15,6 kHz (économe)":
        "15.6 kHz (space saving)",
    "Nouvelle disquette vierge":
        "New blank disk",
    "Son de la disquette":
        "Sound from the disk",
    "Glissez des fichiers audio dans la liste pour commencer.":
        "Drag audio files into the list to get started.",
    "&Fichier":
        "&File",
    "Nouvelle disquette avec OS…":
        "New disk with OS…",
    "Ouvrir une image de disquette…":
        "Open a disk image…",
    "Enregistrer l'image sous…":
        "Save the image as…",
    "Quitter":
        "Quit",
    "&Aide":
        "&Help",
    "Manuel":
        "Manual",
    "Licence":
        "License",
    "À propos":
        "About",
    "1. Instrument":
        "1. Instrument",
    "Nouvel instrument":
        "New instrument",
    "Abandonne la modification et vide l'éditeur.":
        "Discards the changes and empties the editor.",
    "NOUVEAU":
        "NEW",
    "Son tenu":
        "Sustained sound",
    "Son percussif (décroît)":
        "Percussive sound (decays)",
    "Ctrl ou Maj + clic pour sélectionner plusieurs sons : retirer, boucler ou\nchanger la note de base s'applique alors à toute la sélection.":
        "Ctrl or Shift + click to select several sounds: removing, looping or\nchanging the root note then applies to the whole selection.",
    "Glissez ici vos fichiers audio (WAV, AIFF, FLAC, MP3, OGG…), ou utilisez « Ajouter des sons… ».\nLa note de base est reconnue dans le nom du fichier (ex. piano_C3.wav).\nCtrl ou Maj + clic : sélectionner plusieurs sons pour les régler ensemble.":
        "Drag your audio files here (WAV, AIFF, FLAC, MP3, OGG…), or use “Add sounds…”.\nThe root note is read from the file name (e.g. piano_C3.wav).\nCtrl or Shift + click: select several sounds to adjust them together.",
    "Ajouter des sons…":
        "Add sounds…",
    "Retirer":
        "Remove",
    "Écouter":
        "Listen",
    "Joue le son sélectionné tel qu'il sera dans l'EPS (fréquence choisie, 13 bits),\nà sa note de base. Cliquez sur le clavier pour l'entendre sur une autre note.":
        "Plays the selected sound as it will be in the EPS (chosen rate, 13 bits),\nat its root note. Click the keyboard to hear it on another note.",
    "Zones automatiques":
        "Automatic zones",
    "Répartit le clavier à mi-chemin entre les notes de base.":
        "Splits the keyboard halfway between the root notes.",
    "Ajuster le niveau":
        "Normalize level",
    "Couper les silences":
        "Trim silence",
    "Retire le silence au début et à la fin des sons importés,\ntant que leur début et leur fin n'ont pas été réglés à la main.":
        "Removes the silence at the start and end of imported sounds,\nas long as their start and end have not been set by hand.",
    "Cliquez sur une touche pour écouter l'instrument à cette note.\nFaites glisser le bord d'une bande de couleur pour changer la plage d'un son.":
        "Click a key to hear the instrument on that note.\nDrag the edge of a coloured band to change the key range of a sound.",
    "Ajouter l'instrument à la disquette  ▶":
        "Add the instrument to the disk  ▶",
    "2. Disquette":
        "2. Disk",
    "Glissez un instrument pour changer l'ordre, ou vers un emplacement de la clé pour l'y copier.\nGlissez ici un emplacement de la clé pour en importer les instruments.":
        "Drag an instrument to change the order, or onto a slot of the USB stick to copy it there.\nDrag a slot of the USB stick here to import its instruments.",
    "Modifier l'instrument":
        "Edit the instrument",
    "Charge l'instrument sélectionné dans l'éditeur (double-clic).":
        "Loads the selected instrument into the editor (double-click).",
    "Fait entendre les sons de l'instrument sélectionné, l'un après l'autre.":
        "Plays the sounds of the selected instrument, one after the other.",
    "▲ Monter":
        "▲ Up",
    "▼ Descendre":
        "▼ Down",
    "Exporter en WAV…":
        "Export as WAV…",
    "Supprimer":
        "Delete",
    "3. Clé USB du Gotek":
        "3. Gotek USB stick",
    "Parcourir…":
        "Browse…",
    "Actualiser":
        "Refresh",
    "HxC (emplacements numérotés)":
        "HxC (numbered slots)",
    "FlashFloppy (noms libres)":
        "FlashFloppy (free names)",
    "Double-clic : ouvrir l'emplacement.\nGlissez un emplacement vers la disquette pour en importer les instruments.\nDéposez ici un instrument de la disquette pour le copier dans un emplacement (sous les lignes : nouvel emplacement).":
        "Double-click: open the slot.\nDrag a slot onto the disk to import its instruments.\nDrop an instrument from the disk here to copy it into a slot (below the rows: new slot).",
    "Ouvrir":
        "Open",
    "Charge cet emplacement dans la partie « Disquette ».":
        "Loads this slot into the “Disk” section.",
    "Catalogue…":
        "Catalogue…",
    "Remplacer l'emplacement":
        "Replace the slot",
    "Écrire dans un nouvel emplacement":
        "Write to a new slot",
    "Continuer":
        "Continue",
    "Annuler":
        "Cancel",
    "Ajouter des sons":
        "Add sounds",
    "Nouveau fichier":
        "New file",
    "Nom du fichier sur la clé :":
        "File name on the USB stick:",
    "Importer":
        "Import",
    "Ouvrir une image de disquette":
        "Open a disk image",
    "Images de disquette (*.hfe *.img)":
        "Disk images (*.hfe *.img)",
    "Enregistrer l'image":
        "Save the image",
    "Image HFE pour Gotek (*.hfe);;Image brute (*.img)":
        "HFE image for Gotek (*.hfe);;Raw image (*.img)",
    "Sans l'OS, cette disquette ne pourra plus démarrer l'EPS.":
        "Without the OS, this disk will no longer be able to boot the EPS.",
    "Dossier pour les fichiers WAV":
        "Folder for the WAV files",
    "Dossier ou clé USB du Gotek":
        "Gotek folder or USB stick",
    "Enregistrer le catalogue":
        "Save the catalogue",
    "Texte (*.txt)":
        "Text (*.txt)",
    "Fermer":
        "Close",
    "Manuel d'EPS Builder":
        "EPS Builder manual",
    "{0}\n{1:.0f} Hz, {2} échantillons":
        "{0}\n{1:.0f} Hz, {2} samples",
    "Son":
        "Sound",
    "Note de base":
        "Root note",
    "Zone : de":
        "Zone: from",
    "à":
        "to",
    "Boucle":
        "Loop",
    "Durée":
        "Length",
    "Nom :":
        "Name:",
    "Fréquence :":
        "Sample rate:",
    "Enveloppe :":
        "Envelope:",
    "Nom":
        "Name",
    "Type":
        "Type",
    "Blocs":
        "Blocks",
    "Vierge":
        "Blank",
    "Avec OS…":
        "With OS…",
    "Ouvrir…":
        "Open…",
    "Enregistrer sous…":
        "Save as…",
    "Emplacement":
        "Slot",
    "Contenu":
        "Contents",
    "Libre":
        "Free",
    "Mettre à jour l'instrument sur la disquette  ▶":
        "Update the instrument on the disk  ▶",
    "Un instrument contient au maximum 127 sons.":
        "An instrument holds 127 sounds at most.",
    "Le son se répète tant que la touche est enfoncée.\nPoints de boucle lus dans le WAV s'ils existent, sinon tout le son.":
        "The sound repeats for as long as the key is held.\nLoop points are read from the WAV if present, otherwise the whole sound loops.",
    "{0} son(s), {1:.1f} s — environ {2} blocs ({3} Ko) pour {4} blocs libres sur la disquette.":
        "{0} sound(s), {1:.1f} s — about {2} blocks ({3} KB) for {4} free blocks on the disk.",
    "Donnez un nom à l'instrument.":
        "Give the instrument a name.",
    "L'écoute n'est disponible que sous Windows.":
        "Listening is only available on Windows.",
    "mis à jour sur":
        "updated on",
    "ajouté à":
        "added to",
    "Cet emplacement est déjà la disquette ouverte.":
        "This slot is already the open disk.",
    "La disquette en cours a été modifiée et n'est pas encore écrite.":
        "The current disk has been modified and is not written yet.",
    "Abandonner ces modifications ?":
        "Discard these changes?",
    "Choisir une disquette contenant l'OS":
        "Choose a disk that contains the OS",
    "L'OS a été copié ; cette disquette pourra démarrer l'EPS.":
        "The OS has been copied; this disk will be able to boot the EPS.",
    "Aucune clé détectée":
        "No USB stick detected",
    "Fichiers audio ({0});;Tous les fichiers (*)":
        "Audio files ({0});;All files (*)",
    "Modifier la plage désactive les zones automatiques.\nLa plage voisine s'ajuste pour ne pas se chevaucher.":
        "Editing the range turns automatic zones off.\nThe neighbouring range adjusts so that they do not overlap.",
    "Vider l'éditeur d'instrument ?":
        "Empty the instrument editor?",
    "Les sons listés seront retirés de l'éditeur. La disquette n'est pas modifiée.":
        "The listed sounds will be removed from the editor. The disk is not modified.",
    "Les sons actuellement listés dans l'éditeur seront retirés.":
        "The sounds currently listed in the editor will be removed.",
    "DISQUETTE":
        "DISK",
    "la disquette":
        "the disk",
    "{0} blocs utilisés sur {1} — {2} libres ({3} Ko)":
        "{0} blocks used out of {1} — {2} free ({3} KB)",
    " — modifiée":
        " — modified",
    "Supprimer « {0} » de la disquette ?":
        "Delete “{0}” from the disk?",
    "{0} fichier(s) WAV exporté(s) dans {1}":
        "{0} WAV file(s) exported to {1}",
    "Emplacement {0}":
        "Slot {0}",
    "\n\nATTENTION : cet emplacement contient l'OS et la nouvelle disquette ne le contient pas. Si c'est votre disquette de démarrage, l'EPS ne démarrera plus dessus.":
        "\n\nWARNING: this slot contains the OS and the new disk does not. If it is your boot disk, the EPS will no longer boot from it.",
    "Retirer ({0})":
        "Remove ({0})",
    "« {0} » : de {1} à {2}":
        "“{0}”: from {1} to {2}",
    "« {0} » : le bas de la zone est au-dessus du haut.":
        "“{0}”: the bottom of the zone is above the top.",
    "Écoute : « {0} » sur {1}":
        "Listening: “{0}” on {1}",
    "Aucun son sur la note {0}.":
        "No sound on note {0}.",
    "Écoute de « {0} » : {1} son(s), chacun à sa hauteur d'origine.":
        "Listening to “{0}”: {1} sound(s), each at its original pitch.",
    "Instrument « {0} » {1} la disquette.":
        "Instrument “{0}” {1} the disk.",
    "« {0} » contient {1} layers. L'éditeur ne gère pour l'instant que les instruments à un seul layer ; celui-ci peut être déplacé, supprimé ou exporté en WAV.":
        "“{0}” has {1} layers. For now the editor only handles single-layer instruments; this one can be moved, deleted or exported as WAV.",
    "« {0} » chargé : modifiez-le, puis « Mettre à jour l'instrument sur la disquette ».":
        "“{0}” loaded: edit it, then “Update the instrument on the disk”.",
    "Le remplacer ?":
        "Replace it?",
    "emplacement {0}":
        "slot {0}",
    "« {0} » existe déjà sur la clé. Choisissez un autre nom, ou sélectionnez ce fichier et utilisez « Remplacer l'emplacement ».":
        "“{0}” already exists on the USB stick. Choose another name, or select that file and use “Replace the slot”.",
    "Une disquette vierge sera créée sur la clé avec ces instruments.":
        "A blank disk will be created on the USB stick with these instruments.",
    "Cet emplacement est la disquette déjà ouverte : utilisez « Remplacer l'emplacement » pour y écrire vos modifications.":
        "This slot is the disk that is already open: use “Replace the slot” to write your changes to it.",
    "{0} copié(s) dans l'{1} et vérifié(s) sur la clé.":
        "{0} copied to {1} and verified on the USB stick.",
    "{0}   ({1}, {2} blocs)":
        "{0}   ({1}, {2} blocks)",
    "L'emplacement {0} est illisible : {1}":
        "Slot {0} cannot be read: {1}",
    "{0} importé(s) de l'emplacement {1}.":
        "{0} imported from slot {1}.",
    "Nouvelle disquette avec OS (copié de {0})":
        "New disk with OS (copied from {0})",
    "Contenu actuel : {0}\nIl sera définitivement remplacé.":
        "Current contents: {0}\nThey will be permanently replaced.",
    "La disquette est vide.":
        "The disk is empty.",
    "L'écrire quand même sur la clé ?":
        "Write it to the USB stick anyway?",
    "Disquette écrite et vérifiée : {0}. Éjectez la clé avant de la retirer.":
        "Disk written and verified: {0}. Eject the USB stick before removing it.",
    "Les zones de « {0} » et « {1} » se chevauchent sur la note {2}.":
        "The zones of “{0}” and “{1}” overlap on note {2}.",
    "Charger « {0} » dans l'éditeur ?":
        "Load “{0}” into the editor?",
    "L'emplacement {0} ne contient aucun instrument.":
        "Slot {0} contains no instrument.",
    "Catalogue enregistré : {0}":
        "Catalogue saved: {0}",
    "Document introuvable : {0}\n{1}":
        "Document not found: {0}\n{1}",
    "{0} : son trop court":
        "{0}: sound too short",
    "« {0} » existe déjà dans {1}.":
        "“{0}” already exists in {1}.",
    "Copier {0} dans l'{1} ?":
        "Copy {0} to {1}?",
    "Contenu actuel : {0}\nLa clé sera modifiée immédiatement.":
        "Current contents: {0}\nThe USB stick will be modified immediately.",
    "Fichiers de l'emplacement {0} à copier sur la disquette :":
        "Files of slot {0} to copy to the disk:",
    "Remplacer l'{0} ?":
        "Replace {0}?",
    "« {0} » existe déjà sur la disquette.":
        "“{0}” already exists on the disk.",
    "Créer l'{0} avec : {1} ?":
        "Create {0} with: {1}?",
    "Créer {0} avec : {1} ?":
        "Create {0} with: {1}?",
    "Sans boucle":
        "No loop",
    "Sans boucle, a l'envers":
        "No loop, backwards",
    "Boucle avant":
        "Loop forward",
    "Boucle aller-retour":
        "Loop back and forth",
    "Boucle puis relachement":
        "Loop then release",
    "Un instrument contient de 1 a 8 layers":
        "An instrument has 1 to 8 layers",
    "L'instrument ne contient aucun son":
        "The instrument contains no sound",
    "Un instrument contient au maximum 127 sons":
        "An instrument holds 127 sounds at most",
    "Ce fichier n'est pas un instrument EPS valide":
        "This file is not a valid EPS instrument",
    "Code de frequence d'echantillonnage hors limites (12 a 127)":
        "Sample rate code out of range (12 to 127)",
    "Le layer {0} est vide":
        "Layer {0} is empty",
    "Zone de clavier invalide pour {0!r}":
        "Invalid key zone for {0!r}",
    "Le son {0!r} est trop court":
        "The sound {0!r} is too short",
    "Points de boucle invalides pour {0!r}":
        "Invalid loop points for {0!r}",
    "Le son {0!r} est trop long (plus de 1 Mo)":
        "The sound {0!r} is too long (more than 1 MB)",
    "Les zones de clavier se chevauchent sur la note {0} ({1!r})":
        "Key zones overlap on note {0} ({1!r})",
    "Aucun son":
        "No sound",
    "Note hors limites : {0!r}":
        "Note out of range: {0!r}",
    "  Layer {0} ({1}), velocite {2}-{3}":
        "  Layer {0} ({1}), velocity {2}-{3}",
    "Note invalide : {0!r} (exemples : C4, F#3, 60)":
        "Invalid note: {0!r} (examples: C4, F#3, 60)",
    "    {0:12s} {1:7d} ech. {2:7.0f} Hz ({3:5.2f} s)  base {4:4s} zone {5}-{6}  {7}{8}":
        "    {0:12s} {1:7d} smp. {2:7.0f} Hz ({3:5.2f} s)  root {4:4s} zone {5}-{6}  {7}{8}",
    "Boucle puis relâchement":
        "Loop then release",
    "À l'envers, sans boucle":
        "Backwards, no loop",
    "13 bits (EPS)":
        "13 bits (EPS)",
    "12 bits":
        "12 bits",
    "10 bits":
        "10 bits",
    "8 bits":
        "8 bits",
    "6 bits":
        "6 bits",
    "Son sélectionné":
        "Selected sound",
    "Faites glisser les repères : D = début, F = fin, B = bords de la boucle.\nLes parties grisées ne sont pas gardées.":
        "Drag the markers: S = start, E = end, L = loop edges.\nThe greyed parts are not kept.",
    "Début du son gardé.":
        "Start of the part that is kept.",
    "Fin du son gardé.":
        "End of the part that is kept.",
    "Fondu d'entrée : évite un clic si le début est coupé en plein son.":
        "Fade in: avoids a click when the start is cut in the middle of the sound.",
    "Fondu de sortie : évite un clic si la fin est coupée en plein son.":
        "Fade out: avoids a click when the end is cut in the middle of the sound.",
    "Celle de l'instrument":
        "Same as the instrument",
    "Fréquence d'échantillonnage de ce son dans l'EPS.\nPlus basse : moins de mémoire, son plus sourd.":
        "Sample rate of this sound in the EPS.\nLower: less memory, duller sound.",
    "Résolution. L'EPS classique enregistre sur 13 bits ; moins de bits donne un grain « lo-fi ».\nLa place occupée ne change pas.":
        "Resolution. The EPS classic records at 13 bits; fewer bits give a “lo-fi” grain.\nThe space used does not change.",
    "Compression de dynamique : atténue les passages forts et remonte le niveau d'ensemble.":
        "Dynamic compression: tames the loud passages and raises the overall level.",
    "Passages par zéro":
        "Zero crossings",
    "Cale les deux bords de la boucle sur le passage par zéro le plus proche.":
        "Snaps both loop edges to the nearest zero crossing.",
    "Raccord auto":
        "Auto splice",
    "Cherche près de la fin de boucle le point où le raccord s'entend le moins.":
        "Searches near the loop end for the point where the splice is least audible.",
    "Réinitialiser":
        "Reset",
    "Annule tous les réglages de ce son.":
        "Cancels all the settings of this sound.",
    "Sélectionnez un son dans la liste pour le régler.":
        "Select a sound in the list to adjust it.",
    "Position en échantillons du son d'origine.":
        "Position in samples of the original sound.",
    "de":
        "from",
    "Compression":
        "Compression",
    "Début":
        "Start",
    "Fin":
        "End",
    "Fondu début":
        "Fade in",
    "Fondu fin":
        "Fade out",
    "Fréquence":
        "Sample rate",
    "Résolution":
        "Resolution",
    "Son sélectionné : {0}":
        "Selected sound: {0}",
    "(vide)":
        "(empty)",
    "Plus aucun emplacement libre":
        "No free slot left",
    "Nom de fichier invalide":
        "Invalid file name",
    "Le fichier relu sur la cle differe de l'original : cle defectueuse ?":
        "The file read back from the USB stick differs from the original: faulty stick?",
    "Disquette incoherente, ecriture annulee : ":
        "Inconsistent disk, write cancelled: ",
    "Catalogue de la cle {0}":
        "Catalogue of USB stick {0}",
    "Cle USB":
        "USB stick",
    "{0} existe deja sur la cle":
        "{0} already exists on the USB stick",
    "{0}{1}  ({2} blocs libres)":
        "{0}{1}  ({2} blocks free)",
    "lecture impossible : {0}":
        "cannot be read: {0}",
    "Cle inaccessible : {0}":
        "USB stick unavailable: {0}",
    "Ecriture impossible : {0}":
        "Cannot write: {0}",
    "      {0}  {1}, {2} blocs":
        "      {0}  {1}, {2} blocks",
    "l'{0}":
        "{0}",
    "D": "S",
    "F": "E",
    "B": "L",
    "{0} Ko": "{0} KB",
    # 0.5.0 : instruments a plusieurs layers
    "Chaque layer a ses propres sons et zones de clavier.\nLes layers jouent ensemble, selon la vélocité et le patch choisi sur l'EPS.":
        "Each layer has its own sounds and keyboard zones.\nLayers play together, depending on velocity and on the patch selected on the EPS.",
    "+ Layer": "+ Layer",
    "Ajoute un layer vide (8 au maximum).": "Adds an empty layer (8 at most).",
    "Dupliquer": "Duplicate",
    "Ajoute une copie du layer affiché, avec ses sons.": "Adds a copy of the displayed layer, with its sounds.",
    "Supprimer le layer": "Delete layer",
    "Nom du layer :": "Layer name:",
    "Vélocité :": "Velocity:",
    "Le layer ne joue que si la touche est frappée avec une vélocité dans cette plage\n(0-127 : toujours).":
        "The layer only plays when the key is struck with a velocity in this range\n(0-127: always).",
    "Patches :": "Patches:",
    "Patch {0} : le layer joue quand ce patch est choisi avec les boutons Patch Select de l'EPS\n(0 : aucun bouton, 3 : les deux boutons).":
        "Patch {0}: the layer plays when this patch is selected with the EPS Patch Select buttons\n(0: no button, 3: both buttons).",
    "Layer {0} ajouté : ajoutez-y des sons.": "Layer {0} added: add sounds to it.",
    "Supprimer le layer « {0} » et ses {1} son(s) ?": "Delete layer “{0}” and its {1} sound(s)?",
    "La disquette n'est pas modifiée tant que l'instrument n'y est pas écrit.":
        "The disk is not changed until the instrument is written to it.",
    "{0} layers, ": "{0} layers, ",
    "Layer {0} ({1}) : ": "Layer {0} ({1}): ",
    "{0}ce layer n'a aucun son : ajoutez-en ou supprimez le layer.":
        "{0}this layer has no sound: add some or delete the layer.",
    "Aucun layer": "No layer",
    "Le layer « {0} » est vide": "Layer “{0}” is empty",
    "Plage de vélocité invalide pour le layer {0}": "Invalid velocity range for layer {0}",
    "Le son {0!r} est incoherent": "Sound {0!r} is inconsistent",
    "L'instrument est trop gros (plus de 1 Mo)": "The instrument is too large (over 1 MB)",
    "Instrument incomplet : il continue sans doute sur une autre disquette, ce que EPS Builder ne gère pas":
        "Incomplete instrument: it probably continues on another disk, which EPS Builder does not handle",
    # 0.5.0 : gestion des emplacements de la cle
    "Échange l'emplacement avec le précédent (numéro - 1).": "Swaps the slot with the previous one (number - 1).",
    "Échange l'emplacement avec le suivant (numéro + 1).": "Swaps the slot with the next one (number + 1).",
    "Numéro…": "Number…",
    "Renommer…": "Rename…",
    "Gérer…": "Manage…",
    "Nouvel emplacement avec une disquette vierge": "New slot with a blank disk",
    "Nouvel emplacement depuis une image (.hfe, .img)…": "New slot from an image (.hfe, .img)…",
    "Renuméroter sans trous (000, 001, 002…)": "Renumber without gaps (000, 001, 002…)",
    "Ouvrir la corbeille de la clé": "Open the stick's trash folder",
    "Déplace l'image dans la corbeille de la clé ({0}) : rien n'est effacé.":
        "Moves the image to the stick's trash folder ({0}): nothing is erased.",
    "Renommer": "Rename",
    "Nouveau nom du fichier sur la clé :": "New file name on the stick:",
    "Numéro de l'emplacement": "Slot number",
    "Nouveau numéro pour l'emplacement {0} :\n(s'il est déjà pris, les deux emplacements échangent leurs numéros)":
        "New number for slot {0}:\n(if it is already taken, the two slots swap numbers)",
    "Emplacements {0} et {1} échangés.": "Slots {0} and {1} swapped.",
    "Emplacement {0} déplacé en {1}.": "Slot {0} moved to {1}.",
    "{0} renommé en {1}.": "{0} renamed to {1}.",
    "Supprimer l'emplacement {0} ?": "Delete slot {0}?",
    "Contenu : {0}\nL'image sera déplacée dans le dossier {1} de la clé : vous pourrez la récupérer.":
        "Contents: {0}\nThe image will be moved to the {1} folder on the stick: you can get it back.",
    "\n\nATTENTION : cet emplacement contient l'OS de l'EPS.": "\n\nWARNING: this slot holds the EPS OS.",
    "Emplacement {0} mis à la corbeille : {1}": "Slot {0} moved to the trash: {1}",
    "VIERGE": "BLANK",
    "Disquette vierge écrite : {0}": "Blank disk written: {0}",
    "Image de disquette à copier sur la clé": "Disk image to copy to the stick",
    "Images de disquette (*.hfe *.img);;Tous les fichiers (*)": "Disk images (*.hfe *.img);;All files (*)",
    "{0} copiée sur la clé : {1}": "{0} copied to the stick: {1}",
    "Renuméroter les emplacements 000, 001, 002… sans trous ?": "Renumber the slots 000, 001, 002… without gaps?",
    "L'ordre est conservé. Sur le Gotek, les numéros des disquettes changeront.":
        "The order is kept. On the Gotek, the disk numbers will change.",
    "{0} emplacement(s) renuméroté(s).": "{0} slot(s) renumbered.",
    "En mode FlashFloppy, l'ordre suit les noms : utilisez « Renommer… ».":
        "In FlashFloppy mode, the order follows the names: use “Rename…”.",
    "En mode HxC, les images s'appellent DSKA0000.HFE, DSKA0001.HFE…":
        "In HxC mode, images are named DSKA0000.HFE, DSKA0001.HFE…",
    "Seuls les emplacements numérotés (mode HxC) peuvent changer de numéro":
        "Only numbered slots (HxC mode) can change number",
    "Numéro d'emplacement hors limites (0 à {0})": "Slot number out of range (0 to {0})",
    "{0} n'existe plus sur la clé": "{0} no longer exists on the stick",
    "Renommage impossible : {0}": "Cannot rename: {0}",
    "Suppression impossible : {0}": "Cannot delete: {0}",
    "{0} : image illisible ({1})": "{0}: unreadable image ({1})",
}
