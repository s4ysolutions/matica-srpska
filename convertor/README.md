# Convertor cli

## Preparing the environment
This is a command line tool for converting Serbian dictionary from PDF to json, csv or txt formats.

The tool requires python 3.6. It is recommended, but not required, to use a virtual environment, for example
venv.
```shell
python3 -m venv .venv
. .venv/bin/activate
```

## Basic usage
After activating the virtual environment, install the required packages.
```shell
pip install -r convertor/requirements.txt
```

The producing the output in required format is done by running the convertor.py script with the desired options.
```shell
python convertor/convertor.py --txt --progress
```

```shell
python convertor/convertor.py --json > /path/to/output.json
```

```shell
python convertor/convertor.py --csv --progress > /path/to/output.csv
```

The tool is used to upload the dictionary to the firebase database. The service account key json file
is required for this. This option is not recommended due to the slow upload, but it is used internally.

```shell
python --firebase-service-account-key-json /path/to/service-account-key.json
```

Import JSON to Firebase is the recommended way to upload the dictionary to the firebase database.
```shell
python convertor/convertor.py --json-lookup > /path/to/output.json
```

## Fixing decoding errors

The PDF file was created with the OSR software and uses the custom mapping between the specif font
character codes (CIDs) and the unicode characters. 

convertor.py contains [the mapping](https://github.com/s4ysolutions/matica-srpska/blob/2a960e92a33d238ac8e8099f536e9503db40e598/convertor/convertor.py#L1337)
between the CIDs and the unicode characters which is not completed yes.

The tool can be used to find the missing mappings by running the tool with the debug option. For example,
the following command will print the first entry on the 16th page of the PDF.

```shell
convertor/convertor.py --debug 16:0
```
The output will be similar to the following:

```text
-------------------------------------
Page:       16
Entry no:   0
Headword:   а1
Definition: (А) с непром. 1. а. лингв. ниски отворени самогласник задњег реда. б. слово за обележавање тога самогласника, прво слово ћирилице и латинице. 2. при набрајању: прво (по редy). 3. муз. шести тон основне дијатонске (C-dur) лествице (у солмизацији ла). 4. скраћ. за ампер (А). • од а до ш (od а do z) од почетка до краја. није рекао ни а ништа није рекао.
Lines:
==> /C0_1:\x00\x01\x00\xc3\x06\xe1[а1 ],  /C0_1:\x001\x00\xdd\x00.\x06\xe1[(А) ],  /C0_2:\x00\x1f\x01=[с ],  /C0_3:\x00\x07\x00\x04\x00\r\x00\x02\x00\x12\x00\x03\x00h\x03\x1b[непром. ],  /C0_4:\x03H\x02'\x12I[1. ],  /C0_1:\x00\x01\x00&\x06\xe1[а. ],  /C0_1:\x02\xa8[ЛШIГВ>лингв],  /C0_5:\x00\xd6\x02\x84[. ],  /C0_4:\x0ej\x0c\xf4\nP\x03O\n\xb0\x12I[ниС1Ш >ниски ],  /C0_4:\x0e\xc4\x10\xd1\x0b\xe4\x0e\xc4\x0f-\x0c!\x0ej\x0c\xf4\x12I[ошворени >отворени ],  /C0_4:\x05\x8d\x05o\x07\xd2\x05\xf1\x05I\x05\x8d\x04j\x04\xe9\x04\xa4\x12I[caмof.nacHUK >cамoглаcник ],  /C0_4:\x0c\xd5\x05I\x06\x10\x11\xd2\x0c!\x05\xee\x12I[зagњеf, >задњег ],  
==> /C0_4:\x07\xeb\x05\xb5\x06\x10\x05I\x02\x0f\x12I[pega. >peда. ],  /C0_1:\x00\x0f\x00&\x06\xe1[б. ],  /C0_4:\x0f\x83\r\xe7\x0e\xc4\x0b\xe4\x0e\xc4\x12I[слово ],  /C0_4:\x0c\xd5\n\xe9\x12I[за ],  /C0_4:\x0e\xc4\x0b\xb2\x0c![обе],  /C0_4:\r\xe7\x0c!\x0c\xb1\n\xe9\x0b\xe4\n\xe9\x11\xd2\x0c!\x12I[лежавање ],  /C0_4:\x10\xd1\x0e\xc4\x05\xeb\n\xe9\x12I[шоf,а >тога ],  /C0_4:\x05\x8d\x05o\x07\xd2\x05\xf1\x05I\x05\x8d\x04j\x04\xe9\x04\xa4\x05I\x01S\x12I[caмof.nacHUKa, >cамoглаcника, ],  /C0_4:\rh\x0f-[йр>пр],  /C0_4:\x0b\xe4\x0e\xc4\x12I[во ],  /C0_4:\x0f\x83\r\xe7\x0e\xc4\x0b\xe4\x0e\xc4\x12I[слово ],  
==> /C0_4:\x06<\x0c\xf4\x0f-\rB\x0c\xf4\x10|\x0c!\x12I[hирилице >ћирилице ],  /C0_4:\x0c\xf4\x12I[и ],  /C0_4:\r\xe7\n\xe9\n\xa4\x0c\xf4\x0ej\x0c\xf4\x10|\x0c!\x02\x0f\x12I[лаШинице. >латинице. ],  /C0_4:\x03\xa2\x025\x12I[2. ],  /C0_4:\rh\x0f-\x0c\xf4\x12I[йри >при ],  /C0_4:\x0ej\n\xe9\x0b\xb2[наб],  /C0_4:\x0f-\n\xe9[ра],  /C0_4:\x11k\n\xe9\x11\xd2\x0f\xfe\x03\xd1\x12I[јању: ],  /C0_4:\rh\x0f-[йр>пр],  /C0_4:\x0b\xe4\x0e\xc4\x12I[во ],  /C0_4:\x00\xd9\rh\x0e\xc4\x12I[(йо >(по ],  /C0_4:\x07\xeb\x05\xb5\x06\x10\t\x05\x01B\x02\x0f\x12I[pegy). >peдy). ],  /C0_4:\x03\xab\x025\x12I[3. ],  /C0_3:\x00\x03\x00 \x00\x16\x00h\x03\x1b[муз. ],  
==> /C0_4:\x10\xd2\x0c!\x0f\x83\x10\xd1\x0c\xf4\x12I[шесши >шести ],  /C0_4:\x10\xd1\x0e\xc4\x0ej\x12I[шон >тон ],  /C0_4:\x0e\xc4\x0f\x83\x0ej\x0e\xc4\x0b\xe4\x0ej\x0c!\x12I[основне ],  /C0_4:\x06\x10\x0c\xf4[gи>ди],  /C0_4:\x11k\n\xe9\x10\xd1\x0e\xc4\x0ej\x0f\x83\r\xb0\x0c!\x12I[јашонске >јатонске ],  /C0_4:\x00\xe0\x04\\\x01\xf8\x05\xaa[(C-d],  /C0_4:\x08l\x08\x1f\x01-\x12I[ur) ],  /C0_4:\r\xe7\x0c!\x0f\x83\x10\xd1\x0b\xe4\x0c\xf4\x10|\x0c!\x12I[лесшвице >лествице ],  /C0_4:\x00\xd9\x0f\xfe\x12I[(у ],  /C0_4:\x0f\x83\x0e\xc4\x0e\x12\x0c\xf4\x0c\xd5\n\xe9\x10|\x0c\xf4\t'[солмизаци­],  
==> /C0_4:\x11k\x0c\xf4\x12I[ји ],  /C0_4:\r\xe7\n\xe9\x01B\x02\x0f\x12I[ла). ],  /C0_4:\x03\xaf\x025\x12I[4. ],  /C0_4:\x0f\x83\r\xb0[ск],  /C0_4:\x0f-\n\xe9\x11\xe2\x02\x0f\x12I[раћ. ],  /C0_4:\x0c\xd5\n\xe9\x12I[за ],  /C0_4:\x0bq\t\xd7\x0c![амЙе>ампе],  /C0_4:\x0f-\x12I[р ],  /C0_4:\x00\xd9\t\x99[(А],  /C0_4:\x01*\x022\x12I[). ],  /C0_6:\x00v\x00{[• ],  /C0_7:\x00\x03\x00\x0c\x01\xca[од ],  /C0_7:\x00\x04\x01\xca[а ],  /C0_7:\x00\x0c\x00\x03\x01\xca[до ],  /C0_8:\x02\xfa\x03}[m >ш ],  /C0_9:\x00\xe1\x00\x91\x00\x90\x035[(od ],  /C0_7:\x00\x04\x01\xca[а ],  /C0_9:\x00\x90\x00\x91\x035[do ],  /C0_9:\x02]\x00\xf3\x035[z) ],  /C0_4:\x07\xd2\x06\x10\x12I[og >oд ],  /C0_4:\rh\x0e\xc4\x10\xa8\x0c!\x10\xd1\r\xb0\n\xe9\x12I[йочешка >почетка ],  /C0_4:\x06\x10\x07\xd2\x12I[go >дo ],  
==> /C0_4:\r\xb0\x0f-\n\xe9[кра],  /C0_4:\x11k\n\xe9\x02\x0f\x12I[ја. ],  /C0_7:\x00\x06\x00.\x00\x15\x00\x02\x01\xca[није ],  /C0_7:\x00\n\x00\x02\x00\t\x00\x04\x00\x03\x01\xca[рекао ],  /C0_7:\x00\x06\x00.\x01\xca[ни ],  /C0_7:\x00\x04\x01\xca[а ],  /C0_4:\x0ej\x0c\xf4\x10\xd2\x10\xd1\n\xe9\x12I[нишша >ништа ],  /C0_4:\x0ej\x0c\xf4\x11k\x0c!\x12I[није ],  /C0_4:\x0f-\x0c!\r\xb0\n\xe9\x0e\xc4\x02\x0f\x12I[рекао. ],  
```

Each entry contains list of lines each containing the comma separated list of chunks as they are read from the PDF file.
For each chunk the provided info is:
- the font name (C0_1, C0_2, C0_3, C0_4, C0_5, C0_6, C0_7, C0_8, C0_9)
- 16-bit character codes (CIDs) (e.g. \x00\x01)
- the text transformed to unicode with custom mapping applied ([а1 ])
- optionally (if it is different) the unicode without mapping (e.g. [SoMEBeIRt >some weird])
