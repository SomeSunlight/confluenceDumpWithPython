# Confluence Dump with Python

This script exports content from a Confluence instance (Cloud or Data Center) using various modes (single page, page tree, full space, all spaces, or by label).

**Key Features:**

- **Visual Copy:** Fetches the rendered HTML (`export_view`) to preserve macros, tables, and formatting.
    
- **Offline Browsing:** Downloads embedded images/emoticons and rewrites links to be relative, creating a self-contained offline HTML archive.
    
- **Metadata:** Injects Confluence metadata (Page ID, Labels, Title) directly into the HTML headers.
    
- **Complete Archive:** Downloads _all_ page attachments, not just those displayed on the page.
    
- **Multi-Format:** Exports as JSON (metadata + raw body), HTML (visual), and optional RST.
    

## Platform Support

This script supports both:

- **Confluence Cloud**
    
- **Confluence Data Center**
    

The platform-specific API paths and authentication methods are defined in the `confluence_products.ini` file.

## Requirements

- Python 3.x
    
- `requests`
    
- `beautifulsoup4` (for HTML parsing and link rewriting)
    
- `pypandoc` (optional, for RST export or legacy HTML conversion)
    

## Installation

```
git clone [https://github.com/jgoldin-skillz/confluenceDumpWithPython.git](https://github.com/jgoldin-skillz/confluenceDumpWithPython.git)
cd confluenceDumpWithPython
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

The script uses a robust **Two-Layer Styling Strategy** to ensure the exported HTML looks correct.

### Layer 1: Standard CSS (Default)

The project folder contains a `styles/` directory. This should contain a "Best Guess" CSS file (e.g., `site.css`) extracted from a standard Confluence instance.

- **Automatic:** If a CSS file exists in the local `styles/` folder, it is **automatically applied** to every export.
    
- **Maintenance:** You can update this file manually if Confluence changes its base layout significantly.
    

### Layer 2: Custom CSS (Optional)

If you have specific styles for your Space (logos, colors, custom macros) that override the standard look, you can provide a second CSS file via the command line.

- **Usage:** Use `--css-file "/path/to/my_custom.css"`.
    
- **Behavior:** This file will be loaded **after** the standard CSS, allowing you to override specific styles without losing the basic formatting.
    

## Usage

### General Syntax

```
python3 confluenceDumpWithPython.py [GLOBAL_OPTIONS] <COMMAND> [COMMAND_OPTIONS]
```

### Command-Line Arguments

Run `python3 confluenceDumpWithPython.py -h` to see all options.

```
usage: confluenceDumpWithPython.py [-h] -o OUTDIR --base-url BASE_URL --profile PROFILE [--context-path CONTEXT_PATH] [-R] [--css-file CSS_FILE] {single,tree,space,all-spaces,label} ...

Global Options:
  -h, --help            show this help message and exit
  -o OUTDIR, --outdir OUTDIR
                        The output directory (will be created)
  --base-url BASE_URL   The full base URL.
  --profile PROFILE     Platform profile ('cloud' or 'dc').
  --context-path CONTEXT_PATH
                        (Data Center only) Manually override the context path.
  -R, --rst             Export pages as RST.
  --css-file CSS_FILE   Path to a local custom CSS file (applied AFTER standard CSS).
```

### Examples

#### 1\. Standard Dump (Uses default CSS)

Dumps a page tree. Automatically applies `styles/site.css` if present in the script folder.

```
python3 confluenceDumpWithPython.py \
    --base-url "[https://confluence.mycompany.com](https://confluence.mycompany.com)" \
    --profile "dc" \
    --context-path "/wiki" \
    -o "./tree_dump" \
    tree \
    --pageid "67890"
```

#### 2\. Customized Dump (Standard + Custom CSS)

Dumps a page tree. Applies `styles/site.css` (standard) AND `my_overrides.css` (custom).

```
python3 confluenceDumpWithPython.py \
    --base-url "[https://confluence.mycompany.com](https://confluence.mycompany.com)" \
    --profile "dc" \
    --context-path "/wiki" \
    -o "./tree_dump" \
    --css-file "./my_overrides.css" \
    tree \
    --pageid "67890"
```