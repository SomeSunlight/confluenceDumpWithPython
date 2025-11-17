#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script dumps content from a Confluence instance (Cloud or Data Center).
It fetches rendered HTML (export_view), processes it with BeautifulSoup to
localize images and links, downloads attachments, and optionally converts to RST/HTML.
"""

import argparse
import os
import sys
import json
import shutil
import glob
from confluence_dump import myModules

# --- External Libraries ---
try:
    import pypandoc
except ImportError:
    pypandoc = None

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm is not installed: simple iterator that prints nothing extra
    print("Info: 'tqdm' not found. Progress bars will be disabled. (pip install tqdm)", file=sys.stderr)


    def tqdm(iterable, **kwargs):
        return iterable

# --- Global Config & State ---
platform_config = {}
auth_info = {}
all_pages_metadata = []  # Stores dicts: {'id': str, 'title': str, 'parent_id': str}


# --- Processing Helpers ---

def collect_page_metadata(page_full):
    """ Collects metadata for the index generation. """
    try:
        page_id = page_full.get('id')
        title = page_full.get('title')
        ancestors = page_full.get('ancestors', [])
        parent_id = ancestors[-1]['id'] if ancestors else None

        if page_id:
            all_pages_metadata.append({
                'id': page_id,
                'title': title,
                'parent_id': parent_id
            })
    except Exception as e:
        print(f"Warning: Could not collect metadata for index: {e}", file=sys.stderr)


def save_page_attachments(page_id, attachments, base_url, auth_info):
    """ Downloads all attachments listed in the API response for a page. """
    if not attachments or 'results' not in attachments:
        return

    for att in attachments['results']:
        download_path = att.get('_links', {}).get('download')
        filename = att.get('title')

        if download_path and filename:
            if download_path.startswith('/'):
                full_url = base_url.rstrip('/') + download_path
            else:
                full_url = base_url.rstrip('/') + '/' + download_path

            local_path = os.path.join(myModules.outdir_attachments, filename)
            myModules.download_file(full_url, local_path, auth_info)


def convert_html(page_id, page_title, page_body, outdir_pages, css_filename=None):
    """
    Converts Confluence storage HTML to standard HTML via pandoc.
    Uses --standalone to create full HTML files with head/body.
    """
    if pypandoc is None: return

    page_filename_html = f"{outdir_pages}{page_id}.html"

    # Default CSS path relative to the HTML file
    css_path = "../styles/site.css"
    if css_filename:
        css_path = f"../styles/{os.path.basename(css_filename)}"

    pdoc_args = [
        '--standalone',
        f'--css={css_path}',
        '--metadata', f'title={page_title}'
    ]

    try:
        output = pypandoc.convert_text(
            page_body,
            'html',
            format='html',
            outputfile=page_filename_html,
            extra_args=pdoc_args
        )
        assert output == ""
    except Exception as e:
        print(f"  Error converting HTML for {page_id}: {e}", file=sys.stderr)


def convert_rst(page_id, page_body, outdir_pages):
    """ Converts processed HTML file to RST via pandoc """
    if pypandoc is None: return

    page_filename_rst = f"{outdir_pages}{page_id}.rst"
    # print(f"  Converting to RST: {page_filename_rst}")
    try:
        output = pypandoc.convert_text(page_body, 'rst', format='html', outputfile=page_filename_rst)
        assert output == ""
    except Exception as e:
        print(f"  Error converting RST for {page_id}: {e}", file=sys.stderr)


# --- Core Logic ---

def create_error_placeholder(page_id, page_title, html_filename):
    """ Creates a minimal HTML file indicating that the download failed. """
    try:
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Download Failed: {page_title}</title>
                <style>
                    body {{ font-family: sans-serif; padding: 50px; text-align: center; }}
                    .error-box {{ border: 2px solid #d32f2f; background: #ffebee; padding: 20px; display: inline-block; }}
                    h1 {{ color: #d32f2f; }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1>Download Failed</h1>
                    <p>The content for page <b>{page_id}</b> could not be retrieved during export.</p>
                    <p>Please check the export logs for details.</p>
                </div>
            </body>
            </html>
            """)
        print(f"  -> Created placeholder for failed page: {page_id}")
    except Exception as e:
        print(f"  Error creating placeholder: {e}", file=sys.stderr)


def process_page(page_id, global_args, active_css_files=None, exported_page_ids=None, verbose=True):
    """
    Downloads and processes a single page.
    :param verbose: If True, prints details to stdout. If False (for progress bars), stays silent except for errors.
    """
    if verbose:
        print(f"\nProcessing page ID: {page_id}")

    # 1. Get Page (with export_view)
    page_full = myModules.get_page_full(
        page_id,
        global_args.base_url,
        platform_config,
        auth_info,
        global_args.context_path
    )

    # Define filename early
    html_filename = os.path.join(myModules.outdir_pages, f"{page_id}.html")

    if not page_full:
        # ERROR HANDLING: Create placeholder
        print(f"  Warning: Could not fetch page {page_id}. Creating placeholder.", file=sys.stderr)
        create_error_placeholder(page_id, "Unknown Title", html_filename)
        return

    # Collect Metadata for Index
    collect_page_metadata(page_full)

    page_title = page_full.get('title', 'Untitled')
    if verbose:
        print(f"  Title: {page_title}")

    # 2. Get Raw HTML
    raw_html = page_full.get('body', {}).get('export_view', {}).get('value')
    if not raw_html:
        raw_html = page_full.get('body', {}).get('view', {}).get('value', '')

    # 3. Process HTML (BeautifulSoup)
    processed_html = myModules.process_page_content(
        raw_html,
        page_full,
        global_args.base_url,
        auth_info,
        active_css_files,
        exported_page_ids
    )

    # 4. Save HTML File
    html_filename = os.path.join(myModules.outdir_pages, f"{page_id}.html")
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(processed_html)

    # 5. Get & Download Attachments
    page_attachments = myModules.get_page_attachments(
        page_id,
        global_args.base_url,
        platform_config,
        auth_info,
        global_args.context_path
    )
    save_page_attachments(page_id, page_attachments, global_args.base_url, auth_info)

    # 6. Save Metadata JSON
    json_filename = os.path.join(myModules.outdir_pages, f"{page_id}.json")
    page_full['body_processed'] = processed_html
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(page_full, f, indent=4, ensure_ascii=False)

    # 7. Optional RST Export
    if global_args.rst:
        convert_rst(page_id, processed_html, myModules.outdir_pages)


# --- Index Generation ---

def build_index_html(output_dir, css_files=None):
    """ Generates an index.html file listing all downloaded pages hierarchically. """
    print("\nGenerating index.html...")
    tree_map = {}
    pages_map = {}
    for page in all_pages_metadata:
        pid = page['id']
        parent = page['parent_id']
        pages_map[pid] = page
        if parent not in tree_map: tree_map[parent] = []
        tree_map[parent].append(pid)

    def build_list_html(parent_id):
        if parent_id not in tree_map: return ""
        html = "<ul>"
        for child_id in tree_map[parent_id]:
            if child_id in pages_map:
                child = pages_map[child_id]
                html += f'<li><a href="pages/{child_id}.html">{child["title"]}</a>'
                html += build_list_html(child_id)
                html += '</li>'
        html += "</ul>"
        return html

    downloaded_ids = set(pages_map.keys())
    root_ids = []
    for page in all_pages_metadata:
        parent = page['parent_id']
        if parent is None or parent not in downloaded_ids:
            root_ids.append(page['id'])

    body_html = "<h1>Confluence Export Index</h1><ul>"
    for rid in root_ids:
        page = pages_map[rid]
        body_html += f'<li><a href="pages/{rid}.html">{page["title"]}</a>'
        body_html += build_list_html(rid)
        body_html += '</li>'
    body_html += "</ul>"

    css_links = ""
    if css_files:
        for css in css_files:
            clean_css = css.replace('../', '')
            css_links += f'<link rel="stylesheet" href="{clean_css}" type="text/css">'

    full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Index</title>{css_links}<style>body{{font-family:sans-serif;padding:20px;}}ul{{list-style-type:disc;}}li{{margin-bottom:5px;}}a{{text-decoration:none;color:#0052cc;}}a:hover{{text-decoration:underline;}}</style></head><body>{body_html}</body></html>"""

    with open(os.path.join(output_dir, "index.html"), 'w', encoding='utf-8') as f:
        f.write(full_html)


# --- Handlers ---

def handle_single(args, active_css_files=None):
    target_ids = {args.pageid}
    print(f"Starting 'single' dump for {args.pageid}")
    # Single page -> No progress bar needed, verbose=True
    process_page(args.pageid, args, active_css_files, target_ids, verbose=True)


def get_page_tree_recursive(page_id, args):
    pids = [page_id]
    children = myModules.get_page_children(page_id, args.base_url, platform_config, auth_info, args.context_path)
    if children and 'results' in children:
        for child in children['results']:
            pids.extend(get_page_tree_recursive(child['id'], args))
    return pids


def handle_tree(args, active_css_files=None):
    print(f"Starting 'tree' dump for {args.pageid} (Inventory Phase)...")
    all_ids = get_page_tree_recursive(args.pageid, args)
    target_ids = set(all_ids)

    print(f"Found {len(all_ids)} pages in tree. Processing...")
    # Progress bar loop
    for pid in tqdm(all_ids, desc="Downloading Pages", unit="page"):
        process_page(pid, args, active_css_files, target_ids, verbose=False)


def handle_space(args, active_css_files=None):
    print(f"Starting 'space' dump for {args.space_key}")
    print("Phase 1: Inventory Scan (Fetching Page IDs)...")

    target_ids = set()
    all_pages_list = []
    start = 0

    # Phase 1: Scan (Spinner logic could be added here, but simple print is OK)
    while True:
        res = myModules.get_pages_from_space(args.space_key, start, 200, args.base_url, platform_config, auth_info,
                                             args.context_path)
        if not res or not res.get('results'): break

        results = res['results']
        for p in results:
            target_ids.add(p['id'])
            all_pages_list.append(p['id'])

        print(f"  Scanned {len(results)} pages (Total found: {len(target_ids)})...")
        start += 200

    print(f"Phase 2: Downloading & Processing {len(target_ids)} pages...")
    # Progress bar loop
    for pid in tqdm(all_pages_list, desc="Downloading Pages", unit="page"):
        process_page(pid, args, active_css_files, target_ids, verbose=False)


def handle_label(args, active_css_files=None):
    print(f"Starting 'label' dump for {args.label}")
    print("Phase 1: Inventory Scan (Fetching Page IDs)...")

    target_ids = set()
    all_pages_list = []
    start = 0

    while True:
        res = myModules.get_pages_by_label(args.label, start, 200, args.base_url, platform_config, auth_info,
                                           args.context_path)
        if not res or not res.get('results'): break

        results = res['results']
        for p in results:
            target_ids.add(p['id'])
            all_pages_list.append(p['id'])

        print(f"  Scanned {len(results)} pages (Total found: {len(target_ids)})...")
        start += 200

    print(f"Phase 2: Downloading & Processing {len(target_ids)} pages...")
    for pid in tqdm(all_pages_list, desc="Downloading Pages", unit="page"):
        process_page(pid, args, active_css_files, target_ids, verbose=False)


def handle_all_spaces(args, active_css_files=None):
    print("Starting 'all-spaces' dump...")
    spaces = myModules.get_all_spaces(args.base_url, platform_config, auth_info, args.context_path)

    if spaces and 'results' in spaces:
        for s in spaces['results']:
            print(f"\n--- Processing Space: {s['key']} ---")
            s_args = argparse.Namespace(**vars(args))
            s_args.space_key = s['key']
            handle_space(s_args, active_css_files)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Confluence Dump (Cloud/DC) with HTML Processing")

    # Global
    g = parser.add_argument_group('Global')
    g.add_argument('-o', '--outdir', required=True, help="Output directory")
    g.add_argument('--base-url', required=True, help="Confluence Base URL")
    g.add_argument('--profile', required=True, help="cloud or dc")
    g.add_argument('--context-path', default=None, help="Context path (DC only)")
    g.add_argument('--css-file', default=None, help="Path to custom CSS file (applied AFTER standard CSS)")
    g.add_argument('-R', '--rst', action='store_true', help="Also export RST")

    # Subcommands
    subs = parser.add_subparsers(dest='command', required=True)

    p_single = subs.add_parser('single')
    p_single.add_argument('-p', '--pageid', required=True)
    p_single.set_defaults(func=handle_single)

    p_tree = subs.add_parser('tree')
    p_tree.add_argument('-p', '--pageid', required=True)
    p_tree.set_defaults(func=handle_tree)

    p_space = subs.add_parser('space')
    p_space.add_argument('-sp', '--space-key', required=True)
    p_space.set_defaults(func=handle_space)

    p_label = subs.add_parser('label')
    p_label.add_argument('-l', '--label', required=True)
    p_label.set_defaults(func=handle_label)

    p_all = subs.add_parser('all-spaces')
    p_all.set_defaults(func=handle_all_spaces)

    args = parser.parse_args()

    # Setup
    global platform_config, auth_info
    active_css_files = []

    try:
        platform_config = myModules.load_platform_config(args.profile)
        auth_info = myModules.get_auth_config(platform_config)

        myModules.setup_output_directories(args.outdir)
        myModules.set_variables()

        # --- CSS Strategy: Standard + Custom ---
        local_styles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'styles')
        standard_css_source = None

        if os.path.exists(local_styles_dir):
            possible_files = glob.glob(os.path.join(local_styles_dir, "*.css"))
            if os.path.join(local_styles_dir, "site.css") in possible_files:
                standard_css_source = os.path.join(local_styles_dir, "site.css")
            elif possible_files:
                standard_css_source = possible_files[0]

        if standard_css_source:
            print(f"Found standard CSS: {standard_css_source}")
            std_dest_name = os.path.basename(standard_css_source)
            target_std = os.path.join(myModules.outdir_styles, std_dest_name)
            shutil.copy(standard_css_source, target_std)
            active_css_files.append(f"../styles/{std_dest_name}")
        else:
            print("Info: No standard CSS found in ./styles/. Base styling might be missing.")

        if args.css_file:
            if os.path.exists(args.css_file):
                print(f"Adding custom CSS: {args.css_file}")
                custom_dest_name = os.path.basename(args.css_file)
                if standard_css_source and custom_dest_name == os.path.basename(standard_css_source):
                    name, ext = os.path.splitext(custom_dest_name)
                    custom_dest_name = f"{name}_custom{ext}"
                    print(f"  -> Renamed to {custom_dest_name} to avoid collision.")
                target_custom = os.path.join(myModules.outdir_styles, custom_dest_name)
                shutil.copy(args.css_file, target_custom)
                active_css_files.append(f"../styles/{custom_dest_name}")
            else:
                print(f"Warning: Custom CSS file {args.css_file} not found.", file=sys.stderr)

    except Exception as e:
        print(f"Init Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run
    try:
        args.func(args, active_css_files)
        build_index_html(args.outdir, active_css_files)
        print(f"\nDump Complete. Output in {args.outdir}")
    except Exception as e:
        print(f"Execution Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()