# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/ "null"), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html "null").

## \[2.5.0\] - 2025-11-22

Introduction of the "Architecture Sandbox" for offline restructuring.

### Added

- **Architecture Sandbox:** Introduced `create_editor.py` and `patch_sidebar.py`. Users can now generate a visual Drag & Drop editor (`editor_sidebar.html`) to restructure the exported documentation offline and apply changes massively using the patcher.
    
- **Robust Editor Generation:** The editor generator now uses a safe string concatenation approach to avoid syntax errors and supports creating a working copy of the sidebar structure (`sidebar_edit.md`).
    

### Changed

- **CSS Strategy:** Refined the "Two-Layer" styling approach (Standard + Custom) to be more robust in the documentation and implementation.
    

## \[2.4.1\] - 2025-11-21

UI/UX Improvements and Bug Fixes.

### Added

- **Metadata Injection:** Page Title, Author, and Modification Date are now injected directly into the HTML Body (top of the page) for better readability.
    
- **Automatic Time-stamping:** Output folders are now automatically named with `YYYY-MM-DD HHMM [Title]` to support clean versioned backups.
    
- **Persistent Sidebar:** The sidebar width is now remembered across page loads using `localStorage`.
    
- **Absolute Links in Markdown:** The generated `sidebar.md` uses absolute file URIs to support opening links in external editors like Logseq or WebStorm directly.
    

### Fixed

- **Empty Page Bug:** Fixed an issue where pages with empty bodies (folders) resulted in 0-byte HTML files. Now generates a proper HTML skeleton with title and sidebar.
    
- **Markdown Patching:** Updated `patch_sidebar.py` to handle absolute file URIs correctly.
    
- **UI Layout:** Optimized Sidebar/Content padding and Hamburger button alignment.
    

## \[2.4.0\] - 2025-11-21

Advanced Filtering and Tree Logic Update.

### Added

- **Label Forest Mode:** The `label` command now supports deep recursion ("Forest Export"). It finds all pages with the include-label and treats them as roots for full tree exports.
    
- **Label Pruning:** Added `--exclude-label` to prune subtrees based on a specific label (e.g., 'archived') during recursion.
    

## \[2.3.0\] - 2025-11-21

Enterprise Performance & Usability Release.

### Added

- **Recursive Inventory:** Changed scanning logic to use `/child/page` API endpoints. This ensures the export respects the **manual sort order** of Confluence.
    
- **Multithreading:** Added `-t/--threads` argument to parallelize page downloads (Phase 2), significantly improving performance on large spaces.
    
- **Tree Pruning (ID):** Added `--exclude-page-id` to skip specific branches during recursion.
    
- **JS Resizer:** The sidebar now has a robust JavaScript-based drag-handle for resizing.
    
- **UX Improvements:**
    
    - Fixed Hamburger position (top-left).
        
    - Added "Heartbeat" visualization during inventory scan.
        
    - Added VPN Reminder for Data Center profiles.
        

### Changed

- **Architecture:** Split process into a strict "Inventory Phase" (Serial, Recursive for sorting) and "Download Phase" (Parallel).
    

## \[2.2.0\] - 2025-11-20

Introduction of Static Sidebar Injection.

### Added

- **Static Sidebar Injection:** Automatically generates a hierarchical navigation tree and injects it into every HTML page.
    
- **Inventory Phase:** Scans all pages/metadata _before_ downloading content to allow for accurate progress bars (`tqdm`) and global tree generation.
    
- **Smart Linking:** Improved detection of dead/external links vs. local links based on the inventory.
    
- **CSS Auto-Discovery:** The script automatically detects and applies `site.css` from the local `styles/` folder.
    
- **Multi-CSS Support:** Allows layering multiple CSS files (Standard + Custom).
    
- **`sidebar.html` Export:** Saves the generated sidebar tree as a separate file.
    

### Changed

- **HTML Layout:** Pages are now wrapped in a Flexbox layout container to support the sidebar.
    
- **Logging:** Cleaned up library logging to support progress bars.
    

## \[2.1.0\] - 2025-11-19

Major functionality restore and improvement ("Visual Copy" release).

### Added

- **HTML Processing with BeautifulSoup:** Re-introduced intelligent HTML parsing.
    
    - **Image Downloading:** Automatically detects embedded images/emoticons, downloads them, and rewrites HTML links to local paths (`../attachments/`).
        
    - **Link Sanitizing:** Attempts to rewrite Confluence internal links to relative filenames.
        
    - **Metadata Injection (Head):** Injects Title, Page ID, and Labels into the HTML `<head>`.
        
- **Export View:** Switched API fetch from `storage` format to `export_view` (or `view`) to get rendered HTML (resolves macros like TOC).
    
- **Attachment Downloading:** Downloads _all_ attachments of a page via API list, not just those embedded in the text.
    

### Changed

- **HTML First:** The primary output format is now processed HTML (`export_view`). RST export is optional via `-R`.
    
- **Dependencies:** Added `beautifulsoup4` to requirements.
    
- **CSS handling:** Improved relative pathing for robust offline viewing.
    

## \[2.0.0\] - 2025-11-17

This version introduces a major architectural refactoring to support both Confluence Cloud and Data Center.

### Added

- **Confluence Data Center Support:** The script now supports both Confluence Cloud (`--profile cloud`) and Data Center (`--profile dc`).
    
- **Configuration File (`confluence_products.ini`):** All platform-specific values (API URL templates, auth methods, base paths) are now defined in this external INI file.
    
- **Data Center Authentication:** Added support for Bearer Token (Personal Access Token) authentication.
    
- **New `label` Command:** Added support for dumping all pages with a specific label.
    
- **Troubleshooting Hints:** Added specific error messages for Data Center users when authentication fails (Intranet/VPN warning).
    
- **Documentation:** Added `CONTRIBUTING.md` and `CHANGELOG.md`.
    

### Changed

- **\[BREAKING CHANGE\] CLI Architecture (Sub-Commands):** The script's interface has been completely modernized, replacing the `-m`/`--mode` flag with sub-commands (like `git`).
    
    - **REMOVED:** The `-m`/`--mode` flag.
        
    - **REMOVED:** The `-s`/`--site` argument.
        
    - **ADDED:** Sub-commands: `single`, `tree`, `space`, `all-spaces`, `label`.
        
    - **ADDED (Global):** `--base-url`, `--profile`, `--context-path`.
        
- **Refactored `myModules.py`:** All API functions are now platform-agnostic. Hardcoded URLs removed.
    
- **Internationalization:** All code comments translated to English.
    

_History below this line is from the original author (jgoldin-skillz)._

## \[1.0.2\] - 2022-03-03

- Bugfixes
    

## \[1.0.1\] - 2022-03-03

- Added `confluenceDumpWithPython.py`
    

## \[1.0.0\] - 2022-03-01

- Initial version