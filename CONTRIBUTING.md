# Contributing Guide

This document explains the internal architecture of this script, primarily for future contributors or the original author when reviewing pull requests.

## Refactoring Goal

The main goal of the 2024 refactoring was to decouple the script from a specific Confluence platform (Confluence Cloud) and enable robust support for **Confluence Data Center (DC)**.

The original code had hardcoded URLs (e.g., `f"https://{site}.atlassian.net/wiki/..."`) which made it impossible to use with self-hosted instances.

## Core Architecture: `confluence_products.ini`

The core of this new architecture is the `confluence_products.ini` file.

This file acts as a **platform definition file**. It defines _how_ to talk to a specific platform, not _which_ instance to talk to.

It contains profiles (e.g., `[cloud]`, `[dc]`) that specify two key things:

1. `auth_method`: The authentication required (e.g., `basic_api_token` for Cloud, `bearer_pat` for DC).
    
2. **URL Templates**: A list of API and view paths for all required functions (e.g., `url_get_page`, `url_view_page`).
    

This approach allows the main script logic to be completely platform-agnostic.

## How It Works: The Data Flow

1. The main script (`confluenceDumpWithPython.py`) no longer accepts a "site" name. It now requires the user to specify:
    
    - `--profile "cloud"`: Selects the `[cloud]` section from the `.ini`.
        
    - `--base-url "https://myteam.atlassian.net"`: Provides the specific instance URL.
        
2. At startup, the script calls `myModules.load_platform_config(profile)` to load all URL templates and settings for the chosen profile into a `platform_config` dictionary.
    
3. It then calls `myModules.get_auth_config(platform_config)` to get the correct `requests` auth object or header (based on `auth_method` and environment variables).
    
4. All API functions in `myModules.py` (e.g., `get_page_full`) are no longer hardcoded. They now receive the `base_url`, `platform_config`, and `auth_info` as arguments.
    
5. Inside `myModules.py`, a helper function (`_build_api_url`) dynamically constructs the correct, full URL by combining the `base_url`, the `context_path` (for DC), and the appropriate URL template from the `platform_config` dictionary.
    

## How to Add a New Feature (e.g., "Add Comment")

If you want to add a new function that calls a new API endpoint, the process is simple and clean:

1. **Add Templates to `.ini`**: Open `confluence_products.ini` and add the new URL template to _both_ profiles:
    
    ```
    [cloud]
    ...
    url_add_comment = /rest/api/content/{pageId}/child/comment
    
    [dc]
    ...
    url_add_comment = {context_path}/rest/api/content/{pageId}/child/comment
    ```
    
2. **Add Function to `myModules.py`**: Create your new function (e.g., `add_comment`). Inside it, use the new config key by calling the internal helpers:
    
    ```
    def add_comment(pageId, comment_body, base_url, platform_config, auth_info, context_path_override):
        path_params = {'pageId': pageId}
        url = _build_api_url(
            base_url, 
            platform_config, 
            context_path_override, 
            'url_add_comment',  # This key must match the .ini
            path_params
        )
    
        payload = {"body": {"storage": {"value": comment_body, "representation": "storage"}}}
    
        # Use _execute_post_request (or similar)
        # ...
    ```