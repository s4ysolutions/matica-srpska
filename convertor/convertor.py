import json
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
DEBUG_INDENT = False
DEBUG_LINES = False
DEBUG_GLITCHES = False

debug_progress = False


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


BREAK = False


class NewLineDetector:
    def __init__(self):
        self.current_chunk = None
        self.is_new_line = False

    def set_chunk(self, chunk):
        global BREAK
        if BREAK:
            print()
        if self.current_chunk is None:
            self.current_chunk = chunk
            self.is_new_line = False
            return
        # same line
        if abs(self.current_chunk.y - chunk.y) < 1:
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


def is_se_brackets(text):
    if len(text) >= 4 and text[0] == '(' and text[3] == ')':
        return is_se(text[1:3])

    return False


def _concat_chunks_by_same_font(chunks):
    chunksx = []
    prev_chunk = None
    for chunk in chunks:
        if chunk == 'indent':  # hack, assuming this never will be called in the context requiring indent
            continue
        if prev_chunk is None:
            prev_chunk = chunk.copy()
        elif prev_chunk.font == chunk.font and not (is_se(chunk.text) or is_se_brackets(chunk.text)):
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


def fix_cyrillic(text):
    return _word_lat_to_cyr(text)


class ChunksParagraph:
    def __init__(self, lines):
        if lines[0] == 'indented':
            self.indented = True
            self.lines = lines[1:]
        else:
            self.indented = False
            self.lines = lines

    def headword_and_body(self, page_no=None, para_no=None):
        # removes spaces before comma and dot
        pattern = r'\s+([.,.])'

        def r(para_words):
            body = ' '.join(para_words).strip()
            body = body.strip()
            body = re.sub(pattern, r'\1', body)
            return body

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
        if len(para_words) == 0:
            raise ValueError("Empty definition")
            return '', ''

        if not self.indented:
            return '', r(para_words)

        # first word is headword
        headword = para_words[0]
        if headword.endswith(','):
            # comma is marker of end of headword
            # clean it up and return
            headword = headword[:-1]
            return headword, r(para_words[1:])

        # search for what can be added to headword
        para_words = para_words[1:]
        if len(para_words) == 0:
            print(f"Empty definition for headword: {headword} |{' '.join(para_words)}|", file=sys.stderr)
            print("Lines:", file=sys.stderr)
            for line in self.lines:
                print(f"Line: {line}", file=sys.stderr)
            raise ValueError(
                f"Empty definition for headword: {headword}/{self.lines[0].cids.__bytes__()} on page {page_no} in para {para_no}")
            return headword, r(para_words)

        # check for -ce
        first_word = para_words[0]
        if is_se(first_word):
            headword += ' се'
            # leave comma as the first chart of the next word
            para_words[0] = para_words[0][2:].strip()
        elif is_se_brackets(first_word):
            headword += ' (се)'
            # leave comma as the first chart of the next word
            para_words[0] = para_words[0][4:].strip()
        # TODO: inconsistent with the -se after и
        if para_words[0] == '' and len(para_words) > 0:
            para_words = para_words[1:]
            first_word = para_words[0]

        # if comma is first char in first word, clean it up and return
        if first_word.startswith(','):
            # headword ends with comma
            para_words[0] = para_words[0][1:]
            if para_words[0] == '' and len(para_words) > 0:
                para_words = para_words[1:]
            return headword, r(para_words)

        # headword can continue with и
        if len(headword) > 0 and first_word.startswith('и ') or first_word == 'и':
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
                return headword, r(para_words[1:])

            if len(para_words) == 0:
                return headword, r(para_words[1:])

            para_words = para_words[1:]
            if len(para_words) == 0:
                raise ValueError("No definition")
            first_word = para_words[0]

            if is_se(first_word):
                headword += ' се'
                # leave comma as the first chart of the next word
                para_words[0] = para_words[0][2:]
                first_word = para_words[0].strip()
            if is_se_brackets(first_word):
                headword += ' (се)'
                # leave comma as the first chart of the next word
                para_words[0] = para_words[0][4:]
            # inconsistent with the -se after single word
            first_word = para_words[0].strip()
            if first_word == '' and len(para_words) > 0:
                para_words = para_words[1:]
                first_word = para_words[0]

            # if comma is first char (after -се) in first word, clean it up and return
            if first_word.startswith(','):
                # clean up leading comma
                para_words[0] = para_words[0][1:].strip()
                if first_word == '' and len(para_words) > 0:
                    para_words = para_words[1:]
                return headword, r(para_words)

        return headword, r(para_words)

    @staticmethod
    def _get_without_hyphens(lines):
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


class IndentDetector:
    def __init__(self, lines_1, left_x_1, lines_2, left_x_2):
        self.max_between_lines = 0
        self.min_between_paragraphs = 1000
        self.max_space_non_indent = 0
        self.min_space_indent = 1000
        if DEBUG_INDENT:
            print(f"set dim column 1:", file=sys.stderr)
        self._set_dims(lines_1, left_x_1)
        if DEBUG_INDENT:
            print(f"set dim column 2:", file=sys.stderr)
        self._set_dims(lines_2, left_x_2)
        if self.min_space_indent == 1000:
            raise ValueError('Cannot evaluate min_space_indent')
        if self.max_space_non_indent == 0:
            raise ValueError('Cannot evaluate max_space_non_indent')

    def _set_dims(self, lines, left):
        non_ident = 6
        indent = 12
        indent_hard_mark = 8
        newline = 10
        para = 12
        interval_hard_mark = 11

        _min_space_indent = 1000
        _max_space_non_indent = 0
        _min_between_paragraphs = 1000
        _max_between_lines = 0

        while _min_space_indent == 1000 or _max_space_non_indent == 0:
            if DEBUG_INDENT:
                print(f"traversing lines from 1 to {len(lines)}",
                      file=sys.stderr)
            for i in range(1, len(lines)):
                chunk = lines[i][0]
                prev_chunk = lines[i - 1][0]
                if DEBUG_INDENT:
                    print(f"comparing line {i}: {prev_chunk.text}/{chunk.text}",
                          file=sys.stderr)
                # first take a look at the indent and make a guess about the line interval
                dx = chunk.x - left
                if DEBUG_INDENT:
                    print(f"indent space={dx} evaluate intervals between lines/paragraphs", file=sys.stderr)
                if dx > indent:
                    # definitely new paragraph based on big indent
                    # can assume interval between paragraphs
                    dy = prev_chunk.y - chunk.y
                    if _min_between_paragraphs > dy:
                        if dy < interval_hard_mark:
                            if DEBUG_INDENT:
                                print(
                                    f"min_between_paragraphs less than {interval_hard_mark} ({dy}) in line {i}: {prev_chunk.text}/{chunk.text}, ignored",
                                    file=sys.stderr)
                        else:
                            if DEBUG_INDENT:
                                print(f"set min_between_paragraphs to {dy}", file=sys.stderr)
                            _min_between_paragraphs = dy
                elif dx < non_ident:
                    # definitely new line based on small indent
                    # can assume interval between lines
                    dy = prev_chunk.y - chunk.y
                    if _max_between_lines < dy:
                        if dy > interval_hard_mark:
                            if DEBUG_INDENT:
                                print(
                                    f"max_between_lines more than {interval_hard_mark} ({dy}) in line {i}: {prev_chunk.text}/{chunk.text}, ignored",
                                    file=sys.stderr)
                        else:
                            if DEBUG_INDENT:
                                print(f"set max_between_lines to {dy}", file=sys.stderr)
                            _max_between_lines = dy
                else:
                    if DEBUG_INDENT:
                        print(f"undefined indent space {dx} in line {i}: {prev_chunk.text}/{chunk.text}",
                              file=sys.stderr)

                # now take a look at the space between lines and make a guess about the indent

                dy = prev_chunk.y - chunk.y
                if DEBUG_INDENT:
                    print(f"line interval={dy} evaluate indent space", file=sys.stderr)
                if dy > para:
                    # definitely new paragraph
                    # can assume indent
                    dx = chunk.x - left
                    if DEBUG_INDENT:
                        print(
                            f"try to set min_space_indent to {dx}(current = {_min_space_indent}) due to interval {dy} > threshold {para}",
                            file=sys.stderr)
                    if _min_space_indent > dx:
                        if dx < indent_hard_mark:
                            if DEBUG_INDENT:
                                print(
                                    f"min_space_indent less than {indent_hard_mark} ({dx}) while line interval is big ({dy}) in line {i}: {prev_chunk.text}/{chunk.text}, ignored",
                                    file=sys.stderr)
                        else:
                            if DEBUG_INDENT:
                                print(f"set min_space_indent to {dx}", file=sys.stderr)
                            _min_space_indent = dx
                elif dy < newline:
                    # definitely new line, can assume non indent
                    if abs(dy) > 4:  # ignore noise
                        dx = chunk.x - left
                        if DEBUG_INDENT:
                            print(
                                f"try to set max_space_non_indent to {dx}(current = {_max_space_non_indent}) due to interval {dy} < threshold {newline}",
                                file=sys.stderr)
                        if _max_space_non_indent < dx:
                            if dx > indent_hard_mark:
                                if DEBUG_INDENT:
                                    print(
                                        f"max_space_non_indent more than {indent_hard_mark} ({dx}) while line interval is small ({prev_chunk.y - chunk.y}) in line {i}: {prev_chunk.text}/{chunk.text}, ignored",
                                        file=sys.stderr)
                            else:
                                if DEBUG_INDENT:
                                    print(f"set max_space_non_indent to {dx}", file=sys.stderr)
                                _max_space_non_indent = dx
                else:
                    if DEBUG_INDENT:
                        print(f"undefined interval {dy} in line {i}: {prev_chunk.text}/{chunk.text}", file=sys.stderr)
            # indent was not set due para threshold was set too high
            # let's try to lower it
            if _min_space_indent == 1000:
                para -= 0.1
                if para < interval_hard_mark:
                    break
                else:
                    if DEBUG_INDENT:
                        print(f"para threshold set to {para}", file=sys.stderr)
            # non_indent was not set due newline threshold was set too low
            if _max_space_non_indent == 0:
                newline += 0.1
                if newline > interval_hard_mark:
                    break
                else:
                    if DEBUG_INDENT:
                        print(f"newline threshold set to {newline}", file=sys.stderr)

        if _min_space_indent < self.min_space_indent:
            self.min_space_indent = _min_space_indent
        if _max_space_non_indent > self.max_space_non_indent:
            self.max_space_non_indent = _max_space_non_indent
        if _min_between_paragraphs < self.min_between_paragraphs:
            self.min_between_paragraphs = _min_between_paragraphs
        if _max_between_lines > self.max_between_lines:
            self.max_between_lines = _max_between_lines


class ChunksPage:
    def __init__(self, chunks):
        if DEBUG_GLITCHES:
            print('before remove leading glitches', file=sys.stderr)
            print(chunks[0], file=sys.stderr)
            print(chunks[1], file=sys.stderr)
            print(chunks[2], file=sys.stderr)
        chunks = ChunksPage.remove_leading_glitches(chunks)
        if DEBUG_GLITCHES:
            print('after remove leading glitches', file=sys.stderr)
            print(chunks[0], file=sys.stderr)
            print(chunks[1], file=sys.stderr)
            print(chunks[2], file=sys.stderr)
        i = 0
        # clean garbage from the beginning
        if DEBUG_INDENT:
            print(f"clean chunk[{i}]: {chunks[i].text}", file=sys.stderr)
        while i < len(chunks) and chunks[i].text == 'I ' or chunks[i].text == 'а ':
            i += 1
            if DEBUG_INDENT:
                print(f"clean chunk[{i}]: {chunks[i].text}", file=sys.stderr)
        chunks = chunks[i:]

        self.chunks = chunks
        self.chunks_title = []
        self.chunks_page = []
        self.chunks_lines = []
        self.chunks_lines_1 = []
        self.chunks_lines_2 = []
        self.left_x_column_1 = 0
        self.left_x_column_2 = 0
        self.indented_lines_1 = {}
        self.indented_lines_2 = {}
        self.chunks_paragraphs: List[ChunksParagraph] = []

        self._set_title_and_page()
        self._set_lines()
        self._set_columns()
        self._set_idented_lines()
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
        if DEBUG_LINES:
            print(f"chunks_page: {len(self.chunks_page)}", file=sys.stderr)
            for i in range(min(30, len(self.chunks_page))):
                print(f"chunk[{i}]: {str(self.chunks_page[i])}", file=sys.stderr)
            for i in range(max(0, len(self.chunks_page) - 30), len(self.chunks_page)):
                print(f"chunk[{i}]: {str(self.chunks_page[i])}", file=sys.stderr)

    def _set_lines(self):
        self.chunks_lines = self._get_lines(self.chunks_page)

    def _set_columns(self):
        if len(self.chunks_lines) == 0:
            return
        left_xs = [self.chunks_lines[0][0].x, 1000]
        columns = [[self.chunks_lines[0]], []]
        current_column = 0
        for i in range(1, len(self.chunks_lines)):
            line = self.chunks_lines[i]
            chunk = line[0]
            prev_line = self.chunks_lines[i - 1]
            prev_chunk = prev_line[0]
            if current_column == 0:
                # detect second column as leap above current line more than some amount of pixels
                dy = chunk.y - prev_chunk.y
                if dy > 30:  # leap above current line more the 50 pixels, assume new column
                    current_column = 1
                elif dy < -30:  # leap below current line more the 50 pixels, assume new column
                    # assume second column always above the first one
                    raise ValueError(f"Unexpected column: {current_column}")
            else:
                assert len(left_xs) == 2
                # detect first column as leap to the left more than some amount of pixels
                if chunk.x < left_xs[1] - 100:
                    current_column = 0
            # move left_x to the left if needed
            if chunk.x < left_xs[current_column]:
                left_xs[current_column] = chunk.x
            # add line to the existing column
            columns[current_column].append(line)

        self.left_x_column_1 = left_xs[0]
        self.left_x_column_2 = left_xs[1]
        self.chunks_lines_1 = columns[0]
        self.chunks_lines_2 = columns[1]

    def _set_idented_lines(self):
        if DEBUG_INDENT:
            print(f"chunks_lines_1: {len(self.chunks_lines_1)}", file=sys.stderr)
            print(f"chunks_lines_2: {len(self.chunks_lines_2)}", file=sys.stderr)
        indentDetector = IndentDetector(self.chunks_lines_1, self.left_x_column_1,
                                        self.chunks_lines_2, self.left_x_column_2)
        if DEBUG_INDENT:
            print(f"indentDetector for page:", file=sys.stderr)
            print(f"  .max_space_non_indent={indentDetector.max_space_non_indent}", file=sys.stderr)
            print(f"  .min_space_indent={indentDetector.min_space_indent}", file=sys.stderr)
            print(f"  .max_between_lines={indentDetector.max_between_lines}", file=sys.stderr)
            print(f"  .min_between_paragraphs={indentDetector.min_between_paragraphs}", file=sys.stderr)
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
    def remove_leading_glitches(chunks):
        while len(chunks) > 0 and chunks[0].has_leading_glitches():
            cleaned_chunk = chunks[0].copy_without_first_2bytes()
            if cleaned_chunk.is_empty():
                chunks = chunks[1:]
            else:
                chunks = [cleaned_chunk] + chunks[1:]
        return chunks

    @staticmethod
    def _get_lines(chunks):
        detector = NewLineDetector()
        i = 0
        lines = []
        line = []
        while i < len(chunks):
            chunk = chunks[i]
            detector.set_chunk(chunk)
            if detector.is_new_line:
                line = ChunksPage.remove_leading_glitches(line)
                if len(line) == 0:
                    i += 1
                    continue
                lines.append(line)
                line = []
            line.append(chunk)
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
            chunk = lines[i][0]
            space = chunk.x - left_x

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
                if idents.get(i, False):
                    lines = ['indented', line]
                else:
                    lines = [line]
                continue
            if idents.get(i, False):
                if ChunksPage.no_osr_glitch_line(lines):
                    paragraphs.append(lines)
                lines = ['indented']
            lines.append(line)

        if len(lines) > 0:
            if ChunksPage.no_osr_glitch_line(lines):
                paragraphs.append(lines)

        return paragraphs

    @staticmethod
    def no_osr_glitch_line(lines):
        if len(lines) == 0:
            return True
        elif len(lines) == 1:
            test = lines
        elif len(lines) == 2 and lines[0] == 'indented':
            test = lines[1:]
        else:
            return True

        if len(test[0]) > 1:
            return True

        chunk = test[0][0]

        glitch = (True
                  or chunk.cids.__bytes__() == b'\x00\\\x12I'
                  or chunk.cids.__bytes__() == b'\x00\x14'
                  or chunk.cids.__bytes__() == b'\x00\x7f\x12I'
                  or chunk.cids.__bytes__() == b'\x00\xbb\x01='
                  or chunk.cids.__bytes__() == b'\x01\x88\x02\xf2'
                  or chunk.cids.__bytes__() == b'\x02|\x02\x84'
                  or chunk.cids.__bytes__() == b'\x01I\x01\xb8'
                  or chunk.cids.__bytes__() == b'\x02\x80\x04\xed'
                  or chunk.cids.__bytes__() == b'\x02\xb2\x12I'
                  or chunk.cids.__bytes__() == b'\x02\xe8\x06\x0e'
                  or chunk.cids.__bytes__() == b'\x02\xe9\x06\x0e'
                  or chunk.cids.__bytes__() == b'\x02\xeb\x06\x0e'
                  or chunk.cids.__bytes__() == b'\x02\xed\x06\x0e'
                  or chunk.cids.__bytes__() == b'\x02%\x04F'
                  or chunk.cids.__bytes__() == b'\x02n\x02o\x02\x84'
                  or chunk.cids.__bytes__() == b'\x02x\x04\xed'
                  or chunk.cids.__bytes__() == b'\x02z\x04\xed'
                  or chunk.cids.__bytes__() == b'\x03!'
                  or chunk.cids.__bytes__() == b'\x04\xaa'
                  or chunk.cids.__bytes__() == b'\x03w\x03}'
                  )
        return not glitch

    @staticmethod
    def _get_top_left_bak(chunks):
        if len(chunks) == 0:
            return 0, 0
        top = chunks[0].y
        left = chunks[0].x

        for i in range(0, len(chunks)):
            chunk = chunks[i]
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

    def to_unicode(self, pikepdf_string, apply_fixups=True):
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
                if apply_fixups and cid in self.to_unicode_fixed:
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
        self._chunks_page = None
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
                print(f'Operator: {operator}', file=sys.stderr)

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
                    print(f"Td: dx={dx} x={operands[0]} y={operands[1]}", file=sys.stderr)
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
                            if DEBUG_PDF:
                                print(
                                    f"Tj: x={x} y={y} {text.__bytes__()} -> \"{font_decoder.to_unicode(text)}\", Font: {font_decoder.name}",
                                    file=sys.stderr)
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
                                    if DEBUG_PDF:
                                        print(
                                            f"TJ: x={x} y={y} {text.__bytes__()} -> \"{font_decoder.to_unicode(text)}\", Font: {font_decoder.name}",
                                            file=sys.stderr)
                                    lmbd(text, font_decoder, x, y, dx)
                                elif isinstance(element, int):
                                    if DEBUG_PDF:
                                        print(
                                            f"TJ: x={x} y={y} int={element} -> \"{element}\", Font: {font}",
                                            file=sys.stderr)
                                    pass
                                elif isinstance(element, Decimal):
                                    if DEBUG_PDF:
                                        print(
                                            f"TJ: x={x} y={y} Decimal={element} -> \"{element}\", Font: {font}",
                                            file=sys.stderr)
                                    pass
                                else:
                                    print(f"Unexpected element type: {type(element)}")
                        else:
                            print(f"Unexpected operand type: {type(operand)}")
                elif operator == pikepdf.Operator('Tm'):
                    if DEBUG_PDF:
                        print(
                            f"Tm: 0={operands[0]} 1={operands[1]} 2={operands[2]} 3={operands[3]} 4={operands[4]} 5={operands[5]}",
                            file=sys.stderr)
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

    # TODO: static method?
    def convert_to_chunks_page(self):
        chunks = []

        def lmbd(text, font_decoder, x, y, dx):
            nonlocal chunks
            original_text = font_decoder.to_unicode(text, False)
            unicode_text = font_decoder.to_unicode(text)
            chunks.append(Chunk(text, unicode_text, original_text, x, y, font_decoder.name, dx))

        self._call_for_tj(lmbd)

        if self._chunks_page is None:
            self._chunks_page = ChunksPage(chunks)
        return self._chunks_page

    @staticmethod
    def _paragraphs_to_entries(paragraphs, page_no):
        entries = []
        para_no = 0  # debug purposes
        for paragraph in paragraphs:
            headword, body = paragraph.headword_and_body(page_no, para_no)
            entries.append(Entry(headword, body, page_no, para_no, paragraph))
            para_no += 1
        return entries

    # prev_entries is used to concatenate entries from the previous page
    # if the first entry on the current page is a continuation of the last entry on the previous page
    def convert_to_entries(self, prev_entries):
        if self._chunks_page is None:
            self._chunks_page = self.convert_to_chunks_page()
        chunks_page = self._chunks_page

        entries = PdfDecoderForPage._paragraphs_to_entries(chunks_page.chunks_paragraphs, self.page_no)

        if len(prev_entries) > 0:
            if not entries[0].headword:
                prev_entries[-1].definition += entries[0].definition
                entries = entries[1:]

        return entries

    def title(self):
        if self._chunks_page is None:
            self._chunks_page = self.convert_to_chunks_page()
        return self._chunks_page.title()


class Chunk:
    def __init__(self, cids, text, original_text, x, y, font, dx):
        if isinstance(cids, bytes):
            self.cids = cids
        else:
            self.cids = cids.__bytes__()
        self.text = text
        self.original_text = original_text
        self.x = float(x)
        self.y = float(y)
        self.font = font
        self.dx = float(dx)

    def __str__(self):
        return f'"{self.text}"/"{self.original_text}" x: {self.x} y: {self.y} font: {self.font} dx: {self.dx} cids: {self.cids.__bytes__()}'

    def __repr__(self):
        return f'Chunk({self.cids.__bytes__()}, "{self.text}", "{self.original_text}", {self.x}, {self.y}, {self.font}, {self.dx})'

    def copy(self):
        return Chunk(self.cids, self.text, self.original_text, self.x, self.y, self.font, self.dx)

    def copy_without_first_2bytes(self):
        # TODO: make sure the font is 2 bytes
        if len(self.cids) < 2:
            return self.copy()
        return Chunk(self.cids[2:], self.text[1:], self.original_text[1:], self.x, self.y, self.font, self.dx)

    def is_empty(self):
        return len(self.cids) == 0

    def startswith(self, char, font=None):
        if isinstance(char, bytes):
            if font is not None and self.font != font:
                return False
            if len(char) > len(self.cids):
                return False
            for i in range(len(char)):
                if self.cids[i] != char[i]:
                    return False
            return True
        else:
            return self.text.startswith(char)

    def has_leading_glitches(self):
        res = (False
               or self.startswith(b'\n"', '/C0_3')
               or self.startswith(b'\n"', '/C0_5')
               or self.startswith(b'\x00~', '/C0_0')
               or self.startswith(b'\x01*', '/C0_3')
               or self.startswith(b'\x007', '/C0_3')
               or self.startswith(b'\x01\x9d', '/C0_8')
               or self.startswith(b'\x01\xaf', '/C0_5')
               or self.startswith(b'\x01\xe1', '/C0_0')
               or self.startswith(b'\x01\xf9', '/C0_0')
               or self.startswith(b'\x02\x94', '/C0_0')
               or self.startswith(b'\x03*', '/C0_0')
               or self.startswith(b'\x03*', '/C0_5')
               or self.startswith(b'\x03\x0c', '/C0_10')
               or self.startswith('.')
               or self.startswith(','))
        return res


class Entry:
    def __init__(self, headword, definition, page_no, entry_no, paragraph):
        self.headword = headword.strip()
        self.definition = definition.strip()
        self.page_no = page_no
        self.entry_no = entry_no
        self.paragraph = paragraph

    def __str__(self):
        return f'/{self.headword}/({self.page_no})\n{self.definition}'

    def __repr__(self):
        return f'Entry("{self.headword}", "{self.definition}", {self.page_no})'

    def txt(self, separator=' '):
        return f'{self.headword}{separator}{self.definition}{separator}{self.page_no}{separator}{self.entry_no}'

    def debug(self):
        print("-------------------------------------")
        print(f"Page:       {self.page_no}")
        print(f"Entry no:   {self.entry_no}")
        print(f"Headword:   {self.headword}")
        print(f"Definition: {self.definition}")
        print(f"Lines:")
        for line in self.paragraph.lines:
            print(f"==> ", end='')
            for chunk in line:
                if chunk.original_text == chunk.text:
                    text = chunk.text
                else:
                    text = f"{chunk.original_text}>{chunk.text}"
                print(f"{chunk.font}:{self.fcids(chunk.cids)}[{text}]", end=',  ')
            print()

    @staticmethod
    def fcids(cids):
        s = str(cids)
        return s[2:-1]


class PdfDecoderForFile:
    def __init__(self, pdf_file):
        self.pdf_file = pdf_file

    def check_titles(self):
        with pikepdf.open(self.pdf_file) as pdf:
            for n, page in enumerate(pdf.pages):
                if n < 16:
                    continue
                if n > 1528:
                    break
                title = re.split(r'[ \-]', PdfDecoderForPage(page, n).title())
                if len(title) < 3:
                    print(f"{{{n}:'{title}'}}")

    # from and to are page numbers inclusive..exclusive (as in range)
    def each(self, lmbda, f=16, t=1528):
        with pikepdf.open(self.pdf_file) as pdf:
            prev_entries = []
            for n, page in enumerate(pdf.pages):
                if n < f:
                    continue
                if n > t:
                    break
                if False and page["/Resources"].get("/Font", None) is None:
                    print(f"No fonts found in page resources for page: {n}", file=sys.stderr)
                    continue
                if debug_progress:
                    print(f"Page: {n}", end=' ', file=sys.stderr)
                decoder = PdfDecoderForPage(page, n, fixes, typos)
                if debug_progress:
                    print(decoder.title(), file=sys.stderr)

                entries = decoder.convert_to_entries(prev_entries)
                prev_entries = entries
                for entry in entries:
                    if entry.headword is not None:
                        lmbda(entry)
                    else:
                        raise ValueError(f"Entry without headword: {entry}")

    def debug_entry(self, page_no, entry_no_or_headword):
        def lmbd(entry):
            if isinstance(entry_no_or_headword, int):
                if entry.entry_no == entry_no_or_headword:
                    entry.debug()
            elif isinstance(entry_no_or_headword, str):
                if entry.headword == entry_no_or_headword:
                    entry.debug()
            else:
                raise ValueError(f"Unexpected type: {type(entry_no_or_headword)}")

        self.each(lmbd, page_no, page_no)

    def print_txt(self, f=16, t=1528):
        self.each(lambda entry: print(entry.txt()), f, t)

    def print_csv(self, f=16, t=1528):
        print("headword\tdefinition\tpage\tpara")
        self.each(lambda entry: print(entry.txt('\t')), f, t)

    def print_json(self, f=16, t=1528):
        json_key = 0
        j = {}

        def process_entries_json(entry):
            nonlocal json_key
            j[json_key] = {
                "headword": entry.headword,
                "definition": entry.definition,
                "page": entry.page_no
            }
            json_key += 1

        #        def process_entries_json(entry):
        #            nonlocal json_key
        #            if json_key > 0:
        #                print(",")
        #            m = {json_key: {
        #                "headword": entry.headword,
        #                "definition": entry.definition,
        #                "page": entry.page_no
        #            }}
        #            print(json.dumps(m, indent=4, ensure_ascii=False), end="")
        #            json_key += 1
        # print("{")
        # self.each(process_entries_json, args.debug)
        # print("}")
        self.each(process_entries_json, f, t)
        json.dump(j, sys.stdout, indent=2, ensure_ascii=False)

    def export_mongodb(self, connection_string, f=16, t=1528):
        raise NotImplementedError("MongoDB export is not implemented lookup feature yet")
        client = MongoClient(connection_string)
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

        self.each(process_entries_mongodb, f, t)

    def export_firebase(self, connection_string, f=16, t=1528):
        from firebase_admin import credentials
        from firebase_admin import db

        credentials = credentials.Certificate(connection_string)
        firebase_admin.initialize_app(credentials, {
            # TODO: should be picked up from json?
            'databaseURL': 'https://matica-srpska-sy4-default-rtdb.europe-west1.firebasedatabase.app'
        })

        entries_ref = db.reference('entries')
        # search by headword is not good idea, because they are not unique
        entries_ref.delete()

        key = 0

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
            nonlocal key
            ref = entries_ref.child(str(key))
            # else:
            # ref = entries_ref.push()
            ref.set(
                {'headword': entry.headword,
                 'definition': entry.definition,
                 'page': entry.page_no,
                 'lookup': ''.join((entry.headword + entry.definition).lower().split())})

            key += 1
            # end_time = time.time()
            # execution_time = end_time - start_time
            # print(f"Execution time ref.set ({entry.headword}): {execution_time} seconds")

        self.each(process_entries_rtdb, f, t)


def bytes2cid(b):
    return b[0] << 8 | b[1]


fixes = {
    '/C0_0': {
        bytes2cid(b'\x00b'): '~',
        bytes2cid(b'\x00['): 'а',
        bytes2cid(b'\x00e'): '~',
        # bytes2cid(b'\x00\x0b'): '~', breaks p23. ајурведски -а, -о који се односи на ајурведу: медицина.
        bytes2cid(b'\x00\r'): '~',
        # bytes2cid(b'\x00\x0b'): '~', ^26:27 2[-зма >-з~а ]
        # bytes2cid(b'\x00\x0b'): '~', ^18:6 политички~
        bytes2cid(b'\x00\x13'): '~',
        bytes2cid(b'\x00\xb8'): 'и',
        bytes2cid(b'\x00\xd0'): 'и',
        bytes2cid(b'\x01\xb5'): 'л',
    },
    '/C0_1': {
        # bytes2cid(b'\x00"'): 'ш',
        # bytes2cid(b'\x00"'): 'а', # 16:7 аБДИRација >абдикација - not needed
        # bytes2cid(b'\x00"'): 'ш', # 17:14 ^[дошао. >доаао. ] - not needed
        bytes2cid(b'\x00|'): 'с',
        # bytes2cid(b'\x08<'): 'к',!!!
        bytes2cid(b'\x00f'): 'и',
        bytes2cid(b'\x00h'): 'к',
        bytes2cid(b'\x00r'): 'к',
        # bytes2cid(b'\x00t'): 'е', # 17:14 [речце: >речцее ],
        # bytes2cid(b'\x00\x0c'): 'д', # ^16:32 абонос > абондс
        bytes2cid(b'\x00\x13'): '~',
        bytes2cid(b'\x00\x14'): '~',
        bytes2cid(b'\x00\x7f'): 'д',
        bytes2cid(b'\x00\x83'): 'н',
        bytes2cid(b'\x00\x8f'): 'и',
        bytes2cid(b'\x00\x95'): 'о',
        bytes2cid(b'\x00\x9e'): 'т',
        bytes2cid(b'\x00\xa2'): '~',
        bytes2cid(b'\x00\xa7'): 'а',
        bytes2cid(b'\x00\xac'): 'л',
        bytes2cid(b'\x00\xb9'): 'д',
        bytes2cid(b'\x00\xbd'): 'и',
        bytes2cid(b'\x00\xd5'): 'и',
        bytes2cid(b'\x00\xfa'): 'ч',
        bytes2cid(b'\x01j'): 'ц',
        bytes2cid(b'\x01\x02'): 'у',
        bytes2cid(b'\x01\x07'): 'б',
        bytes2cid(b'\x01\xd6'): 'о',
        bytes2cid(b'\x02+'): 'и',
        bytes2cid(b'\x02\xa8'): 'лингв',
        bytes2cid(b'\x02\x9f'): 'к',
        bytes2cid(b'\x03\x86'): '.',
        bytes2cid(b'\x03\x1a'): '',
        bytes2cid(b'\x04l'): 'д',
        bytes2cid(b'\x04\x16'): 'и',
        bytes2cid(b'\x04\x85'): 'и',
        bytes2cid(b'\x04\xbe'): 'ак',
        bytes2cid(b'\x04\xbf'): 'и',

        # bytes2cid(b'\x01\xff'): '@1',
        # bytes2cid(b'\x00\x07'): '@3',
        # bytes2cid(b'\x00\x07'): '@3',
    },
    '/C0_2': {
        bytes2cid(b'\x00|'): 'с',
        bytes2cid(b'\x00.'): 'мн',
        bytes2cid(b'\x00F'): 'е',
        bytes2cid(b'\x01Z'): 'и',
        bytes2cid(b'\x00t'): 'е',
        # bytes2cid(b'\x00\x01'): 'а', !16:7 ж >а
        bytes2cid(b'\x00\x19'): 'ј',
        bytes2cid(b'\x00\xa9'): 'р',
        bytes2cid(b'\x00\xb3'): 'к',
        bytes2cid(b'\x00\xbe'): 'в',
        bytes2cid(b'\x01l'): 'д',
        bytes2cid(b'\x01\x02'): 'у',
        bytes2cid(b'\x06\xdb'): 'и',

        # bytes2cid(b'\x00\x07'): '?',
    },
    '/C0_3': {
        bytes2cid(b'\n%\x05'): 'њ',
        bytes2cid(b'\n+'): 'о',
        bytes2cid(b'\nP'): 'с',
        bytes2cid(b'\no'): 'у',
        bytes2cid(b'\rh'): 'п',
        bytes2cid(b'\n\x14'): 'н',
        bytes2cid(b'\n\xa4'): 'т',
        bytes2cid(b'\n\xcb'): 'а',
        bytes2cid(b'\n\xe4'): 'п',
        bytes2cid(b'\t\xd7'): 'п',
        bytes2cid(b'\x000'): 'п',
        bytes2cid(b'\x06<'): 'ћ',
        # bytes2cid(b'\x08^'): 'лингв', broken
        bytes2cid(b'\x08]'): 'п',
        # bytes2cid(b'\x00\r'):
        bytes2cid(b'\x00\t'): 'с',  # 16:9 [евр. >свр. ]
        # bytes2cid(b'\x00\t'): 'в, #p21 агресивност, -ости
        bytes2cid(b'\x00V'): 'п',
        bytes2cid(b'\x00\x08'): 'т',
        bytes2cid(b'\x00\x0c'): 'д',
        bytes2cid(b'\x00\xa3'): 'г',
        # bytes2cid(b'\x00\x16'): 'т', # 'з', /адмирал/(21) ...  2. тоол. врста
        bytes2cid(b'\x00\xff'): 'љ',
        bytes2cid(b'\x01d'): '1',
        bytes2cid(b'\x02\x13'): '',
        bytes2cid(b'\x04l'): 'н',
        bytes2cid(b'\x04U'): 'с',
        bytes2cid(b'\x04\xa0'): 'м',
        bytes2cid(b'\x04\xa4'): 'к',
        bytes2cid(b'\x04\xb1'): 'м',
        bytes2cid(b'\x04\xc0'): 'о',
        bytes2cid(b'\x04\xe8'): 'п',
        # bytes2cid(b'\x04\xe9'): 'у', # ^17:55 дрyгUЈИ дрyгуЈИ
        bytes2cid(b'\x04\xe9'): 'и',  # 17:55 дрyгUЈИ дрyгиЈИ
        bytes2cid(b'\x05m'): 'ал',
        bytes2cid(b'\x05\x1e'): 'пл',  # 17:55 ваздуоповни
        bytes2cid(b'\x06\x10'): 'д',
        bytes2cid(b'\x08^'): 'и',  # p21, ајурведски ... односи,
        bytes2cid(b'\x0b\xa8'): 'аљ',  # p21, ајурведски ... односи,
        bytes2cid(b'\x0cP'): 'с',
        # bytes2cid(b'\x0e\xc4'): '@1',
        bytes2cid(b'\x0f-'): 'р',
        # bytes2cid(b'\x0f\x83'): 'ј',
        # bytes2cid(b'\x0c\xf4'): 'ни',
        bytes2cid(b'\x10\xcf'): 'е',
        bytes2cid(b'\x10\xd1'): 'т',
        bytes2cid(b'\x12G'): 'в',
    },
    '/C0_4': {
        bytes2cid(b'\n+'): 'о',
        bytes2cid(b'\nP'): 'с',
        bytes2cid(b'\no'): 'у',
        bytes2cid(b'\n\x14'): 'н',
        bytes2cid(b'\n\xa4'): 'т',
        bytes2cid(b'\n\xb0'): 'и',
        bytes2cid(b'\rh'): 'п',
        bytes2cid(b'\r\x92'): 'т',
        bytes2cid(b'\r\xa2'): 'тл',
        bytes2cid(b'\t\x88'): 'љ',
        bytes2cid(b'\t\xc4'): 'ж',
        bytes2cid(b'\t\xd7'): 'п',
        bytes2cid(b'\t\xef'): 'к',
        bytes2cid(b'\t\xf8'): 'л',
        bytes2cid(b'\x00;'): 'г',
        bytes2cid(b'\x00:'): 'г',
        bytes2cid(b'\x00x'): 'н',
        bytes2cid(b'\x00y'): '~',
        bytes2cid(b'\x00\t'): 'с',
        # bytes2cid(b'\x00\x12'): '~', ^17:8 [геол. >ге~л. ]
        bytes2cid(b'\x00\x17'): 'г',
        bytes2cid(b'\x00\xd0'): 'гм',
        bytes2cid(b'\x01_'): 'к',
        bytes2cid(b'\x01,'): 'и',
        bytes2cid(b'\x02&'): '.',
        bytes2cid(b'\x02\xb8'): '',  # 16:9 [. > ]
        bytes2cid(b'\x03O'): 'к',
        bytes2cid(b'\x03)'): 'о',
        bytes2cid(b'\x03\xc9'): 'д',
        bytes2cid(b'\x04j'): 'н',
        bytes2cid(b'\x04l'): 'н',
        bytes2cid(b'\x04U'): 'с',
        bytes2cid(b'\x04\xb1'): 'м',
        bytes2cid(b'\x04\xe9'): 'и',
        bytes2cid(b'\x04\xa4'): 'к',
        bytes2cid(b'\x04\xc0'): 'о',
        bytes2cid(b'\x05I'): 'а',
        bytes2cid(b'\x05o'): 'ам',
        bytes2cid(b'\x05\x0c'): 'иљ',
        bytes2cid(b'\x05\xb7'): 'в',
        bytes2cid(b'\x05\xf1'): 'гл',
        bytes2cid(b'\x05\xee'): 'г',
        bytes2cid(b'\x05\xeb'): 'г',
        # bytes2cid(b'\x00\x01'): '', #p21 агресивност, -ости {ж}
        bytes2cid(b'\x06<'): 'ћ',
        bytes2cid(b'\x06L'): 'г',
        bytes2cid(b'\x06\x10'): 'д',
        bytes2cid(b'\x07?'): 'г',
        bytes2cid(b'\x08^'): 'и',
        bytes2cid(b'\x0c '): 'ил',
        bytes2cid(b'\x0c\x9a'): 'ељ',
        bytes2cid(b'\x0e\x1e'): 'пл',
        bytes2cid(b'\x10\xd1'): 'т',
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
        # bytes2cid(b'\x00\1b'): '~', ^18:6 [хем. >хем~ ]
        bytes2cid(b'\x00\01'): '~',
    },
    '/C0_7': {
        bytes2cid(b'\x00y'): '~',
        bytes2cid(b'\x00\x0b'): '~',
        bytes2cid(b'\x00\x07'): 'л',
        bytes2cid(b'\x001'): 'с',
    },
    '/C0_8': {
        bytes2cid(b'\x00.'): 'у',
        bytes2cid(b'\x00\x04'): 'а',
        bytes2cid(b'\x00\x14'): 'з',
        bytes2cid(b'\x00\x1c'): 'в',
        bytes2cid(b'\x02\xfa'): 'ш',
    },
    '/C0_9': {
        bytes2cid(b'\x00\x8e'): '~',
    },
    '/C0_10': {
        # bytes2cid(b'\x00\x04'): 'ц', #!!!!
        # bytes2cid(b'\x00 '): '@1',
        bytes2cid(b'\x00A'): 'и',
        # bytes2cid(b'\x00\t'): 'ијс', # 16:8 (абдик3.цйјскЙ), >(абдикацски) ^16:1[данас? >данаијс? ],
        bytes2cid(b'\x00\x04'): 'е',
        bytes2cid(b'\x00\x13'): 'ј',  # 16:8 (абдик3.цйјскЙ), >(абдикацски)
        # bytes2cid(b'\x00\x1c'): 'ј', # 16:8 (абдик3.цйјскЙ), >(абдикацски)
        bytes2cid(b'\x00\x1c'): ',',
        bytes2cid(b'\x01H'): 'р',
        bytes2cid(b'\x01\x12'): 'и',
        # bytes2cid(b'\x01\x12'): 'а',
        bytes2cid(b'\x021'): 'е',
        bytes2cid(b'\x02\xcc'): 'ациј',  # 16:8 (абдик3.цйјскЙ), >(абдикацски)
        bytes2cid(b'\x03`'): 'д',

        # bytes2cid(b'\x00O'): '@2', # 16:8 (абдик3.цйјскЙ), >(абдикацски)
    }
}
typos = {
    # '/C0_4': mongodb://localhost:27017/{
    #    'cамoгаcник ': 'самогласник ',
    # }
}


class Th:
    def __init__(self, pos, expected_headword, expected_body=None):
        self.pos = pos
        self.expected_headword = expected_headword
        self.expected_body = expected_body


def test_page_entries(page_no, expected_title, expected_entries, test_entries):
    print("Testing entries, page", page_no)
    with pikepdf.open(os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf')) as pdf:
        page = pdf.pages[page_no]
        # decoder = PdfDecoderForPage(page, page_no, fixes, typos)
        decoder = PdfDecoderForPage(page, page_no)  # no fixes for easier comparision with PDF
        entries = decoder.convert_to_entries([])

        print("Expected title:", expected_title, end=" ")
        title_foo = decoder.title()
        title = decoder.title()
        expected_title = fix_cyrillic(expected_title)
        if title == expected_title:
            print("PASSED")
        else:
            print("FAILED. Actual title:", title)
            raise ValueError(f"Expected title: {expected_title} Actual title: {title}")

        for test in test_entries:
            i = test.pos
            headword = fix_cyrillic(test.expected_headword)
            print(f"Headword {i}:", end=" ")
            if entries[i].headword == headword:
                print(f"PASSED {headword}")
            else:
                print(f'FAILED. Expected: "{headword}" Actual: "{entries[i].headword}"')
                raise ValueError(f'Expected: "{headword}" Actual: "{entries[i].headword}"')
            if test.expected_body:
                body = fix_cyrillic(test.expected_body)
                print(f"Body {i}:", end=" ")
                if entries[i].definition == body:
                    print(f"PASSED {body}")
                else:
                    print(f'FAILED. Expected: "{body}" Actual: "{entries[i].definition}"')
                    for j in range(len(body)):
                        if entries[i].definition[j] != body[j]:
                            print(
                                f'FAILED. at pos {j}:{body[j]}/{entries[i].definition[j]} Expected: "{body[j - 5:j + 5]}" Actual: "{entries[i].definition[j - 5:j + 5]}"')
                            break
                    raise ValueError(f'Expected: "{body}" Actual: "{entries[i].definition}"')

        print("Number of entries:", end=" ")
        if len(entries) == expected_entries:
            print("PASSED")
        else:
            print(f"FAILED. Expected: {expected_entries} Actual: ", len(entries))
            raise ValueError(f"Expected entries: {expected_entries} Actual entries: {len(entries)}")


def test_page_chunks(page_no, expected_title, expected_paragraphs, headwords):
    print("Testing paragraphs, page", page_no)
    with pikepdf.open(os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf')) as pdf:
        page = pdf.pages[page_no]
        decoder = PdfDecoderForPage(page, page_no)
        chunks_page = decoder.convert_to_chunks_page()

        print("Title exists:", end=" ")
        if len(chunks_page.chunks_title) > 0:
            print("PASSED")
        else:
            print("FAILED")
            exit(1)

        print("Expected title:", expected_title, end=" ")
        title_foo = chunks_page.title()
        title = chunks_page.title()
        if title == expected_title:
            print("PASSED")
        else:
            print("FAILED. Actual title:", title)
            exit(1)

        for test in headwords:
            i = test.pos
            headword = test.expected_headword
            print(f"Headword {i}:", end=" ")
            headword1, _ = chunks_page.chunks_paragraphs[i].headword_and_body()
            if headword1 == headword:
                print(f"PASSED {headword1}")
            else:
                print(f'FAILED. Expected: "{headword}" Actual: "{headword1}"')
                exit(1)

        print("Number of paragraphs:", end=" ")
        if len(chunks_page.chunks_paragraphs) == expected_paragraphs:
            print("PASSED")
        else:
            print(f"FAILED. Expected: {expected_paragraphs} Actual: ", len(chunks_page.chunks_paragraphs))
            exit(1)


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Парсер за Матицу Српску')

    parser.add_argument('--debug', default=None,
                        help='Приказивање дебаг информација: --debug page_no:entry_no')
    parser.add_argument('--progress', action='store_true',
                        help='Приказивање прогреса')
    parser.add_argument('--positions', action='store_true',
                        help='Приказивање позиција у PDF-у')
    parser.add_argument('--txt', action='store_true',
                        help='Екстракција свих страна из PDF-а у текстуални фајл')
    parser.add_argument('--csv', action='store_true',
                        help='Екстракција свих страна из PDF-а у SCV фајл')
    parser.add_argument('--json', action='store_true',
                        help='Екстракција свих страна из PDF-а у JSON фајл')
    parser.add_argument('--mongodb-connection-string', default=None,
                        help='Екстракција свих страна из PDF-а у mongodb')
    parser.add_argument('--firebase-service-account-key-json', default=None,
                        help='Екстракција свих страна из PDF-а у firebase real-time database')

    args = parser.parse_args()

    debug_progress = args.progress

    convertor = PdfDecoderForFile(os.path.join(os.path.dirname(__file__), 'matica/matica-full.pdf'))

    if args.txt:
        convertor.print_txt()
        exit(0)

    if args.positions:
        print('Not implemented')
        exit(1)

    if args.csv:
        convertor.print_csv()
        exit(0)

    if args.json:
        convertor.print_json()
        exit(0)

    if args.mongodb_connection_string:
        from pymongo import MongoClient

        convertor.export_mongodb(args.mongodb_connection_string)
        exit(0)

    if args.firebase_service_account_key_json:
        import firebase_admin

        convertor.export_firebase(args.firebase_service_account_key_json)
        exit(0)

    if args.debug:
        page_no, entry_no_or_headword = args.debug.split(':')
        convertor.debug_entry(int(page_no), int(entry_no_or_headword))
        exit(0)
    #################### KNOWN PROBLEMS #########################
    # [агенс][аге нс]
    # августовски -3., -о који се односу на август1: ~сунце, ~вру-ћина. 17 35
    #################### TESTST #########################
    convertor.debug_entry(18, 6)
    exit(0)

    problem_titles = [154, 660, 772, 774, 796, 1010, 1330]

    test_entries = [
        Th(0, "надометнути"),
        Th(40, "надридуховит"),
    ]
    test_page_entries(751, "750 НАДОМЕТНУТИ -НАДРИДУХОВИТ", 41, test_entries)

    test_entries = [
        Th(0, "позитрон"),
        Th(48, "пој"),
    ]
    test_page_entries(944, "ПО3ИТРОН -ПОЈ 943", 49, test_entries)

    test_entries = [
        Th(0, "подсетник"),
        Th(61, "подужи"),
    ]
    test_page_entries(940, "ПОДСЕТНИК -ПОДУЖИ 939", 62, test_entries)

    test_entries = [
        Th(0, "галиматијас"),
        Th(55, "гањивати (се)"),
    ]
    test_page_entries(175, "174 ГАЛИМАТИЈАС -ГАЊИВАТИ (СЕ)", 56, test_entries)

    test_entries = [
        Th(0, "осмак"),
        Th(53, "основац"),
    ]

    test_page_entries(878, "ОСМАК -ОСНОВАЦ 877", 54, test_entries)

    test_entries = [
        Th(0, "задерати"),
        Th(57, "задоцњивати (се)"),
    ]

    test_page_entries(374, "ЗАДЕРАТИ -ЗАДОЦЊИВАТИ (СЕ) 373", 58, test_entries)

    test_entries = [
        Th(0, "зацењивати (се)"),
        Th(56, "зачеће"),
    ]

    test_page_entries(408, "ЗАЦЕЊИВАТИ (СЕ)l -ЗА ЧЕЋЕ 407", 57, test_entries)

    test_entries = [
        Th(0, "затирати (се)"),
        Th(53, "затрести"),
    ]

    test_page_entries(404, "3АТИРАТИ(СЕ)-3АТРЕСТИ 403", 54, test_entries)

    test_entries = [
        Th(0, "заозбиљно"),
        Th(53, "западно"),
    ]

    test_page_entries(390, "ЗАОЗБИЉНО -ЗАПАДНО 389", 54, test_entries)

    test_entries = [
        Th(0, "дiшилац"),
        Th(45, "дактилоскопија"),
    ]

    test_page_entries(230, "ДАВИЛАЦ -ДАКТИЛОСКОПИЈА 229", 46, test_entries)

    test_entries = [
        Th(0, ""),
        Th(19, "водено"),
    ]

    test_page_entries(152, "ВОДАН -ВОДЕНО 151", 20, test_entries)

    test_entries = [
        Th(0, "гарниmна"),
        Th(52, "гатити"),
    ]
    test_page_entries(177, "176 ГАРНИШНА -ГАТИТИ", 53, test_entries)

    test_entries = [
        Th(0, ""),
        Th(55, "гвожђурина"),
    ]
    test_page_entries(178, "ГАТИЋ -ГВОЖЂУРИНА 177", 56, test_entries)

    test_entries = [
        Th(0, "гаовица"),
        Th(47, "гарнитура"),
    ]
    test_page_entries(176, "ГАОВИЦА-ГАРНИТУРА 175", 48, test_entries)

    test_entries = [
        Th(0, "",
           "свршено, lошово; gосша: - Тако је и амин. 3. (у им. служби) м свршешан:, н:рај: доћи на -. • као - CUlYPHO, заисша, неминовно."),
        Th(1, "аминати"),
        Th(49, "амфитеатралан"),
    ]
    test_page_chunks(31, "30 АМИНАТИ -АМФИТЕАТРАЛАН", 50, test_entries)
    test_page_entries(31, "30 АМИНАТИ -АМФИТЕАТРАЛАН", 50, test_entries)

    test_entries = [
        Th(61, "архијерејскй"),
    ]
    test_page_entries(45, "44 АРТИЉЕРИЈСКИ -АРХИЈЕРЕЈСКИ", 62, test_entries)

    test_entries = [
        Th(0, "а1"),
        Th(3, "а4"),
        Th(4, "а-"),
        Th(5, "абажур"),
        Th(10, "аберација",
           "ж лат:l. а. аетр. йривиgна йромена йоложаја звезgа условЈЬена 3емљиним крешањем и брзином ширења свейlло-сШи. б. у ойшици, оgсшуйање йреломљених свейlлосних зракова og ЙОЖеЈЬНОf, Йравца. 2. биол. оgсшуйање og шийичноf, облика. 3. фиг. скрешање, засШрањивање."),
        Th(15, "аБЕщедни и абецедни"),
        Th(25, "аболицијСRИ и аболициони"),
        Th(27, "аболиционист(а)", "-ё м (ми. -сти) йоборник аболиционизма."),
        Th(28, "аБОЛИЦИОНИСТИЧRИ"),
        Th(29, "абонент"),
        Th(30, "абонеНТRиња"),
    ]
    test_page_entries(16, "А", 34, test_entries)

    test_entries = [
        Th(12, "архитектоника"),
        Th(13, "архитектонички и архитектонични"),
        Th(58, "асинхронија"),
    ]
    test_page_entries(46, "АРХИЛАЖАЦ -АСИНХРОНИЈА 45", 59, test_entries)

    test_entries = [
    ]
    test_page_entries(27, "26 АЛЕЛУЈА -АЛКУРАН", 47, test_entries)
    test_page_chunks(27, "26 АЛЕЛУЈА -АЛКУРАН", 47, test_entries)

    test_entries = [
        Th(0, "амфитеатрално"),
        Th(10, "анакрон-"),
        Th(15, "анализа"),
        Th(20, "аналист(а)"),
        Th(25, "аналитичар"),
        Th(26, "аналитичкй"),
        Th(27, "аналитички"),
        Th(28, "аналитичност"),
        Th(56, "анархичност"),
    ]
    test_page_chunks(32, "АМФИТЕАТРАЛНО -АНАРХИЧНОСТ 31", 57, test_entries)
    test_page_entries(32, "АМФИТЕАТРАЛНО -АНАРХИЧНОСТ 31", 57, test_entries)

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
    test_page_chunks(33, '32 АНАРХО--АНГЛОФОПСКИ', 57, test_para)

    test_entries = [
        Th(0, ""),
        Th(47, "вёровати"),
    ]
    test_page_entries(133, "132 ВЕРАН -ВЕРОВАТИ", 48, test_entries)

    test_entries = [
        Th(10, "баздети"),
        Th(12, "базён"),
        Th(13, "базенчић"),
        Th(15, "базирати"),
        Th(25, "бајалац"),
        Th(35, "бајацо"),
        Th(38, "бај-бај"),
        Th(39, "бај"),
        Th(40, "бајити"),
        Th(46, "бајно"),
    ]
    test_page_entries(57, "56 БАЖДАРИТИ -БАЈНО", 47, test_entries)

    test_entries = [
        Th(55, "беседа"),
    ]
    test_page_entries(76, "БЕРБАНСКИ -БЕСЕДА 75", 56, test_entries)

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
