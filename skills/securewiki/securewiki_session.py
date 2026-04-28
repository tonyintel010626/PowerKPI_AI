#!/usr/bin/env python3
"""
SecureWiki Session Publisher - Publish OpenCode sessions to Confluence Wiki

Converts OpenCode session markdown files into themed Confluence pages with
terminal-style formatting that matches the OpenCode execution look and feel.

Usage:
    python securewiki_session.py <session_file>                    # Publish to default location
    python securewiki_session.py <session_file> --parent <page_id> # Publish under specific parent
    python securewiki_session.py <session_file> --space <key>      # Publish to specific space
    python securewiki_session.py <session_file> --title "Custom"   # Override auto-generated title
    python securewiki_session.py <session_file> --preview          # Preview HTML without publishing
    python securewiki_session.py <session_file> --dry-run          # Show what would be published
"""

import os
import re
import sys
import json
import html
import argparse
from pathlib import Path
from datetime import datetime

# Import SecureWiki from same directory
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from securewiki import SecureWiki, BASE_URL

# Defaults
DEFAULT_PARENT_ID = "4617023376"  # Ocode Session Use Cases Sharing
DEFAULT_SPACE_KEY = "ITSfvpm"
MAX_TITLE_LENGTH = 80


# ─── OpenCode Theme Inline Styles (Confluence-compatible) ───────────────────
# Confluence strips <style> blocks and CSS classes. All styles MUST be inline.
#
# IMPORTANT: Confluence dark theme overrides background colors but often leaves
# inline color: properties. To be safe, every element with text MUST have BOTH
# an explicit background AND an explicit color that form a readable pair.
# We use dark backgrounds with light text throughout to guarantee readability
# in BOTH light and dark Confluence themes.

STYLE = {
    # ── Layout ──
    'session': 'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;max-width:960px;',
    # ── Header - dark bg, white text (works in both themes) ──
    'header': 'background:#1e293b;color:#f8fafc;padding:24px 32px;margin-bottom:0;',
    'header_h1': 'margin:8px 0 0 0;font-size:22px;color:#ffffff;',
    'badge': 'display:inline-block;background:#3b82f6;color:#ffffff;padding:3px 12px;border-radius:12px;font-size:11px;font-weight:700;letter-spacing:0.5px;margin-bottom:8px;',
    'meta': 'font-size:13px;color:#e2e8f0;line-height:1.6;',
    'meta_code': 'background:#334155;padding:2px 6px;border-radius:4px;font-family:Cascadia Code,Fira Code,JetBrains Mono,monospace;font-size:12px;color:#f8fafc;',
    # ── Turn containers - use dark bg with light text for guaranteed readability ──
    'turn_user': 'padding:16px 24px;margin:8px 0;border-left:5px solid #3b82f6;background:#1e3a5f;color:#e8f0fe;',
    'turn_assistant': 'padding:16px 24px;margin:8px 0;border-left:5px solid #22c55e;background:#1a3328;color:#d1fae5;',
    'turn_header': 'margin-bottom:10px;',
    # ── Role labels - bright, high contrast on dark bg ──
    'role_user': 'font-weight:700;font-size:14px;color:#93c5fd;',
    'role_assistant': 'font-weight:700;font-size:14px;color:#86efac;',
    # ── Agent/Model/Runtime info pills - dark bg + bright text pairs ──
    'agent_pill': 'display:inline-block;background:#1e40af;color:#dbeafe;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:8px;',
    'model_pill': 'display:inline-block;background:#3730a3;color:#e0e7ff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:4px;',
    'runtime_pill': 'display:inline-block;background:#78350f;color:#fef3c7;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:4px;',
    # ── Content text - light text on dark turn bg ──
    'content': 'font-size:14px;line-height:1.7;',
    'content_p': 'margin:8px 0;',
    'content_p_user': 'margin:8px 0;color:#e8f0fe;',
    'content_p_assistant': 'margin:8px 0;color:#d1fae5;',
    # ── Tool/code blocks - darkest bg with bright mono text ──
    'tool': 'margin:12px 0;border:1px solid #475569;border-radius:6px;overflow:hidden;',
    'tool_header': 'background:#334155;color:#f1f5f9;padding:8px 16px;font-size:12px;font-family:Cascadia Code,monospace;',
    'tool_icon': 'color:#fbbf24;',
    'tool_name': 'color:#93c5fd;font-weight:600;',
    'tool_body': 'background:#0f172a;color:#e2e8f0;padding:12px 16px;font-family:Cascadia Code,Fira Code,monospace;font-size:12px;line-height:1.5;overflow-x:auto;white-space:pre-wrap;word-break:break-word;',
    'tool_body_output': 'background:#1e293b;border-top:1px solid #475569;color:#cbd5e1;padding:12px 16px;font-family:Cascadia Code,Fira Code,monospace;font-size:12px;line-height:1.5;overflow-x:auto;white-space:pre-wrap;word-break:break-word;',
    'tool_label': 'color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;',
    # ── Footer - dark bg with muted light text ──
    'footer': 'text-align:center;padding:16px;color:#94a3b8;font-size:11px;border-top:1px solid #334155;background:#1e293b;',
    'footer_link': 'color:#60a5fa;text-decoration:none;',
    # ── Inline elements - dark bg with bright text ──
    'inline_code': 'background:#334155;color:#f8fafc;padding:2px 5px;border-radius:3px;font-size:12px;font-family:Cascadia Code,Fira Code,monospace;',
    'list_user': 'margin:4px 0;padding-left:24px;color:#e8f0fe;',
    'list_assistant': 'margin:4px 0;padding-left:24px;color:#d1fae5;',
    'heading3_user': 'font-size:16px;font-weight:700;color:#bfdbfe;margin:16px 0 8px 0;',
    'heading3_assistant': 'font-size:16px;font-weight:700;color:#a7f3d0;margin:16px 0 8px 0;',
    'heading4_user': 'font-size:14px;font-weight:700;color:#bfdbfe;margin:12px 0 6px 0;',
    'heading4_assistant': 'font-size:14px;font-weight:700;color:#a7f3d0;margin:12px 0 6px 0;',
}


def parse_session_markdown(content):
    """Parse an OpenCode session markdown file into structured data.
    
    Returns dict with:
        title: str - session title from H1
        session_id: str - session identifier
        created: str - creation timestamp
        updated: str - last update timestamp
        turns: list[dict] - conversation turns with role, model_info, content
    """
    lines = content.split('\n')
    session = {
        'title': '',
        'session_id': '',
        'created': '',
        'updated': '',
        'turns': [],
        'raw_lines': lines
    }
    
    # Extract H1 title (first line starting with #)
    for line in lines:
        if line.startswith('# '):
            session['title'] = line[2:].strip()
            break
    
    # Extract metadata
    for line in lines:
        if line.startswith('**Session ID:**'):
            session['session_id'] = line.replace('**Session ID:**', '').strip()
        elif line.startswith('**Created:**'):
            session['created'] = line.replace('**Created:**', '').strip()
        elif line.startswith('**Updated:**'):
            session['updated'] = line.replace('**Updated:**', '').strip()
    
    # Split into turns at ## User / ## Assistant boundaries
    current_turn = None
    current_lines = []
    
    for line in lines:
        # Detect turn headers
        if line.startswith('## User'):
            # Save previous turn
            if current_turn:
                current_turn['content'] = '\n'.join(current_lines).strip()
                session['turns'].append(current_turn)
            current_turn = {'role': 'user', 'model_info': '', 'content': ''}
            current_lines = []
            continue
        elif line.startswith('## Assistant'):
            # Save previous turn
            if current_turn:
                current_turn['content'] = '\n'.join(current_lines).strip()
                session['turns'].append(current_turn)
            # Parse agent/model/runtime from "## Assistant (FV · claude-opus-4.5 · 10.8s)"
            model_match = re.match(r'## Assistant\s*\((.+?)\)', line)
            model_info = model_match.group(1) if model_match else ''
            # Split on · (middle dot) to get agent, model, runtime
            agent_name = ''
            model_name = ''
            runtime = ''
            if model_info:
                parts = [p.strip() for p in model_info.split('·')]
                if len(parts) >= 3:
                    agent_name = parts[0]   # e.g. "FV", "Explore", "agent"
                    model_name = parts[1]   # e.g. "claude-opus-4.5"
                    runtime = parts[2]      # e.g. "10.2s"
                elif len(parts) == 2:
                    model_name = parts[0]
                    runtime = parts[1]
                else:
                    model_name = parts[0]
            current_turn = {
                'role': 'assistant', 
                'model_info': model_info,
                'agent': agent_name,
                'model': model_name,
                'runtime': runtime,
                'content': ''
            }
            current_lines = []
            continue
        
        if current_turn is not None:
            current_lines.append(line)
    
    # Save last turn
    if current_turn:
        current_turn['content'] = '\n'.join(current_lines).strip()
        session['turns'].append(current_turn)
    
    return session


def _escape(text):
    """HTML-escape text."""
    return html.escape(text, quote=True)


def _convert_inline_markdown(text):
    """Convert basic inline markdown to HTML."""
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text* (but not inside **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    # Inline code `text`
    text = re.sub(r'`([^`]+)`', lambda m: f'<code style="{STYLE["inline_code"]}">{m.group(1)}</code>', text)
    return text


def _truncate_output(text, max_lines=50, max_chars=3000):
    """Truncate long tool outputs for readability."""
    lines = text.split('\n')
    if len(lines) > max_lines or len(text) > max_chars:
        truncated = '\n'.join(lines[:max_lines])
        if len(truncated) > max_chars:
            truncated = truncated[:max_chars]
        remaining = len(lines) - max_lines
        return truncated + f'\n\n... ({remaining} more lines truncated)'
    return text


def convert_turn_content_to_html(content, role):
    """Convert a single turn's markdown content to themed HTML.
    
    Handles:
    - Regular text paragraphs
    - Tool call blocks (**Tool: name**, **Input:**/json, **Output:**/result)
    - Code blocks (```...```)
    - Horizontal rules (---)
    - Lists (- item, 1. item)
    """
    html_parts = []
    lines = content.split('\n')
    i = 0
    in_code_block = False
    code_block_lang = ''
    code_block_lines = []
    in_tool_block = False
    tool_name = ''
    tool_section = ''  # 'input' or 'output'
    tool_lines = []
    
    def flush_tool():
        """Flush accumulated tool block."""
        nonlocal tool_lines, tool_section, tool_name, in_tool_block
        if tool_lines and tool_section:
            text = '\n'.join(tool_lines).strip()
            # Remove wrapping ```json ... ``` if present
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
            text = _truncate_output(text)
            
            label = 'Input' if tool_section == 'input' else 'Output'
            body_style = STYLE['tool_body_output'] if tool_section == 'output' else STYLE['tool_body']
            html_parts.append(
                f'<div style="{body_style}">'
                f'<div style="{STYLE["tool_label"]}">{label}</div>'
                f'{_escape(text)}'
                f'</div>'
            )
        tool_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # ── Code block handling ──
        if line.startswith('```') and not in_tool_block:
            if in_code_block:
                # End code block
                code_text = _escape('\n'.join(code_block_lines))
                html_parts.append(
                    f'<div style="{STYLE["tool"]}">'
                    f'<div style="{STYLE["tool_header"]}"><span style="{STYLE["tool_icon"]}">$</span> '
                    f'<span style="{STYLE["tool_name"]}">{_escape(code_block_lang) if code_block_lang else "code"}</span></div>'
                    f'<div style="{STYLE["tool_body"]}">{code_text}</div>'
                    f'</div>'
                )
                in_code_block = False
                code_block_lines = []
                code_block_lang = ''
                i += 1
                continue
            else:
                in_code_block = True
                code_block_lang = line[3:].strip()
                i += 1
                continue
        
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # ── Tool block detection ──
        tool_header_match = re.match(r'\*\*Tool:\s*(\w+)\*\*', line)
        if tool_header_match:
            # Close any previous tool
            if in_tool_block:
                flush_tool()
                html_parts.append('</div>')  # close ocode-tool
            
            tool_name = tool_header_match.group(1)
            in_tool_block = True
            tool_section = ''
            html_parts.append(
                f'<div style="{STYLE["tool"]}">'
                f'<div style="{STYLE["tool_header"]}">'
                f'<span style="{STYLE["tool_icon"]}">&#9881;</span> '
                f'<span style="{STYLE["tool_name"]}">{_escape(tool_name)}</span>'
                f'</div>'
            )
            i += 1
            continue
        
        if in_tool_block:
            if line.startswith('**Input:**'):
                flush_tool()
                tool_section = 'input'
                i += 1
                continue
            elif line.startswith('**Output:**'):
                flush_tool()
                tool_section = 'output'
                i += 1
                continue
            elif line.strip() == '---':
                # End of tool block on separator
                flush_tool()
                html_parts.append('</div>')  # close ocode-tool
                in_tool_block = False
                tool_name = ''
                tool_section = ''
                i += 1
                continue
            elif tool_section:
                tool_lines.append(line)
                i += 1
                continue
            else:
                i += 1
                continue
        
        # ── Horizontal rule ──
        if line.strip() == '---':
            i += 1
            continue
        
        # ── Empty line ──
        if not line.strip():
            i += 1
            continue
        
        # ── List items ──
        list_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)', line)
        if list_match:
            indent = len(list_match.group(1))
            marker = list_match.group(2)
            text = list_match.group(3)
            tag = 'ol' if marker[0].isdigit() else 'ul'
            # Collect consecutive list items
            items = [text]
            j = i + 1
            while j < len(lines):
                next_match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.+)', lines[j])
                if next_match:
                    items.append(next_match.group(3))
                    j += 1
                elif not lines[j].strip():
                    j += 1
                    break
                else:
                    break
            
            list_style = STYLE['list_user'] if role == 'user' else STYLE['list_assistant']
            items_html = ''.join(f'<li>{_convert_inline_markdown(_escape(item))}</li>' for item in items)
            html_parts.append(f'<{tag} style="{list_style}">{items_html}</{tag}>')
            i = j
            continue
        
        # ── Headings (### and ####) ──
        heading_match = re.match(r'^(#{3,4})\s+(.+)', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2)
            if level == 3:
                h_style = STYLE['heading3_user'] if role == 'user' else STYLE['heading3_assistant']
                html_parts.append(f'<h3 style="{h_style}">{_convert_inline_markdown(_escape(heading_text))}</h3>')
            else:
                h_style = STYLE['heading4_user'] if role == 'user' else STYLE['heading4_assistant']
                html_parts.append(f'<h4 style="{h_style}">{_convert_inline_markdown(_escape(heading_text))}</h4>')
            i += 1
            continue
        
        # ── Regular paragraph ──
        paragraph_lines = [line]
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            if (not next_line.strip() or next_line.startswith('```') or 
                next_line.startswith('**Tool:') or next_line.startswith('## ') or
                next_line.startswith('# ') or next_line.startswith('### ') or
                next_line.startswith('#### ') or next_line.strip() == '---' or
                re.match(r'^(\s*)([-*]|\d+\.)\s+', next_line)):
                break
            paragraph_lines.append(next_line)
            j += 1
        
        para_text = ' '.join(paragraph_lines)
        p_style = STYLE['content_p_user'] if role == 'user' else STYLE['content_p_assistant']
        html_parts.append(f'<p style="{p_style}">{_convert_inline_markdown(_escape(para_text))}</p>')
        i = j
        continue
    
    # Close any open tool block
    if in_tool_block:
        flush_tool()
        html_parts.append('</div>')
    
    return '\n'.join(html_parts)


def generate_wiki_title(session_title, max_length=MAX_TITLE_LENGTH):
    """Generate a concise wiki page title from the session title.
    
    Adds a date prefix and truncates if needed.
    """
    date_prefix = datetime.now().strftime('%Y-%m-%d')
    
    # Clean up the title
    title = session_title.strip()
    
    # If title is too long, truncate intelligently at word boundary
    available = max_length - len(date_prefix) - 3  # 3 for " - "
    if len(title) > available:
        title = title[:available].rsplit(' ', 1)[0] + '...'
    
    return f"{date_prefix} - {title}"


def session_to_html(session):
    """Convert a parsed session dict to Confluence-compatible themed HTML.
    
    Uses Confluence expand macros for collapsible turns to enable fast navigation.
    Each turn header shows role + agent/model/runtime info as a summary line.
    """
    parts = []
    
    # Container
    parts.append(f'<div style="{STYLE["session"]}">')
    
    # ── Header ──
    parts.append(f'<div style="{STYLE["header"]}">')
    parts.append(f'<div style="{STYLE["badge"]}">OPENCODE SESSION</div>')
    parts.append(f'<h1 style="{STYLE["header_h1"]}">{_escape(session["title"])}</h1>')
    parts.append(f'<div style="{STYLE["meta"]}">')
    if session['session_id']:
        parts.append(f'Session: <code style="{STYLE["meta_code"]}">{_escape(session["session_id"])}</code><br/>')
    if session['created']:
        parts.append(f'Created: {_escape(session["created"])}')
    if session['updated']:
        parts.append(f' &middot; Updated: {_escape(session["updated"])}')
    parts.append(f'<br/>Published: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    parts.append('</div>')
    parts.append('</div>')
    
    # ── Body with turns ──
    parts.append(f'<div style="padding:12px 0;">')
    
    for idx, turn in enumerate(session['turns'], 1):
        role = turn['role']
        
        # Build the expand macro title (visible when collapsed)
        if role == 'user':
            # Show first line of user content as summary
            first_line = turn['content'].split('\n')[0].strip()[:120]
            if not first_line:
                first_line = '(empty)'
            expand_title = f"[#{idx}] User: {first_line}"
        else:
            # Show agent, model, runtime in the expand title
            info_parts = []
            if turn.get('agent'):
                info_parts.append(f"Agent: {turn['agent']}")
            if turn.get('model'):
                info_parts.append(f"Model: {turn['model']}")
            if turn.get('runtime'):
                info_parts.append(f"Runtime: {turn['runtime']}")
            info_str = ' | '.join(info_parts) if info_parts else ''
            expand_title = f"[#{idx}] Assistant"
            if info_str:
                expand_title += f" ({info_str})"
        
        # Confluence expand macro for collapsible turn
        parts.append(f'<ac:structured-macro ac:name="expand">')
        parts.append(f'<ac:parameter ac:name="title">{_escape(expand_title)}</ac:parameter>')
        parts.append(f'<ac:rich-text-body>')
        
        # Turn container with colored left border
        if role == 'user':
            turn_style = STYLE['turn_user']
        else:
            turn_style = STYLE['turn_assistant']
        
        parts.append(f'<div style="{turn_style}">')
        
        # Turn header with role label and info pills
        parts.append(f'<div style="{STYLE["turn_header"]}">')
        if role == 'user':
            parts.append(f'<span style="{STYLE["role_user"]}">&#9654; User</span>')
        else:
            parts.append(f'<span style="{STYLE["role_assistant"]}">&#9881; Assistant</span>')
            if turn.get('agent'):
                parts.append(f'<span style="{STYLE["agent_pill"]}">Agent: {_escape(turn["agent"])}</span>')
            if turn.get('model'):
                parts.append(f'<span style="{STYLE["model_pill"]}">Model: {_escape(turn["model"])}</span>')
            if turn.get('runtime'):
                parts.append(f'<span style="{STYLE["runtime_pill"]}">&#9201; {_escape(turn["runtime"])}</span>')
        parts.append('</div>')
        
        # Turn content
        parts.append(f'<div style="{STYLE["content"]}">')
        parts.append(convert_turn_content_to_html(turn['content'], role))
        parts.append('</div>')
        parts.append('</div>')
        
        # Close expand macro
        parts.append('</ac:rich-text-body>')
        parts.append('</ac:structured-macro>')
    
    parts.append('</div>')  # body
    
    # ── Footer ──
    parts.append(f'<div style="{STYLE["footer"]}">')
    parts.append('Published by <strong>OpenCode</strong> &middot; ')
    parts.append(f'<a style="{STYLE["footer_link"]}" href="https://github.com/anomalyco/opencode">github.com/anomalyco/opencode</a>')
    parts.append('</div>')
    
    parts.append('</div>')  # session
    
    return '\n'.join(parts)


def resolve_parent_from_url(url):
    """Extract page ID from a Confluence URL.
    
    Supports:
        https://wiki.ith.intel.com/pages/viewpage.action?pageId=123456
        https://wiki.ith.intel.com/spaces/KEY/pages/123456/Title
    """
    # Try pageId parameter
    match = re.search(r'pageId=(\d+)', url)
    if match:
        return match.group(1)
    
    # Try /pages/<id>/ pattern
    match = re.search(r'/pages/(\d+)', url)
    if match:
        return match.group(1)
    
    return None


def resolve_space_from_url(url):
    """Extract space key from a Confluence URL.
    
    Supports:
        https://wiki.ith.intel.com/spaces/ITSfvpm/pages/...
    """
    match = re.search(r'/spaces/([A-Za-z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def publish_session(session_file, parent_id=None, space_key=None, title=None, 
                     username=None, preview=False, dry_run=False):
    """Publish an OpenCode session markdown file to Confluence Wiki.
    
    Args:
        session_file: Path to the session-*.md file
        parent_id: Confluence parent page ID (default: Ocode Session Use Cases Sharing)
        space_key: Confluence space key (default: ITSfvpm)
        title: Override auto-generated title
        username: Intel IDSID (default: current user)
        preview: If True, write HTML to local file instead of publishing
        dry_run: If True, show what would be done without publishing
    
    Returns:
        dict with page_id, title, url on success
    """
    session_path = Path(session_file)
    if not session_path.exists():
        print(f"[ERROR] Session file not found: {session_file}")
        sys.exit(1)
    
    # Read and parse session
    print(f"[INFO] Reading session file: {session_path.name}")
    content = session_path.read_text(encoding='utf-8')
    session = parse_session_markdown(content)
    
    if not session['title']:
        print("[WARN] No title found in session file, using filename")
        session['title'] = session_path.stem
    
    print(f"[INFO] Session: {session['title']}")
    print(f"[INFO] Turns: {len(session['turns'])} ({sum(1 for t in session['turns'] if t['role'] == 'user')} user, {sum(1 for t in session['turns'] if t['role'] == 'assistant')} assistant)")
    
    # Generate HTML
    html_body = session_to_html(session)
    
    # Generate title
    page_title = title or generate_wiki_title(session['title'])
    print(f"[INFO] Page title: {page_title}")
    
    # Resolve defaults
    parent = parent_id or DEFAULT_PARENT_ID
    space = space_key or DEFAULT_SPACE_KEY
    
    if preview:
        # Write HTML preview to local file
        # Convert Confluence expand macros to HTML5 <details>/<summary> for browser preview
        preview_html = html_body
        preview_html = re.sub(
            r'<ac:structured-macro ac:name="expand">\s*<ac:parameter ac:name="title">(.+?)</ac:parameter>\s*<ac:rich-text-body>',
            r'<details style="margin:4px 0;border:1px solid #e2e8f0;border-radius:6px;"><summary style="cursor:pointer;padding:10px 16px;background:#f8fafc;font-weight:600;font-size:13px;color:#334155;user-select:none;">\1</summary><div style="padding:0;">',
            preview_html
        )
        preview_html = preview_html.replace('</ac:rich-text-body>\n</ac:structured-macro>', '</div></details>')
        
        preview_path = session_path.with_suffix('.preview.html')
        preview_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{_escape(page_title)}</title>
    <style>
        body {{ background: #f0f0f0; padding: 40px; font-family: sans-serif; }}
        .preview-wrapper {{ max-width: 1000px; margin: 0 auto; background: white; 
                           padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        details summary:hover {{ background: #eef2ff; }}
    </style>
</head>
<body>
    <div class="preview-wrapper">
        {preview_html}
    </div>
</body>
</html>"""
        preview_path.write_text(preview_content, encoding='utf-8')
        print(f"[OK] Preview written to: {preview_path}")
        return {"preview": str(preview_path)}
    
    if dry_run:
        print(f"\n[DRY RUN] Would publish:")
        print(f"  Title:  {page_title}")
        print(f"  Space:  {space}")
        print(f"  Parent: {parent}")
        print(f"  HTML:   {len(html_body)} bytes")
        return {"dry_run": True, "title": page_title, "space": space, "parent": parent}
    
    # Publish to Confluence
    print(f"[INFO] Publishing to space '{space}' under parent {parent}...")
    wiki = SecureWiki(username)
    
    try:
        result = wiki.create_page(space, page_title, html_body, parent)
        print(f"[OK] Page created successfully!")
    except Exception as e:
        err_msg = str(e)
        if '400' in err_msg or 'already exists' in err_msg.lower() or 'title' in err_msg.lower():
            # Page with same title likely exists — find it and update
            print(f"[INFO] Page with this title may already exist, searching...")
            try:
                import requests as req
                from securewiki import get_credentials, BASE_URL
                creds = get_credentials(username)
                search_url = f"{BASE_URL}/rest/api/content"
                resp = req.get(search_url, params={
                    'spaceKey': space,
                    'title': page_title,
                    'type': 'page'
                }, auth=(creds[0], creds[1]), verify=False)
                resp.raise_for_status()
                results = resp.json().get('results', [])
                if results:
                    existing_id = results[0]['id']
                    print(f"[INFO] Found existing page {existing_id}, updating...")
                    result = wiki.update_page(existing_id, html_body)
                    print(f"[OK] Page updated successfully!")
                else:
                    print(f"[ERROR] Could not find existing page and create failed: {e}")
                    sys.exit(1)
            except Exception as e2:
                print(f"[ERROR] Failed to find/update existing page: {e2}")
                print(f"[ERROR] Original create error: {e}")
                sys.exit(1)
        else:
            print(f"[ERROR] Failed to publish: {e}")
            sys.exit(1)
    
    print(f"  Page ID: {result['id']}")
    print(f"  Title:   {result['title']}")
    print(f"  URL:     {result['url']}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="SecureWiki Session Publisher - Publish OpenCode sessions to Confluence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Publish session to default location (Ocode Session Use Cases Sharing)
  python securewiki_session.py session-ses-2026W08.1127am.md

  # Publish under a specific parent page (by ID or URL)
  python securewiki_session.py session.md --parent 4617023376
  python securewiki_session.py session.md --parent "https://wiki.ith.intel.com/spaces/ITSfvpm/pages/4617023376/..."

  # Custom title
  python securewiki_session.py session.md --title "HSDES Test Case Analysis Session"

  # Preview locally without publishing
  python securewiki_session.py session.md --preview

  # Dry run - show what would be published
  python securewiki_session.py session.md --dry-run
"""
    )
    
    parser.add_argument('session_file', help='Path to OpenCode session markdown file (session-*.md)')
    parser.add_argument('--parent', type=str, default=None,
                        help=f'Parent page ID or URL (default: {DEFAULT_PARENT_ID} - Ocode Session Use Cases Sharing)')
    parser.add_argument('--space', type=str, default=None,
                        help=f'Confluence space key (default: {DEFAULT_SPACE_KEY})')
    parser.add_argument('--title', type=str, default=None,
                        help='Override auto-generated page title')
    parser.add_argument('--user', type=str, default=None,
                        help='Intel IDSID username')
    parser.add_argument('--preview', action='store_true',
                        help='Generate local HTML preview instead of publishing')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be published without actually publishing')
    parser.add_argument('--json', action='store_true',
                        help='Output result as JSON')
    
    args = parser.parse_args()
    
    # Resolve parent from URL if needed
    parent_id = args.parent
    space_key = args.space
    
    if parent_id and parent_id.startswith('http'):
        url = parent_id
        parent_id = resolve_parent_from_url(url)
        if not parent_id:
            print(f"[ERROR] Could not extract page ID from URL: {url}")
            sys.exit(1)
        # Also try to extract space key from URL if not specified
        if not space_key:
            space_key = resolve_space_from_url(url)
        print(f"[INFO] Resolved parent from URL: page_id={parent_id}, space={space_key or DEFAULT_SPACE_KEY}")
    
    result = publish_session(
        session_file=args.session_file,
        parent_id=parent_id,
        space_key=space_key,
        title=args.title,
        username=args.user,
        preview=args.preview,
        dry_run=args.dry_run
    )
    
    if args.json:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
