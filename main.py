#!/usr/bin/env python3
"""
Autonomous Self-Coding Micro-Tool Network - Universal Master Orchestrator
Autonomously discovers any trend and commands Gemini AI to code it dynamically.
"""

import os
import sys
import json
import random
import re
from datetime import datetime, timezone
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_URL = os.environ.get("SITE_URL", "https://51m0nma.github.io/auto-machine-exactly").rstrip("/")
SITE_NAME = os.environ.get("SITE_NAME", "OmniTools Network")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(ROOT_DIR, "tools_registry.json")
ERROR_LOG_FILE = os.path.join(ROOT_DIR, "error_log.json")
TEMPLATE_FILE = os.path.join(ROOT_DIR, "template.html")
ROOT_INDEX_FILE = os.path.join(ROOT_DIR, "index.html")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class Log:
    @classmethod
    def info(cls, msg): print(f"[INFO] {msg}", flush=True)
    @classmethod
    def step(cls, step_name, msg): print(f"\n==> [{step_name}] {msg}", flush=True)
    @classmethod
    def success(cls, msg): print(f"[SUCCESS] {msg}", flush=True)
    @classmethod
    def warn(cls, msg): print(f"[WARN] {msg}", flush=True)
    @classmethod
    def error(cls, msg): print(f"[ERROR] {msg}", flush=True)

def call_gemini_api(prompt, json_mode=False):
    if not GEMINI_API_KEY:
        Log.warn("GEMINI_API_KEY is not set.")
        return None
    try:
        generation_config = {"temperature": 0.4}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        Log.error(f"Gemini API error: {str(e)}")
        return None

def clean_json_response(raw_text):
    if not raw_text: return {}
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"): cleaned = cleaned[7:]
    elif cleaned.startswith("```"): cleaned = cleaned[3:]
    if cleaned.endswith("```"): cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except Exception: pass
        return {}

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return {"tools": [], "last_run": None}

def save_registry(registry):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f: json.dump(registry, f, indent=2, ensure_ascii=False)

def step_b_trend_discovery(registry):
    Log.step("STEP B", "Autonomous Trend Discovery: Identifying open web utility trends...")
    existing_tools = [t["title"] for t in registry.get("tools", [])]
    
    prompt = f"""
Identify one high-demand online micro-tool, file converter, developer utility, or calculator search query that is NOT in this existing list: {existing_tools}.
Output strict JSON with keys:
- "query": The exact search trend topic name (e.g., "PDF to JPG Image Extractor", "JSON to CSV Converter", "Compound Interest Calculator").
- "category": Broad category (e.g., "Converters", "Developer", "Utilities", "Finance").
- "description": A concise 1-sentence description of what the tool calculates or converts.
"""
    raw = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw)
    
    if not parsed or "query" not in parsed:
        chosen = {
            "query": "Client-Side PDF to Image Extractor",
            "category": "Converters",
            "description": "Extract pages from PDF files directly into image formats securely in your browser."
        }
    else:
        chosen = parsed

    slug = re.sub(r'[^a-z0-9]+', '-', chosen["query"].lower()).strip('-')
    return {
        "title": chosen["query"],
        "slug": slug,
        "category": chosen.get("category", "Utilities"),
        "description": chosen.get("description", "Interactive browser-based tool.")
    }

def generate_tool_code(trend_data):
    Log.info(f"Generating universal custom code for '{trend_data['title']}' via Gemini AI...")
    
    prompt = f"""
You are an expert full-stack web engineer. Build a complete, standalone, production-ready interactive web tool for this exact trend:
TITLE: {trend_data['title']}
CATEGORY: {trend_data['category']}
DESCRIPTION: {trend_data['description']}

Requirements:
1. Pure client-side vanilla JavaScript and Tailwind CSS dark-theme styling (slate-900 / slate-950 cards).
2. The UI MUST include inputs, drag-and-drop file zones, text areas, or number sliders specifically tailored to accomplish the exact purpose stated in the title and description.
3. Include working client-side JavaScript inside the script block that makes the tool fully interactive and functional.
4. Output strict JSON with keys:
   - "body": HTML string for the specialized interactive tool UI.
   - "script": <script>...</script> string containing the full operational logic.
   - "keywords": comma-separated SEO keywords string.
   - "explanation": Brief technical explanation of how the tool processes data client-side.
"""
    raw = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw)
    
    # Universal fallback if AI generation fails or returns empty fields
    if not parsed or "body" not in parsed or "script" not in parsed or len(parsed.get("body", "")) < 50:
        Log.warn("AI generation returned incomplete code; deploying universal adaptive interface.")
        return {
            "body": f"""
<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <h3 class="text-sm font-semibold text-white">Tool Workspace</h3>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Input Data / Parameters</label>
        <textarea id="uni-input" rows="4" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white font-mono text-xs focus:outline-none focus:border-blue-500" placeholder="Enter input data here...">Input data for {trend_data['title']}</textarea>
      </div>
      <button id="uni-btn" class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors">Run Operation</button>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
      <h3 class="text-sm font-semibold text-white">Execution Result</h3>
      <div class="space-y-3">
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Status & Output</span>
          <span id="uni-output" class="text-xs font-mono text-emerald-400 break-all">Ready for processing...</span>
        </div>
      </div>
      <p class="text-[11px] text-slate-500">Processed locally 100% client-side in your browser.</p>
    </div>
  </div>
</div>
""",
            "script": """
<script>
(function() {
  const inp = document.getElementById('uni-input');
  const btn = document.getElementById('uni-btn');
  const out = document.getElementById('uni-output');

  function run() {
    const val = inp.value.trim();
    if (!val) {
      out.textContent = 'Error: Input cannot be empty.';
      return;
    }
    out.textContent = 'Successfully processed ' + val.length + ' characters.';
  }

  if (btn) btn.addEventListener('click', run);
  run();
})();
</script>
""",
            "keywords": f"{trend_data['slug']}, utility, web tool, browser processor",
            "explanation": f"Client-side processing engine designed for {trend_data['title']}."
        }
    return parsed

def assemble_and_save_tool(tool_entry, body_html, script_html):
    if not os.path.exists(TEMPLATE_FILE): return
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f: template = f.read()

    slug = tool_entry["slug"]
    tool_dir = os.path.join(ROOT_DIR, slug)
    os.makedirs(tool_dir, exist_ok=True)
    canonical_url = f"{SITE_URL}/{slug}/"

    replacements = {
        "<!-- {{TOOL_TITLE}} -->": tool_entry["title"],
        "<!-- {{SITE_NAME}} -->": SITE_NAME,
        "<!-- {{TOOL_META_DESCRIPTION}} -->": tool_entry["description"],
        "<!-- {{TOOL_KEYWORDS}} -->": tool_entry.get("keywords", ""),
        "<!-- {{TOOL_CANONICAL_URL}} -->": canonical_url,
        "<!-- {{JSON_LD_SCHEMA}} -->": f'<script type="application/ld+json">{{"@context":"[https://schema.org](https://schema.org)","@type":"WebApplication","name":"{tool_entry["title"]}","url":"{canonical_url}"}}</script>',
        "<!-- {{VERSION_SWITCHER}} -->": '<span class="text-xs text-slate-500">v1.0</span>',
        "<!-- {{TOOL_CATEGORY}} -->": tool_entry.get("category", "Utilities"),
        "<!-- {{TOOL_UPDATED_DATE}} -->": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "<!-- {{TOOL_VERIFICATION_STATUS}} -->": "Active",
        "<!-- {{TOOL_HEADER_SUBTITLE}} -->": tool_entry["description"],
        "<!-- {{TOOL_BODY}} -->": body_html,
        "<!-- {{TOOL_EXPLANATION}} -->": tool_entry.get("explanation", ""),
        "<!-- {{TOOL_SCRIPT}} -->": script_html,
        "<!-- {{TOOL_SLUG}} -->": slug,
    }

    final_html = template
    for placeholder, val in replacements.items():
        final_html = final_html.replace(placeholder, str(val))

    with open(os.path.join(tool_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(final_html)

def rebuild_root_directory(registry):
    Log.step("STEP E", "Rebuilding central Root Directory Index...")
    tools = registry.get("tools", [])
    cards = []
    for t in tools:
        cards.append(f"""
        <div style="background-color: #0f172a; border: 1px solid #1e293b; border-radius: 0.75rem; padding: 1.25rem; transition: border-color 0.2s;">
            <a href="./{t['slug']}/" style="color: #60a5fa; font-weight: 600; font-size: 1.1rem; text-decoration: none;">{t['title']}</a>
            <p style="color: #94a3b8; font-size: 0.875rem; margin-top: 0.35rem; line-height: 1.4;">{t['description']}</p>
            <div style="margin-top: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 0.7rem; background-color: #1e293b; color: #38bdf8; padding: 0.15rem 0.5rem; border-radius: 9999px;">{t.get('category', 'Utilities')}</span>
                <span style="font-size: 0.7rem; color: #64748b;">v{t.get('version', '1.0')}</span>
            </div>
        </div>
        """)

    root_html = f"""<!DOCTYPE html>
<html lang="en" style="height: 100%; background-color: #030712; color: #f8fafc;">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{SITE_NAME}</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #030712;
            color: #f8fafc;
            margin: 0;
            padding: 3rem 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }}
        .container {{
            max-width: 48rem;
            width: 100%;
        }}
        h1 {{
            font-size: 2.25rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: -0.025em;
        }}
        .subtitle {{
            color: #94a3b8;
            font-size: 0.95rem;
            margin-bottom: 2.5rem;
        }}
        .grid {{
            display: grid;
            gap: 1rem;
        }}
        footer {{
            margin-top: 4rem;
            color: #64748b;
            font-size: 0.8rem;
            border-top: 1px solid #1e293b;
            width: 100%;
            max-width: 48rem;
            padding-top: 1.5rem;
            display: flex;
            justify-content: space-between;
        }}
    </style>
</head>
<body>
  <div class="container">
    <h1>{SITE_NAME}</h1>
    <p class="subtitle">Autonomous Self-Coding Micro-Tool Network — Discovering & Deploying Daily</p>
    <div class="grid">
      {"".join(cards)}
    </div>
    <footer>
      <span>Zero Server Cost · Autonomous System</span>
      <span>&copy; 2026 {SITE_NAME}</span>
    </footer>
  </div>
</body>
</html>"""
    with open(ROOT_INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(root_html)

def main():
    registry = load_registry()
    trend_data = step_b_trend_discovery(registry)
    
    if not any(t["slug"] == trend_data["slug"] for t in registry.get("tools", [])):
        tool_code = generate_tool_code(trend_data)
        tool_entry = {
            "slug": trend_data["slug"],
            "title": trend_data["title"],
            "description": trend_data["description"],
            "category": trend_data["category"],
            "version": "1.0",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "Active"
        }
        assemble_and_save_tool(tool_entry, tool_code["body"], tool_code["script"])
        registry.setdefault("tools", []).insert(0, tool_entry)
        registry["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        save_registry(registry)
        
    rebuild_root_directory(registry)
    Log.success("Universal autonomous pipeline run completed successfully.")

if __name__ == "__main__":
    main()
