# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://www.google.com/search?q=https://keepachangelom.com/en/1.0.0/ "null"), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html "null").

# Changelog

## \[2.1.0\] - 2025-11-19

Major functionality restore and improvement ("Visual Copy" release).

### Added

- **HTML Processing with BeautifulSoup:**
    
    - Re-introduced intelligent HTML parsing.
        
    - **Image Downloading:** Automatically detects embedded images/emoticons, downloads them, and rewrites HTML links to local paths (`../attachments/`).
        
    - **Link Sanitizing:** Attempts to rewrite Confluence internal links.
        
    - **Metadata Injection:** Injects Title, Page ID, and Labels into the HTML `<head>`.
        
- **Export View:** Switched API fetch from `storage` format to `export_view` (or `view`) to get rendered HTML (resolves macros like TOC).
    
- **Attachment Downloading:** Downloads _all_ attachments of a page, not just those embedded in the text.
    

### Changed

- **HTML is now the primary output:** The script always generates a standalone, browsable `.html` file linked to the CSS.
    
- **Dependencies:** Added `beautifulsoup4` to requirements.
    
- **CSS handling:** Improved relative pathing for robust offline viewing.

## \[2.0.0\] - 2025-11-17

This version introduces a major architectural refactoring to support both Confluence Cloud and Data Center, and replaces the CLI mode logic with a robust sub-command architecture. All original functionality (all modes, all formats) is preserved and extended.

### Added

- **Confluence Data Center Support:** The script now supports both Confluence Cloud (`--profile cloud`) and Data Center (`--profile dc`).
    
- **Configuration File (`confluence_products.ini`):** All platform-specific values (API URL templates, auth methods, base paths) are now defined in this external INI file.
    
- **Data Center Authentication:** Added support for Bearer Token (Personal Access Token) authentication.
    
- **New `label` Command:** Added support for dumping all pages with a specific label via the `label` sub-command (previously missing from refactoring).
    
- **Custom CSS Support:** Added `--css-file` argument to supply a custom CSS stylesheet, ensuring properly styled HTML exports.
    
- **Troubleshooting Hints:** Added specific error messages for Data Center users when authentication fails (Intranet/VPN warning).
    
- **`CONTRIBUTING.md`:** A new file explaining the new architecture.
    
- **`CHANGELOG.md`:** This file.
    

### Changed

- **\[BREAKING CHANGE\] CLI Architecture (Sub-Commands):** The script's interface has been completely modernized, replacing the `-m`/`--mode` flag with sub-commands (like `git`).
    
    - **REMOVED:** The `-m`/`--mode` flag.
        
    - **REMOVED:** The `-s`/`--site` argument.
        
    - **ADDED:** Sub-commands: `single`, `tree`, `space`, `all-spaces`, and `label` to select the mode.
        
    - **CHANGED:** The `-p`/`--pageid` and `-sp`/`--space-key` (formerly `--space`) arguments are now context-specific arguments for their respective commands (e.g., `single --pageid ...`).
        
    - **ADDED (Global, Required):** `--base-url` argument for the instance URL.
        
    - **ADDED (Global, Required):** `--profile` argument to select 'cloud' or 'dc'.
        
    - **ADDED (Global, Optional):** `--context-path` argument for Data Center.
        
    - **PRESERVED (Global):** `-o`/`--outdir`, `-H`/`--html`, `-R`/`--rst` are now global options.
        
- **Refactored `myModules.py`:**
    
    - All API functions (e.g., `get_page_full`) are now platform-agnostic, driven by the `.ini` file.
        
    - All hardcoded URLs (e.g., `.atlassian.net`) have been removed.
        
    - Added helper functions (`_build_api_url`, `_execute_get_request`, `load_platform_config`, `get_auth_config`).
        
    - Added `get_pages_by_label` to support label-based dumping.
        
    - Improved directory creation logic (`setup_output_directories`) to be robust against re-runs.
        
- **Refactored `confluenceDumpWithPython.py`:**
    
    - Re-implemented all modes (`single`, `tree`, `space`, `all-spaces`, `label`) using the new sub-command architecture.
        
    - Preserved all original output logic (JSON, HTML, RST).
        
    - Improved HTML generation: now produces standalone HTML files linked to a custom CSS stylesheet if provided.
        
    - Replaced `if/elif` "spaghetti code" with clean, dedicated handler functions for each mode.
        
- **Updated `README.md`:** The README now reflects the new sub-command architecture, provides examples for all major use cases, documents the `--css-file` option, and includes a troubleshooting section for Data Center VPN issues.
    
- **Internationalization:** All code comments, docstrings, and user-facing error messages have been translated to English.
    

_History below this line is from the original author (jgoldin-skillz)._

## \[1.0.2\] - 2022-03-03

- Bugfixes
    

## \[1.0.1\] - 2022-03-03

- Added `confluenceDumpWithPython.py`
    

## \[1.0.0\] - 2022-03-01

- Initial version