# Project Card Style Reference

Use this reference when generating or editing HTML reports for `github-god-tier-projects`.

## Layout

Each repository is a single poster-like card sized around 480px wide on desktop, responsive to one column on mobile.

Card structure:

1. GitHub preview panel
2. Meta row: avatar dot, star icon, star number, language badge, topic chips
3. Project name
4. Chinese value summary
5. Feature labels with red underline strokes
6. Clone command block
7. Repository URL footer

## Visual Tokens

- Page background: `#f3eddc` or similar warm paper color.
- Card background: `#fbf7e9`.
- Text: `#111111`.
- Muted text: `#595959`.
- Star accent: `#f5d21f`.
- Language badge: `#1f6feb`.
- Topic badge: pale yellow, `#fff6b8`.
- Underline accent: `#ef4d3f`.
- Border: `#ddd3b8`, dashed at the bottom when useful.
- Radius: 6-8px.

## GitHub Preview Panel

Do not require a real screenshot. Recreate the feel with HTML/CSS:

- dark GitHub top nav strip
- repository breadcrumb
- tab row
- file list rows
- right-side "About" block

Use actual repository name, owner, description, default branch, stars, forks, and topics where available.

## Typography

Use system fonts. Keep the title strong and compact. Do not use oversized hero typography inside cards.

## Interaction

The card itself may link to the repository. Keep the command block selectable. Avoid hidden content that requires clicking to understand the project.
