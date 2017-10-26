from hachoir.metadata.metadata_item import QUALITY_BEST, QUALITY_FASTEST
from hachoir.metadata.safe import fault_tolerant, getValue
from hachoir.metadata.metadata import (
    RootMetadata, Metadata, MultipleMetadata, registerExtractor)
from hachoir.parser.archive import (Bzip2Parser, CabFile, GzipParser,
                                    TarFile, ZipFile, MarFile, RarFile)
from hachoir.core.tools import humanUnixAttributes


def maxNbFile(meta):
    if meta.quality <= QUALITY_FASTEST:
        return 0
    if QUALITY_BEST <= meta.quality:
        return None
    return 1 + int(10 * meta.quality)


def computeCompressionRate(meta):
    """
    Compute compression rate, sizes have to be in byte.
    """
    if (not meta.has("file_size")
            or not meta.get("compr_size", 0)):
        return
    file_size = meta.get("file_size")
    if not file_size:
        return
    meta.compr_rate = float(file_size) / meta.get("compr_size")


# noinspection PyAttributeOutsideInit
class Bzip2Metadata(RootMetadata):

    def extract(self, zip):
        if "file" in zip:
            self.compr_size = zip["file"].size // 8


# noinspection PyAttributeOutsideInit
class GzipMetadata(RootMetadata):

    def extract(self, gzip):
        self.useHeader(gzip)
#        computeCompressionRate(self)

    @fault_tolerant
    def useHeader(self, gzip):
        self.compression = gzip["compression"].display
        if gzip["mtime"]:
            self.last_modification = gzip["mtime"].value
        self.os = gzip["os"].display
        if gzip["has_filename"].value:
            self.filename = getValue(gzip, "filename")
        if gzip["has_comment"].value:
            self.comment = getValue(gzip, "comment")
        self.compr_size = gzip["file"].size // 8
        self.file_size = gzip["size"].value


# noinspection PyAttributeOutsideInit
class ZipMetadata(MultipleMetadata):

    def extract(self, zip):
        max_nb = maxNbFile(self)
        for index, field in enumerate(zip.array("file")):
            if max_nb is not None and max_nb <= index:
                self.warning("ZIP archive contains many files, "
                             "but only first %s files are processed"
                             % max_nb)
                break
            self.processFile(field)

        self.extract_end_central_directory(zip)

    @fault_tolerant
    def extract_end_central_directory(self, parser):
        comment = parser['end_central_directory/comment'].value
        if comment:
            self.comment = comment

    @fault_tolerant
    def processFile(self, field):
        meta = Metadata(self)
        meta.filename = field["filename"].value
        meta.creation_date = field["last_mod"].value
        meta.compression = field["compression"].display
        if "data_desc" in field:
            meta.file_size = field["data_desc/file_uncompressed_size"].value
            if field["data_desc/file_compressed_size"].value:
                meta.compr_size = field["data_desc/file_compressed_size"].value
        else:
            meta.file_size = field["uncompressed_size"].value
            if field["compressed_size"].value:
                meta.compr_size = field["compressed_size"].value
#        computeCompressionRate(meta)
        self.addGroup(field.name, meta, "File \"%s\"" % meta.get('filename'))


class TarMetadata(MultipleMetadata):

    def extract(self, tar):
        max_nb = maxNbFile(self)
        for index, field in enumerate(tar.array("file")):
            if max_nb is not None and max_nb <= index:
                self.warning("TAR archive contains many files, "
                             "but only first %s files are processed"
                             % max_nb)
                break
            meta = Metadata(self)
            self.extractFile(field, meta)
            if meta.has("filename"):
                title = 'File "%s"' % meta.getText('filename')
            else:
                title = "File"
            self.addGroup(field.name, meta, title)

    @fault_tolerant
    def extractFile(self, field, meta):
        meta.filename = field["name"].value
        meta.file_attr = humanUnixAttributes(field.getOctal("mode"))
        meta.file_size = field.getOctal("size")
        try:
            if field.getOctal("mtime"):
                meta.last_modification = field.getDatetime()
        except ValueError:
            pass
        meta.file_type = field["type"].display
        meta.author = "%s (uid=%s), group %s (gid=%s)" %\
            (field["uname"].value, field.getOctal("uid"),
             field["gname"].value, field.getOctal("gid"))


# noinspection PyAttributeOutsideInit
class CabMetadata(MultipleMetadata):

    def extract(self, cab):
        if "folder[0]" in cab:
            self.useFolder(cab["folder[0]"])
        self.format_version = ("Microsoft Cabinet version %s.%s"
                               % (cab["major_version"].display,
                                  cab["minor_version"].display))
        self.comment = "%s folders, %s files" % (
            cab["nb_folder"].value, cab["nb_files"].value)
        max_nb = maxNbFile(self)
        for index, field in enumerate(cab.array("file")):
            if max_nb is not None and max_nb <= index:
                self.warning("CAB archive contains many files, "
                             "but only first %s files are processed"
                             % max_nb)
                break
            self.useFile(field)

    @fault_tolerant
    def useFolder(self, folder):
        compr = folder["compr_method"].display
        if folder["compr_method"].value != 0:
            compr += " (level %u)" % folder["compr_level"].value
        self.compression = compr

    @fault_tolerant
    def useFile(self, field):
        meta = Metadata(self)
        meta.filename = field["filename"].value
        meta.file_size = field["filesize"].value
        meta.creation_date = field["timestamp"].value
        attr = field["attributes"].value
        if attr != "(none)":
            meta.file_attr = attr
        if meta.has("filename"):
            title = "File \"%s\"" % meta.getText('filename')
        else:
            title = "File"
        self.addGroup(field.name, meta, title)


# noinspection PyAttributeOutsideInit
class MarMetadata(MultipleMetadata):

    def extract(self, mar):
        self.comment = "Contains %s files" % mar["nb_file"].value
        self.format_version = ("Microsoft Archive version %s"
                               % mar["version"].value)
        max_nb = maxNbFile(self)
        for index, field in enumerate(mar.array("file")):
            if max_nb is not None and max_nb <= index:
                self.warning("MAR archive contains many files, "
                             "but only first %s files are processed"
                             % max_nb)
                break
            meta = Metadata(self)
            meta.filename = field["filename"].value
            meta.compression = "None"
            meta.file_size = field["filesize"].value
            self.addGroup(field.name, meta,
                          "File \"%s\"" % meta.getText('filename'))


# noinspection PyAttributeOutsideInit
class RarMetadata(MultipleMetadata):
    def extract(self, rar):
        l_max_nb = maxNbFile(self)

        l_rarformat = rar["signature"].value
        if l_rarformat == b"RE~^":
            l_format_version = "1.4"
        elif l_rarformat[0:6] == b"Rar!\x1A\x07":
            if l_rarformat[6:7] == b"\x00":
                l_format_version = "1.5"      # RAR 4
            elif l_rarformat[6:7] == b"\x01":
                l_format_version = "5.0"
            elif l_rarformat[6:7] == b"\x02":
                l_format_version = "> 5.0"

        self.format_version = "RAR version %s" % l_format_version

        if l_format_version != "1.5":
            self.warning("RAR TODO: unknown format_version \"%s\" " % l_format_version)

        l_has_recovery_record = False
        l_has_auth_verification = False
        l_has_password = False
        l_is_multivolume = False
        l_is_solid = False

        if rar["/archive_start/flags/has_comment"].value:
            self.warning("RAR TODO: comment extraction not implemented")
            self.comment = "HACHOIR: comment extraction not implemented"

        l_has_recovery_record = rar["/archive_start/flags/has_recovery_record"].value
        l_has_auth_verification = rar["/archive_start/flags/has_auth_information"].value
        l_has_password = rar["/archive_start/flags/is_locked"].value
        l_is_multivolume = rar["/archive_start/flags/vol"].value
        l_is_solid = rar["/archive_start/flags/is_solid"].value
        is_first_vol = rar["/archive_start/flags/is_first_vol"].value

        for l_index, l_field in enumerate(rar.array("new_sub_block")):
            if l_field["filename"].value == "CMT":
                self.warning("RAR TODO: comment unpacking not implemented")
                self.comment = "HACHOIR: comment unpacking not implemented"
            elif l_field["filename"].value == "AV":
                l_has_auth_verification = True
            elif l_field["filename"].value == "RR":
                    l_has_recovery_record = True
            else:
                self.warning("RAR TODO: unknown sub_block \"%s\" " % l_field["filename"].value)

        self.has_recovery_record = l_has_recovery_record
        self.has_auth_verification = l_has_auth_verification
        self.has_password = l_has_password
        self.is_multivolume = l_is_multivolume
        self.is_solid = l_is_solid
        self.is_first_vol = is_first_vol

        for l_index, l_field in enumerate(rar.array("file")):
            if l_max_nb is not None and l_max_nb <= l_index:
                self.warning("RAR archive contains many files, but only first %s files are processed" % l_max_nb)
                break
            l_meta = Metadata(self)
            l_meta.filename = l_field["filename"].value
            l_meta.last_modification = l_field["ftime"].value
            l_meta.os = l_field["host_os"].display
            l_meta.application_version = l_field["version"].display
            l_meta.compression = l_field["method"].display
            l_meta.file_size = l_field["uncompressed_size"].value
            l_meta.compr_size = l_field["compressed_size"].value
            self.addGroup(l_field.name, l_meta, "File \"%s\"" % l_meta.get('filename'))


registerExtractor(CabFile, CabMetadata)
registerExtractor(GzipParser, GzipMetadata)
registerExtractor(Bzip2Parser, Bzip2Metadata)
registerExtractor(TarFile, TarMetadata)
registerExtractor(ZipFile, ZipMetadata)
registerExtractor(MarFile, MarMetadata)
registerExtractor(RarFile, RarMetadata)
