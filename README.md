# Confluence Dump with Python

This script exports content from a Confluence instance (Cloud or Data Center) using various modes.

**Key Features:**

- **Visual Fidelity & Sidebar:** Creates a visually faithful copy of Confluence pages, including a **fully functional, static navigation sidebar** on the left—something even the standard Confluence export does not provide.
    
- **Offline Browsing:** Localizes images and links, and downloads **all** attachments (PDFs, Office docs, etc.) for complete offline access.
    
- **Recursive Inventory:** Scans the tree hierarchy to ensure the **correct sort order** (manual Confluence order) in the sidebar.
    
- **Metadata Injection:** Automatically adds Page Title, Author, and Modification Date to the top of every page.
    
- **Versioning:** Automatically creates timestamped output subfolders (e.g., `2025-11-21 1400 Space IT`). This allows you to run the script repeatedly (e.g., after changes in Confluence) and maintain a history of snapshots without overwriting previous exports.
    
- **Performance:** Supports **Multithreaded** downloading (`--threads`) to speed up the export of large spaces.
    
- **Tree Pruning:** Exclude specific branches with `--exclude-page-id` or `--exclude-label`.
    
- **Index Sandbox:** Includes visual tools to manually restructure the navigation tree via Drag & Drop and apply it to the downloaded files without affecting Confluence.
    

## Missing Features / Ideas

- **Incremental Update:** Currently, the script always performs a full export. An update mode that only downloads changed pages would be a valuable addition.
    

## Requirements

- Python 3.x
    
- `requests`, `beautifulsoup4`, `tqdm`
    
- `pypandoc` (optional, only needed for RST export)
    

```
pip install -r requirements.txt
```

## Authentication

Authentication is handled via environment variables, based on the profile you select.

### For Confluence Cloud (`--profile cloud`)

```
export CONFLUENCE_USER="your-email@example.com"
export CONFLUENCE_TOKEN="YourApiTokenHere"
```

### For Confluence Data Center (`--profile dc`)

```
export CONFLUENCE_TOKEN="YourPersonalAccessTokenHere"
```

**⚠️ Troubleshooting Note for Data Center:** If authentication fails (Intranet/SSO blocks), ensure you are on VPN and PATs are enabled.

## Exporting with CSS Styling

The script uses a robust **Two-Layer Styling Strategy**.

### Layer 1: Standard CSS (Default)

The project folder contains a `styles/` directory. If a CSS file exists there (e.g., `styles/site.css`), it is **automatically applied** to every export.

### Layer 2: Custom CSS (Optional)

Use `--css-file "/path/to/my_custom.css"` to apply specific overrides. This file will be loaded **after** the standard CSS.

## Usage

### General Syntax

```
python3 confluenceDumpWithPython.py [GLOBAL_OPTIONS] <COMMAND> [COMMAND_OPTIONS]
```

### Global Options

```
  -o OUTDIR, --outdir OUTDIR
                        The output directory (will be created)
  --base-url BASE_URL   Confluence Base URL (e.g., '[https://confluence.corp.com](https://confluence.corp.com)')
  --profile PROFILE     Platform profile ('cloud' or 'dc')
  --context-path PATH   (DC only) Context path (e.g., '/wiki')
  --threads THREADS, -t THREADS
                        Number of download threads (Default: 1)
  --exclude-page-id ID  Exclude a page ID and its children (can be repeated)
  --no-vpn-reminder     Skip the VPN check confirmation (DC only)
  --css-file CSS_FILE   Path to custom CSS file
  -R, --rst             Export pages as RST (requires pypandoc)
```

### Commands

- **`space`**: Dumps an entire space. Starts at the Space Homepage and recurses down.
    
    - `-sp`, `--space-key`: The Key of the space.
        
- **`tree`**: Dumps a specific page and all its descendants.
    
    - `-p`, `--pageid`: The Root Page ID.
        
- **`single`**: Dumps a single page.
    
    - `-p`, `--pageid`: The Page ID.
        
- **`label`**: Dumps pages by label ("Forest Mode"). Finds all pages with the label and treats them as roots for recursion.
    
    - `-l`, `--label`: The label to include.
        
    - `--exclude-label`: Exclude subtrees that have this specific label (e.g. 'archived').
        
- **`all-spaces`**: Dumps all visible spaces.
    

### Examples

**1\. Data Center: Entire Space, 8 Threads, Exclude Archive**

```
python3 confluenceDumpWithPython.py \
    --base-url "[https://confluence.corp.com](https://confluence.corp.com)" \
    --profile dc \
    --context-path "/wiki" \
    -o "./dump_it" \
    -t 8 \
    --exclude-page-id "999999" \
    space -sp "IT"
```

**2\. Cloud: Single Page Tree**

```
python3 confluenceDumpWithPython.py \
    --base-url "[https://myteam.atlassian.net](https://myteam.atlassian.net)" \
    --profile cloud \
    -o "./dump_tree" \
    tree -p "12345"
```

## Index Restructuring Sandbox

This additional toolset allows you to re-organize the pages and sub-pages structure (the index) of your export locally. This is useful for testing structural changes or cleaning up the navigation flow without touching Confluence or re-downloading pages.

**The Workflow:**

1. **Generate Editor:** Create a visual Drag & Drop editor for the index of all exported pages.
    
    ```
    python3 create_editor.py --site-dir "./output/2025-01-01 Space IT"
    ```
    
2. **Edit:** Open `editor_sidebar.html` in your browser. Move pages, create folders, delete items.
    
3. **Save:** Click "Copy Markdown" in the editor and paste the content into a new file `sidebar_edit.md` in the site directory.
    
4. **Apply:** Patch the new index structure into all **downloaded** HTML files.
    
    ```
    python3 patch_sidebar.py --site-dir "./output/2025-01-01 Space IT"
    ```