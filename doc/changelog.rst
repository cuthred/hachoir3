+++++++++
Changelog
+++++++++

hachoir 3.0a3
=============

Parsers:

* Fix ELF parser (on Python 3)

hachoir 3.0a2 (2017-02-24)
==========================

Parsers:

* Add initial parser for Mapsforge .map files (only version 3 supported)
* Add parser for PAK files from "Project: Starfighter" game
* Add OS X ``.bom`` parser
* mov parser: add ``traf`` entry
* Update iTunesDB Parser
* 7zip: Improve and expand 7zip parser
* tar: Support ustar prefix field in tar archives.
* Enhance the Java class parser.
* Added more field to exif extractor
* Add WIP Mach-O parser
* ntfs improvements: parse non-resident runlists
* ext2: support ext4, massive parser improvements

  Huge changeset that may break backwards compatibility, for better
  consistency and deeper parsing. Basic rundown:

  - Support many more (new) flags added in ext4 and beyond
  - Create nice option displays for flags
  - Improve handling of groups using SeekableFieldSet
  - Parse (demarcate) inode data blocks
  - Consistently use lower case for flag names

* Enhance mpeg_ts parser to support MTS/M2TS; add MIME type

New features:

* Python parser supports Python 3.3-3.7 .pyc files.
* metadata: get comment from ZIP
* Support InputIOStream.read(0)
* Add a close() method and support for the context manager protocol
  (``with obj: ...``) to parsers, input and output streams.
* Add more file extensions for PE program parser.
* ZIP: add MIME type for Android APK, ``.apk`` file.
* Add editable field for TimestampMac32 type

Bugfixes:

* Issue #2: Fix saving a filed into a file in urwid

  * FileFromInputStream: fix comparison between None and an int
  * InputIOStream: open the file in binary mode

* Fix OutputStream.writeBits() (was broken since the migration to Python 3)
* Fix ResourceWarning warnings on files: use the new close() methods and
  context managers.
* Fix a few pending warnings on StopIteration.
* Fixup and relocate hachoir-wx, which now works mostly properly.
* Fix hachoir-parser matroska SimpleBlock
* Fix Mac timestamp name

Remove the unmaintained experimental HTTP interface.

hachoir 3.0a1 (2017-01-09)
==========================

Changes:

* metadata: support TIFF picture

Big refactoring:

* First release of the Python 3 port
* The 7 Hachoir subprojects (core, editor, metadata, parser, regex, subfile,
  urwid) which lived in different directories are merged again into one big
  unique Python 3 module: hachoir. For example, "hachoir_parser" becomes
  "hachoir.parser".
* The project moved from Bitbucket (Mercurial repository) to GitHub (Git
  repository). The Mercurial history since 2007 was kept.
* Reorganize tests into a new tests/ subdirectory. Copy test files directly
  into the Git repository, instead of relying on an old FTP server which
  is not convenient. For example, it's now possible to add the required test
  file in a Git commit. So it's more convenient for pull requests as well.
* Port code to Python 3: "for field in parser: yield field" becomes
  "yield from parser".
* Fix PEP 8 issues: most of the code does now respect the latest PEP 8 coding
  style.
* Enable Travis CI on the project: tests are on Python 3.5, check also
  pep8 and documentation.
* Copy old wiki pages and documentation splitted into many subdirectories
  into a single consistent Sphinx documentation in the doc/ subdirectory.
  Publish the documentation online at http://hachoir3.readthedocs.io/
