from hachoir.metadata.metadata import RootMetadata, registerExtractor, Metadata, MultipleMetadata
from hachoir.metadata.safe import fault_tolerant
from hachoir.parser.file_system import ISO9660
from datetime import datetime, tzinfo, timedelta
from hachoir.field import Field, FieldSet
from os.path import sep
import hashlib

SECTOR_SIZE = 2048


class Iso9660Tz(tzinfo):
    def __init__(self, offset=0):
        self._hours = offset // 4
        self._mins = (offset % 4) * 15

    def utcoffset(self, dt):
        return timedelta(hours=self._hours, minutes=self._mins)

    def tzname(self, dt):
        return "GMT %+d" % self._hours

    def dst(self, dt):
        return timedelta(0)


class ISO9660_Metadata(MultipleMetadata):
    DEBUG = False

    # noinspection PyAttributeOutsideInit
    def extract(self, p_iso):
        l_volume = None
        for l_index, l_volume in enumerate(p_iso.array("volume")):
            if l_volume["type"].value == 1:
                break

        if l_volume is not None:
            l_desc = l_volume['content']
            self.title = l_desc['volume_id'].value
            self.author = l_desc['publisher'].value
            self.producer = l_desc['application'].value
            self.copyright = l_desc['copyright'].value
            self.readTimestamp('creation_date', l_desc['creation_ts'].value)
            self.readTimestamp('last_modification', l_desc['modification_ts'].value)

            l_root = l_desc['root_directory_record']

            self.traverse_dir(l_root, "", p_iso.array("records"))

    def traverse_dir(self, p_dir_entry, p_cur_path, p_list):
        l_loc = p_dir_entry["extent_loc"].value * SECTOR_SIZE
        l_len = p_dir_entry["size"].value

        l_read = 0

        if self.DEBUG is True:
            print(80 * "*")
            for l_index, l_field in enumerate(p_list):
                print("[%d] 0x%0.8x" % (l_index, l_field.absolute_address // 8))
            print(80 * "*")

        while l_read < l_len:
            l_entry = self.find_entry(l_loc, p_list)
            if l_entry is not None:

                if self.DEBUG:
                    for l_field in l_entry:
                        print("%#x:%s=%s" % (l_field.absolute_address // 8, l_field.name, l_field.display))

                l_new_len = l_entry["rec_length"].value
                l_read += l_new_len
                if l_entry["name_length"].value > 1:
                    l_filename = self.get_filename(l_entry)
                    if l_entry["file_flags"].value & 2:
                        if self.DEBUG:
                            print("entering directory %s" % l_filename)
                        self.traverse_dir(l_entry, "%s%s%s" % (p_cur_path, l_filename, sep), p_list)
                        if self.DEBUG:
                            print("leaving directory %s" % l_filename)
                    else:
                        (acc_time, crea_time, mod_time) = self.get_dates(l_entry)
                        meta = Metadata(self)
                        meta.filename = "%s%s" % (p_cur_path, l_filename)
                        meta.last_modification = mod_time
                        meta.creation_date = crea_time
                        meta.file_size = l_entry["size"].value
                        self.addGroup("file[]", meta, "File \"%s\"" % meta.get('filename'))
                        if self.DEBUG:
                            print("adding file[] %s" % meta.get('filename'))
                l_loc = l_loc + l_new_len
            else:
                l_node_sec, l_node_rest = divmod(l_loc, SECTOR_SIZE)
                if self.DEBUG:
                    print(
                        "no entry found at %#x, skipping %d bytes to sector boundary"
                        % (l_loc, SECTOR_SIZE - l_node_rest))
                l_loc = (l_node_sec + 1) * SECTOR_SIZE
                l_read += (SECTOR_SIZE - l_node_rest)

    @staticmethod
    def format_date(p_date, p_format):
        if isinstance(p_date, datetime):
            return p_date
        if p_format:
            # 17 byte String
            l_ret_value = datetime(int(p_date[0:4]), int(p_date[4:6]), int(p_date[6:8]),
                                   int(p_date[8:10]), int(p_date[10:12]), int(p_date[12:14]),
                                   tzinfo=Iso9660Tz(ord(p_date[14:])))
        else:
            # 7 byte string
            l_ret_value = datetime(1900 + ord(p_date[0:1]), ord(p_date[1:2]), ord(p_date[2:3]),
                                   ord(p_date[3:4]), ord(p_date[4:5]), ord(p_date[5:6]),
                                   tzinfo=Iso9660Tz(ord(p_date[6:])))
        return l_ret_value

    def get_dates(self, p_entry):
        l_filedate = p_entry["recording_time"]
        l_acc_time = l_crea_time = l_mod_time = l_filedate
        for l_index, l_field in enumerate(p_entry.array("system_use_entry")):
            if l_field["sig"].value == "TF":
                l_flags = l_field["flags"].value
                l_format = l_flags & 0x80
                l_idx = 0
                if l_flags & 0x01:
                    l_crea_time = self.format_date(l_field["timestamp[%d]" % l_idx].value, l_format)
                    l_idx += 1
                if l_flags & 0x02:
                    l_mod_time = self.format_date(l_field["timestamp[%d]" % l_idx].value, l_format)
                    l_idx += 1
                if l_flags & 0x04:
                    l_acc_time = self.format_date(l_field["timestamp[%d]" % l_idx].value, l_format)
                    l_idx += 1
                break
        return l_acc_time, l_crea_time, l_mod_time

    @staticmethod
    def get_filename(p_entry):
        l_name = p_entry["filename"].value.split(';')[0]
        for l_index, l_field in enumerate(p_entry.array("system_use_entry")):
            if l_field["sig"].value == "NM":
                l_name = l_field["name_content"].value
                break
        return l_name

    @staticmethod
    def find_entry(p_location, p_list):
        for l_index, l_field in enumerate(p_list):
            if l_field.absolute_address // 8 == p_location:
                return l_field
        return None

    @fault_tolerant
    def readTimestamp(self, key, value):
        if value.startswith("0000"):
            return
        value = datetime(
            int(value[0:4]), int(value[4:6]), int(value[6:8]),
            int(value[8:10]), int(value[10:12]), int(value[12:14]))
        setattr(self, key, value)


registerExtractor(ISO9660, ISO9660_Metadata)
