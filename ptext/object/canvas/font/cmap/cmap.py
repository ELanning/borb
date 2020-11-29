import io
from typing import Union, List, Optional, Tuple

from ptext.io.tokenizer.high_level_tokenizer import HighLevelTokenizer
from ptext.primitive.pdf_array import PDFArray
from ptext.primitive.pdf_string import PDFHexString


class CMap:
    """
    A CMap shall specify the mapping from character codes to character selectors. In PDF, the character selectors
    shall be CIDs in a CIDFont (as mentioned earlier, PostScript CMaps can use names or codes as well). A CMap
    serves a function analogous to the Encoding dictionary for a simple font. The CMap shall not refer directly to a
    specific CIDFont; instead, it shall be combined with it as part of a CID-keyed font, represented in PDF as a
    Type 0 font dictionary (see 9.7.6, "Type 0 Font Dictionaries"). Within the CMap, the character mappings shall
    refer to the associated CIDFont by font number, which in PDF shall be 0.
    """

    def __init__(self):
        self._unicode_to_code = {}
        self._code_to_unicode = {}

    def unicode_to_code(self, unicode: Union[int, List[int]]) -> Optional[int]:
        return self._unicode_to_code.get(unicode)

    def code_to_unicode(self, character_code: int) -> Optional[int]:
        return self._code_to_unicode.get(character_code, -1)

    def add_symbol(self, character_code: int, unicode: Union[int, List[int]]) -> "CMap":
        self._unicode_to_code[unicode] = character_code
        self._code_to_unicode[character_code] = unicode
        return self

    def can_encode_unicode(self, unicode: Union[int, List[int]]) -> bool:
        return unicode in self._unicode_to_code

    def can_encode_character_code(self, character_code: int) -> bool:
        return character_code in self._code_to_unicode

    def read(self, cmap_bytes: str) -> "CMap":

        N = len(cmap_bytes)
        tok = HighLevelTokenizer(io.BytesIO(cmap_bytes.encode("latin-1")))

        prev_token = None
        while tok.tell() < N:

            token = tok.next_non_comment_token()
            if token is None:
                break

            # beginbfchar
            if token.text == "beginbfchar":
                n = int(prev_token.text)
                for j in range(0, n):
                    c = self._hex_string_to_int_or_tuple(tok.read_object())
                    uc = self._hex_string_to_int_or_tuple(tok.read_object())
                    self.add_symbol(c, uc)
                continue

            # beginbfrange
            if token.text == "beginbfrange":
                n = int(prev_token.text)
                for j in range(0, n):

                    c_start_token = tok.read_object()
                    c_start = int(c_start_token.get_text(), 16)

                    c_end_token = tok.read_object()
                    c_end = int(c_end_token.get_text(), 16)

                    tmp = tok.read_object()
                    if isinstance(tmp, PDFHexString):
                        uc = self._hex_string_to_int_or_tuple(tmp)
                        for k in range(0, c_end - c_start + 1):
                            if isinstance(uc, int):
                                self.add_symbol(c_start + k, uc + k)
                            elif isinstance(uc, tuple):
                                self.add_symbol(c_start + k, (uc[0], uc[1] + k))

                    elif isinstance(tmp, PDFArray):
                        for k in range(0, c_end - c_start + 1):
                            uc = self._hex_string_to_int_or_tuple(tmp[k])
                            self.add_symbol(c_start + k, uc)

            # default
            prev_token = token

        return self

    def _hex_string_to_int_or_tuple(
        self, token: PDFHexString
    ) -> Union[int, Tuple[int, int]]:
        uc_hex = token.get_text().replace(" ", "")
        uc = [int(uc_hex[k : k + 4], 16) for k in range(0, int(len(uc_hex)), 4)]
        return tuple(uc) if len(uc) > 1 else uc[0]
