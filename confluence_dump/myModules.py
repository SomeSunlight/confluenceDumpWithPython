# -*- coding: utf-8 -*-
"""
Module to abstract Confluence API calls and provide local file/directory utilities.
Supports both Confluence Cloud and Data Center platforms.
Includes BeautifulSoup logic for HTML processing (downloading assets, fixing links).
"""

import os
import sys
import requests
import configparser
import re
from requests.auth import HTTPBasicAuth
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup

# --- Globals for output directories ---
outdir_base = ""
outdir_pages = ""
outdir_attachments = ""
outdir_styles = ""
outdir_logs = ""


# --- Setup Functions ---

def set_variables():
    """ Sets and returns global variables. """
    global page_ids_in_space, page_names_in_space, attachments_in_space
    page_ids_in_space = []
    page_names_in_space = []
    attachments_in_space = []
    return


def setup_output_directories(base_outdir):
    """ Sets global directory variables and robustly creates them. """
    global outdir_base, outdir_pages, outdir_attachments, outdir_styles, outdir_logs

    outdir_base = base_outdir.rstrip('/') + '/'
    outdir_pages = outdir_base + "pages/"
    outdir_attachments = outdir_base + "attachments/"
    outdir_styles = outdir_base + "styles/"
    outdir_logs = outdir_base + "logs/"

    try:
        os.makedirs(outdir_pages, exist_ok=True)
        os.makedirs(outdir_attachments, exist_ok=True)
        os.makedirs(outdir_styles, exist_ok=True)
        os.makedirs(outdir_logs, exist_ok=True)
    except Exception as e:
        print(f"Fatal Error creating directories: {e}", file=sys.stderr)
        sys.exit(1)
    return


# --- Configuration & Auth ---

def load_platform_config(profile_name):
    config = configparser.ConfigParser()
    if not os.path.exists('confluence_products.ini'):
        print("Error: 'confluence_products.ini' not found.", file=sys.stderr)
        sys.exit(1)
    config.read('confluence_products.ini')
    if profile_name not in config:
        print(f"Error: Profile '{profile_name}' not found.", file=sys.stderr)
        sys.exit(1)
    return dict(config[profile_name])


def get_auth_config(platform_config):
    auth_method = platform_config.get('auth_method')
    if auth_method == 'basic_api_token':
        try:
            return HTTPBasicAuth(os.environ['CONFLUENCE_USER'], os.environ['CONFLUENCE_TOKEN'])
        except KeyError:
            print("Error: Missing CONFLUENCE_USER/TOKEN for Cloud.", file=sys.stderr)
            sys.exit(1)
    elif auth_method == 'bearer_pat':
        try:
            return {'Authorization': f"Bearer {os.environ['CONFLUENCE_TOKEN']}"}
        except KeyError:
            print("Error: Missing CONFLUENCE_TOKEN for Data Center.", file=sys.stderr)
            sys.exit(1)
    return None


# --- API Helpers ---

def _build_api_url(base_url, platform_config, context_path_override, template_key, path_params=None):
    if path_params is None: path_params = {}
    template = platform_config.get(template_key)
    if not template:
        print(f"Error: Template '{template_key}' missing in INI.", file=sys.stderr)
        sys.exit(1)

    if platform_config.get('platform_type') == 'dc':
        # Data Center Context Path Logic
        c_path = context_path_override if context_path_override is not None else platform_config.get(
            'default_context_path', '')
        if c_path:
            c_path = '/' + c_path.strip().strip('/')
        else:
            c_path = ''
        path_params['context_path'] = c_path

    return f"{base_url.rstrip('/')}{template.format(**path_params)}"


def _execute_get_request(url, auth_info, params=None):
    headers = {"Accept": "application/json"}
    if isinstance(auth_info, dict): headers.update(auth_info)

    try:
        resp = requests.get(url, headers=headers, auth=auth_info if not isinstance(auth_info, dict) else None,
                            params=params)
        resp.raise_for_status()
        if 'application/json' not in resp.headers.get('Content-Type', ''):
            print("Error: Non-JSON response. Likely Auth/SSO issue.", file=sys.stderr)
            if isinstance(auth_info, dict):
                print("[Hint]: Check VPN/Intranet connection for Data Center.", file=sys.stderr)
                print("Also ensure that Personal Access Tokens are not disabled by an SSO policy.", file=sys.stderr)
                print("Please verify your CONFLUENCE_TOKEN environment variable.", file=sys.stderr)
            else:
                print("\nPlease verify your CONFLUENCE_USER and CONFLUENCE_TOKEN environment variables.",
                      file=sys.stderr)
            return None
        return resp.json()
    except Exception as e:
        print(f"Request Error: {e}", file=sys.stderr)
        return None


def get_page_view_url(base_url, platform_config, context_path_override, spaceKey, pageId):
    path_params = {'spaceKey': spaceKey, 'pageId': pageId}
    return _build_api_url(base_url, platform_config, context_path_override, 'url_view_page', path_params)


# --- Downloader ---

def download_file(url, local_filename, auth_info):
    """
    Downloads a file (image/attachment) from a URL to the local file system.
    """
    headers = {}
    auth_obj = None
    if isinstance(auth_info, dict):
        headers.update(auth_info)
    else:
        auth_obj = auth_info

    try:
        with requests.get(url, headers=headers, auth=auth_obj, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"    Failed to download {url}: {e}", file=sys.stderr)
        return False


# --- HTML Processor (The Core Logic) ---

def process_page_content(html_content, page_metadata, base_url, auth_info, css_files=None, exported_page_ids=None):
    """
    Parses the HTML content using BeautifulSoup.
    1. Injects Metadata.
    2. Downloads images.
    3. SMART LINK REWRITING:
       - If link target IS in exported_page_ids -> Rewrite to ID.html (Offline link)
       - If link target is NOT in exported_page_ids -> Keep/Make absolute URL (Online link)
    4. Injects CSS links.

    Returns:
        str: The processed, standalone HTML.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')

    # Ensure exported_page_ids is a set for fast lookup (or empty set if None)
    valid_ids = set(exported_page_ids) if exported_page_ids else set()

    # 1. Metadata Injection (Head)
    # Create head if missing (export_view usually just gives body fragments)
    if not soup.head:
        head = soup.new_tag('head')
        soup.insert(0, head)

    # Title
    title_tag = soup.new_tag('title')
    title_tag.string = page_metadata.get('title', 'Untitled')
    soup.head.append(title_tag)

    # Meta Tags
    meta_id = soup.new_tag('meta', attrs={'name': 'confluence-page-id', 'content': page_metadata.get('id')})
    soup.head.append(meta_id)

    labels = [l['name'] for l in page_metadata.get('metadata', {}).get('labels', {}).get('results', [])]
    meta_labels = soup.new_tag('meta', attrs={'name': 'confluence-labels', 'content': ', '.join(labels)})
    soup.head.append(meta_labels)

    # CSS Links (Inject all provided CSS files)
    if css_files:
        for css_path in css_files:
            link_css = soup.new_tag('link', attrs={'rel': 'stylesheet', 'href': css_path, 'type': 'text/css'})
            soup.head.append(link_css)

    # Body wrapper (if missing)
    if not soup.body:
        body = soup.new_tag('body')
        for element in list(soup.children):
            if element.name != 'head':
                body.append(element)
        soup.append(body)

    # 2. Image Downloading & rewriting
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue

        # Construct full URL if relative
        if src.startswith('/'):
            full_url = base_url.rstrip('/') + src
        else:
            full_url = src

        # Only download Confluence assets
        if '/download/' in src or '/images/icons/' in src:
            filename = unquote(os.path.basename(urlparse(src).path))
            local_path = os.path.join(outdir_attachments, filename)

            if download_file(full_url, local_path, auth_info):
                img['src'] = f"../attachments/{filename}"
            else:
                print(f"    Warning: Could not download image {src}", file=sys.stderr)

    # 3. Link Rewriting (The Smart Logic)
    for a in soup.find_all('a'):
        href = a.get('href')
        if not href: continue

        target_id = None

        # Attempt to extract Page ID from the link
        linked_id = a.get('data-linked-resource-id')
        resource_type = a.get('data-linked-resource-type')

        if linked_id and (not resource_type or resource_type == 'page'):
            target_id = linked_id
        elif '/pages/' in href:
            # Data Center URL pattern detection
            match = re.search(r'/pages/(\d+)', href)
            if match: target_id = match.group(1)
        elif 'pageId=' in href:
            # Query param detection
            try:
                target_id = re.search(r'pageId=(\d+)', href).group(1)
            except:
                pass

        # Decision Logic
        if target_id and target_id in valid_ids:
            # CASE A: Page is in our export -> Make relative offline link
            a['href'] = f"{target_id}.html"
        else:
            # CASE B: Page is NOT in export (or external link) -> Ensure absolute online link
            # If it's a relative link (starts with /), prepend the base_url
            if href.startswith('/'):
                a['href'] = base_url.rstrip('/') + href
            # If it's already absolute (http...), leave it alone.

    return str(soup)


# --- API Calls (Updated for export_view) ---
# Note: Removed print statements to keep output clean for progress bars.

def get_page_full(pageId, base_url, platform_config, auth_info, context_path_override):
    # print(f"Fetching details for page: {pageId}") # DISABLED
    params = {'expand': 'body.export_view,version,ancestors,space,metadata.labels'}
    path_params = {'pageId': pageId}

    url = _build_api_url(base_url, platform_config, context_path_override, 'url_get_page', path_params)

    data = _execute_get_request(url, auth_info, params=params)
    if not data: return None

    spaceKey = data.get('space', {}).get('key')
    if spaceKey:
        data['view_url'] = get_page_view_url(base_url, platform_config, context_path_override, spaceKey, pageId)

    return data


def get_page_basic(pageId, base_url, platform_config, auth_info, context_path_override):
    path_params = {'pageId': pageId}
    url = _build_api_url(base_url, platform_config, context_path_override, 'url_get_page', path_params)
    return _execute_get_request(url, auth_info)


def get_page_children(pageId, base_url, platform_config, auth_info, context_path_override):
    # print(f"Fetching children for page: {pageId}") # DISABLED
    url = _build_api_url(base_url, platform_config, context_path_override, 'url_cql_search')
    params = {'cql': f'parent={pageId}', 'limit': 200}
    return _execute_get_request(url, auth_info, params=params)


def get_page_attachments(pageId, base_url, platform_config, auth_info, context_path_override):
    # print(f"Fetching attachment list for page: {pageId}") # DISABLED
    path_params = {'pageId': pageId}
    url = _build_api_url(base_url, platform_config, context_path_override, 'url_get_attachments', path_params)
    params = {'limit': 200}
    return _execute_get_request(url, auth_info, params=params)


def get_pages_from_space(spaceKey, start, limit, base_url, platform_config, auth_info, context_path_override):
    # print(f"Fetching pages for space '{spaceKey}' ({start}-{start+limit})") # DISABLED
    url = _build_api_url(base_url, platform_config, context_path_override, 'url_cql_search')
    params = {'cql': f'space="{spaceKey}"', 'start': start, 'limit': limit}
    return _execute_get_request(url, auth_info, params=params)


def get_pages_by_label(label, start, limit, base_url, platform_config, auth_info, context_path_override):
    # print(f"Fetching pages with label '{label}' ({start}-{start+limit})") # DISABLED
    url = _build_api_url(base_url, platform_config, context_path_override, 'url_cql_search')
    params = {'cql': f'label="{label}"', 'start': start, 'limit': limit}
    return _execute_get_request(url, auth_info, params=params)


def get_all_spaces(base_url, platform_config, auth_info, context_path_override):
    # print("Fetching all spaces...") # DISABLED
    url = _build_api_url(base_url, platform_config, context_path_override, 'url_get_all_spaces')
    params = {'limit': 200}
    return _execute_get_request(url, auth_info, params=params)