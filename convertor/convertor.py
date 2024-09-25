import os
import pikepdf
import re

from decimal import Decimal

ENCODING_TYPE_1B = 1
ENCODING_TYPE_2B = 2
ENCODING_TYPE_MB = 0

PARAGRAPH_INTERVAL = 12


def string_to_cids(string, encoding_type):
    cids = []
    if encoding_type == ENCODING_TYPE_1B:
        for char in string:
            cids.append(ord(char))
    elif encoding_type == ENCODING_TYPE_2B:
        for char in string:
            cids.append(ord(char))
    elif encoding_type == ENCODING_TYPE_MB:
        for char in string:
            cids.append(ord(char))
    return cids


class PdfDecoderForFont():
    def __init__(self, font_name, font, to_unicode_fixed=None, typos=None):
        self.name = font_name
        self.font = font
        # encoding type
        encoding = font.get("/Encoding", None)
        if not encoding:
            self.encoding_type = ENCODING_TYPE_1B
        elif encoding in ["/WinAnsiEncoding", "/MacRomanEncoding", "/MacExpertEncoding", "/StandardEncoding",
                          "/PDFDocEncoding"]:
            self.encoding_type = ENCODING_TYPE_1B
        elif encoding == "/Identity-H":
            self.encoding_type = ENCODING_TYPE_2B
        elif encoding == "/Identity-V":
            self.encoding_type = ENCODING_TYPE_MB
        else:
            self.encoding_type = ENCODING_TYPE_1B
        # ToUnicode CMap
        self.to_unicode_map = {}
        range_pattern = re.compile(r"<([0-9A-F]+)> <([0-9A-F]+)> <([0-9A-F]+)>")
        char_pattern = re.compile(r"<([0-9A-F]+)> <([0-9A-F]+)>")
        if "/ToUnicode" in font:
            cmap_stream = font["/ToUnicode"]
            cmap_data = cmap_stream.read_bytes()
            cmap_text = cmap_data.decode('utf-8', errors='ignore')
            for line in cmap_text.splitlines():
                range_match = range_pattern.search(line)
                if range_match:
                    start_cid = int(range_match.group(1), 16)
                    end_cid = int(range_match.group(2), 16)
                    start_unicode = int(range_match.group(3), 16)

                    # Add all CID to Unicode mappings in this range
                    for cid in range(start_cid, end_cid + 1):
                        self.to_unicode_map[cid] = chr(start_unicode + (cid - start_cid))
                else:
                    # Parse individual character mappings (e.g., <0020> <0020>)
                    char_match = char_pattern.search(line)
                    if char_match:
                        cid = int(char_match.group(1), 16)
                        bytes_string = bytes.fromhex(char_match.group(2))
                        self.to_unicode_map[cid] = bytes_string.decode('utf-16be', errors='ignore')
        # Fixups  Unicode CMap
        self.to_unicode_fixed = to_unicode_fixed or {}
        self.typos = typos or {}

    def to_unicode(self, pikepdf_string):
        bytes = pikepdf_string.__bytes__()
        if self.encoding_type == ENCODING_TYPE_2B:
            cids = [bytes[i] << 8 | bytes[i + 1] for i in range(0, len(bytes), 2)]
        elif self.encoding_type == ENCODING_TYPE_MB:
            cids = [bytes[i] << 8 | bytes[i + 1] for i in range(0, len(bytes), 2)]
        else:
            cids = [byte for byte in bytes]
        unicode_text = ""
        for cid in cids:
            try:
                if cid in self.to_unicode_fixed:
                    unicode_text += self.to_unicode_fixed[cid]
                elif cid in self.to_unicode_map:
                    unicode_text += self.to_unicode_map[cid]
                else:
                    unicode_text += f"<${cid.to_bytes()}>"
            except (OverflowError, ValueError) as e:
                unicode_text += "?"
                print(f"====> Error decoding CID {cid} to Unicode: {e}")
        return self.remove_garbage(self.typos.get(unicode_text, unicode_text))

    def remove_garbage(self, text):
        return text.replace('.м', 'м')  # //.replace('ЈЬ','љ')


HYPHEN = chr(173)


class PdfDecoderForPage():
    def __init__(self, page, page_no, to_unicode_fixed=None, typos=None):
        if to_unicode_fixed is None:
            to_unicode_fixed = {}
        self.page = page
        self.page_no = page_no
        self.resources = page["/Resources"]
        self.fonts = self.resources.get("/Font", None)
        self.font_decoders = {}
        if self.fonts is None:
            raise ValueError(f"No fonts found in page resources for page: {page}")
        else:
            for font_name, font_dict in self.fonts.items():
                font = font_dict
                fixed = (to_unicode_fixed or {}).get(font_name, {})
                self.font_decoders[font_name] = PdfDecoderForFont(font_name, font, fixed,
                                                                  (typos or {}).get(font_name, {}))

    def _call_for_tj(self, lmbd):
        intext = False
        font = None
        x = 0
        y = 0
        for operands, operator in pikepdf.parse_content_stream(self.page):
            # debug code
            #            print(f" ==== > Operator: {operator}", "Operands: ", operands)
            #            if operator == pikepdf.Operator('Tj'):
            #                for operand in operands:
            #                    if isinstance(operand, pikepdf.String):
            #                        text = operand
            #                        font_decoder = self.font_decoders[font]
            #                        self.lmbd_debug(text, font_decoder, x, y)
            #                    else:
            #                        print(f"Unexpected operand type: {type(operand)}")
            #            elif operator == pikepdf.Operator('TJ'):
            #                for operand in operands:
            #                    if isinstance(operand, pikepdf.Array):
            #                        for element in operand:
            #                            if isinstance(element, pikepdf.String):
            #                                text = element
            #                                font_decoder = self.font_decoders[font]
            #                                self.lmbd_debug(text, font_decoder, x, y)
            #                            elif isinstance(element, int):
            #                                pass
            #                            elif isinstance(element, Decimal):
            #                                pass
            #                            else:
            #                                print(f"Unexpected element type: {type(element)}")
            #                    else:
            #                        print(f"Unexpected operand type: {type(operand)}")

            if operator == pikepdf.Operator('BT'):
                intext = True
                font = None
                continue
            if operator == pikepdf.Operator('ET'):
                intext = False
                font = None
                continue
            # if operator == pikepdf.Operator('Tc'):
            #    x += operands[0] * words length
            #    continue
            # if operator == pikepdf.Operator('Tw'):
            #    x += operands[0]
            #    continue
            if operator == pikepdf.Operator('TL'):
                raise ValueError("Unexpected operator TL")
            if operator == pikepdf.Operator('TD'):
                raise ValueError("Unexpected operator TD")
            if operator == pikepdf.Operator('Td'):
                x += operands[0]
                y += operands[1]
                continue
            if operator == pikepdf.Operator('T*'):
                raise ValueError("Unexpected operator T*")
            if operator == pikepdf.Operator('TL'):
                raise ValueError("Unexpected operator TL")
            if intext:
                if operator == pikepdf.Operator('Tf'):
                    font = str(operands[0])
                elif operator == pikepdf.Operator('Tj'):
                    for operand in operands:
                        if isinstance(operand, pikepdf.String):
                            text = operand
                            font_decoder = self.font_decoders[font]
                            lmbd(text, font_decoder, x, y)
                        else:
                            print(f"Unexpected operand type: {type(operand)}")
                elif operator == pikepdf.Operator('TJ'):
                    for operand in operands:
                        if isinstance(operand, pikepdf.Array):
                            for element in operand:
                                if isinstance(element, pikepdf.String):
                                    text = element
                                    font_decoder = self.font_decoders[font]
                                    lmbd(text, font_decoder, x, y)
                                elif isinstance(element, int):
                                    pass
                                elif isinstance(element, Decimal):
                                    pass
                                else:
                                    print(f"Unexpected element type: {type(element)}")
                        else:
                            print(f"Unexpected operand type: {type(operand)}")
                elif operator == pikepdf.Operator('Tm'):
                    x = operands[4]
                    y = operands[5]

    @staticmethod
    def lmbd_debug(text, font_decoder, x, y):
        unicode_text = font_decoder.to_unicode(text)
        print(f"Text: x={x} y={y} {text.__bytes__()} -> \"{unicode_text}\", Font: {font_decoder.name}")

    def debug_text(self):
        self._call_for_tj(self.lmbd_debug)

    def print_positions(self):
        chunks = []
        prev_y = 0  # assume there's top
        prev_x = 785  # assume there's no indent
        first = True

        def lmbd(text, font_decoder, x, y):
            nonlocal prev_y
            nonlocal prev_x
            nonlocal chunks
            nonlocal first

            if first:
                first = False
                if x > 200:
                    return

            unicode_text = font_decoder.to_unicode(text)

            if prev_y == -1:
                dy = 0
            else:
                dy = prev_y - y
            prev_y = y

            if prev_x == -1:
                dx = 1
            else:
                dx = prev_x - x
            prev_x = x

            print(f"{x}, {y}, {dx}, {dy}, {self.page_no}")

    def convert_to_chunks(self):
        chunks = []

        def lmbd(text, font_decoder, x, y):
            nonlocal chunks
            unicode_text = font_decoder.to_unicode(text)
            chunks.append(Chunk(unicode_text, x, y))

        self._call_for_tj(lmbd)
        return chunks

    @staticmethod
    def _skip_header(chunks):
        dy = 0  # pixels
        p = 0  # pos
        while dy < 8 and p < len(chunks) - 1:
            y_prev = chunks[p].y
            p += 1
            dy = y_prev - chunks[p].y
        return chunks[p:]

    @staticmethod
    def _next_para_pos_by_interval(pos, chunks):
        interval = 0
        top = chunks[pos].y
        p = pos + 1
        while p < len(chunks) and interval < PARAGRAPH_INTERVAL:
            while p < len(chunks) and abs(chunks[p].y - top) < 3:
                p += 1
            if p == len(chunks):
                break
            interval = top - chunks[p].y
            top = chunks[p].y
        return p

    @staticmethod
    def _get_top_left(chunks):
        if len(chunks) == 0:
            return 0, 0
        top = chunks[0].y
        left = chunks[0].x

        for chunk in chunks:
            if chunk.x < left:
                left = chunk.x

        return top, left

    #    @staticmethod
    #    def _get_min_indent(chunks, left):
    #        indent = 15
    #        while (len(chunks) < 0):
    #            p1 = PdfDecoderForPage._next_para_pos_by_interval(chunks)
    #            # indented paragraph
    #            if chunks[p1].x > left + 7:
    #                if chunks[p1].x < indent:
    #                    indent = chunks[p1].x
    #            chunks = chunks[p1:]
    #        return indent

    @staticmethod
    def _split_by_column(chunks):
        p = 0
        prev_y = chunks[0].y
        # +7 for dot is hack (fine turning)
        while p < len(chunks) and (
                chunks[p].y <= prev_y or (chunks[p].text.startswith('.') and chunks[p].y <= prev_y + 7)):
            prev_y = chunks[p].y
            p += 1
        return chunks[:p], chunks[p:]

    @staticmethod
    def _chunks_to_definition(chunks):
        definition = ""
        i = 0
        while i < len(chunks):
            if i + 1 < len(chunks) and chunks[i + 1].y < chunks[i].y and chunks[i].text.endswith(HYPHEN):
                definition += chunks[i].text[:-1]
            else:
                definition += chunks[i].text
            i += 1
        return definition

    @staticmethod
    def _chunks_to_entries(chunks, page_no):
        top, left = PdfDecoderForPage._get_top_left(chunks)
        first = True
        p = 0
        entries = []
        while p < len(chunks):
            p1 = PdfDecoderForPage._next_para_pos_by_interval(p, chunks)
            if first:
                first = False
                if chunks[p].x - left < 2:
                    headword = None
                    definition = chunks[p:p1]
                else:
                    headword = chunks[p]
                    definition = chunks[p + 1:p1]
            else:
                headword = chunks[p]
                definition = chunks[p + 1:p1]
            if (not headword is None) and len(definition) > 0 and definition[0].text.startswith('се,'):
                headword.text += 'се,'
                definition0 = definition[0].text[3:]
                if len(definition0) == 0:
                    definition = definition[1:]
                else:
                    definition[0].text = definition0
            if headword is None:
                headword_text = ""
            else:
                headword_text = headword.text.strip()
            entries.append(Entry(headword_text, PdfDecoderForPage._chunks_to_definition(definition), page_no))
            p = p1
        return entries

    @staticmethod
    def _concatenate_entries(entries1, entries2):
        if entries2[0].headword is None:
            entries1[-1].definition += entries2[0].definition
            entries2 = entries2[1:]
        return entries1 + entries2

    # prev_entries is used to concatenate entries from the previous page
    # if the first entry on the current page is a continuation of the last entry on the previous page
    def convert_to_entries(self, prev_entries):
        chunks = self.convert_to_chunks()
        chunks = PdfDecoderForPage._skip_header(chunks)
        chunks1, chunks2 = PdfDecoderForPage._split_by_column(chunks)
        entries1 = PdfDecoderForPage._chunks_to_entries(chunks1, self.page_no)
        entries2 = PdfDecoderForPage._chunks_to_entries(chunks2, self.page_no)

        if len(entries2) == 0:
            entries = entries1
        else:
            entries = PdfDecoderForPage._concatenate_entries(entries1, entries2)

        if len(prev_entries) > 0:
            if not entries[0].headword:
                prev_entries[-1].definition += entries[0].definition
                entries = entries[1:]

        return entries


class Chunk:
    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y

    def __str__(self):
        return f'"{self.text}" x: {self.x} y: {self.y}'

    def __repr__(self):
        return f'Chunk("{self.text}", {self.x}, {self.y})'


class Entry:
    def __init__(self, headword, definition, page_no):
        self.headword = headword
        self.definition = definition
        self.page_no = page_no

    def __str__(self):
        return f'"{self.headword}"({self.page_no})\n{self.definition}'

    def __repr__(self):
        return f'Entry("{self.headword}", "{self.definition}", {self.page_no})'

    def txt(self, headword_separator=' '):
        return f'{self.headword}{headword_separator}{self.definition}{headword_separator}{self.page_no}'


class PdfDecoderForFile():
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file

    def each(self, lmbda, debug=True):
        with pikepdf.open(self.pdf_file) as pdf:
            prev_entries = []
            for n, page in enumerate(pdf.pages, start=1):
                if n < 17:
                    continue
                if n > 1529:
                    break
                if (debug and page["/Resources"].get("/Font", None) is None):
                    print(f"No fonts found in page resources for page: {n}", file=sys.stderr)
                    continue
                decoder = PdfDecoderForPage(page, n, fixes, typos)
                entries = decoder.convert_to_entries(prev_entries)
                if debug:
                    print(f"Page {n}: {entries[0].headword}", file=sys.stderr)
                prev_entries = entries
                for entry in entries:
                    if entry.headword or entry.definition:
                        lmbda(entry)


def bytes2cid(b):
    return b[0] << 8 | b[1]


fixes = {
    '/C0_0': {
        bytes2cid(b'\x00e'): '~',
        bytes2cid(b'\x00\x0b'): '~',
        bytes2cid(b'\x00\r'): '~',
    },
    '/C0_1': {
        bytes2cid(b'\x00|'): 'с',
        bytes2cid(b'\x00f'): 'и',
        bytes2cid(b'\x00r'): 'к',
        bytes2cid(b'\x00t'): 'е',
        bytes2cid(b'\x00\x7f'): 'д',
        bytes2cid(b'\x00\x83'): 'н',
        bytes2cid(b'\x04\x85'): 'и',
        bytes2cid(b'\x00\x8f'): 'и',
        bytes2cid(b'\x00\x95'): 'о',
        bytes2cid(b'\x00\x9e'): 'т',
        bytes2cid(b'\x00\xa2'): '~',
        bytes2cid(b'\x00\xac'): 'л',
        bytes2cid(b'\x00\xb9'): 'д',
        bytes2cid(b'\x00\xfa'): 'ч',
        bytes2cid(b'\x01j'): 'ц',
        bytes2cid(b'\x04l'): 'д',
        bytes2cid(b'\x01\x02'): 'у',
        bytes2cid(b'\x01\x07'): 'б',
        bytes2cid(b'\x02\xa8'): 'лингв',
        bytes2cid(b'\x03\x86'): '.',
        bytes2cid(b'\x04\x16'): 'и',
    },
    '/C0_3': {
        bytes2cid(b'\x01d'): '1',
        bytes2cid(b'\x00\t'): 'с',
        bytes2cid(b'\x08^'): 'лингв',
    },
    '/C0_4': {
        bytes2cid(b'\n+'): 'о',
        bytes2cid(b'\rh'): 'п',
        bytes2cid(b'\nP'): 'с',
        bytes2cid(b'\no'): 'у',
        bytes2cid(b'\n\x14'): 'н',
        bytes2cid(b'\n\xa4'): 'т',
        bytes2cid(b'\n\xb0'): 'и',
        bytes2cid(b'\r\x92'): 'т',
        bytes2cid(b'\r\xa2'): 'тл',
        bytes2cid(b'\t\x88'): 'љ',
        bytes2cid(b'\t\xc4'): 'ж',
        bytes2cid(b'\t\xd7'): 'п',
        bytes2cid(b'\t\xef'): 'к',
        bytes2cid(b'\x00\x17'): 'г',
        bytes2cid(b'\x02&'): '.',
        bytes2cid(b'\x04j'): 'н',
        bytes2cid(b'\x03O'): 'к',
        bytes2cid(b'\x04U'): 'с',
        bytes2cid(b'\x04\xb1'): 'м',
        bytes2cid(b'\x04\xe9'): 'и',
        bytes2cid(b'\x04\xa4'): 'к',
        bytes2cid(b'\x04\xc0'): 'о',
        bytes2cid(b'\x05o'): 'ам',
        bytes2cid(b'\x05\xb7'): 'в',
        bytes2cid(b'\x05\xf1'): 'гл',
        bytes2cid(b'\x05I'): 'а',
        bytes2cid(b'\x06<'): 'ћ',
        bytes2cid(b'\x06\x10'): 'д',
        bytes2cid(b'\x05\xee'): 'г',
        bytes2cid(b'\x05\xeb'): 'г',
        bytes2cid(b'\x08^'): 'и',
        bytes2cid(b'\x0c '): 'ил',
        bytes2cid(b'\x0c\x9a'): 'ељ',
        bytes2cid(b'\x0e\x1e'): 'пл',
        bytes2cid(b'\x10\xd1'): 'т',

        bytes2cid(b'\t\xf8'): 'л',

    },
    '/C0_5': {
        bytes2cid(b'\x00y'): '~',
        bytes2cid(b'\x00\x9e'): '~',
    },
    '/C0_6': {
        bytes2cid(b'\x00\1b'): '~',
    },
    '/C0_7': {
        bytes2cid(b'\x00\x0b'): '~',
    },
    '/C0_8': {
        bytes2cid(b'\x00\x04'): 'а',
        bytes2cid(b'\x02\xfa'): 'ш',
    },
    '/C0_9': {
        bytes2cid(b'\x00\x8e'): '~',
    },
    '/C0_10': {
        # bytes2cid(b'\x00\x04'): 'ц', #!!!!
        bytes2cid(b'\x00\x04'): 'е',  # !!!!
        bytes2cid(b'\x00\x1c'): ',',
        bytes2cid(b'\x01H'): 'р',
        bytes2cid(b'\x01\x12'): 'и',
        bytes2cid(b'\x021'): 'е',
        bytes2cid(b'\x03`'): 'д',
    }
}
typos = {
    # '/C0_4': {
    #    'cамoгаcник ': 'самогласник ',
    # }
}

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Парсер за Матицу Српску')

    parser.add_argument('--debug', action='store_true',
                        help='Приказивање дебаг информација')
    parser.add_argument('--full-search-txt', action='store_true',
                        help='Екстракција свих страна из PDF-а у текстуални фајл')
    parser.add_argument('--full-search-csv', action='store_true',
                        help='Екстракција свих страна из PDF-а у SCV фајл')
    parser.add_argument('--mongodb-connection-string', default=None,
                        help='Екстракција свих страна из PDF-а у mongodb')

    args = parser.parse_args()
    if args.full_search_txt or args.full_search_csv or args.mongodb_connection_string:
        convertor = PdfDecoderForFile(os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf'))
        if args.full_search_txt:
            convertor.each(lambda entry: print(entry.txt), args.debug)
        if args.full_search_csv:
            print("headword\tdefinition\tpage")
            convertor.each(lambda entry: print(entry.txt('\t')), args.debug)
        if args.mongodb_connection_string:
            from pymongo import MongoClient

            client = MongoClient(args.mongodb_connection_string)
            db = client.matica
            collection = db.entries
            collection.drop()
            collection = db.create_collection(
                'entries',
                validator={
                    '$jsonSchema': {
                        'bsonType': 'object',
                        'required': ['headword', 'definition', 'page'],
                        'properties': {
                            'headword': {
                                'bsonType': 'string',
                                'description': 'must be a string and is required'
                            },
                            'definition': {
                                'bsonType': 'string',
                                'description': 'must be a string and is required'
                            },
                            'page': {
                                'bsonType': 'string',
                                'description': 'must be a int and is required'
                            }
                        }
                    }
                }
            )
            def process_entries(entry):
                # Insert into MongoDB collection
                collection.insert_one({
                    'headword': entry.headword,
                    'definition': entry.definition,
                    'page': str(entry.page_no)  # Ensure page_no is converted to a string
                })
            convertor.each(process_entries, args.debug)
        exit(0)

    matica_pdf = os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf')
    with pikepdf.open(matica_pdf) as pdf:
        prev_entries = []
        for n, page in enumerate(pdf.pages, start=1):
            # print(f"Page =========> {n}")
            if n < 302:
                continue
            if n > 302:
                break
            # if n> 20:
            #    break
            # if n < 21:
            #    continue
            # if n > 21:
            #    break
            if (page["/Resources"].get("/Font", None) is None):
                print(f"No fonts found in page resources for page: {n}")
                continue
            decoder = PdfDecoderForPage(page, n, fixes, typos)
            # decoder.debug_text()
            # decoder.convert_to_chunks()
            # print(''.join([(a.is_headword and "\n=>" or "") + a.text for a in decoder.convert_to_chunks()]))
            entries = decoder.convert_to_entries(prev_entries)
            print(''.join(["=>" + str(a) + "\n" for a in prev_entries]))
            prev_entries = entries
        print(''.join(["=>" + str(a) + "\n" for a in prev_entries]))
