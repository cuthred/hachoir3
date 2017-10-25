"""
ISO 9660 (cdrom) file system parser.

Documents:
- Standard ECMA-119 (december 1987)
  http://www.nondot.org/sabre/os/files/FileSystems/iso9660.pdf

Author: Victor Stinner
Creation: 11 july 2006

Updated by: Oliver Stabel

additional info taken from
http://wiki.osdev.org/ISO_9660
https://github.com/barneygale/iso9660/blob/master/iso9660.py
http://www.gnu.org/software/libcdio/doxygen/structiso9660__svd__s.html#details
http://www.gnu.org/software/libcdio/doxygen/iso9660_8h.html
http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-119.pdf

RockRidge Extension:
http://en.wikipedia.org/wiki/Rock_Ridge
http://libburnia-project.org/wiki/AAIP
http://www.ymi.com/ymi/sites/default/files/pdf/Rockridge.pdf

Joliet Spec:
http://www.singlix.org/trdos/Joliet.html#unicode

d-characters are specified as: [0x30-0x39,0x41-0x5A,0x5F]
a-characters are specified as: [0x20-0x22,0x25-0x3F,0x41-0x5A,0x5F]
"""

from hachoir.parser import Parser
from hachoir.field import (FieldSet, ParserError,
                           UInt8, UInt32, Enum,
                           NullBytes, RawBytes, String)
from hachoir.core.endian import LITTLE_ENDIAN, BIG_ENDIAN
from hachoir.core.tools import humanDatetime
from datetime import datetime
from hachoir.field import Bits, FieldError
from sys import byteorder
import string


class GenericISO9660Integer(Bits):
    """
    Generic integer class used to generate other classes. The class holds an integer value in both endian
    representations which is used in iso9660
    ISO9660 usually stores values in LITTLE_ENDIAN/BIG_ENDIAN order
    """
    def __init__(self, p_parent, p_name, p_signed, p_size, p_description=None):
        if not (8 <= p_size <= 16384):
            raise FieldError("Invalid integer size (%s): have to be in 8..16384" % p_size)
        Bits.__init__(self, p_parent, p_name, p_size, p_description)
        self.signed = p_signed

    def createValue(self):
        if byteorder == "little":
            return self._parent.stream.readInteger(self.absolute_address, self.signed, self._size//2,
                                                   LITTLE_ENDIAN)
        elif byteorder == "big":
            return self._parent.stream.readInteger(self.absolute_address+self._size//2, self.signed, self._size//2,
                                                   BIG_ENDIAN)
        else:
            return self._parent.stream.readInteger(self.absolute_address, self.signed, self._size//2,
                                                   self._parent.endian)


def iso9660_integer_factory(p_name, p_is_signed, p_size, p_doc):
    # noinspection PyShadowingNames
    class ISO9660Integer(GenericISO9660Integer):
        __doc__ = p_doc
        static_size = p_size * 2

        def __init__(self, p_parent, p_name, p_description=None):
            GenericISO9660Integer.__init__(self, p_parent, p_name, p_is_signed, p_size * 2, p_description)
    l_cls = ISO9660Integer
    l_cls.__name__ = p_name
    return l_cls


ISO9660UInt16_LSB_MSB = iso9660_integer_factory("ISO9660UInt16_LSB_MSB", False, 16,
                                                "ISO9660 Little-endian followed by big-endian unsigned 16-bit integer")
ISO9660UInt32_LSB_MSB = iso9660_integer_factory("ISO9660UInt32_LSB_MSB", False, 32,
                                                "ISO9660 Little-endian followed by big-endian unsigned 32-bit integer")


class ISO9660DirTimeDate(FieldSet):
    """
    56-bit timestamp
    """
    static_size = 56

    def createFields(self):
        yield Bits(self, "year", 8)
        yield Bits(self, "month", 8)
        yield Bits(self, "day", 8)

        yield Bits(self, "hour", 8)
        yield Bits(self, "minute", 8)
        yield Bits(self, "second", 8)
        yield Bits(self, "offset", 8)

    def createValue(self):
        return datetime(
            1900 + self["year"].value, self["month"].value, self["day"].value,
            self["hour"].value, self["minute"].value, self["second"].value)

    def createDisplay(self):
        return humanDatetime(self.value)


SECTOR_SIZE = 2048
SECTOR_HEAD_SIZE = 7
SECTOR_DATA_SIZE = SECTOR_SIZE - SECTOR_HEAD_SIZE

ISO_MAX_SYSTEM_ID = 32
ISO_MAX_VOLUME_ID = 32


class ComponentRecord(FieldSet):
    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)
        self.printDebug()

    def createFields(self):
        yield UInt8(self, "component_flags", "Flags")
        yield UInt8(self, "component_len", "length in bytes of the component or portion thereof recorded in the" 
                                           " current Component Record (without flags and len)")
        l_len = self["component_len"].value
        if l_len != 0:
            yield String(self, "component_content", l_len, "Component or portion thereof recorded in the current" 
                                                           " Component Record")


class SystemUseEntry(FieldSet):
    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)

    def createFields(self):
        yield String(self, "sig", 2, "System Use Entry Signature Word")
        yield UInt8(self, "len_sue", "System Use Entry Length")
        yield UInt8(self, "version", "System Use Entry version")
        l_type = self["sig"].value
        if l_type == "CE":
            # Continuation area
            yield ISO9660UInt32_LSB_MSB(self, "block_location", "Block Location of Continuation Area (iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "offset", "Offset to Start of Continuation Area (iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "length_cont_area", "Length of the Continuation Area (iso9660 format)")
        elif l_type == "PD":
            # Padding Field
            l_len = self["len_sue"].value - 4
            yield NullBytes(self, "padding[]", l_len)
        elif l_type == "SP":
            # System Use Sharing Protocol Indicator
            yield RawBytes(self, "check_bytes", 2, "Check bytes for SP, should always be 0xBE, 0xEF")
            yield UInt8(self, "len_skp", "Number of bytes to be skipped within the System Use field of each" 
                                         " Directory Record")
        elif l_type == "ST":
            # System Use Sharing Protocol Terminator
            # no more additional fields
            pass
        elif l_type == "ER":
            # Extensions Reference
            yield UInt8(self, "len_id", "Length in bytes of the Extension Identifier recorded in this \"ER\"" 
                                        " System Use Entry.")
            yield UInt8(self, "len_des", "Length in bytes of the Extension Descriptor recorded in this \"ER\""
                                         " System Use Entry.")
            yield UInt8(self, "len_src", "Length in bytes of the Extension Specification Source recorded in this"
                                         " \"ER\" System Use Entry.")
            yield UInt8(self, "ext_ver", "Identification of the version of the system-specific extensions to which" 
                                         " this \"ER\" System Use Entry refers")
            l_len_id = self["len_id"].value
            # mandatory
            yield String(self, "ext_id", l_len_id, "The exact content of this field is specified by the organization"
                                                   " which defined the extensions to which this \"ER\" System Use Entry" 
                                                   " refers")
            l_len_des = self["len_des"].value
            if l_len_des > 0:
                # optional
                yield String(self, "ext_des", l_len_des, "The minimal content of this field may be specified or" 
                                                         " recommended by the organization which defined the extensions" 
                                                         " to which this \"ER\" System Use Entry refers")
            l_len_src = self["len_src"].value
            # mandatory
            yield String(self, "ext_src", l_len_src, "The minimal content of this field may be specified or recommended" 
                                                     " by the organization which defined the extensions to which this" 
                                                     " \"ER\" System Use Entry refers")
        elif l_type == "ES":
            # Extension Selector
            yield UInt8(self, "ext_seq", "Extension Sequence Number of the extension specification utilized in the" 
                                         " entries immediately following this System Use Entry")
        elif l_type == "RR":
            #  Rock Ridge extensions in-use indicator (note: dropped from standard after version 1.09)
            yield RawBytes(self, "unknown", 1, "unknown value for RR")
        elif l_type == "PX":
            # POSIX file attributes
            yield ISO9660UInt32_LSB_MSB(self, "file_mode", "st_mode field specified in POSIX (iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "links", "st_nlink field of POSIX (iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "uid", "st_uid field of POSIX (iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "gid", "st_gid field of POSIX (iso9660 format)")
            if self["len_sue"].value > 36:
                yield ISO9660UInt32_LSB_MSB(self, "serial", "st_ino field of POSIX (iso9660 format)")
        elif l_type == "PN":
            # POSIX device numbers
            yield ISO9660UInt32_LSB_MSB(self, "dev_t_high", "high order 32-bits of the 64 bit device number" 
                                                            " (iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "dev_t_low", "low order 32-bits of the 64 bit device number" 
                                                           " (iso9660 format)")
        elif l_type == "SL":
            # symbolic link
            yield UInt8(self, "flags", "Flags")
            l_len = self["len_sue"].value - 5
            while l_len > 0:
                l_comp = ComponentRecord(self, "component[]")
                yield l_comp
                l_len -= (2 + l_comp["component_len"].value)
        elif l_type == "NM":
            # alternate name
            yield UInt8(self, "flags", "Flags")
            l_len = self["len_sue"].value - 5
            yield String(self, "name_content", l_len, "Content or portion thereof of the Alternate Name")
        elif l_type == "CL":
            # child link
            yield ISO9660UInt32_LSB_MSB(self, "child_loc", "Logical Block Number of the first Logical Block allocated" 
                                                           " to the moved directory (iso9660 format)")
        elif l_type == "PL":
            # parent link
            yield ISO9660UInt32_LSB_MSB(self, "parent_loc", "Logical Block Number of the first Logical Block allocated" 
                                                            " to the original parent directory of the moved directory" 
                                                            " (iso9660 format)")
        elif l_type == "RE":
            # relocated directory
            pass
        elif l_type == "TF":
            # time stamp
            yield UInt8(self, "flags", "Flags")
            l_flags = self["flags"].value
            l_len = self["len_sue"].value - 5
            while l_len > 0:
                if l_flags & 0x80:
                    yield String(self, "timestamp[]", 17, "Timestamp", strip=" ")
                    l_len -= 17
                else:
                    yield RawBytes(self, "timestamp[]", 7, "Timestamp")
                    l_len -= 7
        elif l_type == "SF":
            # sparse file data
            yield ISO9660UInt32_LSB_MSB(self, "size_high", "high order 32-bits of the 64 bit file size." 
                                                           "(iso9660 format)")
            yield ISO9660UInt32_LSB_MSB(self, "size_low", "low order 32-bits of the 64 bit file size." 
                                                          "(iso9660 format)")
            yield UInt8(self, "table_depth", "depth of the First Index Block, and therefore the maximum virtual size" 
                                             " of the file")
        elif l_type == "AA":
            # Apple extension, preferred
            self.warning("SystemUseEntry AA not implemented yet")
            l_len = self["len_sue"].value - 4
            yield RawBytes(self, "unknown", l_len, "no docu from Apple")
        elif l_type == "AB":
            # Apple extension, old
            self.warning("SystemUseEntry AB not implemented yet")
            l_len = self["len_sue"].value - 4
            yield RawBytes(self, "unknown", l_len, "no docu from Apple")
        elif l_type == "AS":
            #  Amiga file properties
            # see http://www.estamos.de/makecd/Rock_Ridge_Amiga_Specific
            self.warning("SystemUseEntry AS not implemented yet")
            l_len = self["len_sue"].value - 4
            yield RawBytes(self, "unknown", l_len, "amiga specific data")
        elif l_type == "ZF":
            # see http://libburnia-project.org/wiki/zisofs
            self.warning("SystemUseEntry ZF not implemented yet")
            l_len = self["len_sue"].value - 4
            yield RawBytes(self, "unknown", l_len, "zisofs specific data")
        elif l_type == "XA":
            self.warning("SystemUseEntry XA not implemented yet")
            l_len = self["len_sue"].value - 4
            yield RawBytes(self, "unknown", l_len, "mkisofs specific data")
        else:
            self.warning("SystemUseEntry %s not implemented yet" % l_type)
            l_len = self["len_sue"].value - 4
            yield RawBytes(self, "unknown", l_len, "unknown data for sue %s" % l_type)


class DirRecord(FieldSet):
    DEBUG = False

    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)
        self.printDebug()

    def createFields(self):
        yield UInt8(self, "rec_length", "Length of Directory Record")
        yield UInt8(self, "xa_length", "Extended Attribute Record length")
        yield ISO9660UInt32_LSB_MSB(self, "extent_loc", "Location of extent (LBA) (iso9660 format)")
        yield ISO9660UInt32_LSB_MSB(self, "size", "Data length (size of extent) (iso9660 format)")
        yield ISO9660DirTimeDate(self, "recording_time", "Recording date and time")
        yield UInt8(self, "file_flags", "File Flags")
        yield UInt8(self, "file_unit_size", "File unit size for files recorded in interleaved mode")
        yield UInt8(self, "interleave_gap", "Interleave gap size for files recorded in interleaved mode")
        yield ISO9660UInt16_LSB_MSB(self, "volume_sequence_number", "Volume sequence number (iso9660 format)")
        # upto here, the record has a length of 32 Bytes
        l_length = self["rec_length"].value
        l_length -= 32

        yield UInt8(self, "name_length", "Length of file identifier (filename)")
        l_len = self["name_length"].value
        l_length -= 1

        l_length -= l_len
        if l_len == 1:
            yield NullBytes(self, "unused[]", 1)
        else:
            yield String(self, "filename", l_len, "Filename")

        # if length of the "File Identifier" is odd, we need to add 1 byte padding
        if l_len % 2 == 0:
            l_length -= 1
            yield NullBytes(self, "unused[]", 1)

        # if length is now still > 0, we may have RR extensions:
        while l_length > 0:
            l_offset = self["rec_length"].value - l_length
            l_read_ahead = self.stream.readBytes(self.absolute_address + l_offset*8, 1)
            if l_read_ahead.decode() in string.ascii_uppercase:
                l_susp = SystemUseEntry(self, "system_use_entry[]")
                yield l_susp
                l_length -= l_susp["len_sue"].value
            else:
                yield NullBytes(self, "unused[]", l_length)
                break


class VolumePartitionDescriptor(FieldSet):
    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)

    def createFields(self):
        yield NullBytes(self, "unused[]", 1)
        yield String(self, "system_id", ISO_MAX_SYSTEM_ID, "System identifier", strip=" ")
        yield String(self, "volume_id", ISO_MAX_VOLUME_ID, "Volume identifier", strip=" ")
        yield ISO9660UInt32_LSB_MSB(self, "volume_partition_location", "Logical Block Number of the first Logical" 
                                                                       " Block allocated to the Volume Partition" 
                                                                       " (iso9660 format)")
        yield ISO9660UInt32_LSB_MSB(self, "volume_partition_size", "Number of Logical Blocks in which the Volume" 
                                                                   " Partition is recorded (iso9660 format)")
        yield NullBytes(self, "unused[]", 1960)


class SupplementaryVolumeDescriptor(FieldSet):
    endian = LITTLE_ENDIAN
    static_size = SECTOR_DATA_SIZE*8

    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)
        self.printDebug()
#        new_name = self.stream.readBytes(self.absolute_address + 0x51 * 8, 3)

    def createFields(self):
        yield NullBytes(self, "flags", 1)
        yield String(self, "system_id", ISO_MAX_SYSTEM_ID, "System identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "volume_id", ISO_MAX_VOLUME_ID, "Volume identifier", strip=" ", charset="UTF-16-LE")
        yield NullBytes(self, "unused[]", 8)
        yield ISO9660UInt32_LSB_MSB(self, "volume_space_size", "Total number of sectors (iso9660 format)")
        yield RawBytes(self, "escape_sequences", 32, "Escape sequences for Joliet extension")
        yield ISO9660UInt16_LSB_MSB(self, "volume_set_size", "Volume set size (iso9660 format)")
        yield ISO9660UInt16_LSB_MSB(self, "volume_seq_number", "Volume sequence number (iso9660 format)")
        yield ISO9660UInt16_LSB_MSB(self, "logical_block_size", "Sector size (usually 2048) (iso9660 format)")
        yield ISO9660UInt32_LSB_MSB(self, "path_table_size", "Path table size in bytes (iso9660 format)")
        yield UInt32(self, "type_l_path_table", "First sector of little-endian path table")
        yield UInt32(self, "opt_type_l_path_table", "First sector of optional little-endian path table")
        yield UInt32(self, "type_m_path_table", "First sector of big-endian path table")
        yield UInt32(self, "opt_type_m_path_table", "First sector of optional big-endian path table")
        yield DirRecord(self, "root_directory_record")
        yield String(self, "vol_set_id", 128, "Volume set identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "publisher", 128, "Publisher identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "data_preparer", 128, "Data preparer identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "application", 128, "Application identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "copyright", 37, "Copyright file identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "abstract", 37, "Abstract file identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "biographic", 37, "Biographic file identifier", strip=" ", charset="UTF-16-LE")
        yield String(self, "creation_ts", 17, "Creation date and time", strip=" \0")
        yield String(self, "modification_ts", 17, "Modification date and time", strip=" \0")
        yield String(self, "expiration_ts", 17, "Expiration date and time", strip=" \0")
        yield String(self, "effective_ts", 17, "Effective date and time", strip=" \0")
        yield UInt8(self, "struct_ver", "Structure version")
        yield NullBytes(self, "unused[]", 1)
        yield String(self, "app_use", 512, "Application use", strip=" \0")
        yield NullBytes(self, "unused[]", 653)


class PrimaryVolumeDescriptor(FieldSet):
    endian = LITTLE_ENDIAN
    static_size = SECTOR_DATA_SIZE*8

    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)
        self.printDebug()

    def createFields(self):
        yield NullBytes(self, "unused[]", 1)
        yield String(self, "system_id", ISO_MAX_SYSTEM_ID, "System identifier", strip=" \0")
        yield String(self, "volume_id", ISO_MAX_VOLUME_ID, "Volume identifier", strip=" \0")
        yield NullBytes(self, "unused[]", 8)
        yield ISO9660UInt32_LSB_MSB(self, "volume_space_size", "Total number of sectors (iso9660 format)")
        yield NullBytes(self, "unused[]", 32)
        yield ISO9660UInt16_LSB_MSB(self, "volume_set_size", "Volume set size (iso9660 format)")
        yield ISO9660UInt16_LSB_MSB(self, "volume_seq_number", "Volume sequence number (iso9660 format)")
        yield ISO9660UInt16_LSB_MSB(self, "logical_block_size", "Sector size (usually 2048) (iso9660 format)")
        yield ISO9660UInt32_LSB_MSB(self, "path_table_size", "Path table size in bytes (iso9660 format)")
        yield UInt32(self, "type_l_path_table", "First sector of little-endian path table")
        yield UInt32(self, "opt_type_l_path_table", "First sector of optional little-endian path table")
        yield UInt32(self, "type_m_path_table", "First sector of big-endian path table")
        yield UInt32(self, "opt_type_m_path_table", "First sector of optional big-endian path table")
        yield DirRecord(self, "root_directory_record")
        yield String(self, "vol_set_id", 128, "Volume set identifier", strip=" \0")
        yield String(self, "publisher", 128, "Publisher identifier", strip=" \0")
        yield String(self, "data_preparer", 128, "Data preparer identifier", strip=" \0")
        yield String(self, "application", 128, "Application identifier", strip=" \0")
        yield String(self, "copyright", 37, "Copyright file identifier", strip=" \0")
        yield String(self, "abstract", 37, "Abstract file identifier", strip=" \0")
        yield String(self, "biographic", 37, "Biographic file identifier", strip=" \0")
        yield String(self, "creation_ts", 17, "Creation date and time", strip=" \0")
        yield String(self, "modification_ts", 17, "Modification date and time", strip=" \0")
        yield String(self, "expiration_ts", 17, "Expiration date and time", strip=" \0")
        yield String(self, "effective_ts", 17, "Effective date and time", strip=" \0")
        yield UInt8(self, "struct_ver", "Structure version")
        yield NullBytes(self, "unused[]", 1)
        yield String(self, "app_use", 512, "Application use", strip=" \0")
        yield NullBytes(self, "unused[]", 653)


class BootRecord(FieldSet):
    static_size = SECTOR_DATA_SIZE*8

    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)

    def createFields(self):
        yield String(self, "sys_id", 31, "Boot system identifier", strip="\0")
        yield String(self, "boot_id", 31, "Boot identifier", strip="\0")
        yield RawBytes(self, "system_use", 1979, "Boot system use")


class Terminator(FieldSet):
    static_size = SECTOR_DATA_SIZE*8

    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)

    def createFields(self):
        yield NullBytes(self, "null", SECTOR_DATA_SIZE)


class Volume(FieldSet):
    endian = BIG_ENDIAN
    TERMINATOR = 255
    type_name = {
        0: "Boot Record",
        1: "Primary Volume Descriptor",
        2: "Supplementary Volume Descriptor",
        3: "Volume Partition Descriptor",
        TERMINATOR: "Volume Descriptor Set Terminator",
    }
    static_size = SECTOR_SIZE * 8
    content_handler = {
        0: BootRecord,
        1: PrimaryVolumeDescriptor,
        2: SupplementaryVolumeDescriptor,
        3: VolumePartitionDescriptor,
        TERMINATOR: Terminator,
    }

    def __init__(self, p_parent, p_name):
        FieldSet.__init__(self, p_parent, p_name)

    def createFields(self):
        yield Enum(UInt8(self, "type", "Volume descriptor type"), self.type_name)
        yield RawBytes(self, "id", 5, "ISO 9960 signature (CD001)")
        if self["id"].value != b"CD001":
            raise ParserError("Invalid ISO 9960 volume signature")
        yield UInt8(self, "version", "Volume descriptor version")
        l_cls = self.content_handler.get(self["type"].value, None)
        if l_cls:
            yield l_cls(self, "content")
        else:
            yield RawBytes(self, "raw_content", SECTOR_SIZE - 7)


class ISO9660(Parser):
    DEBUG = False

    endian = LITTLE_ENDIAN
    MAGIC = b"\x01CD001"
    NULL_BYTES = 16 * SECTOR_SIZE
    PARSER_TAGS = {
        "id": "iso9660",
        "category": "file_system",
        "file_ext": ("iso", "img", "bin",),
        "mime": (u"application/x-iso9660-image", ),
        "description": "ISO 9660 file system",
        "min_size": (NULL_BYTES + 6) * 8,
        "magic": ((MAGIC, NULL_BYTES * 8),),
    }

    # we need to build a list with DirRecords using random access since they are usually not linear in the data stream
    # and hachoir can only provide data in a stream
    def build_record_list(self, p_node_loc, p_node_len, p_rec_list):
        l_read = 0
        while l_read < p_node_len:
            # read first byte of record structure at ex_loc (rec_length)
            l_new_len = self.stream.readInteger((p_node_loc + 0) * 8, False, 8 * 1, LITTLE_ENDIAN)
            if l_new_len == 0:
                # we either have hit a boundary and the remaining space is <= 34 bytes or the end of the directory list
                l_node_sec, l_node_rest = divmod(p_node_loc, SECTOR_SIZE)
                l_read += (SECTOR_SIZE-l_node_rest)
                if l_read < p_node_len:
                    if self.DEBUG:
                        print("sector boundary detected, skipping %d bytes" % (SECTOR_SIZE-l_node_rest))
                    p_node_loc = (l_node_sec + 1) * SECTOR_SIZE
                    l_new_len = self.stream.readInteger((p_node_loc + 0) * 8, False, 8 * 1, LITTLE_ENDIAN)
                else:
                    # end of the directory!
                    break

            # read new "extend_loc"
            l_new_node_loc = self.stream.readInteger((p_node_loc + 2) * 8, False, 8 * 4, LITTLE_ENDIAN) * SECTOR_SIZE
            # read new "size"
            l_new_node_len = self.stream.readInteger((p_node_loc + 10) * 8, False, 8 * 4, LITTLE_ENDIAN)
            # read new "file_flags"
            l_new_flags = self.stream.readInteger((p_node_loc + 25) * 8, False, 8 * 1, LITTLE_ENDIAN)
            if self.DEBUG:
                # read "name_length"
                l_name_len = self.stream.readInteger((p_node_loc + 32) * 8, False, 8 * 1, LITTLE_ENDIAN)
                if l_name_len > 1:
                    # read "filename"
                    l_new_name = self.stream.readBytes((p_node_loc + 33) * 8, l_name_len)
                else:
                    if p_node_loc == l_new_node_loc:
                        l_new_name = "."
                    else:
                        l_new_name = ".."
                print("total read=%s/%s, read position @%#x-%#x[%d]: child node name=%s @%#x[%d]"
                      % (l_read, p_node_len, p_node_loc, p_node_loc + l_new_len, l_new_len, l_new_name,
                         l_new_node_loc, l_new_node_len))

            if p_node_loc not in p_rec_list.keys():
                p_rec_list[p_node_loc] = p_node_len
                if l_new_flags & 2:
                    if self.DEBUG:
                        print("enter directory %s, length=%s {" % (l_new_name, l_new_node_len))
                    self.build_record_list(l_new_node_loc, l_new_node_len, p_rec_list)
                    if self.DEBUG:
                        print("leave directory %s }" % l_new_name)
            else:
                if self.DEBUG:
                    print("skipping entry %s" % l_new_name)
            l_read += l_new_len
            p_node_loc += l_new_len

    def validate(self):
        if self.stream.readBytes(self.NULL_BYTES * 8, len(self.MAGIC)) != self.MAGIC:
            return "Invalid signature"
        return True

    def __init__(self, *args, **kw):
        Parser.__init__(self, *args, **kw)

    def createFields(self):
        yield self.seekByte(self.NULL_BYTES, null=True)

        l_vol_pvd = None
        l_vol_supl = None
        while True:
            l_volume = Volume(self, "volume[]")
            yield l_volume
            if l_volume["type"].value == 1:
                l_vol_pvd = l_volume
            if l_volume["type"].value == 2:
                l_vol_supl = l_volume
            if l_volume["type"].value == Volume.TERMINATOR:
                break

# reading dir records
# since they can be randomized on the disc, we need to build a sequential ordered list of the record locations
        l_rec_list = {}

        if l_vol_supl is not None:
            l_escape = l_vol_supl["content/escape_sequences"].value
            if self.DEBUG:
                if l_escape[0:3] == b"\x25\x2F\x40":
                    print("Joliet 1")
                elif l_escape[0:3] == b"\x25\x2F\x43":
                    print("Joliet 2")
                elif l_escape[0:3] == b"\x25\x2F\x45":
                    print("Joliet 3")

        l_record = l_vol_pvd["content/root_directory_record"]
        l_extent_loc = l_record["extent_loc"].value * SECTOR_SIZE
        l_size = l_record["size"].value

        l_rec_list[l_extent_loc] = l_size

        self.build_record_list(l_extent_loc, l_size, l_rec_list)

        if self.DEBUG:
            print(80*"*")
            print("RecordsFound")
            for l_location in sorted(l_rec_list.keys()):
                print("0x%0.8x" % l_location)
            print(80*"*")

        for l_extent, l_size in sorted(l_rec_list.items()):
            if self.DEBUG:
                print("current record at byte %#0.8x" % l_extent)
            l_padding = self.seekByte(l_extent, null=True)
            if l_padding:
                yield l_padding
            l_rec = DirRecord(self, "records[]")
            yield l_rec

        if self.current_size < self._size:
            yield self.seekBit(self._size, "end")
