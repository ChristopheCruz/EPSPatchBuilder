# EPS Builder — Manuel

EPS Builder fabrique des instruments pour l'échantillonneur **Ensoniq EPS** à partir de vos
fichiers audio, les range sur des disquettes virtuelles et gère la clé USB d'un lecteur
**Gotek** (firmware HxC ou FlashFloppy). Les instruments sont au format EPS classique, que
l'EPS-16+ et l'ASR-10 savent relire.

La fenêtre se lit de gauche à droite : **1. Instrument**, **2. Disquette**, **3. Clé USB**.

## En bref

1. Glissez des fichiers audio dans la liste « Instrument ».
2. Vérifiez la note de base de chaque son et donnez un nom à l'instrument.
3. Cliquez sur « Ajouter l'instrument à la disquette ».
4. Cliquez sur « Écrire dans un nouvel emplacement » pour l'envoyer sur la clé.
5. Éjectez la clé, branchez-la sur le Gotek, démarrez l'EPS sur l'emplacement qui contient
   l'OS, puis choisissez le nouvel emplacement et chargez l'instrument.

## 1. Instrument

### Ajouter des sons

Glissez vos fichiers dans la liste ou utilisez « Ajouter des sons… ». Formats acceptés : WAV,
AIFF, FLAC, MP3, OGG. Les formats M4A, AAC, WMA et Opus demandent que le programme
*ffmpeg* soit installé sur l'ordinateur. Les sons stéréo sont mélangés en mono.

La **note de base** est la note à laquelle le son est joué à sa hauteur d'origine. Elle est
reconnue dans le nom du fichier (`piano_C3.wav`, `basse F#1.flac`) ; sinon elle vaut C4, le do
du milieu. Corrigez-la dans la colonne « Note de base ».

### Plages du clavier

Chaque son occupe une plage de notes, affichée en couleur au-dessus du clavier.

- **Zones automatiques** : le clavier est réparti à mi-chemin entre les notes de base.
- **À la main** : faites glisser le bord d'une bande de couleur sur le clavier, ou choisissez
  les notes dans les colonnes « Zone : de … à ». La plage voisine s'ajuste toute seule.
  Toute retouche à la main désactive les zones automatiques.

### Sélection multiple

Ctrl + clic ou Maj + clic sélectionne plusieurs sons. « Retirer », la case « Boucle » et la
note de base s'appliquent alors à toute la sélection (la note de base déplace tous les sons du
même intervalle). Il en va de même pour la fréquence, la résolution, la compression, les fondus
et le type de boucle dans l'éditeur de son.

### Réglage d'un son

Le panneau « Son sélectionné » montre la forme d'onde du premier son sélectionné.

| Réglage | Effet |
|---|---|
| **Début / Fin** | Partie du son conservée. Faites glisser les repères **D** et **F** ou saisissez les temps. Les parties grisées sont supprimées, ce qui économise de la place. |
| **Fondu début / fin** | Entrée ou sortie progressive, pour éviter un clic quand on coupe en plein son. |
| **Fréquence** | Fréquence d'échantillonnage de ce son. Plus basse : moins de place, son plus sourd. Par défaut, celle de l'instrument. |
| **Résolution** | L'EPS enregistre sur 13 bits. Une valeur plus faible donne un grain « lo-fi » ; la place occupée ne change pas. |
| **Compression** | Atténue les passages forts et remonte le niveau d'ensemble. |
| **Boucle** | Sans boucle, boucle avant, aller-retour, ou boucle puis relâchement. Les repères **B** délimitent la partie répétée tant que la touche est enfoncée. |
| **Passages par zéro** | Cale les bords de la boucle sur le passage par zéro le plus proche, pour réduire les clics. |
| **Raccord auto** | Cherche près de la fin de boucle le point où le raccord s'entend le moins. |
| **Réinitialiser** | Annule les réglages des sons sélectionnés. |

« Couper les silences » retire le silence au début et à la fin des sons importés tant que vous
n'avez pas réglé leur début et leur fin à la main. « Ajuster le niveau » amène chaque son
importé au niveau maximal.

### Réglages de l'instrument

- **Nom** : 12 caractères au plus.
- **Fréquence** : valeur par défaut des sons importés. 31,3 kHz est un bon compromis ; à cette
  fréquence une disquette contient environ 12 secondes de son.
- **Enveloppe** : « Son tenu » garde le volume tant que la touche est enfoncée ; « Son
  percussif » le laisse décroître jusqu'au silence, comme un piano.

### Layers

Un instrument EPS contient de 1 à 8 **layers**. Chaque layer a ses propres sons et ses propres
plages de clavier ; quand on joue une note, tous les layers actifs sonnent ensemble. On s'en sert
pour superposer deux sons (une attaque et une nappe), ou pour changer de son selon la force de
frappe.

Les onglets au-dessus de la liste des sons choisissent le layer affiché ; la liste, le clavier et
l'éditeur de son ne montrent que ce layer.

| Réglage | Effet |
|---|---|
| **+ Layer** | Ajoute un layer vide. Ajoutez-y des sons comme d'habitude. |
| **Dupliquer** | Ajoute une copie du layer affiché, avec ses sons. |
| **Supprimer le layer** | Retire le layer affiché et ses sons de l'éditeur (la disquette n'est modifiée qu'à l'écriture de l'instrument). |
| **Nom du layer** | 12 caractères au plus. |
| **Vélocité** | Le layer ne joue que si la touche est frappée avec une vélocité dans cette plage. 0 à 127 : toujours. Exemple : un layer « doux » de 0 à 80 et un layer « fort » de 81 à 127. |
| **Patches 0 à 3** | Les deux boutons Patch Select de l'EPS choisissent un des quatre patches (0 : aucun bouton, 3 : les deux). Le layer joue dans les patches cochés. |

Un instrument contient au plus 127 sons, tous layers confondus. Un layer vide empêche d'écrire
l'instrument : ajoutez-y des sons ou supprimez-le.

Les instruments d'usine utilisent souvent des **copies** : plusieurs sons qui relisent les mêmes
échantillons avec d'autres réglages. EPS Builder les garde telles quelles, ce qui évite de
multiplier la place occupée. Un son que vous retravaillez (début, fin, fréquence, compression…)
reçoit ses propres échantillons ; changer seulement sa boucle, sa note ou sa plage ne coûte rien.

### Écouter

- « Écouter » joue le son sélectionné tel qu'il sera dans l'EPS, à sa note de base.
- Un clic sur une touche du clavier joue l'instrument à cette note.

L'écoute fonctionne sous Windows.

## 2. Disquette

Une disquette EPS contient 1585 blocs, soit environ 790 Ko, et 39 fichiers au plus. La barre
indique la place utilisée.

| Bouton | Rôle |
|---|---|
| **Vierge** | Nouvelle disquette vide. |
| **Avec OS…** | Nouvelle disquette contenant le système de l'EPS, copié depuis une disquette existante. Elle pourra démarrer la machine. |
| **Ouvrir… / Enregistrer sous…** | Lit ou écrit une image `.hfe` (Gotek) ou `.img` (image brute). |
| **Modifier l'instrument** | Charge l'instrument dans l'éditeur (double-clic), avec tous ses layers. Ses sons gardent leurs réglages ; modifiez-le puis cliquez sur « Mettre à jour l'instrument sur la disquette ». Les réglages qu'EPS Builder ne montre pas (filtres, enveloppes, LFO…) sont conservés. |
| **Écouter** | Fait entendre les sons de l'instrument l'un après l'autre. |
| **Monter / Descendre** | Change l'ordre des instruments. On peut aussi les faire glisser dans la liste. L'OS reste en tête. |
| **Exporter en WAV…** | Enregistre tous les sons de la disquette en fichiers WAV. |
| **Supprimer** | Retire le fichier de la disquette. |

Tant que la disquette n'est pas écrite sur la clé ou enregistrée, son titre porte la mention
« modifiée ».

## 3. Clé USB du Gotek

Choisissez la clé dans la liste (« Parcourir… » pour un dossier quelconque). Le firmware est
reconnu automatiquement :

- **HxC** : les images s'appellent `DSKA0000.hfe`, `DSKA0001.hfe`… Le numéro est celui que l'on
  choisit sur le Gotek.
- **FlashFloppy** : les noms de fichiers sont libres.

| Action | Effet |
|---|---|
| **Ouvrir** (ou double-clic) | Charge l'emplacement dans la partie « Disquette ». |
| **Écrire dans un nouvel emplacement** | Écrit la disquette en cours dans le premier emplacement libre. |
| **Remplacer l'emplacement** | Remplace l'emplacement sélectionné, après confirmation. |
| **Catalogue…** | Enregistre la liste de tous les emplacements et de leur contenu dans un fichier texte. |

Chaque écriture est relue pour contrôle. **Éjectez toujours la clé** depuis Windows avant de la
retirer.

### Glisser-déposer

- Un instrument de la disquette déposé **sur un emplacement** y est copié. Déposé sous la
  dernière ligne, il crée un nouvel emplacement. La clé est modifiée aussitôt, après
  confirmation.
- Un emplacement déposé **sur la disquette** propose d'importer ses instruments.

### Modifier un emplacement existant

Ouvrez-le, faites vos changements (ajout, suppression, ordre, modification d'un instrument),
puis cliquez sur « Remplacer l'emplacement ».

### Gérer les emplacements

| Action | Effet |
|---|---|
| **▲ Monter / ▼ Descendre** | Mode HxC : échange l'emplacement avec le précédent ou le suivant (numéro − 1 ou + 1). |
| **Numéro…** | Mode HxC : donne un autre numéro à l'emplacement. S'il est déjà pris, les deux emplacements échangent leurs numéros. |
| **Renommer…** | Mode FlashFloppy : change le nom du fichier image. |
| **Glisser un emplacement sur un autre** | Mode HxC : les deux emplacements échangent leurs numéros. |
| **Supprimer** (ou touche Suppr) | Déplace l'image dans le dossier `CORBEILLE_EPS` de la clé, après confirmation. Rien n'est effacé : pour la récupérer, utilisez « Gérer… → Nouvel emplacement depuis une image » et choisissez-la dans ce dossier. |
| **Gérer… → Nouvel emplacement avec une disquette vierge** | Écrit une disquette vide dans le premier emplacement libre. |
| **Gérer… → Nouvel emplacement depuis une image** | Copie une image `.hfe` ou `.img` de l'ordinateur dans le premier emplacement libre (elle est vérifiée avant l'écriture). |
| **Gérer… → Renuméroter sans trous** | Mode HxC : renumérote les emplacements 000, 001, 002… dans leur ordre actuel. |
| **Gérer… → Ouvrir la corbeille** | Ouvre le dossier `CORBEILLE_EPS` de la clé. |

Si la disquette ouverte vient d'un emplacement qui change de numéro, EPS Builder suit le
changement. Les numéros changent aussi sur le Gotek : pensez-y si vous avez noté où se trouve
l'OS.

## Sur l'EPS

1. Mettez le Gotek sur l'emplacement qui contient l'OS (000 en général) et allumez l'EPS.
2. Une fois l'EPS démarré, choisissez l'emplacement voulu sur le Gotek.
3. Appuyez sur LOAD, puis INSTRUMENT, choisissez l'instrument et validez.

## En cas de problème

| Message ou symptôme | Cause et solution |
|---|---|
| **OS NOT ON DISK** au démarrage | Le Gotek est sur un emplacement sans OS. Revenez à l'emplacement qui contient l'OS. |
| **KBD FAILED – TRY AGAIN** | La calibration du clavier a échoué : rallumez sans toucher les touches. Si cela persiste, c'est une panne de contact du clavier, sans rapport avec la clé. |
| **DISK DRIVE NOT READY** | Réglage du Gotek (cavaliers, délai de changement de disque), pas un défaut du fichier. |
| Le son s'arrête alors que la touche est enfoncée | Choisissez l'enveloppe « Son tenu » et activez la boucle. |
| Clic à chaque tour de boucle | Utilisez « Passages par zéro » ou « Raccord auto », ou déplacez les repères B. |
| « Trop gros pour la disquette » | Raccourcissez les sons (début, fin), baissez la fréquence, ou répartissez sur deux disquettes. |

## Limites

- Format EPS classique seulement (13 bits, disquettes de 800 Ko). Les formats propres à
  l'EPS-16+ et à l'ASR-10 ne sont pas écrits.
- Les instruments répartis sur deux disquettes (très gros instruments d'usine) ne peuvent pas
  être ouverts.
- Les enveloppes détaillées, le filtre, le LFO et les autres réglages des layers se règlent sur
  l'EPS lui-même ; EPS Builder les conserve.

## Licence

EPS Builder est un logiciel libre distribué sous licence MIT : vous pouvez l'utiliser, le
copier, le modifier et le redistribuer librement, y compris à des fins commerciales, à
condition de conserver la mention de droit d'auteur.
