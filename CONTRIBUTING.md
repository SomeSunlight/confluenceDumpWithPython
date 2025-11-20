# Contributing Guide

This document explains the internal architecture of this script, primarily for future contributors or the original author when reviewing pull requests.

## Architectural Overview

The codebase has been refactored from a simple linear scraper to a multi-phase, multithreaded export engine designed for enterprise stability.

### Core Philosophy

- **Inventory First:** We scan the entire structure _before_ downloading content. This allows for accurate progress bars (`tqdm`) and correct sorting.
    
- **Static & Self-Contained:** The output HTML must work without a server, internet connection, or JavaScript dependencies (Zero-Dependency).
    
- **Platform Agnostic:** `confluence_products.ini` abstracts the differences between Cloud and Data Center.
    

### The Export Pipeline (`confluenceDumpWithPython.py`)

1. **Inventory Phase (Serial):**
    
    - Uses recursion (e.g., `recursive_scan`) to walk the Confluence tree using `child/page` endpoints.
        
    - This guarantees the sidebar matches the _manual sort order_ of Confluence (unlike CQL search).
        
    - Applies pruning (excludes) at this stage to save time.
        
    - Generates `sidebar.md` (Markdown representation) and `sidebar.html` (HTML Tree).
        
2. **Download Phase (Parallel):**
    
    - Uses `ThreadPoolExecutor` to fetch `export_view` HTML and attachments in parallel.
        
    - Calls `myModules.process_page_content` to sanitize HTML (BeautifulSoup).
        
3. **Injection Phase:**
    
    - Injects the pre-calculated Sidebar, Metadata, and CSS into every downloaded page.
        

### The Editor Workflow (`create_editor.py` & `patch_sidebar.py`)

We treat the exported structure as mutable.

- **`create_editor.py`**: Parses the `sidebar.md` and generates a standalone HTML Single-Page-Application using vanilla JavaScript. It allows Drag & Drop reordering.
    
- **`patch_sidebar.py`**: Parses the modified Markdown and re-injects the new navigation tree into all existing HTML files.
    

## Key Files

- **`confluenceDumpWithPython.py`**: Main entry point and orchestration.
    
- **`myModules.py`**: API abstraction, BeautifulSoup logic, and HTML templating.
    
- **`confluence_products.ini`**: URL templates for Cloud vs. DC.
    
- **`create_editor.py`**: Tool to generate the visual sidebar editor.
    
- **`patch_sidebar.py`**: Tool to apply structure changes.