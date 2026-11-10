"""Rewrite the open-source section of README.md from my pull requests to other people's projects."""

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

USER = "aaryagodbole"
# Below this, a repo is a friend's or class project rather than an open-source project.
MIN_STARS = 100
START, END = "<!-- OSS:START -->", "<!-- OSS:END -->"


def gh(*args: str) -> object:
    return json.loads(subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout)


def stars(count: int) -> str:
    return f"{count / 1000:.1f}k".replace(".0k", "k") if count >= 1000 else str(count)


def render() -> str:
    prs = gh("search", "prs", "--author", USER, "--limit", "200",
             "--json", "repository,number,title,url,state,isDraft")
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for pr in prs:
        repo = pr["repository"]["nameWithOwner"]
        if repo.split("/")[0] != USER:
            by_repo[repo].append(pr)

    rows = []
    for repo, items in by_repo.items():
        info = gh("api", f"repos/{repo}")
        if info["stargazers_count"] < MIN_STARS:
            continue
        merged = [p for p in items if p["state"] == "merged"]
        open_ = [p for p in items if p["state"] == "open" and not p["isDraft"]]
        if merged or open_:
            rows.append((info, merged, open_))

    rows.sort(key=lambda r: (-len(r[1]), -r[0]["stargazers_count"]))
    total_merged = sum(len(r[1]) for r in rows)
    total_open = sum(len(r[2]) for r in rows)
    lines = [f"**{total_merged} merged** · **{total_open} in review** across **{len(rows)}** projects", ""]
    for info, merged, open_ in rows:
        owner, name = info["owner"]["login"], info["full_name"]
        lines.append(
            f'<img src="https://github.com/{owner}.png?size=40" width="20" height="20" align="center" /> '
            f'**[{name}]({info["html_url"]})** ⭐ {stars(info["stargazers_count"])}'
        )
        lines.append("")
        for pr in merged + open_:
            mark = "🟣 merged" if pr["state"] == "merged" else "🟢 open"
            lines.append(f'- [{pr["title"]}]({pr["url"]}) · {mark}')
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    readme = Path("README.md")
    text = readme.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print("OSS markers missing from README.md", file=sys.stderr)
        return 1
    readme.write_text(pattern.sub(lambda _: f"{START}\n{render()}\n{END}", text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
