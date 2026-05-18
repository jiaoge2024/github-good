---
name: github-god-tier-projects
description: Discover god-tier, high-quality GitHub repositories from keywords and generate a Chinese visual report. Use when the user asks to query, search, recommend, discover, rank, or compare GitHub projects by keywords, including Chinese triggers such as GitHub 神仙级项目, 神级项目, 宝藏项目, 优质开源项目, 热点项目, 项目推荐, 按关键词查询 GitHub 项目.
---

# GitHub 神仙级项目发现

## Overview

Use this skill to turn a keyword or fuzzy need into a ranked set of high-quality GitHub repositories, then present them in Chinese as project cards. The default output is an HTML report whose cards follow the provided reference style: GitHub page preview on top, then stars/language/tags, project name, one-sentence Chinese value summary, feature chips, clone command, and repository URL.

## Quick Start

Run the bundled script from the skill directory:

```bash
python scripts/find_github_god_tier_projects.py "关键词或需求"
```

Useful options:

```bash
python scripts/find_github_god_tier_projects.py "ai coding assistant" --max-results 10 --min-stars 500
python scripts/find_github_god_tier_projects.py "图片压缩 cli" --output-dir output --language Python
```

If `GITHUB_TOKEN` is available, the script uses it automatically. Without a token, it still works with public rate limits.

## Workflow

1. Parse the user's query into a concrete intent before searching. Expand short terms and Chinese phrases into precise GitHub search vocabulary:
   - `TTS`, `文本转语音`, `语音合成` => text-to-speech / speech synthesis / TTS repositories
   - `STT`, `语音识别`, `语音转文字` => speech-to-text / speech recognition repositories
   - Keep proper nouns, framework names, language names, and tool categories.
2. Search GitHub repositories with multiple intent-specific queries instead of one loose keyword query:
   - default minimum stars: 500
   - default sort: stars
   - prefer active repositories updated within the last 24 months
   - prefer repositories with description, topics, license, recent releases, and clear README
3. Apply a relevance gate before ranking. A repository must match the intent in its name, description, topics, or other GitHub metadata. For example, a `TTS` query must show text-to-speech, speech synthesis, voice synthesis, voice cloning, or closely related TTS terms; generic AI projects that merely mention voice/audio once should be filtered out.
4. If results are weak or empty, automatically broaden:
   - lower `min_stars` to 100
   - remove language restriction
   - search related English keywords while keeping the relevance gate active
5. Score and rank repositories. Favor intent relevance first, then star count, recency, forks, topics, release activity, license presence, and clarity of description.
6. Generate the output report in Simplified Chinese. Do not stop to ask the user which projects to include unless the request explicitly asks for interactive selection.

## Output Requirements

Create a single HTML file under `output/` named like `github-god-tier-projects-YYYYMMDD-HHMMSS.html`.

Each project card must include:

- A top preview area that visually resembles a GitHub repository page screenshot.
- A compact meta row with a star icon, star count, primary language badge, and 1-3 project tags.
- Repository name as a bold title.
- A concise Chinese summary explaining what the project does and why it is worth attention.
- A handwritten/marker-like feature row with short Chinese or bilingual labels such as `语音 / TTS`, `音频`, `生成`, `部署`.
- A command block containing `git clone <repo clone url> && cd <repo name>`.
- The canonical repository URL aligned near the bottom right.

Match the reference card mood:

- warm off-white background
- subtle dotted/grid texture
- soft paper-like card
- yellow star count accent
- blue language badge
- red underline accents under feature labels
- dense information, no marketing landing page

Read `references/card-style.md` when modifying the card template.

## Quality Rules

Define "神仙级" as repositories that satisfy most of these signals:

- Meaningful adoption: high stars for its niche, active forks, or strong community attention.
- Practical usefulness: solves a clear developer/user problem, not only a demo.
- Recent vitality: commits/releases/issues activity within the last 24 months unless it is a mature stable tool.
- Clear onboarding: README explains installation or usage.
- Trust signals: license, topics, examples, docs, tests, or maintainers with track record.
- Distinctiveness: avoid listing many near-identical wrappers unless the user asks for exhaustive comparison.

Avoid low-signal entries:

- archived repositories unless historically important
- no README or unclear purpose
- spammy generated repos
- repos with misleading names unrelated to the query
- broad AI/model hubs that do not directly solve the requested task
- opposite-direction tools, such as STT/ASR results for a TTS query, unless the repository explicitly supports both

## Script

Use `scripts/find_github_god_tier_projects.py` for the default implementation. It searches GitHub, ranks repositories, and writes the HTML report. Patch the script when the user asks for a different card style, fields, ranking formula, or output format.

The script does not perform AI summarization. After it runs, improve weak Chinese summaries manually if needed, based on repository description, topics, and README snippets. For current or precise repository data, always rely on live GitHub/API results rather than memory.
