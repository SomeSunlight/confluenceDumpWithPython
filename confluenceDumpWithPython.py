#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script dumps content from a Confluence instance (Cloud or Data Center).
Features:
- Recursive Inventory Scan (Correct Sort Order)
- Multithreaded Downloading
- HTML Processing with BeautifulSoup (Images, Links, Sidebar, Resizer)
- Static Sidebar Injection
- CSS Auto-Discovery
- Label-based Tree Pruning
- Automatic Timestamped Subdirectories
"""

import argparse
import os
import sys
import json
import shutil
import glob
import time
import re
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from confluence_dump import myModules

# --- External Libraries ---
try:
    import pypandoc
except ImportError:
    pypandoc = None

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

# --- Global Config & State ---
platform_config = {}
auth_info = {}
all_pages_metadata = []
seen_metadata_ids = set()
global_sidebar_html = ""


# --- Helper Functions ---

def sanitize_filename(filename):
    """
    Sanitizes a string to be safe for directory names.
    Removes/replaces invalid characters for Windows/Linux/macOS.
    """
    # Replace bad chars with underscore or space
    # Invalid chars: < > : " / \ | ? *
    s = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Strip whitespace and dots from ends
    return s.strip().strip('.')


def get_run_title(args, base_url, platform_config, auth_info):
    """ Determines the semantic title for the output folder based on the command. """
    if args.command == 'all-spaces':
        return "all spaces"

    elif args.command == 'space':
        return f"Space {args.space_key}"

    elif args.command == 'label':
        return f"Export {args.label}"

    elif args.command in ('single', 'tree'):
        # For page-based commands, we need the page title.
        # We perform a quick API fetch here.
        print(f"Fetching title for page {args.pageid} to name the output folder...")
        try:
            # Assuming context path is needed for DC
            context_path = args.context_path
            page_data = myModules.get_page_basic(args.pageid, base_url, platform_config, auth_info, context_path)
            if page_data and 'title' in page_data:
                return page_data['title']
            else:
                return f"Page {args.pageid}"  # Fallback if title fetch fails
        except Exception as e:
            print(f"Warning: Could not fetch page title: {e}", file=sys.stderr)
            return f"Page {args.pageid}"

    return "Export"


# --- Processing Helpers ---

def collect_page_metadata(page_full):
    try:
        page_id = page_full.get('id')
        if not page_id or page_id in seen_metadata_ids:
            return
        title = page_full.get('title')
        ancestors = page_full.get('ancestors', [])
        parent_id = ancestors[-1]['id'] if ancestors else None
        all_pages_metadata.append({'id': page_id, 'title': title, 'parent_id': parent_id})
        seen_metadata_ids.add(page_id)
    except Exception as e:
        print(f"Warning: Could not collect metadata for index: {e}", file=sys.stderr)


def save_page_attachments(page_id, attachments, base_url, auth_info):
    if not attachments or 'results' not in attachments: return
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


def convert_rst(page_id, page_body, outdir_pages):
    if pypandoc is None: return
    page_filename_rst = f"{outdir_pages}{page_id}.rst"
    try:
        pypandoc.convert_text(page_body, 'rst', format='html', outputfile=page_filename_rst)
    except Exception as e:
        print(f"  Error converting RST for {page_id}: {e}", file=sys.stderr)


# --- Tree Generation ---

def build_tree_structure(target_ids):
    tree_map = {}
    pages_map = {}
    relevant_pages = [p for p in all_pages_metadata if p['id'] in target_ids]
    for page in relevant_pages:
        pid = page['id']
        parent = page['parent_id']
        pages_map[pid] = page
        if parent not in tree_map: tree_map[parent] = []
        tree_map[parent].append(pid)
    downloaded_ids = set(pages_map.keys())
    root_ids = []
    for page in relevant_pages:
        parent = page['parent_id']
        if parent is None or parent not in downloaded_ids:
            root_ids.append(page['id'])
    return tree_map, pages_map, root_ids


def generate_tree_html(target_ids):
    tree_map, pages_map, root_ids = build_tree_structure(target_ids)

    def build_branch(parent_id):
        if parent_id not in tree_map: return ""
        html = "<ul>"
        for child_id in tree_map[parent_id]:
            if child_id not in pages_map: continue
            child = pages_map[child_id]
            title = child['title']
            link = f'<a href="{child_id}.html">{title}</a>'
            if child_id in tree_map:
                sub_tree = build_branch(child_id)
                html += f'<li class="folder"><details><summary>{link}</summary>{sub_tree}</details></li>'
            else:
                html += f'<li class="leaf">{link}</li>'
        html += "</ul>"
        return html

    sidebar = '<div class="sidebar-tree"><ul>'
    for rid in root_ids:
        if rid not in pages_map: continue
        page = pages_map[rid]
        title = page['title']
        link = f'<a href="{rid}.html">{title}</a>'
        if rid in tree_map:
            sub_tree = build_branch(rid)
            sidebar += f'<li class="folder"><details open><summary>{link}</summary>{sub_tree}</details></li>'
        else:
            sidebar += f'<li class="leaf">{link}</li>'
    sidebar += '</ul></div>'
    return sidebar


def generate_tree_markdown(target_ids):
    tree_map, pages_map, root_ids = build_tree_structure(target_ids)
    md_lines = []
    pages_dir_abs = os.path.abspath(myModules.outdir_pages)
    pages_uri = Path(pages_dir_abs).as_uri()

    def build_branch_md(parent_id, level):
        if parent_id not in tree_map: return
        indent = "  " * level
        for child_id in tree_map[parent_id]:
            if child_id not in pages_map: continue
            child = pages_map[child_id]
            md_lines.append(f"{indent}- [{child['title']}]({pages_uri}/{child_id}.html)")
            if child_id in tree_map:
                build_branch_md(child_id, level + 1)

    for rid in root_ids:
        if rid not in pages_map: continue
        page = pages_map[rid]
        md_lines.append(f"- [{page['title']}]({pages_uri}/{rid}.html)")
        if rid in tree_map:
            build_branch_md(rid, 1)

    return "\n".join(md_lines)


def save_sidebars(outdir, target_ids):
    global global_sidebar_html
    global_sidebar_html = generate_tree_html(target_ids)
    with open(os.path.join(outdir, 'sidebar.html'), 'w', encoding='utf-8') as f:
        f.write(global_sidebar_html)

    sidebar_md = generate_tree_markdown(target_ids)
    with open(os.path.join(outdir, 'sidebar.md'), 'w', encoding='utf-8') as f:
        f.write(sidebar_md)


# --- Core Logic ---

def process_page(page_id, global_args, active_css_files=None, exported_page_ids=None, verbose=True):
    if verbose: print(f"\nProcessing page ID: {page_id}")
    page_full = myModules.get_page_full(page_id, global_args.base_url, platform_config, auth_info,
                                        global_args.context_path)
    if not page_full:
        print(f"  Warning: Could not fetch page {page_id}. Skipping.", file=sys.stderr)
        return
    if verbose: collect_page_metadata(page_full)

    raw_html = page_full.get('body', {}).get('export_view', {}).get('value')
    if not raw_html:
        raw_html = page_full.get('body', {}).get('view', {}).get('value', '')

    processed_html = myModules.process_page_content(
        raw_html, page_full, global_args.base_url, auth_info, active_css_files, exported_page_ids, global_sidebar_html
    )

    html_filename = os.path.join(myModules.outdir_pages, f"{page_id}.html")
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(processed_html)

    page_attachments = myModules.get_page_attachments(page_id, global_args.base_url, platform_config, auth_info,
                                                      global_args.context_path)
    save_page_attachments(page_id, page_attachments, global_args.base_url, auth_info)

    json_filename = os.path.join(myModules.outdir_pages, f"{page_id}.json")
    page_full['body_processed'] = processed_html
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(page_full, f, indent=4, ensure_ascii=False)

    if global_args.rst:
        convert_rst(page_id, processed_html, myModules.outdir_pages)


# --- Index Generation ---

def build_index_html(output_dir, css_files=None):
    print("\nGenerating global index.html...")
    tree_map, pages_map, root_ids = build_tree_structure(set(p['id'] for p in all_pages_metadata))

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


# --- Recursive Inventory & Scanning ---

def recursive_scan(page_id, args, exclude_ids, scanned_count, exclude_label=None):
    if page_id in exclude_ids:
        print(f"  [Excluded by ID] Pruning tree at page {page_id}", file=sys.stderr)
        return []

    tree_ids = [page_id]
    scanned_count[0] += 1
    if scanned_count[0] % 10 == 0:
        sys.stderr.write(f"\rScanned {scanned_count[0]} pages...")
        sys.stderr.flush()

    while True:
        children_data = myModules.get_child_pages(page_id, args.base_url, platform_config, auth_info, args.context_path)
        if not children_data or 'results' not in children_data: break
        children = children_data['results']
        if not children: break

        for child in children:
            child_id = child['id']
            if exclude_label:
                labels = [l['name'] for l in child.get('metadata', {}).get('labels', {}).get('results', [])]
                if exclude_label in labels:
                    print(f"  [Excluded by Label '{exclude_label}'] Pruning tree at page {child_id}", file=sys.stderr)
                    continue
            collect_page_metadata(child)
            tree_ids.extend(recursive_scan(child_id, args, exclude_ids, scanned_count, exclude_label))
        break
    return tree_ids


def scan_space_inventory(args, exclude_ids):
    print("Phase 1: Recursive Inventory Scan...")
    scanned_count = [0]
    homepage = myModules.get_space_homepage(args.space_key, args.base_url, platform_config, auth_info,
                                            args.context_path)
    if not homepage:
        print("Error: Could not find Space Homepage.", file=sys.stderr)
        return [], []
    root_id = homepage['id']
    collect_page_metadata(homepage)
    all_ids_ordered = recursive_scan(root_id, args, exclude_ids, scanned_count)
    print(f"\nInventory complete. Found {len(all_ids_ordered)} pages.")
    return set(all_ids_ordered), all_ids_ordered


def scan_tree_inventory(root_id, args, exclude_ids):
    print("Phase 1: Recursive Tree Scan...")
    scanned_count = [0]
    root_page = myModules.get_page_full(root_id, args.base_url, platform_config, auth_info, args.context_path)
    if root_page: collect_page_metadata(root_page)
    all_ids_ordered = recursive_scan(root_id, args, exclude_ids, scanned_count)
    print(f"\nInventory complete. Found {len(all_ids_ordered)} pages.")
    return set(all_ids_ordered), all_ids_ordered


def scan_label_forest_inventory(args, exclude_ids):
    print(f"Phase 1: Label Forest Scan (Roots: '{args.label}')...")
    scanned_count = [0]
    root_pages = []
    start = 0
    while True:
        res = myModules.get_pages_by_label(args.label, start, 200, args.base_url, platform_config, auth_info,
                                           args.context_path)
        if not res or not res.get('results'): break
        for p in res['results']:
            if p['id'] in exclude_ids: continue
            root_pages.append(p)
        start += 200

    full_forest_ids = []
    exclude_label = getattr(args, 'exclude_label', None)
    for root in root_pages:
        collect_page_metadata(root)
        branch_ids = recursive_scan(root['id'], args, exclude_ids, scanned_count, exclude_label)
        full_forest_ids.extend(branch_ids)
    unique_ordered = list(dict.fromkeys(full_forest_ids))
    print(f"\nInventory complete. Found {len(unique_ordered)} unique pages.")
    return set(unique_ordered), unique_ordered


# --- Mode Handlers ---

def run_download_phase(args, all_pages_list, target_ids, active_css_files):
    print(f"Phase 2: Downloading & Processing {len(all_pages_list)} pages with {args.threads} threads...")
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for pid in all_pages_list:
            futures.append(executor.submit(process_page, pid, args, active_css_files, target_ids, verbose=False))
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Downloading", unit="page"):
            pass


def handle_space(args, active_css_files, exclude_ids):
    print(f"Starting 'space' dump for {args.space_key}")
    target_ids, all_pages_list = scan_space_inventory(args, exclude_ids)
    save_sidebars(args.outdir, target_ids)
    run_download_phase(args, all_pages_list, target_ids, active_css_files)


def handle_tree(args, active_css_files, exclude_ids):
    print(f"Starting 'tree' dump for {args.pageid}")
    target_ids, all_pages_list = scan_tree_inventory(args.pageid, args, exclude_ids)
    save_sidebars(args.outdir, target_ids)
    run_download_phase(args, all_pages_list, target_ids, active_css_files)


def handle_label(args, active_css_files, exclude_ids):
    print(f"Starting 'label' dump for {args.label}")
    target_ids, all_pages_list = scan_label_forest_inventory(args, exclude_ids)
    save_sidebars(args.outdir, target_ids)
    run_download_phase(args, all_pages_list, target_ids, active_css_files)


def handle_single(args, active_css_files, exclude_ids):
    print(f"Starting 'single' dump for {args.pageid}")
    root = myModules.get_page_full(args.pageid, args.base_url, platform_config, auth_info, args.context_path)
    if root: collect_page_metadata(root)
    save_sidebars(args.outdir, {args.pageid})
    process_page(args.pageid, args, active_css_files, {args.pageid}, verbose=True)


def handle_all_spaces(args, active_css_files, exclude_ids):
    print("Starting 'all-spaces' dump...")
    spaces = myModules.get_all_spaces(args.base_url, platform_config, auth_info, args.context_path)
    if spaces and 'results' in spaces:
        for s in spaces['results']:
            print(f"\n--- Processing Space: {s['key']} ---")
            global all_pages_metadata, global_sidebar_html, seen_metadata_ids
            all_pages_metadata = []
            seen_metadata_ids = set()
            s_args = argparse.Namespace(**vars(args))
            s_args.space_key = s['key']
            handle_space(s_args, active_css_files, exclude_ids)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Confluence Dump")
    g = parser.add_argument_group('Global Options')
    g.add_argument('-o', '--outdir', required=True)
    g.add_argument('--base-url', required=True)
    g.add_argument('--profile', required=True)
    g.add_argument('--context-path', default=None)
    g.add_argument('--css-file', default=None)
    g.add_argument('-R', '--rst', action='store_true')
    g.add_argument('-t', '--threads', type=int, default=1)
    g.add_argument('--exclude-page-id', action='append')
    g.add_argument('--no-vpn-reminder', action='store_true')

    subs = parser.add_subparsers(dest='command', required=True)
    p_single = subs.add_parser('single');
    p_single.add_argument('-p', '--pageid', required=True);
    p_single.set_defaults(func=handle_single)
    p_tree = subs.add_parser('tree');
    p_tree.add_argument('-p', '--pageid', required=True);
    p_tree.set_defaults(func=handle_tree)
    p_space = subs.add_parser('space');
    p_space.add_argument('-sp', '--space-key', required=True);
    p_space.set_defaults(func=handle_space)
    p_label = subs.add_parser('label');
    p_label.add_argument('-l', '--label', required=True);
    p_label.add_argument('--exclude-label');
    p_label.set_defaults(func=handle_label)
    p_all = subs.add_parser('all-spaces');
    p_all.set_defaults(func=handle_all_spaces)

    args = parser.parse_args()
    global platform_config, auth_info
    active_css_files = []
    exclude_ids = set(args.exclude_page_id) if args.exclude_page_id else set()
    try:
        platform_config = myModules.load_platform_config(args.profile)
        auth_info = myModules.get_auth_config(platform_config)
        if args.profile == 'dc' and not args.no_vpn_reminder:
            print("\n[!] DATA CENTER CHECK: Are you connected to the VPN/Intranet?")
            input("    Press Enter to confirm...")

        # --- NEW: Auto-Subfolder Generation ---
        timestamp = datetime.now().strftime("%Y-%m-%d %H%M")
        run_title = get_run_title(args, args.base_url, platform_config, auth_info)
        safe_title = sanitize_filename(run_title)

        # Update output dir to include timestamped folder
        new_outdir = os.path.join(args.outdir, f"{timestamp} {safe_title}")
        print(f"Creating new output directory: {new_outdir}")
        args.outdir = new_outdir  # Update arg for rest of script

        myModules.setup_output_directories(args.outdir)
        myModules.set_variables()

        local_styles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'styles')
        if os.path.exists(local_styles_dir):
            for f in glob.glob(os.path.join(local_styles_dir, "*.css")):
                if "site.css" in f:
                    target = os.path.join(myModules.outdir_styles, os.path.basename(f))
                    shutil.copy(f, target)
                    active_css_files.append(f"../styles/{os.path.basename(f)}")
        if args.css_file and os.path.exists(args.css_file):
            target = os.path.join(myModules.outdir_styles, os.path.basename(args.css_file))
            shutil.copy(args.css_file, target)
            active_css_files.append(f"../styles/{os.path.basename(args.css_file)}")
    except Exception as e:
        print(f"Init Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        args.func(args, active_css_files, exclude_ids)
        build_index_html(args.outdir, active_css_files)
        print(f"\nDump Complete. Output in {args.outdir}")
    except Exception as e:
        print(f"Execution Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()