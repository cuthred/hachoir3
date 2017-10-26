"""
information based on README:

RAR parser

Status: can only read higher-level attructures
Author: Christophe Gisquet

based on:



               RAR version 3.91 - Technical information
               ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

THE ARCHIVE FORMAT DESCRIBED BELOW IS ONLY VALID FOR VERSIONS SINCE 1.50

==========================================================================
                         RAR archive file format
==========================================================================

   Archive file consists of variable length blocks. The order of these
blocks may vary, but the first block must be a marker block followed by
an archive header block.

   Each block begins with the following fields:

HEAD_CRC       2 bytes     CRC of total block or block part
HEAD_TYPE      1 byte      Block type
HEAD_FLAGS     2 bytes     Block flags
HEAD_SIZE      2 bytes     Block size
ADD_SIZE       4 bytes     Optional field - added block size

   Field ADD_SIZE present only if (HEAD_FLAGS & 0x8000) != 0

   Total block size is HEAD_SIZE if (HEAD_FLAGS & 0x8000) == 0
and HEAD_SIZE+ADD_SIZE if the field ADD_SIZE is present - when
(HEAD_FLAGS & 0x8000) != 0.

   In each block the followings bits in HEAD_FLAGS have the same meaning:

  0x4000 - if set, older RAR versions will ignore the block
           and remove it when the archive is updated.
           if clear, the block is copied to the new archive
           file when the archive is updated;

  0x8000 - if set, ADD_SIZE field is present and the full block
           size is HEAD_SIZE+ADD_SIZE.

  Declared block types:

HEAD_TYPE=0x72          marker block
HEAD_TYPE=0x73          archive header
HEAD_TYPE=0x74          file header
HEAD_TYPE=0x75          old style comment header
HEAD_TYPE=0x76          old style authenticity information
HEAD_TYPE=0x77          old style subblock
HEAD_TYPE=0x78          old style recovery record
HEAD_TYPE=0x79          old style authenticity information
HEAD_TYPE=0x7a          subblock

   Comment block is actually used only within other blocks and doesn't
exist separately.

   Archive processing is made in the following manner:

1. Read and check marker block
2. Read archive header
3. Read or skip HEAD_SIZE-sizeof(MAIN_HEAD) bytes
4. If end of archive encountered then terminate archive processing,
   else read 7 bytes into fields HEAD_CRC, HEAD_TYPE, HEAD_FLAGS,
   HEAD_SIZE.
5. Check HEAD_TYPE.
   if HEAD_TYPE==0x74
     read file header ( first 7 bytes already read )
     read or skip HEAD_SIZE-sizeof(FILE_HEAD) bytes
     if (HEAD_FLAGS & 0x100)
       read or skip HIGH_PACK_SIZE*0x100000000+PACK_SIZE bytes
     else
       read or skip PACK_SIZE bytes
   else
     read corresponding HEAD_TYPE block:
       read HEAD_SIZE-7 bytes
       if (HEAD_FLAGS & 0x8000)
         read ADD_SIZE bytes
6. go to 4.


==========================================================================
                               Block Formats
==========================================================================


   Marker block ( MARK_HEAD )


HEAD_CRC        Always 0x6152
2 bytes

HEAD_TYPE       Header type: 0x72
1 byte

HEAD_FLAGS      Always 0x1a21
2 bytes

HEAD_SIZE       Block size = 0x0007
2 bytes

   The marker block is actually considered as a fixed byte
sequence: 0x52 0x61 0x72 0x21 0x1a 0x07 0x00



   Archive header ( MAIN_HEAD )


HEAD_CRC        CRC of fields HEAD_TYPE to RESERVED2
2 bytes

HEAD_TYPE       Header type: 0x73
1 byte

HEAD_FLAGS      Bit flags:
2 bytes
                0x0001  - Volume attribute (archive volume)
                0x0002  - Archive comment present
                          RAR 3.x uses the separate comment block
                          and does not set this flag.

                0x0004  - Archive lock attribute
                0x0008  - Solid attribute (solid archive)
                0x0010  - New volume naming scheme ('volname.partN.rar')
                0x0020  - Authenticity information present
                          RAR 3.x does not set this flag.

                0x0040  - Recovery record present
                0x0080  - Block headers are encrypted
                0x0100  - First volume (set only by RAR 3.0 and later)

                other bits in HEAD_FLAGS are reserved for
                internal use

HEAD_SIZE       Archive header total size including archive comments
2 bytes

RESERVED1       Reserved
2 bytes

RESERVED2       Reserved
4 bytes



   File header (File in archive)


HEAD_CRC        CRC of fields from HEAD_TYPE to FILEATTR
2 bytes         and file name

HEAD_TYPE       Header type: 0x74
1 byte

HEAD_FLAGS      Bit flags:
2 bytes
                0x01 - file continued from previous volume
                0x02 - file continued in next volume
                0x04 - file encrypted with password

                0x08 - file comment present
                       RAR 3.x uses the separate comment block
                       and does not set this flag.

                0x10 - information from previous files is used (solid flag)
                       (for RAR 2.0 and later)

                bits 7 6 5 (for RAR 2.0 and later)

                     0 0 0    - dictionary size   64 KB
                     0 0 1    - dictionary size  128 KB
                     0 1 0    - dictionary size  256 KB
                     0 1 1    - dictionary size  512 KB
                     1 0 0    - dictionary size 1024 KB
                     1 0 1    - dictionary size 2048 KB
                     1 1 0    - dictionary size 4096 KB
                     1 1 1    - file is directory

               0x100 - HIGH_PACK_SIZE and HIGH_UNP_SIZE fields
                       are present. These fields are used to archive
                       only very large files (larger than 2Gb),
                       for smaller files these fields are absent.

               0x200 - FILE_NAME contains both usual and encoded
                       Unicode name separated by zero. In this case
                       NAME_SIZE field is equal to the length
                       of usual name plus encoded Unicode name plus 1.

                       If this flag is present, but FILE_NAME does not
                       contain zero bytes, it means that file name
                       is encoded using UTF-8.

               0x400 - the header contains additional 8 bytes
                       after the file name, which are required to
                       increase encryption security (so called 'salt').

               0x800 - Version flag. It is an old file version,
                       a version number is appended to file name as ';n'.

              0x1000 - Extended time field present.

              0x8000 - this bit always is set, so the complete
                       block size is HEAD_SIZE + PACK_SIZE
                       (and plus HIGH_PACK_SIZE, if bit 0x100 is set)

HEAD_SIZE       File header full size including file name and comments
2 bytes

PACK_SIZE       Compressed file size
4 bytes

UNP_SIZE        Uncompressed file size
4 bytes

HOST_OS         Operating system used for archiving
1 byte                 0 - MS DOS
                       1 - OS/2
                       2 - Win32
                       3 - Unix
                       4 - Mac OS
                       5 - BeOS

FILE_CRC        File CRC
4 bytes

FTIME           Date and time in standard MS DOS format
4 bytes

UNP_VER         RAR version needed to extract file
1 byte
                Version number is encoded as
                10 * Major version + minor version.

METHOD          Packing method
1 byte
                0x30 - storing
                0x31 - fastest compression
                0x32 - fast compression
                0x33 - normal compression
                0x34 - good compression
                0x35 - best compression

NAME_SIZE       File name size
2 bytes

ATTR            File attributes
4 bytes

HIGH_PACK_SIZE  High 4 bytes of 64 bit value of compressed file size.
4 bytes         Optional value, presents only if bit 0x100 in HEAD_FLAGS
                is set.

HIGH_UNP_SIZE   High 4 bytes of 64 bit value of uncompressed file size.
4 bytes         Optional value, presents only if bit 0x100 in HEAD_FLAGS
                is set.

FILE_NAME       File name - string of NAME_SIZE bytes size

SALT            present if (HEAD_FLAGS & 0x400) != 0
8 bytes

EXT_TIME        present if (HEAD_FLAGS & 0x1000) != 0
variable size

other new fields may appear here.


==========================================================================
                              Application notes
==========================================================================

   1. To process an SFX archive you need to skip the SFX module searching
for the marker block in the archive. There is no marker block sequence (0x52
0x61 0x72 0x21 0x1a 0x07 0x00) in the SFX module itself.

   2. The CRC is calculated using the standard polynomial 0xEDB88320. In
case the size of the CRC is less than 4 bytes, only the low order bytes
are used.

************************
and unrar source
"""

from hachoir.parser import Parser
from hachoir.field import (StaticFieldSet, FieldSet,
                           Bit, Bits, Enum,
                           UInt8, UInt16, UInt32, UInt64,
                           String, TimeDateMSDOS32,
                           NullBytes, NullBits, Bytes, RawBytes)
from hachoir.core.text_handler import textHandler, filesizeHandler, hexadecimal
from hachoir.core.endian import LITTLE_ENDIAN
from hachoir.parser.common.msdos import MSDOSFileAttr32
import collections

MAX_FILESIZE = 1000 * 1024 * 1024

BLOCK_NAME = {
    0x72: "Marker",
    0x73: "Archive Main",
    0x74: "File",
    0x75: "Comment",
    0x76: "Authenticity Information",
    0x77: "Old-format service",
    0x78: "Recovery record",
    0x79: "Signature",
    0x7A: "New-format service",
    0x7B: "Archive end",
}

COMPRESSION_NAME = {
    0x30: "Storing",
    0x31: "Fastest compression",
    0x32: "Fast compression",
    0x33: "Normal compression",
    0x34: "Good compression",
    0x35: "Best compression"
}

OS_MSDOS = 0
OS_WIN32 = 2
OS_NAME = {
    0: "MS DOS",
    1: "OS/2",
    2: "Win32",
    3: "Unix",
    4: "Max OS",
    5: "BeOS",
}

DICTIONARY_SIZE = {
    0: "Dictionary size 64 Kb",
    1: "Dictionary size 128 Kb",
    2: "Dictionary size 256 Kb",
    3: "Dictionary size 512 Kb",
    4: "Dictionary size 1024 Kb",
    5: "Dictionary size 2048 Kb",
    6: "Dictionary size 4096 Kb",
    7: "File is a directory",
}


def format_rar_version(field):
    """
    Decodes the RAR version stored on 1 byte
    """
    return "%u.%u" % divmod(field.value, 10)


def common_flags(s):
    yield Bit(s, "has_added_size", "Additional field indicating additional size")
    yield Bit(s, "is_ignorable", "Old versions of RAR should ignore this block when copying data")


# Block type == 0x73 MAIN_HEAD
class ArchiveFlags(StaticFieldSet):
    format = (
        (Bit, "vol", "Archive volume"),
        (Bit, "has_comment", "Whether there is a comment"),
        (Bit, "is_locked", "Archive volume"),
        (Bit, "is_solid", "Whether files can be extracted separately"),
        (Bit, "new_numbering", "New numbering, or compressed comment"),  # From unrar
        (Bit, "has_auth_information", "The integrity/authenticity of the archive can be checked"),
        (Bit, "has_recovery_record", "Recovery record present"),
        (Bit, "is_encrypted", "Block headers are encrypted"),
        (Bit, "is_first_vol", "Whether it is the first volume"),
        (NullBits, "internal", 7, "Reserved for 'internal use'")
    )


def archive_flags(p_s):
    yield ArchiveFlags(p_s, "flags", "Archiver block flags")


def archive_header(p_s):
    yield NullBytes(p_s, "reserved[]", 2, "Reserved word")
    yield NullBytes(p_s, "reserved[]", 4, "Reserved dword")


# Block type == 0x74
class FileFlags(FieldSet):
    static_size = 16

    def createFields(self):
        yield Bit(self, "continued_from", "File continued from previous volume")
        yield Bit(self, "continued_in", "File continued in next volume")
        yield Bit(self, "is_encrypted", "File encrypted with password")
        yield Bit(self, "has_comment", "File comment present")
        yield Bit(self, "is_solid", "Information from previous files is used (solid flag)")
        # The 3 following lines are what blocks more staticity
        yield Enum(Bits(self, "dictionary_size", 3, "Dictionary size"), DICTIONARY_SIZE)
#        for bit in common_flags(self):
#            yield bit
        yield Bit(self, "is_large", "file64 operations needed")
        yield Bit(self, "is_unicode", "Filename also encoded using Unicode")
        yield Bit(self, "has_salt", "Has salt for encryption")
        yield Bit(self, "uses_file_version", "File versioning is used")
        yield Bit(self, "has_ext_time", "Extra time ??")
        yield NullBits(self, "reserved", 2, "Reserved for 'internal use'")
        yield Bit(self, "has_ext_flags", "Extra flag ??")


def file_flags(p_s):
    yield FileFlags(p_s, "flags", "File block flags")


class ExtTime(FieldSet):

    def createFields(self):
        yield textHandler(UInt16(self, "time_flags", "Flags for extended time"), hexadecimal)
        l_flags = self["time_flags"].value
        for l_index in range(4):
            l_rmode = l_flags >> ((3 - l_index) * 4)
            if l_rmode & 8:
                if l_index:
                    yield TimeDateMSDOS32(self, "dos_time[]", "DOS Time")
                if l_rmode & 3:
                    yield RawBytes(self, "remainder[]", l_rmode & 3, "Time remainder")


def special_header(p_s, p_is_file):
    yield filesizeHandler(UInt32(p_s, "compressed_size", "Compressed size (bytes)"))
    yield filesizeHandler(UInt32(p_s, "uncompressed_size", "Uncompressed size (bytes)"))
    yield Enum(UInt8(p_s, "host_os", "Operating system used for archiving"), OS_NAME)
    yield textHandler(UInt32(p_s, "crc32", "File CRC32"), hexadecimal)
    yield TimeDateMSDOS32(p_s, "ftime", "Date and time (MS DOS format)")
    yield textHandler(UInt8(p_s, "version", "RAR version needed to extract file"), format_rar_version)
    yield Enum(UInt8(p_s, "method", "Packing method"), COMPRESSION_NAME)
    yield filesizeHandler(UInt16(p_s, "filename_length", "File name size"))
    if p_s["host_os"].value in (OS_MSDOS, OS_WIN32):
        yield MSDOSFileAttr32(p_s, "file_attr", "File attributes")
    else:
        yield textHandler(UInt32(p_s, "file_attr", "File attributes"), hexadecimal)

    # Start additional field from unrar
    if p_s["flags/is_large"].value:
        yield filesizeHandler(UInt64(p_s, "large_size", "Extended 64bits filesize"))

    # End additional field
    l_size = p_s["filename_length"].value
    if l_size > 0:
        if p_s["flags/is_unicode"].value:
            l_charset = "UTF-8"
        else:
            l_charset = "ISO-8859-15"
        yield String(p_s, "filename", l_size, "Filename", charset=l_charset)
    # Start additional fields from unrar - file only
    if p_is_file:
        if p_s["flags/has_salt"].value:
            yield textHandler(UInt8(p_s, "salt", "Salt"), hexadecimal)
        if p_s["flags/has_ext_time"].value:
            yield ExtTime(p_s, "extra_time", "Extra time info")


def file_header(p_s):
    return special_header(p_s, True)


def file_body(p_s):
    # File compressed data
    l_size = p_s["compressed_size"].value
    if p_s["flags/is_large"].value:
        l_size += p_s["large_size"].value
    if l_size > 0:
        yield RawBytes(p_s, "compressed_data", l_size, "File compressed data")


def file_description(p_s):
    return "File entry: %s (%s)" % \
           (p_s["filename"].display, p_s["compressed_size"].display)


# Block type == 0x75
def old_comment_header(p_s):
    yield filesizeHandler(UInt16(p_s, "total_size", "Comment header size + comment size"))
    yield filesizeHandler(UInt16(p_s, "uncompressed_size", "Uncompressed comment size"))
    yield UInt8(p_s, "required_version", "RAR version needed to extract comment")
    yield UInt8(p_s, "packing_method", "Comment packing method")
    yield UInt16(p_s, "comment_crc16", "Comment CRC")


def old_comment_body(p_s):
    l_size = p_s["total_size"].value - p_s.current_size
    if l_size > 0:
        yield RawBytes(p_s, "comment_data", l_size, "Compressed comment data")


# Block type == 0x76
def old_av_info_header(p_s):
    yield filesizeHandler(UInt16(p_s, "total_size", "Total block size"))
    yield UInt8(p_s, "version", "Version needed to decompress", handler=hexadecimal)
    yield UInt8(p_s, "method", "Compression method", handler=hexadecimal)
    yield UInt8(p_s, "av_version", "Version for AV", handler=hexadecimal)
    yield UInt32(p_s, "av_crc", "AV info CRC32", handler=hexadecimal)


def old_av_info_body(p_s):
    l_size = p_s["total_size"].value - p_s.current_size
    if l_size > 0:
        yield RawBytes(p_s, "av_info_data", l_size, "AV info")


# Block type == 0x78
def old_recovery_header(p_s):
    yield filesizeHandler(UInt32(p_s, "total_size"))
    yield textHandler(UInt8(p_s, "version"), hexadecimal)
    yield UInt16(p_s, "rec_sectors")
    yield UInt32(p_s, "total_blocks")
    yield RawBytes(p_s, "mark", 8)


# Block type == 0x79
def old_signature_header(p_s):
    yield TimeDateMSDOS32(p_s, "creation_time")
    yield filesizeHandler(UInt16(p_s, "arc_name_size"))
    yield filesizeHandler(UInt16(p_s, "user_name_size"))


# Block type == 0x7A
def new_sub_header(p_s):
    return special_header(p_s, False)


# Block type == 0x7B
class EndFlags(StaticFieldSet):
    format = (
        (Bit, "has_next_vol", "Whether there is another next volume"),
        (Bit, "has_data_crc", "Whether a CRC value is present"),
        (Bit, "rev_space"),
        (Bit, "has_vol_number", "Whether the volume number is present"),
        (Bits, "unused[]", 4),
        (Bit, "has_added_size", "Additional field indicating additional size"),
        (Bit, "is_ignorable",
         "Old versions of RAR should ignore this block when copying data"),
        (Bits, "unused[]", 6),
    )


def end_flags(p_s):
    yield EndFlags(p_s, "flags", "End block flags")


# common Block
class BlockFlags(FieldSet):
    static_size = 16

    def createFields(self):
        yield textHandler(Bits(self, "unused[]", 8, "Unused flag bits"), hexadecimal)
        yield Bit(self, "has_added_size", "Additional field indicating additional size")
        yield Bit(self, "is_ignorable", "Old versions of RAR should ignore this block when copying data")
        yield Bits(self, "unused[]", 6)


class Block(FieldSet):
    BLOCK_INFO = {
        # None means 'use default function'
        0x72: ("marker", "Archive header", None, None, None),
        0x73: ("archive_start", "Archive main block", archive_flags, archive_header, None),
        0x74: ("file[]", file_description, file_flags, file_header, file_body),
        0x75: ("comment[]", "Stray comment", None, old_comment_header, old_comment_body),
        0x76: ("av_info[]", "Authenticity information", None, old_av_info_header, old_av_info_body),
        0x77: ("sub_block[]", "Old-format service block", None, new_sub_header, file_body),
        0x78: ("recovery[]", "Recovery block", None, old_recovery_header, None),
        0x79: ("signature", "Signature block", None, old_signature_header, None),
        0x7A: ("new_sub_block[]", "New-format service block", file_flags,
               new_sub_header, file_body),
        0x7B: ("archive_end", "Archive end block", end_flags, None, None),
    }

    def __init__(self, parent, name):
        FieldSet.__init__(self, parent, name)

        # access file "block_type" which is not known yet, therefore createFields is called
        # until "block_type" is returned
        l_t = self["block_type"].value
        if l_t in self.BLOCK_INFO:
            self._name, l_desc, l_parseFlags, l_parseHeader, l_parseBody = self.BLOCK_INFO[
                l_t]
            if isinstance(l_desc, collections.Callable):
                self.createDescription = lambda: l_desc(self)
            elif l_desc:
                self._description = l_desc
            if l_parseFlags:
                self.parse_flags = lambda: l_parseFlags(self)
            if l_parseHeader:
                self.parse_header = lambda: l_parseHeader(self)
            if l_parseBody:
                self.parse_body = lambda: l_parseBody(self)
        else:
            self.info("Processing as unknown block of type %u" % l_t)

        self._size = 8 * self["block_size"].value
        if l_t == 0x74 or l_t == 0x7A:
            self._size += 8 * self["compressed_size"].value
            if "is_large" in self["flags"] and self["flags/is_large"].value:
                self._size += 8 * self["large_size"].value
        elif "has_added_size" in self:
            self._size += 8 * self["added_size"].value
        # TODO: check if any other member is needed here

    def createFields(self):
        # first two fields are always CRC16 and block_type
        yield textHandler(UInt16(self, "crc16", "Block CRC16"), hexadecimal)
        yield textHandler(UInt8(self, "block_type", "Block type"), hexadecimal)

        # Parse flags
        # this is set in __init__ based on block_type
        yield from self.parse_flags()

        # Get block size
        yield filesizeHandler(UInt16(self, "block_size", "Block size"))

        # Parse remaining header
        yield from self.parse_header()

        # Finish header with stuff of unknown size
        size = self["block_size"].value - (self.current_size // 8)
        if size > 0:
            yield RawBytes(self, "unknown", size, "Unknow data (UInt32 probably)")

        # Parse body
        yield from self.parse_body()

    def createDescription(self):
        return "Block entry: %s" % self["type"].display

    def parse_flags(self):
        yield BlockFlags(self, "flags", "Block header flags")

    def parse_header(self):
        if "has_added_size" in self["flags"] and \
           self["flags/has_added_size"].value:
            yield filesizeHandler(UInt32(self, "added_size",
                                         "Supplementary block size"))

    def parse_body(self):
        """
        Parse what is left of the block
        """
        l_size = self["block_size"].value - (self.current_size // 8)
        if "has_added_size" in self["flags"] and self["flags/has_added_size"].value:
            l_size += self["added_size"].value
        if l_size > 0:
            yield RawBytes(self, "body", l_size, "Body data")


class RarFile(Parser):
    RARFMT_NONE, RARFMT14, RARFMT15, RARFMT50, RARFMT_FUTURE = range(5)
    PARSER_TAGS = {
        "id": "rar",
        "category": "archive",
        "file_ext": ("rar",),
        "mime": ("application/x-rar-compressed", ),
        "min_size": 7 * 8,
        "magic_regex": ((
                        "RE~^|Rar!\x1A\x07[\x00\x01\x02]",
                        0),),
        "description": "Roshal archive (RAR)",
    }
    endian = LITTLE_ENDIAN

    # noinspection PyAttributeOutsideInit
    def validate(self):
        l_bytes = self.stream.readBytes(0, 7)
        self.rarformat = self.RARFMT_NONE
        if l_bytes[0:4] == b"RE~^":
            self.rarformat = self.RARFMT14
        elif l_bytes[0:6] == b"Rar!\x1A\x07":
            if l_bytes[6:7] == b"\x00":
                self.rarformat = self.RARFMT15
            elif l_bytes[6:7] == b"\x01":
                self.rarformat = self.RARFMT50
            elif l_bytes[6:7] == b"\x02":
                self.rarformat = self.RARFMT_FUTURE

        if self.rarformat == self.RARFMT_NONE:
            return "Invalid magic"
        return True

    def createFields(self):
        if self.rarformat == self.RARFMT14:
            yield Bytes(self, "signature", 4, "RAR signature")
        else:
            yield Bytes(self, "signature", 7, "RAR signature")
        while not self.eof:
            # rar file is build from Blocks, therefore parse each block separately
            yield Block(self, "block[]")

    def createContentSize(self):
        l_start = 0
        l_end = MAX_FILESIZE * 8
        l_pos = self.stream.searchBytes(
            b"\xC4\x3D\x7B\x00\x40\x07\x00", l_start, l_end)
        if l_pos is not None:
            return l_pos + 7 * 8
        return None
