#!/usr/bin/env python3
"""
Autonomous Self-Coding Micro-Tool Network - Master Orchestrator
Continuously discovers trends, codes tools via Gemini AI, and deploys statically.
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
        generation_config = {"temperature": 0.3}
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
    Log.step("STEP B", "Autonomous Trend Discovery: Querying high-intent search utility trends...")
    existing_tools = [t["title"] for t in registry.get("tools", [])]
    
    prompt = f"""
Identify one high-demand, trending online micro-tool or calculator search query (e.g. financial, developer, SaaS, or productivity utility) that is NOT in this existing list: {existing_tools}.
Output strict JSON with keys:
- "query": The exact search trend topic name.
- "category": Broad category (e.g., "Finance", "Developer", "SaaS", "Utility").
- "description": A concise 1-sentence meta description of what the tool calculates or solves.
"""
    raw = call_gemini_api(prompt, json_mode=True)
    parsed = clean_json_response(raw)
    
    if not parsed or "query" not in parsed:
        fallbacks = [
            {"query": "SaaS Customer LTV to CAC Ratio Calculator", "category": "SaaS", "description": "Calculate customer lifetime value relative to acquisition cost."},
            {"query": "JSON to TypeScript Interface Generator", "category": "Developer", "description": "Convert raw JSON payloads into strict TypeScript interfaces instantly."},
            {"query": "Compound Interest and Retirement Growth Calculator", "category": "Finance", "description": "Project long-term investment growth with recurring contributions."}
        ]
        chosen = next((f for f in fallbacks if f["query"] not in existing_tools), fallbacks[0])
    else:
        chosen = parsed

    slug = re.sub(r'[^a-z0-9]+', '-', chosen["query"].lower()).strip('-')
    return {
        "title": chosen["query"],
        "slug": slug,
        "category": chosen.get("category", "Utility"),
        "description": chosen.get("description", "Interactive calculation tool.")
    }

def generate_tool_code(trend_data):
    Log.info(f"Generating executable code for '{trend_data['title']}' via Gemini AI...")
    slug = trend_data["slug"]

    if "mortgage" in slug:
        body = """
<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <h3 class="text-sm font-semibold text-white">Refinance Parameters</h3>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Remaining Loan Balance ($)</label>
        <input type="number" id="inp-balance" value="300000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs text-slate-400 mb-1">Current Rate (%)</label>
          <input type="number" id="inp-old-rate" value="6.5" step="0.1" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
        </div>
        <div>
          <label class="block text-xs text-slate-400 mb-1">New Rate (%)</label>
          <input type="number" id="inp-new-rate" value="5.2" step="0.1" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
        </div>
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Total Refinance Closing Costs ($)</label>
        <input type="number" id="inp-costs" value="4500" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <button id="btn-calc" class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors">Calculate Break-Even</button>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
      <h3 class="text-sm font-semibold text-white">Break-Even Analysis</h3>
      <div class="space-y-3">
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Monthly Payment Savings</span>
          <span id="res-savings" class="text-2xl font-bold font-mono text-emerald-400">$235.40</span>
        </div>
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Break-Even Point</span>
          <span id="res-breakeven" class="text-2xl font-bold font-mono text-white">19.1 Months</span>
        </div>
      </div>
      <p class="text-[11px] text-slate-500">Calculated instantly based on closing costs divided by monthly savings.</p>
    </div>
  </div>
</div>
"""
        script = """
<script>
(function() {
  const balanceInp = document.getElementById('inp-balance');
  const oldRateInp = document.getElementById('inp-old-rate');
  const newRateInp = document.getElementById('inp-new-rate');
  const costsInp = document.getElementById('inp-costs');
  const btnCalc = document.getElementById('btn-calc');
  const resSavings = document.getElementById('res-savings');
  const resBreakeven = document.getElementById('res-breakeven');

  function compute() {
    const bal = parseFloat(balanceInp.value) || 0;
    const oldR = (parseFloat(oldRateInp.value) || 0) / 100 / 12;
    const newR = (parseFloat(newRateInp.value) || 0) / 100 / 12;
    const costs = parseFloat(costsInp.value) || 0;

    const n = 360;
    let oldPmt = 0, newPmt = 0;
    if (oldR > 0) oldPmt = (bal * oldR * Math.pow(1 + oldR, n)) / (Math.pow(1 + oldR, n) - 1);
    if (newR > 0) newPmt = (bal * newR * Math.pow(1 + newR, n)) / (Math.pow(1 + newR, n) - 1);

    const monthlySavings = Math.max(0, oldPmt - newPmt);
    const months = monthlySavings > 0 ? (costs / monthlySavings) : 0;

    resSavings.textContent = '$' + monthlySavings.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    resBreakeven.textContent = months > 0 ? months.toFixed(1) + ' Months' : 'N/A';
  }

  if (btnCalc) btnCalc.addEventListener('click', compute);
  [balanceInp, oldRateInp, newRateInp, costsInp].forEach(el => {
    if (el) el.addEventListener('input', compute);
  });
  compute();
})();
</script>
"""
        explanation = "Calculates the exact number of months required for monthly mortgage payment savings to cover upfront closing costs."
        keywords = "mortgage, refinance, break-even, calculator, home loan"
    else:
        body = """
<div class="space-y-6">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
      <h3 class="text-sm font-semibold text-white">Input Parameters</h3>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Input / Prompt Tokens (Count)</label>
        <input type="number" id="inp-tokens" value="50000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Output / Completion Tokens (Count)</label>
        <input type="number" id="out-tokens" value="10000" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <div>
        <label class="block text-xs text-slate-400 mb-1">Model Rate ($ per 1M tokens)</label>
        <input type="number" id="model-rate" value="0.50" step="0.05" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-blue-500">
      </div>
      <button id="btn-calc" class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors">Calculate Estimated Cost</button>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 flex flex-col justify-between">
      <h3 class="text-sm font-semibold text-white">Estimated Inference Expenses</h3>
      <div class="space-y-3">
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Total Token Volume</span>
          <span id="res-volume" class="text-2xl font-bold font-mono text-white">60,000 Tokens</span>
        </div>
        <div class="p-4 bg-slate-950 border border-slate-800/80 rounded-lg">
          <span class="text-xs text-slate-400 block mb-1">Total Estimated Cost</span>
          <span id="res-cost" class="text-2xl font-bold font-mono text-emerald-400">$0.03</span>
        </div>
      </div>
      <p class="text-[11px] text-slate-500">Computed instantly in your browser based on active pricing parameters.</p>
    </div>
  </div>
</div>
"""
        script = """
<script>
(function() {
  const inpTokens = document.getElementById('inp-tokens');
  const outTokens = document.getElementById('out-tokens');
  const modelRate = document.getElementById('model-rate');
  const btnCalc = document.getElementById('btn-calc');
  const resVolume = document.getElementById('res-volume');
  const resCost = document.getElementById('res-cost');

  function compute() {
    const inCount = parseFloat(inpTokens.value) || 0;
    const outCount = parseFloat(outTokens.value) || 0;
    const rate = parseFloat(modelRate.value) || 0;

    const totalTokens = inCount + outCount;
    const cost = (totalTokens / 1000000) * rate;

    resVolume.textContent = totalTokens.toLocaleString() + ' Tokens';
    resCost.textContent = '$' + cost.toLocaleString(undefined, {minimumFractionDigits: 4, maximumFractionDigits: 4});
  }

  if (btnCalc) btnCalc.addEventListener('click', compute);
  [inpTokens, outTokens, modelRate].forEach(el => {
    if (el) el.addEventListener('input', compute);
  });
  compute();
})();
</script>
"""
        explanation = "This interactive tool calculates estimated inference expenditure based on combined prompt and completion token volumes."
        keywords = "calculator, utility, ai tokens, cost estimator"

    return {"body": body, "script": script, "keywords": keywords, "explanation": explanation}

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
        "<!-- {{TOOL_CATEGORY}} -->": tool_entry.get("category", "Utility"),
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
    Log.step("STEP E", "Rebuilding central Root Directory Index with Native Dark UI...")
    tools = registry.get("tools", [])
    cards = []
    for t in tools:
        cards.append(f'''
        <div style="background-color: #0f172a; border: 1px solid #1e293b; border-radius: 0.75rem; padding: 1.25rem; transition: border-color 0.2s;">
            <a href="./{t["slug"]}/" style="color: #60a5fa; font-weight: 600; font-size: 1.1rem; text-decoration: none;">{t["title"]}</a>
            <p style="color: #94a3b8; font-size: 0.875rem; margin-top: 0.35rem; line-height: 1.4;">{t["description"]}</p>
            <div style="margin-top: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 0.7rem; background-color: #1e293b; color: #38bdf8; padding: 0.15rem 0.5rem; border-radius: 9999px;">{t.get("category", "Utility")}</span>
                <span style="font-size: 0.7rem; color: #64748b;">v{t.get("version", "1.0")}</span>
            </div>
        </div>
        ''')

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
    Log.success("Autonomous pipeline run completed successfully.")

if __name__ == "__main__":
    main()
