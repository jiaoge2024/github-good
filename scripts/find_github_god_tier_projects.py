#!/usr/bin/env python3
"""Search GitHub repositories and generate Chinese poster-card HTML."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


GITHUB_API = "https://api.github.com"


INTENTS = {
    "tts": {
        "triggers": [
            "tts",
            "text to speech",
            "text-to-speech",
            "文本转语音",
            "文字转语音",
            "语音合成",
            "语音生成",
        ],
        "searches": [
            "tts",
            '"text-to-speech"',
            '"text to speech"',
            '"speech synthesis"',
            "speech-synthesis",
            "topic:tts",
            "topic:text-to-speech",
            "topic:speech-synthesis",
        ],
        "strong_terms": [
            "tts",
            "text-to-speech",
            "text to speech",
            "speech synthesis",
            "speech-synthesis",
            "voice synthesis",
            "voice cloning",
            "语音合成",
            "文本转语音",
        ],
        "weak_terms": ["speech", "voice", "audio", "vocoder"],
        "block_terms": ["speech recognition", "asr", "stt", "speech-to-text", "voice assistant"],
        "generic_hub_terms": [
            "run any model",
            "open models",
            "llm",
            "llms",
            "vision, voice, image",
            "training and running",
            "model hub",
        ],
        "labels": ["语音 / TTS", "文本转语音", "语音合成"],
    },
    "stt": {
        "triggers": ["stt", "speech to text", "speech-to-text", "语音识别", "语音转文字"],
        "searches": [
            "stt",
            '"speech-to-text"',
            '"speech recognition"',
            "automatic-speech-recognition",
            "topic:speech-recognition",
        ],
        "strong_terms": [
            "stt",
            "speech-to-text",
            "speech to text",
            "speech recognition",
            "automatic speech recognition",
            "asr",
            "语音识别",
        ],
        "weak_terms": ["speech", "voice", "audio", "transcription"],
        "block_terms": ["text-to-speech", "tts", "speech synthesis"],
        "generic_hub_terms": ["run any model", "open models", "llm", "llms", "model hub"],
        "labels": ["语音识别", "STT", "转写"],
    },
}


TOPIC_ZH = {
    "ai": "AI",
    "artificial-intelligence": "人工智能",
    "automation": "自动化",
    "cli": "命令行",
    "developer-tools": "开发工具",
    "image-processing": "图像处理",
    "machine-learning": "机器学习",
    "python": "Python",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "react": "React",
    "llm": "大模型",
    "agent": "智能体",
    "tts": "TTS",
    "audio": "音频",
    "speech": "语音",
    "productivity": "效率工具",
    "web": "Web",
}


def detect_intent(query: str) -> dict | None:
    normalized = query.casefold().replace("_", "-")
    for intent in INTENTS.values():
        if any(trigger.casefold() in normalized for trigger in intent["triggers"]):
            return intent
    return None


def repo_text(repo: dict) -> str:
    parts = [
        repo.get("name") or "",
        repo.get("full_name") or "",
        repo.get("description") or "",
        " ".join(repo.get("topics") or []),
        repo.get("language") or "",
    ]
    return " ".join(parts).casefold()


def repo_core_text(repo: dict) -> str:
    parts = [
        repo.get("name") or "",
        repo.get("full_name") or "",
        repo.get("description") or "",
    ]
    return " ".join(parts).casefold()


def term_hit(text: str, term: str) -> bool:
    term = term.casefold()
    if re.search(r"^[a-z0-9+#.-]+$", term):
        return re.search(rf"(?<![a-z0-9+#]){re.escape(term)}(?![a-z0-9+#])", text) is not None
    return term in text


def strong_intent_hits(repo: dict, intent: dict) -> tuple[int, int]:
    core = repo_core_text(repo)
    all_text = repo_text(repo)
    core_hits = sum(1 for term in intent["strong_terms"] if term_hit(core, term))
    all_hits = sum(1 for term in intent["strong_terms"] if term_hit(all_text, term))
    return core_hits, all_hits


def is_generic_hub(repo: dict, intent: dict) -> bool:
    core = repo_core_text(repo)
    return any(term_hit(core, term) for term in intent.get("generic_hub_terms", []))


def relevance_score(repo: dict, intent: dict | None, query: str) -> int:
    text = repo_text(repo)
    score = 0
    if intent:
        for term in intent["strong_terms"]:
            if term_hit(text, term):
                score += 12
        for term in intent["weak_terms"]:
            if term_hit(text, term):
                score += 3
        for term in intent["block_terms"]:
            if term_hit(text, term):
                score -= 18
        topics = {topic.casefold() for topic in repo.get("topics") or []}
        if topics.intersection({t.casefold().replace("topic:", "") for t in intent["searches"] if t.startswith("topic:")}):
            score += 10
        return score

    query_terms = [t.casefold() for t in re.findall(r"[\w+#.-]+", normalize_query(query)) if len(t) > 1]
    for term in query_terms:
        if term_hit(text, term):
            score += 5
    return score


def is_relevant(repo: dict, intent: dict | None, query: str) -> bool:
    if intent:
        core_hits, all_hits = strong_intent_hits(repo, intent)
        if core_hits == 0:
            return False
        if is_generic_hub(repo, intent) and core_hits < 2:
            return False
        return relevance_score(repo, intent, query) >= 12 and all_hits > 0
    return relevance_score(repo, intent, query) >= 5


def request_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-god-tier-projects-skill",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_query(query: str) -> str:
    query = query.strip()
    replacements = {
        "图片": "image",
        "图像": "image",
        "压缩": "compression",
        "语音": "speech tts",
        "文本转语音": "tts",
        "自动化": "automation",
        "命令行": "cli",
        "大模型": "llm",
        "智能体": "agent",
        "前端": "frontend",
        "后台": "backend",
        "部署": "deploy",
        "爬虫": "crawler scraper",
    }
    expanded = query
    for zh, en in replacements.items():
        if zh in query:
            expanded += " " + en
    return expanded


def build_search_query(query: str, min_stars: int, language: str | None) -> str:
    parts = [normalize_query(query), f"stars:>={min_stars}", "archived:false"]
    if language:
        parts.append(f"language:{language}")
    return " ".join(parts)


def build_search_queries(query: str, min_stars: int, language: str | None) -> list[str]:
    intent = detect_intent(query)
    if intent:
        bases = intent["searches"]
    else:
        bases = [normalize_query(query)]

    queries = []
    for base in bases:
        parts = [base, f"stars:>={min_stars}", "archived:false"]
        if language:
            parts.append(f"language:{language}")
        queries.append(" ".join(parts))
    return queries


def search_repos(query: str, min_stars: int, max_results: int, language: str | None, verbose: bool = False) -> list[dict]:
    per_page = min(max(max_results * 2, 10), 50)
    found = {}
    for search_query in build_search_queries(query, min_stars, language):
        q = urllib.parse.quote(search_query)
        url = f"{GITHUB_API}/search/repositories?q={q}&sort=stars&order=desc&per_page={per_page}"
        try:
            data = request_json(url)
        except Exception as exc:
            if verbose:
                print(f"warning: GitHub search failed for {search_query!r}: {exc}", file=sys.stderr)
            continue
        for repo in data.get("items", []):
            found[repo["full_name"]] = repo
    return list(found.values())


def score_repo(repo: dict, intent: dict | None = None, query: str = "") -> float:
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0
    topics = repo.get("topics") or []
    updated_at = repo.get("updated_at") or "1970-01-01T00:00:00Z"
    try:
        updated = dt.datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        updated = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    age_days = max((dt.datetime.now(dt.timezone.utc) - updated).days, 0)
    recency = max(0, 100 - age_days / 7)
    star_score = min(100, math.log10(stars + 1) * 20)
    fork_score = min(100, math.log10(forks + 1) * 25)
    topic_score = min(20, len(topics) * 3)
    license_score = 8 if repo.get("license") else 0
    desc_score = 8 if repo.get("description") else 0
    relevance = min(40, relevance_score(repo, intent, query) * 1.5)
    return star_score * 0.38 + recency * 0.18 + fork_score * 0.12 + topic_score + license_score + desc_score + relevance


def zh_topics(repo: dict) -> list[str]:
    raw = repo.get("topics") or []
    labels = []
    for topic in raw[:5]:
        labels.append(TOPIC_ZH.get(topic.lower(), topic))
    if repo.get("language") and repo["language"] not in labels:
        labels.insert(0, repo["language"])
    return labels[:5]


def summary(repo: dict) -> str:
    desc = repo.get("description") or "这个项目在相关领域具有较高关注度，可作为优先调研的开源方案。"
    desc = re.sub(r"\s+", " ", desc).strip()
    if re.search(r"[\u4e00-\u9fff]", desc):
        text = desc
    else:
        text = f"一个面向 {repo.get('language') or '开发者'} 生态的开源项目，核心能力是 {desc}"
    return text[:120]


def feature_labels(repo: dict) -> list[str]:
    topics = [t.lower() for t in repo.get("topics") or []]
    labels = []
    mapping = [
        ("tts", "语音 / TTS"),
        ("speech", "语音识别"),
        ("audio", "音频"),
        ("image", "图像"),
        ("cli", "CLI"),
        ("agent", "智能体"),
        ("llm", "大模型"),
        ("automation", "自动化"),
        ("deploy", "部署"),
        ("api", "API"),
    ]
    joined = " ".join(topics + [repo.get("name", ""), repo.get("description") or ""]).lower()
    for key, label in mapping:
        if key in joined and label not in labels:
            labels.append(label)
    return (labels or ["开源", "工具", "实践"])[:5]


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def repo_card(repo: dict, rank: int, intent: dict | None = None, query: str = "") -> str:
    full_name = repo["full_name"]
    owner, name = full_name.split("/", 1)
    url = repo["html_url"]
    clone_url = repo.get("clone_url") or f"{url}.git"
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0
    language = repo.get("language") or "Code"
    topics = zh_topics(repo)
    features = feature_labels(repo)
    branch = repo.get("default_branch") or "main"
    updated = (repo.get("updated_at") or "")[:10]
    score = round(score_repo(repo, intent, query))
    topic_html = "".join(f"<span>{esc(t)}</span>" for t in topics[:3])
    feature_html = "".join(f"<b>{esc(t)}</b>" for t in features)
    return f"""
    <article class="project-card" onclick="window.open('{esc(url)}','_blank')">
      <div class="github-preview" aria-label="GitHub repository preview">
        <div class="gh-top"><span class="mark">●</span><span>Platform</span><span>Solutions</span><span>Resources</span><span>Open Source</span><span>Pricing</span></div>
        <div class="gh-repo"><strong>{esc(owner)}</strong> / <strong>{esc(name)}</strong> <em>Public</em></div>
        <div class="gh-tabs"><span>Code</span><span>Issues</span><span>Pull requests</span><span>Actions</span><span>Projects</span><span>Security</span><span>Insights</span></div>
        <div class="gh-body">
          <div class="gh-files">
            <div class="gh-branch">{esc(branch)} <button>Code</button></div>
            <p><strong>{esc(owner)}</strong> update docs and examples <time>{esc(updated)}</time></p>
            <p>src <small>core implementation and modules</small></p>
            <p>README.md <small>usage, installation and examples</small></p>
          </div>
          <aside>
            <strong>About</strong>
            <p>{esc(repo.get("description") or "High quality open source project.")}</p>
            <small>{stars:,} stars · {forks:,} forks</small>
          </aside>
        </div>
      </div>
      <div class="meta">
        <span class="avatar"></span>
        <span class="star">★</span>
        <strong class="star-count">{stars:,}</strong>
        <span class="language">{esc(language)}</span>
        <span class="score">神仙指数 {score}</span>
        <span class="topics">{topic_html}</span>
      </div>
      <h2>{esc(name)}</h2>
      <p class="summary">{esc(summary(repo))}</p>
      <div class="features">{feature_html}</div>
      <pre><code>$ git clone {esc(clone_url)} &amp;&amp; cd {esc(name)}</code></pre>
      <footer>github.com/{esc(full_name)}</footer>
    </article>
    """


def render_html(query: str, repos: list[dict], intent: dict | None = None) -> str:
    cards = "\n".join(repo_card(repo, i + 1, intent, query) for i, repo in enumerate(repos))
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub 神仙级项目 - {esc(query)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #111;
      background-color: #f3eddc;
      background-image: radial-gradient(#dfd4b8 0.8px, transparent 0.8px);
      background-size: 12px 12px;
    }}
    header {{ max-width: 1100px; margin: 0 auto; padding: 34px 18px 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    header p {{ margin: 0; color: #595959; }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 18px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 20px;
    }}
    .project-card {{
      background: #fbf7e9;
      border: 1px solid #ddd3b8;
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 10px 26px rgba(60, 48, 28, 0.10);
      cursor: pointer;
      transition: transform .15s ease, box-shadow .15s ease;
    }}
    .project-card:hover {{ transform: translateY(-2px); box-shadow: 0 14px 30px rgba(60,48,28,.16); }}
    .github-preview {{ border: 1px solid #d8d8d8; border-radius: 4px; overflow: hidden; background: #fff; font-size: 8px; color: #24292f; }}
    .gh-top {{ height: 24px; display: flex; align-items: center; gap: 10px; padding: 0 10px; background: #24292f; color: white; }}
    .gh-top .mark {{ font-size: 10px; }}
    .gh-repo {{ padding: 9px 12px; border-bottom: 1px solid #d8dee4; color: #0969da; }}
    .gh-repo em {{ color: #57606a; border: 1px solid #d0d7de; border-radius: 10px; padding: 1px 5px; font-style: normal; }}
    .gh-tabs {{ display: flex; gap: 12px; padding: 7px 12px; border-bottom: 1px solid #d8dee4; color: #57606a; }}
    .gh-body {{ display: grid; grid-template-columns: 1fr 120px; gap: 12px; padding: 10px 12px; }}
    .gh-files {{ border: 1px solid #d0d7de; border-radius: 4px; overflow: hidden; }}
    .gh-files p, .gh-branch {{ margin: 0; padding: 7px 8px; border-bottom: 1px solid #d8dee4; display: flex; justify-content: space-between; gap: 8px; }}
    .gh-files p:last-child {{ border-bottom: 0; }}
    .gh-branch {{ background: #f6f8fa; }}
    .gh-branch button {{ background: #238636; border: 0; color: white; border-radius: 4px; padding: 2px 8px; font-size: 8px; }}
    aside p {{ margin: 6px 0; line-height: 1.35; }}
    .meta {{ display: flex; align-items: center; gap: 9px; flex-wrap: wrap; padding: 12px 0 4px; }}
    .avatar {{ width: 18px; height: 18px; border-radius: 50%; background: linear-gradient(135deg,#ff9ab0,#ffd16b); }}
    .star {{ color: #d5a900; font-size: 26px; line-height: 1; }}
    .star-count {{ color: #f1df13; font-size: 18px; min-width: 42px; }}
    .language {{ background: #1f6feb; color: white; border-radius: 4px; padding: 5px 8px; font-size: 12px; font-weight: 700; }}
    .score {{ color: #755f00; font-size: 12px; }}
    .topics span {{ background: #fff6b8; border-radius: 4px; padding: 4px 8px; margin-right: 5px; font-size: 11px; }}
    h2 {{ margin: 8px 0 12px; font-size: 22px; line-height: 1.15; }}
    .summary {{ margin: 0 0 14px; font-size: 16px; line-height: 1.65; }}
    .features {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; color: #333; }}
    .features b {{ font-size: 14px; font-weight: 500; border-bottom: 3px solid #ef4d3f; padding-bottom: 3px; }}
    pre {{ margin: 0; padding: 11px 12px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; background: #fff8db; color: #0969da; border-radius: 5px; font-size: 12px; }}
    footer {{ border-bottom: 1px dashed #9bb69b; padding: 12px 0 2px; text-align: right; font-size: 12px; color: #222; }}
    @media (max-width: 520px) {{
      main {{ grid-template-columns: 1fr; padding: 12px; }}
      .gh-body {{ grid-template-columns: 1fr; }}
      .project-card {{ padding: 10px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>GitHub 神仙级项目</h1>
    <p>关键词：{esc(query)} · 生成时间：{esc(generated)} · 共 {len(repos)} 个项目</p>
  </header>
  <main>
    {cards}
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Find god-tier GitHub projects and generate HTML cards.")
    parser.add_argument("query", help="Keyword or user need")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--min-stars", type=int, default=500)
    parser.add_argument("--language")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--verbose", action="store_true", help="Print skipped GitHub search warnings")
    args = parser.parse_args()

    intent = detect_intent(args.query)
    repos = search_repos(args.query, args.min_stars, args.max_results, args.language, args.verbose)
    if len(repos) < max(3, min(args.max_results, 5)) and args.min_stars > 100:
        repos = search_repos(args.query, 100, args.max_results, None, args.verbose)

    relevant = [repo for repo in repos if is_relevant(repo, intent, args.query)]
    ranked = sorted(relevant, key=lambda repo: score_repo(repo, intent, args.query), reverse=True)[: args.max_results]
    if not ranked:
        print("No relevant repositories found. Try broader English keywords or a lower --min-stars value.", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"github-god-tier-projects-{stamp}.html"
    out_path.write_text(render_html(args.query, ranked, intent), encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
