# PyEmailerAJM

Makes automating Outlook Desktop email sending and reading quick and easy.

PyEmailerAJM is a Python package that wraps the Outlook COM (pywin32) object model to:
- Create and send emails via the installed Outlook Desktop client
- Read messages from folders, save attachments, and search/filter messages
- Provide higher-level helpers for common workflows, plus a flexible searcher API

This README documents the stack, requirements, setup, basic usage, tests, and project structure. It preserves previous notes and adds TODOs where details are unclear.

## Overview
- Package name: `PyEmailerAJM`
- Distribution: setuptools package (see setup.py)
- Primary class: `PyEmailer` for sending/reading via Outlook
- Additional utilities:
  - `Msg` wrapper around Outlook items
  - `SearcherFactory` and searchers (`SubjectSearcher`, `AttributeSearcher`) for finding messages
  - Continuous monitoring helpers (`ContinuousMonitor`)

## Requirements
- Operating system: Windows (required for Outlook COM automation via pywin32)
- Installed and configured Microsoft Outlook Desktop (connected profile required)
- Python: 3.x (tested locally with 3.12). TODO: Document official minimum supported version.
- Dependencies (subset):
  - pywin32
  - extract-msg
  - email_validator
  - questionary (interactive prompts)
  - EasyLoggerAJM, ColorizerAJM
  - See requirements.txt and setup.py for the full list and pinned versions used for development.

## Installation
Development install (editable):
- Create/activate a virtual environment
- Install dependencies and package:
  - pip install -r requirements.txt
  - pip install -e .

Regular install from source:
- pip install .

From a tagged release (see setup.py download_url):
- TODO: Add PyPI instructions when/if published.

## Quick start
Import the main class from the package root:

from PyEmailerAJM import PyEmailer

# Initialize
emailer = PyEmailer(display_window=False,  # set True to open the Outlook compose window
                    send_emails=True,      # set False to avoid actually sending
                    email_sig_filename=None,  # or provide a signature file name (see Notes)
                    auto_send=False)

# Compose
emailer.SetupEmail(
    recipient="someone@example.com",
    subject="Hello from PyEmailerAJM",
    text="This is a test message",
    attachments=[  # optional
        # r"C:\\path\\to\\file.txt"
    ],
)

# Send (or display)
failed = emailer.SendOrDisplay(print_ready_msg=False)
if failed:
    print("Some sends failed:", failed)

### Reading and searching messages
Basic subject search using the built-in high-level helper:

from PyEmailerAJM import PyEmailer
emailer = PyEmailer(display_window=False, send_emails=False)
msgs = emailer.FindMsgBySubject("Weekly Report", partial_match_ok=True)

Flexible searching via SearcherFactory:

from PyEmailerAJM import PyEmailer, SearcherFactory
py = PyEmailer(display_window=False, send_emails=False)
factory = SearcherFactory()

# Specialized subject searcher (handles RE:/FW: prefixes)
subject_searcher = factory.get_searcher('subject', get_messages=py.GetMessages)
found = subject_searcher.find_messages_by_attribute('Weekly Report', partial_match_ok=True)

# Generic attribute searcher for Outlook field names (e.g., Body, SenderName)
body_searcher = factory.get_searcher('attribute', attribute='Body', get_messages=py.GetMessages)
found_body = body_searcher.find_messages_by_attribute('deployment succeeded', partial_match_ok=True)

# Convenience: use a known Outlook alias directly
sender_searcher = factory.get_searcher('SenderName', get_messages=py.GetMessages)
found_sender = sender_searcher.find_messages_by_attribute('Alice', partial_match_ok=True)

See PyEmailerAJM/searchers for more details.

## Environment variables and configuration
- Signatures: If you supply a signature file name, the project reads the text signature from
  %APPDATA%/Microsoft/Signatures/<your_signature>.txt
  This matches the original behavior noted in the project.
- TODO: Document any additional environment variables if/when introduced.

## Running tests
This repo uses the built-in unittest framework.
- Run the full suite:
  - python -m unittest
- Run a single test file:
  - python -m unittest tests/test_searcher_factory.py

Note: Tests use light-weight dummy classes and do not require Outlook to be installed.

## Project structure
- PyEmailerAJM/
  - __init__.py: public API imports
  - _version.py: package version (current: 1.8.5)
  - py_emailer_ajm.py: main PyEmailer class and helpers
  - backend/: errors, enums, logger, helpers
  - msg/: message wrapper types
  - searchers/: search utilities and factory
  - continuous_monitor/: monitoring utilities
- tests/: unit tests using unittest
- requirements.txt: development dependency pins
- setup.py / setup.cfg: packaging metadata
- OutlookPywin32Commands.xlsx: reference of available Outlook COM methods/fields
- LICENSE.txt: license file (MIT)

## Scripts and entry points
- This project does not currently define console entry points via setup.py.
- Common developer commands:
  - Build a distribution: python -m build  # or python setup.py sdist bdist_wheel (legacy)
  - Install in editable mode: pip install -e .
  - Run tests: python -m unittest
- TODO: Document any helper scripts in the `building_script/` directory if applicable.

## Notes
- See OutlookPywin32Commands.xlsx for a list of Outlook commands/fields that can be used with a message object.
- Email signature text can be added (as of earlier versions) by placing the signature .txt file in
  %APPDATA%/Microsoft/Signatures/ and passing its name to PyEmailer.

## License
This project is licensed under the MIT License. See LICENSE.txt for details.