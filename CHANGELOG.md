# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog (https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning (https://semver.org/).

## [Unreleased] - 2025-10-30

No user-facing changes have been merged to the default branch since 1.9.

- SemVer impact: patch (no breaking changes detected).

## [1.9] - 2025-10-29

- SemVer impact: minor

Added
- Introduced SearcherFactory for dynamic searcher selection and module exports (03ad810).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/03ad810
- Auto-registration of BaseSearcher subclasses via SEARCH_TYPE (1c31927).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/1c31927
- Added AttributeSearcher for generic attribute-based message searching (caf8e56).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/caf8e56
- Added OUTLOOK_ATSQL_ALIASES for common Outlook SQL field aliases (71d6ed2).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/71d6ed2
- Implemented EmailMsgImportanceLevel enum and Msg.importance property (acd65f4).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/acd65f4
- Added keyword checks for body and attachments in alert detection (799f0c1).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/799f0c1
- Added snoozed messages count in ContinuousMonitor alerts (18156f6).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/18156f6

Changed
- Refactored SubjectSearcher and FastPathSearcher with improved class structure and SQL filter handling with fallback support (c7da738, 9f4aef1).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/c7da738
  https://github.com/amcsparron2793-Water/PyEmailer/commit/9f4aef1
- Optimized and modularized find_messages_by_subject with server-side filtering fallback and helper function (b799b0a, 9df5ee4, 585f236).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/b799b0a
  https://github.com/amcsparron2793-Water/PyEmailer/commit/9df5ee4
  https://github.com/amcsparron2793-Water/PyEmailer/commit/585f236
- Integrated SearcherFactory throughout and enhanced BaseSearcher with default message provider and normalization to string (fa78db4, 71d6ed2, 790facc).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/fa78db4
  https://github.com/amcsparron2793-Water/PyEmailer/commit/71d6ed2
  https://github.com/amcsparron2793-Water/PyEmailer/commit/790facc
- Refactored ContinuousMonitor alert handling and keyword validation (88d98c1).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/88d98c1
- Set email importance levels in ContinuousMonitor alerts (7ad8745).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/7ad8745
- Logger initialization improvements for BaseSearcher/SearcherFactory and PyEmailer (2b8b15b, f62c3cf, 91f76ab).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/2b8b15b
  https://github.com/amcsparron2793-Water/PyEmailer/commit/f62c3cf
  https://github.com/amcsparron2793-Water/PyEmailer/commit/91f76ab
- Updated display_tracker_check signature to return Optional[bool] with explicit None (e35f684).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/e35f684

Fixed
- Fixed email handler initialization and updated type checks (e4a98af).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/e4a98af

Documentation
- Expanded README with detailed installation, usage, testing, and project structure (229f802).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/229f802
- Added Outlook SQL alias cheatsheet (a5ee16b).
  https://github.com/amcsparron2793-Water/PyEmailer/commit/a5ee16b

<!--
Guidance for contributors:
- Group user-facing changes under one of these sections when adding entries:
  - Added, Changed, Deprecated, Removed, Fixed, Security
- Include a short commit hash and GitHub link after each bullet when possible,
  e.g. "Fixed: Corrected time parsing (abcd123)" linking to the commit.
-->

[Unreleased]: https://github.com/amcsparron2793-Water/PyEmailer/compare/1.9...HEAD
[1.9]: https://github.com/amcsparron2793-Water/PyEmailer/compare/1.8.5...1.9
[1.8.5]: https://github.com/amcsparron2793-Water/PyEmailer/releases/tag/1.8.5
