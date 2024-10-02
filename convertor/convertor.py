import os
from typing import List

import pikepdf
import re

from decimal import Decimal
from uuid import uuid4

ENCODING_TYPE_1B = 1
ENCODING_TYPE_2B = 2
ENCODING_TYPE_MB = 0

PARAGRAPH_INTERVAL = 12
LINE_INTERVAL = 6

DEBUG_PDF = False


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


class NewLineDetector():
    def __init__(self):
        self.current_chunk = None
        self.is_new_line = False

    def set_chunk(self, chunk):
        if self.current_chunk is None:
            self.current_chunk = chunk
            self.is_new_line = False
            return
        # same line
        if self.current_chunk.y == chunk.y:
            self.current_chunk = chunk
            self.is_new_line = False
            return

        # TODO: self.current_chunk.x > chunk.x: ?
        # if chunk.text.startswith('.') or chunk.text.startswith(',') or chunk.text.startswith('~'):
        #    raise ValueError(f"Unexpected chunk: {chunk}")

        self.current_chunk = chunk
        self.is_new_line = True
        return


def is_se(text):
    if len(text) > 2 and (text[0] == 'c' or text[0] == 'с') and (text[1] == 'e' or text[1] == 'е') and (
            text[2] == ',' or text[2] == ' '):
        return True
    if len(text) == 2 and (text[0] == 'c' or text[0] == 'с') and (text[1] == 'e' or text[1] == 'е'):
        return True
    return False


def _concat_chunks_by_same_font(chunks):
    chunksx = []
    prev_chunk = None
    for chunk in chunks:
        if prev_chunk is None:
            prev_chunk = chunk.copy()
        elif prev_chunk.font == chunk.font and not is_se(chunk.text):
            prev_chunk.text += chunk.text
        else:
            chunksx.append(prev_chunk)
            prev_chunk = chunk.copy()
    if prev_chunk is not None:
        chunksx.append(prev_chunk)
    return chunksx


HYPHEN = chr(173)
cyrillic_letters = 'абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛМНОПРСТЋУФХЦЧЏШ'
lat_to_cyr = {
    'a': 'а',
    # 'b': 'б',
    'c': 'с',
    # 'd': 'д',
    'e': 'е',
    # 'f': 'ф',
    'g': 'д',
    'h': 'х',
    'i': 'и',
    'j': 'ј',
    'k': 'к',
    # 'l': 'л',
    'm': 'м',
    # 'n': 'н',
    'o': 'о',
    'p': 'р',
    # 'q': 'љ',
    # 'r': 'р',
    # 's': 'с',
    # 't': 'т',
    # 'u': 'у',
    # 'v': 'в',
    # 'w': 'ш',
    'x': 'х',
    # 'y': 'ћ',
    # 'z': 'з',
    'A': 'А',
    'B': 'В',
    'C': 'C',
    'D': 'Д',
    # 'E': 'Е',
    # 'F': 'Ф',
    # 'G': 'Г',
    'H': 'Н',
    # 'I': 'И',
    'J': 'Ј',
    'K': 'К',
    # 'L': 'Л',
    'M': 'М',
    # 'N': 'Н',
    'O': 'О',
    'P': 'Р',
    # 'Q': 'Љ',
    # 'R': 'Р',
    # 'S': 'С',
    'T': 'Т',
    # 'U': 'У',
    # 'V': 'В',
    # 'W': 'Ш',
    'X': 'Х',
    # 'Y': 'Ћ',
    # 'Z': 'З'
}


def _is_cyrillic(char):
    return char in cyrillic_letters


def has_cyrillic(text):
    return any(_is_cyrillic(char) for char in text)


def _word_lat_to_cyr(text):
    if not has_cyrillic(text):
        return text
    return ''.join(lat_to_cyr.get(char, char) for char in text)


class ChunksParagraph:
    def __init__(self, lines):
        self.lines = lines

    def headword_and_body(self):
        removed_hyphens = self._get_without_hyphens(self.lines)
        all_chunks = []
        for line in removed_hyphens:
            all_chunks += line
        concatenated = _concat_chunks_by_same_font(all_chunks)
        cyrillic_fixed = self._fix_cyrillic_i(concatenated)
        para_chunks = cyrillic_fixed

        # join all chunks and divide by space to get words
        para_words = ' '.join(chunk.text for chunk in para_chunks).split()

        # assume no headword
        headword = ''
        if len(para_words) == 0:
            return '', ' '.join(para_words).strip()

        # first word is headword
        headword = para_words[0]
        if headword.endswith(','):
            # comma is marker of end of headword
            # clean it up and return
            headword = headword[:-1]
            return headword, ' '.join(para_words[1:]).strip()

        # search for what can be added to headword
        para_words = para_words[1:]
        if len(para_words) == 0:
            print(f"Empty definition for headword: {headword} |{' '.join(para_words)}|", file=sys.stderr)
            raise ValueError(f"Empty definition for headword: {headword}")
            return headword, ' '.join(para_words).strip()

        # check for -ce
        first_word = para_words[0]
        if is_se(first_word):
            headword += ' се'
            # leave comma as the first chart of the next word
            para_words[0] = para_words[0][2:].strip()
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
                first_word = para_words[0]

        # if comma is first char in first word, clean it up and return
        if first_word.startswith(','):
            # headword ends with comma
            para_words[0] = para_words[0][1:]
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
            return headword, ' '.join(para_words).strip()

        # headword can continue with и
        if first_word.startswith('и ') or first_word == 'и':
            # skip it and take next word
            para_words[0] = para_words[0][1:].strip()
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
            first_word = para_words[0].strip()
            comma = False
            if first_word.endswith(','):
               comma = True
               first_word = first_word[:-1]

            if not (headword.strip() == first_word):
                headword += ' и ' + first_word
            # next can be comma or -се
            # if headword ends with comma, clean it up and return
            if comma:
                return headword, ' '.join(para_words[1:]).strip()

            if len(para_words) == 0:
                return headword, ' '.join(para_words[1:]).strip()

            para_words = para_words[1:]
            first_word = para_words[0]

            if is_se(first_word):
                headword += ' се'
                # leave comma as the first chart of the next word
                para_words[0] = para_words[0][2:]
                first_word = para_words[0].strip()
                if first_word == '' and len(para_words) > 0:
                    para_words = para_words[1:]
                    first_word = para_words[0]

            # if comma is first char (after -се) in first word, clean it up and return
            if first_word.startswith(','):
                # clean up leading comma
                para_words[0] = para_words[0][1:].split()
                if first_word == '' and len(para_words) > 0:
                    para_words = para_words[1:]
                return headword, ' '.join(para_words).strip()

        return headword, ' '.join(para_words).strip()

    def _get_without_hyphens(self, lines):
        linesx = []
        for line in lines:
            last_chunk = line[-1]
            if last_chunk.text.endswith(HYPHEN):
                chunkx = last_chunk.copy()
                chunkx.text = last_chunk.text[:-1]
                linesx.append(line[:-1] + [chunkx])
            else:
                linesx.append(line)
        return linesx

    @staticmethod
    def _fix_cyrillic_i(chunks):
        chunksx = []
        for i in range(len(chunks)):
            chunk = chunks[i].copy()
            chunk.text = _word_lat_to_cyr(chunk.text)
            chunksx.append(chunk)
        return chunksx


class IndentDetector():
    def __init__(self, lines_1, left_x_1, lines_2, left_x_2):
        self.max_between_lines = 0
        self.min_between_paragraphs = 1000
        self.max_space_non_indent = 0
        self.min_space_indent = 1000
        self._set_dims(lines_1, left_x_1)
        self._set_dims(lines_2, left_x_2)

    def _set_dims(self, lines, left):
        for i in range(1, len(lines)):
            chunk = lines[i][0]
            prev_chunk = lines[i - 1][0]
            # definitely new paragraph
            if chunk.x > left + 12:
                if self.min_between_paragraphs > prev_chunk.y - chunk.y:
                    self.min_between_paragraphs = prev_chunk.y - chunk.y
            # definitely new line
            elif chunk.x < left + 6:
                if self.max_between_lines < prev_chunk.y - chunk.y:
                    self.max_between_lines = prev_chunk.y - chunk.y
            # definitely new line
            if prev_chunk.y - chunk.y < 11.5:
                if self.max_space_non_indent < chunk.x - left:
                    self.max_space_non_indent = chunk.x - left
                if chunk.x - left > 12:
                    raise ValueError("xx")
            # definitely new paragraph
            if prev_chunk.y - chunk.y > 14:
                if self.min_space_indent > chunk.x - left:
                    self.min_space_indent = chunk.x - left


class ChunksPage:
    def __init__(self, chunks):
        self.chunks = chunks
        self.chunks_title = []
        self.chunks_page = []
        self.chunks_column_1 = []
        self.chunks_column_2 = []
        self.left_x_column_1 = 0
        self.left_x_column_2 = 0
        self.chunks_lines_1 = []
        self.chunks_lines_2 = []
        self.indented_lines_1 = {}
        self.indented_lines_2 = {}
        self.chunks_paragraphs: List[ChunksParagraph] = []

        self._set_title_and_page()
        self._set_columns()
        self._set_lines()
        self._set_paragraphs()

    def title(self):
        chunks = _concat_chunks_by_same_font(self.chunks_title)
        result = ' '.join(chunk.text.strip() for chunk in chunks)
        return result

    def _set_title_and_page(self):
        chunks = self.chunks
        i = 1
        while i < len(chunks) and abs(chunks[i].y - chunks[i - 1].y) < 3:
            i += 1
        self.chunks_title = chunks[:i]
        self.chunks_page = chunks[i:]

    def _set_columns(self):
        chunks = self.chunks_page

        i = 1
        # leap above current line more the 50 pixels
        while i < len(chunks) and (chunks[i - 1].y - chunks[i].y) >= 0:
            i += 1

        self.chunks_column_1 = chunks[:i]
        self.chunks_column_2 = chunks[i:]

        top, left = self._get_top_left(self.chunks_column_1)
        self.left_x_column_1 = float(left)
        top, left = self._get_top_left(self.chunks_column_2)
        self.left_x_column_2 = float(left)

    def _set_lines(self):
        self.chunks_lines_1 = self._get_lines(self.chunks_column_1)
        self.chunks_lines_2 = self._get_lines(self.chunks_column_2)
        indentDetector = IndentDetector(self.chunks_lines_1, self.left_x_column_1,
                                        self.chunks_lines_2, self.left_x_column_2)
        self.indented_lines_1 = self._get_indented_lines(indentDetector, self.chunks_lines_1, self.left_x_column_1)
        self.indented_lines_2 = self._get_indented_lines(indentDetector, self.chunks_lines_2, self.left_x_column_2)

    def _set_paragraphs(self):
        paragraphs1 = self._get_paragraphs_lines(self.chunks_lines_1, self.indented_lines_1)
        paragraphs2 = self._get_paragraphs_lines(self.chunks_lines_2, self.indented_lines_2)

        # A case there's only one column
        if len(paragraphs2) == 0:
            self.chunks_paragraphs = [ChunksParagraph(lines) for lines in paragraphs1]
            return

        # A case the first paragraph in the second column
        # is not a continuation of the last paragraph in the first column
        # TODO: check len
        if self.indented_lines_2.get(0, False):
            self.chunks_paragraphs = (
                    [ChunksParagraph(lines) for lines in paragraphs1] +
                    [ChunksParagraph(lines) for lines in paragraphs2])
            return

        # A case the first paragraph in the second column is a continuation of
        # the last paragraph in the first column
        self.chunks_paragraphs = (
                [ChunksParagraph(lines) for lines in paragraphs1[:-1]] +
                [ChunksParagraph(paragraphs1[-1] + paragraphs2[0])] +
                [ChunksParagraph(lines) for lines in paragraphs2[1:]]
        )

    @staticmethod
    def _get_lines(chunks):
        detector = NewLineDetector()
        i = 0
        lines = []
        line = []
        while i < len(chunks):
            detector.set_chunk(chunks[i])
            if detector.is_new_line:
                lines.append(line)
                line = []
            line.append(chunks[i])
            i += 1
        if len(line) > 0:
            lines.append(line)
        return lines

    @staticmethod
    def _get_indented_lines(indentDetector, lines, left_x):
        indented_lines = {}
        id = indentDetector
        middle_space = id.max_space_non_indent + (id.min_space_indent - id.max_space_non_indent) / 2
        middle_interval = id.max_between_lines + (id.min_between_paragraphs - id.max_between_lines) / 2
        for i in range(len(lines)):
            space = lines[i][0].x - left_x

            # ....................max_space_non_indent.........min_space_indent..................
            #  likely non indent |                    undefined                 |likely indent
            if space < middle_space:
                logit_non_indent = (middle_space - space) / middle_space
                logit_indent = 0
            else:
                logit_non_indent = 0
                logit_indent = (space - middle_space) / middle_space

            # ..................max_between_lines............min_between_paragraphs.....................
            #  likely new line |                  undefined                        |likely new paragraph

            if i == 0:
                logit_new_line = 0
                logit_paragraph = 0
            else:
                interval = lines[i - 1][0].y - lines[i][0].y
                if interval > middle_interval * 2:
                    interval = middle_interval * 2
                if interval <= middle_interval:
                    logit_new_line = (middle_interval - interval) / middle_interval
                    logit_paragraph = 0
                else:
                    logit_new_line = 0
                    logit_paragraph = (interval - middle_interval) / middle_interval

            weight_indent = 1
            weight_paragraph = 2

            non_indent = ((logit_non_indent * weight_indent) * (logit_non_indent * weight_indent) +
                          (logit_new_line * weight_paragraph) * (logit_new_line * weight_paragraph))

            indent = ((logit_indent * weight_indent) * (logit_indent * weight_indent) +
                      (logit_paragraph * weight_paragraph) * (logit_paragraph * weight_paragraph))

            if indent > non_indent:
                indented_lines[i] = True
            elif non_indent > indent:
                indented_lines[i] = False
            else:
                raise ValueError(f"Unexpected indent: {indent}")
        return indented_lines

    @staticmethod
    def _get_paragraphs_lines(chunks_lines, idents):
        paragraphs = []
        lines = []

        for i in range(len(chunks_lines)):
            line = chunks_lines[i]
            if len(lines) == 0:
                lines = [line]
                continue
            if idents.get(i, False):
                paragraphs.append(lines)
                lines = []
            lines.append(line)

        if len(lines) > 0:
            paragraphs.append(lines)

        return paragraphs

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
        dx = 1000
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
            if DEBUG_PDF:
                print(f'Operator: {operator}')

            if operator == pikepdf.Operator('BT'):
                intext = True
                font = None
                dx = 1000
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
                dx = operands[0]
                x += operands[0]
                y += operands[1]
                if DEBUG_PDF:
                    print(f"Td: dx={dx} x={operands[0]} y={operands[1]}")
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
                            lmbd(text, font_decoder, x, y, dx)
                        else:
                            print(f"Unexpected operand type: {type(operand)}")
                elif operator == pikepdf.Operator('TJ'):
                    for operand in operands:
                        if isinstance(operand, pikepdf.Array):
                            for element in operand:
                                if isinstance(element, pikepdf.String):
                                    text = element
                                    font_decoder = self.font_decoders[font]
                                    lmbd(text, font_decoder, x, y, dx)
                                elif isinstance(element, int):
                                    pass
                                elif isinstance(element, Decimal):
                                    pass
                                else:
                                    print(f"Unexpected element type: {type(element)}")
                        else:
                            print(f"Unexpected operand type: {type(operand)}")
                elif operator == pikepdf.Operator('Tm'):
                    if DEBUG_PDF:
                        print(
                            f"Tm: 0={operands[0]} 1={operands[1]} 2={operands[2]} 3={operands[3]} 4={operands[4]} 5={operands[5]}")
                    x0 = operands[4]
                    if abs(x0 - x) > -1:
                        # raise ValueError(f"Unexpected operator Tm {self.page_no} x {x} x0 {x0}")
                        x = x0
                        dx = 1000
                    y0 = operands[5]
                    if abs(y0 - y) > -1:
                        # raise ValueError(f"Unexpected operator Tm {self.page_no} y {y} y0 {y0}")
                        y = operands[5]

    @staticmethod
    def lmbd_debug(text, font_decoder, x, y, dx):
        unicode_text = font_decoder.to_unicode(text)
        print(f"Text: x={x} y={y} {text.__bytes__()} -> \"{unicode_text}\", Font: {font_decoder.name}")

    def debug_text(self):
        self._call_for_tj(self.lmbd_debug)

    def print_positions(self):
        chunks = []
        prev_y = 0  # assume there's top
        prev_x = 785  # assume there's no indent
        first = True

        def lmbd(text, font_decoder, x, y, dx):
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

    def convert_to_chunks_page(self):
        chunks = []

        def lmbd(text, font_decoder, x, y, dx):
            nonlocal chunks
            unicode_text = font_decoder.to_unicode(text)
            if DEBUG_PDF:
                print(f'Tj: x={x} y={y} "{unicode_text}"')
            chunks.append(Chunk(text, unicode_text, x, y, font_decoder.name, dx))

        self._call_for_tj(lmbd)

        chunks_page = ChunksPage(chunks)
        return chunks_page

    @staticmethod
    def _separate_headword_and_definition(para_chunks):
        # join all chunks and divide by space to get words
        para_words = ' '.join(chunk.text for chunk in para_chunks).split()
        # assume no headword
        headword = ''
        if len(para_words) == 0:
            return '', ' '.join(para_words).strip()

        # first word is headword
        headword = para_words[0]
        if headword.endswith(','):
            # comma is marker of end of headword
            # clean it up and return
            headword = headword[:-1]
            return headword, ' '.join(para_words[1:]).strip()

        # search for what can be added to headword
        para_words = para_words[1:]
        if len(para_words) == 0:
            print(f"Empty definition for headword: {headword} |{' '.join(para_words)}|", file=sys.stderr)
            raise ValueError(f"Empty definition for headword: {headword}")
            return headword, ' '.join(para_words).strip()
        # check for -ce
        first_word = para_words[0]
        if PdfDecoderForPage.is_se(first_word):
            headword += ' се'
            # leave comma as the first chart of the next word
            para_words[0] = para_words[0][2:].strip()
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
                first_word = para_words[0]

        # if comma is first char in first word, clean it up and return
        if first_word.startswith(','):
            # headword ends with comma
            para_words[0] = para_words[0][1:]
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
            return headword, ' '.join(para_words).strip()

        # headword can continue with и
        if first_word.startswith('и ') or first_word == 'и':
            # skip it and take next word
            para_words[0] = para_words[0][1:].strip()
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
            first_word = para_words[0]
            if not (headword.strip() == first_word.strip()):
                headword += ' и ' + first_word
            # next can be comma or -се
            # if headword ends with comma, clean it up and return
            if headword.endswith(','):
                headword = headword[:-1]
                return headword, ' '.join(para_words[1:]).strip()

            if len(para_words) == 0:
                return headword, ' '.join(para_words[1:]).strip()

            para_words = para_words[1:]
            first_word = para_words[0]

            if PdfDecoderForPage.is_se(first_word):
                headword += ' се'
                # leave comma as the first chart of the next word
                para_words[0] = para_words[0][2:]
                first_word = para_words[0].strip()
                if first_word == '' and len(para_words) > 0:
                    para_words = para_words[1:]
                    first_word = para_words[0]

            # if comma is first char (after -се) in first word, clean it up and return
            if first_word.startswith(','):
                # clean up leading comma
                para_words[0] = para_words[0][1:].split()
                if first_word == '' and len(para_words) > 0:
                    para_words = para_words[1:]
                return headword, ' '.join(para_words).strip()

        return headword, ' '.join(para_words).strip()

    @staticmethod
    def _chunks_to_entries(chunks, page_no):
        top, left = PdfDecoderForPage._get_top_left(chunks)
        first = True
        p = 0
        entries = []
        while p < len(chunks):
            p1 = PdfDecoderForPage._next_para_pos_by_interval(p, chunks, left)
            para_chunks = PdfDecoderForPage._remove_hyphens(chunks[p:p1])
            para_chunks = PdfDecoderForPage._concat_chunks_by_same_font(para_chunks)
            para_chunks = PdfDecoderForPage._fix_cyrillic_i(para_chunks)
            if first:
                first = False
                if chunks[p].x - left < 2:
                    headword = ''
                    definition = ' '.join(''.join(chunk.text for chunk in para_chunks).split())
                    entries.append(Entry(headword, definition, page_no))
                    break

            headword, definition = PdfDecoderForPage._separate_headword_and_definition(para_chunks)

            entries.append(Entry(headword, definition, page_no))
            p = p1
        return entries

    @staticmethod
    def _paragraph_to_entry(paragraph):
        print(paragraph)

    @staticmethod
    def _concatenate_entries(entries1, entries2):
        if entries2[0].headword is None or entries2[0].headword == "":
            entries1[-1].definition += entries2[0].definition
            entries2 = entries2[1:]
        return entries1 + entries2

    # prev_entries is used to concatenate entries from the previous page
    # if the first entry on the current page is a continuation of the last entry on the previous page
    def convert_to_entries(self, prev_entries):
        chunks_page = self.convert_to_chunks_page()
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
    def __init__(self, cids, text, x, y, font, dx):
        self.cids = cids
        self.text = text
        self.x = float(x)
        self.y = float(y)
        self.font = font
        self.dx = float(dx)

    def __str__(self):
        return f'"{self.text}" x: {self.x} y: {self.y} font: {self.font} dx: {self.dx} cids: {self.cids}'

    def __repr__(self):
        return f'Chunk({self.cids.__bytes__()}, "{self.text}", {self.x}, {self.y}, {self.font}, {self.dx})'

    def copy(self):
        return Chunk(self.cids, self.text, self.x, self.y, self.font, self.dx)


class Entry:
    def __init__(self, headword, definition, page_no):
        self.headword = headword.strip()
        self.definition = definition.strip()
        self.page_no = page_no

    def __str__(self):
        return f'/{self.headword}/({self.page_no})\n{self.definition}'

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
                    if entry.headword:
                        lmbda(entry)
                    else:
                        raise ValueError(f"Entry without headword: {entry}")


def bytes2cid(b):
    return b[0] << 8 | b[1]


fixes = {
    '/C0_0': {
        bytes2cid(b'\x00b'): '~',
        bytes2cid(b'\x00['): 'а',
        bytes2cid(b'\x00e'): '~',
        # bytes2cid(b'\x00\x0b'): '~', breaks p23. ајурведски -а, -о који се односи на ајурведу: медицина.
        bytes2cid(b'\x00\r'): '~',
        bytes2cid(b'\x00\x13'): '~',
        bytes2cid(b'\x00\xb8'): 'и',
        bytes2cid(b'\x00\xd0'): 'и',
        bytes2cid(b'\x01\xb5'): 'л',
    },
    '/C0_1': {
        bytes2cid(b'\x00"'): 'ш',
        bytes2cid(b'\x00|'): 'с',
        # bytes2cid(b'\x08<'): 'к',!!!
        bytes2cid(b'\x00f'): 'и',
        bytes2cid(b'\x00h'): 'к',
        bytes2cid(b'\x00r'): 'к',
        bytes2cid(b'\x00t'): 'е',
        bytes2cid(b'\x01j'): 'ц',
        bytes2cid(b'\x02+'): 'и',
        bytes2cid(b'\x04l'): 'д',
        bytes2cid(b'\x00\x7f'): 'д',
        bytes2cid(b'\x00\x83'): 'н',
        bytes2cid(b'\x00\x8f'): 'и',
        bytes2cid(b'\x00\x95'): 'о',
        bytes2cid(b'\x00\x9e'): 'т',
        bytes2cid(b'\x00\x0c'): 'д',
        bytes2cid(b'\x00\xa2'): '~',
        bytes2cid(b'\x00\xac'): 'л',
        bytes2cid(b'\x00\xb9'): 'д',
        bytes2cid(b'\x00\xd5'): 'и',
        bytes2cid(b'\x00\xfa'): 'ч',
        bytes2cid(b'\x01\x02'): 'у',
        bytes2cid(b'\x01\x07'): 'б',
        bytes2cid(b'\x02\xa8'): 'лингв',
        bytes2cid(b'\x02\x9f'): 'к',
        bytes2cid(b'\x03\x86'): '.',
        bytes2cid(b'\x04\x16'): 'и',
        bytes2cid(b'\x04\x85'): 'и',
        bytes2cid(b'\x04\xbe'): 'ак',
        bytes2cid(b'\x04\xbf'): 'и',
    },
    '/C0_2': {
        bytes2cid(b'\x00|'): 'с',
        bytes2cid(b'\x00.'): 'мн',
        bytes2cid(b'\x00F'): 'е',
        bytes2cid(b'\x00t'): 'е',
        bytes2cid(b'\x01l'): 'д',
        bytes2cid(b'\x01Z'): 'и',
        bytes2cid(b'\x00\x01'): 'а',
        bytes2cid(b'\x00\x19'): 'ј',
        bytes2cid(b'\x00\xa9'): 'р',
        bytes2cid(b'\x00\xb3'): 'к',
        bytes2cid(b'\x00\xbe'): 'в',
        bytes2cid(b'\x01\x02'): 'у',

        # bytes2cid(b'\x00\x07'): '?',
    },
    '/C0_3': {
        bytes2cid(b'\nP'): 'с',
        bytes2cid(b'\no'): 'у',
        bytes2cid(b'\rh'): 'п',
        bytes2cid(b'\n+'): 'о',
        bytes2cid(b'\n\x14'): 'н',
        bytes2cid(b'\n\xa4'): 'т',
        bytes2cid(b'\n\xcb'): 'а',
        bytes2cid(b'\t\xd7'): 'п',
        bytes2cid(b'\x000'): 'п',
        bytes2cid(b'\x00V'): 'п',
        bytes2cid(b'\x01d'): '1',
        bytes2cid(b'\x04l'): 'н',
        bytes2cid(b'\x05m'): 'ал',
        # bytes2cid(b'\x08^'): 'лингв', broken
        bytes2cid(b'\x08^'): 'и',  # p21, ајурведски ... односи,
        bytes2cid(b'\x0cP'): 'с',
        bytes2cid(b'\x0f-'): 'р',
        # bytes2cid(b'\x00\t'): 'с', #!!!
        bytes2cid(b'\x00\r'): 'ен',
        # bytes2cid(b'\x00\t'): 'в, #p21 агресивност, -ости
        bytes2cid(b'\x00\x08'): 'т',
        bytes2cid(b'\x00\x0c'): 'д',
        # bytes2cid(b'\x00\x16'): 'т', # 'з', /адмирал/(21) ...  2. тоол. врста
        bytes2cid(b'\x00\xff'): 'љ',
        bytes2cid(b'\x02\x13'): '',
        bytes2cid(b'\x04\xa4'): 'к',
        bytes2cid(b'\x06\x10'): 'д',
        # bytes2cid(b'\x0f\x83'): 'ј',
        bytes2cid(b'\x10\xcf'): 'е',
        bytes2cid(b'\x10\xd1'): 'т',
        bytes2cid(b'\x12G'): 'в',
        # bytes2cid(b'\x0c\xf4'): 'ни',
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
        bytes2cid(b'\x00;'): 'г',
        bytes2cid(b'\x00:'): 'г',
        bytes2cid(b'\x00y'): '~',
        bytes2cid(b'\x01_'): 'к',
        bytes2cid(b'\x02&'): '.',
        bytes2cid(b'\x04j'): 'н',
        bytes2cid(b'\x04l'): 'н',
        bytes2cid(b'\x03O'): 'к',
        bytes2cid(b'\x04U'): 'с',
        bytes2cid(b'\x05I'): 'а',
        bytes2cid(b'\x05o'): 'ам',
        bytes2cid(b'\x07?'): 'г',
        # bytes2cid(b'\x00\x01'): '', #p21 агресивност, -ости {ж}
        bytes2cid(b'\x00\x12'): '~',
        bytes2cid(b'\x00\x17'): 'г',
        bytes2cid(b'\x04\xb1'): 'м',
        bytes2cid(b'\x04\xe9'): 'и',
        bytes2cid(b'\x04\xa4'): 'к',
        bytes2cid(b'\x04\xc0'): 'о',
        bytes2cid(b'\x05\xb7'): 'в',
        bytes2cid(b'\x05\xf1'): 'гл',
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
        bytes2cid(b'\nF'): 'р',
        bytes2cid(b'\nP'): 'с',
        bytes2cid(b'\n\xa4'): 'т',
        bytes2cid(b'\t\x88'): 'љ',
        bytes2cid(b'\t\xd7'): 'п',
        bytes2cid(b'\x00y'): '~',
        bytes2cid(b'\x00\x9e'): '~',

        # bytes2cid(b'\n\x9e'): 'н', #useless
        bytes2cid(b'\x03`'): 'н',
        bytes2cid(b'\x004`'): 'г',
        bytes2cid(b'\x10\xd1`'): 'т',
        bytes2cid(b'\x03)'): 'о',
        bytes2cid(b'\x03\xd1'): ':',

        bytes2cid(b'\x08\xe6'): 'имљ',  # p20 /агресивност/(20)
        # bytes2cid(b'\x0c\xf4'): 'и', #p20 /агресивност/(20)
        # bytes2cid(b'\x0b\xe4'): 'љ',
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
    # '/C0_4': mongodb://localhost:27017/{
    #    'cамoгаcник ': 'самогласник ',
    # }
}


class Th:
    def __init__(self, pos, expected):
        self.pos = pos
        self.expected = expected


def test_page_chunks(page_no, expected_title, expected_paragraphs, headwords):
    print("Testing page", page_no)
    with pikepdf.open(os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf')) as pdf:
        page = pdf.pages[page_no]
        decoder = PdfDecoderForPage(page, page_no)
        chunks_page = decoder.convert_to_chunks_page()

        print("Title exists:", end=" ")
        if len(chunks_page.chunks_title) > 0:
            print("PASSED")
        else:
            print("FAILED")

        print("Expected title:", expected_title, end=" ")
        title_foo = chunks_page.title()
        title = chunks_page.title()
        if title == expected_title:
            print("PASSED")
        else:
            print("FAILED. Actual title:", title)

        print("Number of paragraphs:", end=" ")
        if len(chunks_page.chunks_paragraphs) == expected_paragraphs:
            print("PASSED")
        else:
            print(f"FAILED. Expected: {expected_paragraphs} Actual: ", len(chunks_page.chunks_paragraphs))

        for test in headwords:
            i = test.pos
            headword = test.expected
            print(f"Headword {i}:", end=" ")
            headword1, _ = chunks_page.chunks_paragraphs[i].headword_and_body()
            if headword1 == headword:
                print(f"PASSED {headword1}")
            else:
                print(f'FAILED. Expected: "{headword}" Actual: "{headword1}"')


if __name__ == '__main__':
    import argparse
    import sys
    import time

    parser = argparse.ArgumentParser(description='Парсер за Матицу Српску')

    parser.add_argument('--debug', action='store_true',
                        help='Приказивање дебаг информација')
    parser.add_argument('--positions', action='store_true',
                        help='Приказивање позиција у PDF-у')
    parser.add_argument('--full-search-txt', action='store_true',
                        help='Екстракција свих страна из PDF-а у текстуални фајл')
    parser.add_argument('--full-search-csv', action='store_true',
                        help='Екстракција свих страна из PDF-а у SCV фајл')
    parser.add_argument('--full-search-json', action='store_true',
                        help='Екстракција свих страна из PDF-а у JSON фајл')
    parser.add_argument('--mongodb-connection-string', default=None,
                        help='Екстракција свих страна из PDF-а у mongodb')
    parser.add_argument('--firebase-service-account-key-json', default=None,
                        help='Екстракција свих страна из PDF-а у firebase real-time database')

    args = parser.parse_args()

    convertor = PdfDecoderForFile(os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf'))

    if args.full_search_txt:
        convertor.each(lambda entry: print(entry.txt), args.debug)
        exit(0)

    if args.positions:
        print('Not implemented')
        exit(1)

    if args.full_search_csv:
        print("headword\tdefinition\tpage")
        convertor.each(lambda entry: print(entry.txt('\t')), args.debug)
        exit(0)

    if args.full_search_json:
        global json_key
        json_key = 0


        def process_entries_json(entry):
            global json_key
            if json_key > 0:
                print(",")
            print(
                f'   "{json_key}": {{"headword": "{entry.headword.replace('"', '\\"')}", "definition": "{entry.definition.replace('"', '\\"')}", "page": {entry.page_no}}}',
                end="")
            json_key += 1


        print("{")
        convertor.each(process_entries_json, args.debug)
        print("}")
        exit(0)

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


        def process_entries_mongodb(entry):
            # Insert into MongoDB collection
            collection.insert_one({
                'headword': entry.headword,
                'definition': entry.definition,
                'page': str(entry.page_no)  # Ensure page_no is converted to a string
            })


        convertor.each(process_entries_mongodb, args.debug)
        exit(0)

    if args.firebase_service_account_key_json:
        import firebase_admin
        from firebase_admin import credentials
        from firebase_admin import db

        credentials = credentials.Certificate(args.firebase_service_account_key_json)
        firebase_admin.initialize_app(credentials, {
            'databaseURL': 'https://matica-srpska-sy4-default-rtdb.europe-west1.firebasedatabase.app'
        })

        entries_ref = db.reference('entries')
        # search by headword is not good idea, because they are not unique
        entries_ref.delete()


        def process_entries_rtdb(entry):
            # start_time = time.time()
            # snapshot = entries_ref.order_by_child('headword').equal_to(entry.headword).get()
            # end_time = time.time()
            # execution_time = end_time - start_time
            # print(f"Execution time equal_to({entry.headword}): {execution_time} seconds")
            # entries = list(snapshot.items())
            # if len(entries) > 0:
            #    print(f"Duplicate headword: {entry.headword}")
            # key, _ = entries[0]
            # start_time = time.time()
            key = uuid4().hex
            ref = entries_ref.child(key)
            # else:
            # ref = entries_ref.push()
            ref.set(
                {'headword': entry.headword, 'definition': entry.definition, 'page': entry.page_no})
            # end_time = time.time()
            # execution_time = end_time - start_time
            # print(f"Execution time ref.set ({entry.headword}): {execution_time} seconds")


        convertor.each(process_entries_rtdb(), args.debug)
        exit(0)

    test_para = [
        Th(0, "аерорели"),
        Th(20, "азбестни"),
        Th(33, "азил"),
        Th(34, "азилант"),
        Th(35, "азилантски"),
        Th(36, "азимут"),
        Th(37, "азимутни"),
        Th(38, "азоик"),
        Th(39, "азојски"),
        Th(44, "азур"),
        Th(45, "азуран"),
        Th(46, "азурно"),
        Th(47, "аикИдо"),
        Th(50, "аја"),
        Th(67, "ајурведа"),
    ]
    test_page_chunks(21, '20 АЕРОРЕЛИ -АЈУРВЕДА', 68, test_para)
    test_para = [
        Th(0, "анархо-"),
        Th(1, "анархолиберал"),
        Th(10, "анатемнйк и анатемњак"),
        Th(27, "ангажовати"),
        Th(28, "ангелика"),
        Th(56, "англофопски"),
    ]
    # test_page_chunks(33, '32 АНАРХО--АНГЛОФОПСКИ', 57, test_para)

#    matica_pdf = os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf')
#    with pikepdf.open(matica_pdf) as pdf:
#        prev_entries = []
#        for n, page in enumerate(pdf.pages, start=1):
#            # print(f"Page =========> {n}")
#            if n < 33:
#                continue
#            if n > 33:
#                break
#            # if n> 20:
#            #    break
#            # if n < 21:
#            #    continue
#            # if n > 21:
#            #    break
#            if (page["/Resources"].get("/Font", None) is None):
#                print(f"No fonts found in page resources for page: {n}")
#                continue
#            decoder = PdfDecoderForPage(page, n, fixes, typos)
#            decoder.debug_text()
#            decoder.convert_to_chunks()
#            # print(''.join([(a.is_headword and "\n=>" or "") + a.text for a in decoder.convert_to_chunks()]))
#
#            #entries = decoder.convert_to_entries(prev_entries)
#            # print(''.join(["=>" + str(a) + "\n" for a in prev_entries]))
#            prev_entries = entries
#        #print(''.join(["=>" + str(a) + "\n" for a in prev_entries]))
