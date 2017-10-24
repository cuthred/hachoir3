from hachoir.core.tools import (
    humanDuration, humanBitRate,
    humanFrequency, humanBitSize, humanFilesize,
    humanDatetime)
from hachoir.core.language import Language
from hachoir.metadata.filter import Filter, NumberFilter, DATETIME_FILTER
from datetime import date, datetime, timedelta
from hachoir.metadata.formatter import (
    humanAudioChannel, humanFrameRate, humanComprRate, humanAltitude,
    humanPixelSize, humanDPI)
from hachoir.metadata.setter import (
    setDatetime, setTrackNumber, setTrackTotal, setLanguage)
from hachoir.metadata.metadata_item import Data
import sys

MIN_SAMPLE_RATE = 1000              # 1 kHz
MAX_SAMPLE_RATE = 192000            # 192 kHz
MAX_NB_CHANNEL = 8                  # 8 channels
MAX_WIDTH = 20000                   # 20 000 pixels
MAX_BIT_RATE = 500 * 1024 * 1024    # 500 Mbit/s
MAX_HEIGHT = MAX_WIDTH
MAX_DPI_WIDTH = 10000
MAX_DPI_HEIGHT = MAX_DPI_WIDTH
MAX_NB_COLOR = 2 ** 24              # 16 million of color
MAX_BITS_PER_PIXEL = 256            # 256 bits/pixel
MAX_FRAME_RATE = 150                # 150 frame/sec
MAX_NB_PAGE = 20000
MAX_COMPR_RATE = 1000.0
MIN_COMPR_RATE = 0.001
MAX_TRACK = 999

DURATION_FILTER = Filter(timedelta,
                         timedelta(milliseconds=1),
                         timedelta(days=365))

PRIO_GENERAL = 100
PRIO_AUDIO = 200
PRIO_PICTURE = 300
PRIO_TEXT = 400
PRIO_PHOTO = 500
PRIO_GAME = 600
PRIO_ARCHIVE = 800


def prio_generator(n):
    l_start = n
    while True:
        l_new_start = yield l_start
        if l_new_start is not None:
            if l_new_start < l_start:
                print("ERROR: Generator overflow")
                sys.exit(1)
            l_start = l_new_start
        else:
            l_start += 1


def registerAllItems(meta):
    l_prio = prio_generator(PRIO_GENERAL)

    # General Metadata
    meta.register(Data("os", next(l_prio), "OS", type=str))
    meta.register(Data("producer", next(l_prio), "Producer", type=str))
    meta.register(Data("comment", next(l_prio), "Comment", type=str))
    meta.register(Data("text", next(l_prio), "Text", type=str))
    meta.register(Data("format_version", next(l_prio), "Format version", type=str))
    meta.register(Data("application_version", next(l_prio), "Application version", type=str))
    meta.register(Data("mime_type", next(l_prio), "MIME type", type=str))
    meta.register(Data("endian", next(l_prio), "Endianness", type=str))
    meta.register(Data("filename", next(l_prio), "File name", type=str))
    meta.register(Data("file_size", next(l_prio), "File size",
                       text_handler=humanFilesize,
                       type=int))
    meta.register(Data("file_attr", next(l_prio), "File attributes"))
    meta.register(Data("file_type", next(l_prio), "File type"))
    meta.register(Data("creation_date", next(l_prio), "Creation date",
                       text_handler=humanDatetime,
                       filter=DATETIME_FILTER,
                       type=(datetime, date),
                       conversion=setDatetime))
    meta.register(Data("last_modification", next(l_prio), "Last modification",
                       text_handler=humanDatetime,
                       filter=DATETIME_FILTER,
                       type=(datetime, date),
                       conversion=setDatetime))
    meta.register(Data("copyright", next(l_prio), "Copyright", type=str))

    # Audio Metadata
    meta.register(Data("title", l_prio.send(PRIO_AUDIO), "Title", type=str))
    meta.register(Data("artist", next(l_prio), "Artist", type=str))
    meta.register(Data("author", next(l_prio), "Author", type=str))
    meta.register(Data("music_composer", next(l_prio), "Music composer", type=str))
    meta.register(Data("publisher", next(l_prio), "Publisher", type=str))
    meta.register(Data("band", next(l_prio), "Band/orchestra/accompaniment", type=str))
    meta.register(Data("album", next(l_prio), "Album", type=str))
    meta.register(Data("duration", next(l_prio), "Duration",
                       # integer in milliseconde
                       type=timedelta,
                       text_handler=humanDuration,
                       filter=DURATION_FILTER))
    meta.register(Data("nb_page", next(l_prio), "Nb page",
                       filter=NumberFilter(1, MAX_NB_PAGE)))
    meta.register(Data("music_genre", next(l_prio), "Music genre", type=str))
    meta.register(Data("language", next(l_prio), "Language",
                       conversion=setLanguage, type=Language))
    meta.register(Data("track_number", next(l_prio), "Track number",
                       conversion=setTrackNumber,
                       filter=NumberFilter(1, MAX_TRACK), type=int))
    meta.register(Data("track_total", next(l_prio), "Track total",
                       conversion=setTrackTotal,
                       filter=NumberFilter(1, MAX_TRACK), type=int))
    meta.register(Data("organization", next(l_prio), "Organization", type=str))
    meta.register(Data("version", next(l_prio), "Version"))
    meta.register(Data("media_type", next(l_prio), "Media type", type=str))
    meta.register(Data("performer_sort_order", next(l_prio), "Performer Sort Order", type=str))
    meta.register(Data("album_sort_order_itunes", next(l_prio), "Album Sort Order (iTunes)", type=str))
    meta.register(Data("compilation_itunes", next(l_prio), "Compilation (iTunes)", type=str))
    meta.register(Data("bpm", next(l_prio), "Beats per Minute", type=str))

    # Picture Metadata
    meta.register(Data("width", l_prio.send(PRIO_PICTURE), "Image width",
                       filter=NumberFilter(1, MAX_WIDTH),
                       type=int,
                       text_handler=humanPixelSize))
    meta.register(Data("height", next(l_prio), "Image height",
                       filter=NumberFilter(1, MAX_HEIGHT),
                       type=int,
                       text_handler=humanPixelSize))
    meta.register(Data("nb_channel", next(l_prio), "Channel",
                       text_handler=humanAudioChannel,
                       filter=NumberFilter(1, MAX_NB_CHANNEL),
                       type=int))
    meta.register(Data("sample_rate", next(l_prio), "Sample rate",
                       text_handler=humanFrequency,
                       filter=NumberFilter(MIN_SAMPLE_RATE, MAX_SAMPLE_RATE),
                       type=(int, float)))
    meta.register(Data("bits_per_sample", next(l_prio), "Bits/sample",
                       text_handler=humanBitSize,
                       filter=NumberFilter(1, 64), type=int))
    meta.register(Data("image_orientation", next(l_prio), "Image orientation"))
    meta.register(Data("nb_colors", next(l_prio), "Number of colors",
                       filter=NumberFilter(1, MAX_NB_COLOR), type=int))
    meta.register(Data("bits_per_pixel", next(l_prio), "Bits/pixel",
                       filter=NumberFilter(1, MAX_BITS_PER_PIXEL),
                       type=int))
    meta.register(Data("pixel_format", next(l_prio), "Pixel format"))
    meta.register(Data("width_dpi", next(l_prio), "Image DPI width",
                       filter=NumberFilter(1, MAX_DPI_WIDTH),
                       type=int,
                       text_handler=humanDPI))
    meta.register(Data("height_dpi", next(l_prio), "Image DPI height",
                       filter=NumberFilter(1, MAX_DPI_HEIGHT),
                       type=int,
                       text_handler=humanDPI))
    meta.register(Data("encoder", next(l_prio), "Software/Hardware and settings used for encoding",
                       type=str))

    # Text Metadata
    meta.register(Data("subtitle_author", l_prio.send(PRIO_TEXT), "Subtitle author", type=str))
    meta.register(Data("charset", next(l_prio), "Charset", type=str))
    meta.register(Data("font_weight", next(l_prio), "Font weight"))

    # Photo Metadata
    meta.register(Data("latitude", l_prio.send(PRIO_PHOTO), "Latitude", type=float))
    meta.register(Data("longitude", next(l_prio), "Longitude", type=float))
    meta.register(Data("altitude", next(l_prio), "Altitude", type=float,
                       text_handler=humanAltitude))
    meta.register(Data("location", next(l_prio), "Location", type=str))
    meta.register(Data("city", next(l_prio), "City", type=str))
    meta.register(Data("country", next(l_prio), "Country", type=str))
    meta.register(Data("camera_aperture", next(l_prio), "Camera aperture"))
    meta.register(Data("camera_focal", next(l_prio), "Camera focal"))
    meta.register(Data("camera_exposure", next(l_prio), "Camera exposure"))
    meta.register(Data("camera_brightness", next(l_prio), "Camera brightness"))
    meta.register(Data("camera_model", next(l_prio), "Camera model", type=str))
    meta.register(Data("camera_manufacturer", next(l_prio), "Camera manufacturer",
                       type=str))
    meta.register(Data("url", next(l_prio), "URL", type=str))
    meta.register(Data("frame_rate", next(l_prio), "Frame rate",
                       text_handler=humanFrameRate,
                       filter=NumberFilter(1, MAX_FRAME_RATE),
                       type=(int, float)))
    meta.register(Data("bit_rate", next(l_prio), "Bit rate",
                       text_handler=humanBitRate,
                       filter=NumberFilter(1, MAX_BIT_RATE),
                       type=(int, float)))
    meta.register(Data("aspect_ratio", next(l_prio), "Aspect ratio",
                       type=(int, float)))
    meta.register(Data("thumbnail_size", next(l_prio), "Thumbnail size",
                       text_handler=humanFilesize,
                       type=(int, float)))
    meta.register(Data("iso_speed_ratings", next(l_prio), "ISO speed rating"))
    meta.register(Data("exif_version", next(l_prio), "EXIF version"))
    meta.register(Data("date_time_original", next(l_prio), "Date-time original",
                       text_handler=humanDatetime,
                       filter=DATETIME_FILTER,
                       type=(datetime, date), conversion=setDatetime))
    meta.register(Data("date_time_digitized", next(l_prio), "Date-time digitized",
                       text_handler=humanDatetime,
                       filter=DATETIME_FILTER,
                       type=(datetime, date), conversion=setDatetime))
    meta.register(Data("compressed_bits_per_pixel", next(l_prio), "Compressed bits per pixel",
                       type=(int, float)))
    meta.register(Data("shutter_speed_value", next(l_prio), "Shutter speed",
                       type=(int, float)))
    meta.register(Data("aperture_value", next(l_prio), "Aperture"))
    meta.register(Data("exposure_bias_value", next(l_prio), "Exposure bias"))
    meta.register(Data("focal_length", next(l_prio), "Focal length"))
    meta.register(Data("flashpix_version", next(l_prio), "Flashpix version"))
    meta.register(Data("focal_plane_x_resolution", next(l_prio), "Focal plane width"))
    meta.register(Data("focal_plane_y_resolution", next(l_prio), "Focal plane height",
                       type=float))
    meta.register(Data("focal_length_in_35mm_film", next(l_prio), "Focal length in 35mm film"))

    # Game Metadata
    meta.register(Data("region", l_prio.send(PRIO_GAME), "Available Region", type=str))
    meta.register(Data("rom_type", next(l_prio), "ROM Type", type=str))
    meta.register(Data("backup_unit", next(l_prio), "Backup Unit", type=str))
    meta.register(Data("title_id", next(l_prio), "Title ID", type=str))
    meta.register(Data("content_type", next(l_prio), "Content Type", type=str))
    meta.register(Data("title_name", next(l_prio), "Title Name", type=str))
    meta.register(Data("disp_name", next(l_prio), "Display Name", type=str))
    meta.register(Data("disp_name_jpn", next(l_prio), "Display Name (japanese)", type=str))
    meta.register(Data("disp_name_ger", next(l_prio), "Display Name (german)", type=str))
    meta.register(Data("disp_name_fra", next(l_prio), "Display Name (french)", type=str))
    meta.register(Data("disp_name_spa", next(l_prio), "Display Name (spanish)", type=str))
    meta.register(Data("disp_name_ita", next(l_prio), "Display Name (italian)", type=str))
    meta.register(Data("disp_name_kor", next(l_prio), "Display Name (korean)", type=str))
    meta.register(Data("disp_name_chi", next(l_prio), "Display Name (chinese)", type=str))
    meta.register(Data("disp_name_por", next(l_prio), "Display Name (portugese)", type=str))
    meta.register(Data("disp_name_rus", next(l_prio), "Display Name (russian)", type=str))
    meta.register(Data("disp_name_pol", next(l_prio), "Display Name (polish)", type=str))
    meta.register(Data("disp_name_unk", next(l_prio), "Display Name (unknown)", type=str))
    meta.register(Data("disp_desc", next(l_prio), "Display Description", type=str))
    meta.register(Data("disp_desc_jpn", next(l_prio), "Display Description (japanese)", type=str))
    meta.register(Data("disp_desc_ger", next(l_prio), "Display Description (german)", type=str))
    meta.register(Data("disp_desc_fra", next(l_prio), "Display Description (french)", type=str))
    meta.register(Data("disp_desc_spa", next(l_prio), "Display Description (spanish)", type=str))
    meta.register(Data("disp_desc_ita", next(l_prio), "Display Description (italian)", type=str))
    meta.register(Data("disp_desc_kor", next(l_prio), "Display Description (korean)", type=str))
    meta.register(Data("disp_desc_chi", next(l_prio), "Display Description (chinese)", type=str))
    meta.register(Data("disp_desc_por", next(l_prio), "Display Description (portugese)", type=str))
    meta.register(Data("disp_desc_rus", next(l_prio), "Display Description (russian)", type=str))
    meta.register(Data("disp_desc_pol", next(l_prio), "Display Description (polish)", type=str))
    meta.register(Data("disp_desc_unk", next(l_prio), "Display Description (unknown)", type=str))
    meta.register(Data("thumb_size", next(l_prio), "Thumbnail Image Size", type=int))
    meta.register(Data("title_thumb_size", next(l_prio), "Title Thumbnail Image Size", type=int))
    meta.register(Data("user_id", next(l_prio), "User ID", type=str))
    meta.register(Data("console_id", next(l_prio), "Console ID", type=str))
    meta.register(Data("device_id", next(l_prio), "Device ID", type=str))
    meta.register(Data("content_id", next(l_prio), "Contend ID", type=str))
    meta.register(Data("media_id", next(l_prio), "Media ID", type=str))
    meta.register(Data("version_ex", next(l_prio), "Execution Version", type=str))
    meta.register(Data("basever_ex", next(l_prio), "Execution BaseVersion", type=str))
    meta.register(Data("season_id", next(l_prio), "Season ID", type=str))
    meta.register(Data("series_id", next(l_prio), "Series ID", type=str))
    meta.register(Data("asset_id", next(l_prio), "Asset ID", type=str))

    # Archive Metadata
    meta.register(Data("has_recovery_record", l_prio.send(PRIO_ARCHIVE), "Archive has recovery record", type=bool))
    meta.register(Data("has_auth_verification", next(l_prio), "Archive has authenticity verification", type=bool))
    meta.register(Data("has_password", next(l_prio), "Archives is protected by password", type=bool))
    meta.register(Data("is_multivolume", next(l_prio), "Archives has multivolume support", type=bool))
    meta.register(Data("is_solid", next(l_prio), "Archives is solid", type=bool))
    meta.register(Data("is_first_vol", next(l_prio), "First volume of an archive", type=bool))
    meta.register(Data("compr_size", next(l_prio), "Compressed file size",
                       text_handler=humanFilesize,
                       type=int))
    meta.register(Data("compr_rate", next(l_prio), "Compression rate",
                       text_handler=humanComprRate,
                       filter=NumberFilter(MIN_COMPR_RATE, MAX_COMPR_RATE),
                       type=(int, float)))
    meta.register(Data("compression", next(l_prio), "Compression"))

