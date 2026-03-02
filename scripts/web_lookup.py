#!/usr/bin/env python3
"""Lightweight citation helper for web evidence lookup.

No extra install required beyond `requests` + `bs4`.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0"}


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


def _fetch(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, headers=UA, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _clean(text: str) -> str:
    return " ".join(text.split())


def _decode_ddg_redirect(url: str) -> str:
    # DDG HTML results wrap links as //duckduckgo.com/l/?uddg=<target>
    if "duckduckgo.com/l/?" not in url:
        return url
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    target = params.get("uddg", [url])[0]
    return urllib.parse.unquote(target)


def cmd_search(args: argparse.Namespace) -> int:
    q = args.query
    ddg_url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(q)
    soup = BeautifulSoup(_fetch(ddg_url, timeout=args.timeout), "html.parser")

    results: list[SearchResult] = []
    for row in soup.select(".result")[: args.limit]:
        a = row.select_one(".result__a")
        if not a:
            continue
        title = _clean(a.get_text(" ", strip=True))
        href = a.get("href", "").strip()
        url = _decode_ddg_redirect(href)
        snippet_node = row.select_one(".result__snippet")
        snippet = _clean(snippet_node.get_text(" ", strip=True)) if snippet_node else ""
        results.append(SearchResult(title=title, url=url, snippet=snippet))

    print(f"query: {q}")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}")
        print(f"   {r.url}")
        if args.snippets and r.snippet:
            print(f"   {r.snippet}")
    return 0


def cmd_forum(args: argparse.Namespace) -> int:
    args.query = f'site:odoo.com/forum {args.query}'
    return cmd_search(args)


def cmd_github(args: argparse.Namespace) -> int:
    query = args.query
    params = {"q": query, "per_page": args.limit}
    r = requests.get(
        "https://api.github.com/search/issues",
        params=params,
        headers={"Accept": "application/vnd.github+json", **UA},
        timeout=args.timeout,
    )
    r.raise_for_status()
    data = r.json()
    print(f"query: {query}")
    print(f"total_count: {data.get('total_count')}")
    for i, item in enumerate(data.get("items", [])[: args.limit], 1):
        print(f"{i}. {item.get('title')}")
        print(f"   {item.get('html_url')}")
    return 0


def _extract_text_nodes(soup: BeautifulSoup) -> list[str]:
    nodes = soup.select("main h1, main h2, main h3, main p, main li")
    if not nodes:
        nodes = soup.select("h1, h2, h3, p, li")
    return [_clean(n.get_text(" ", strip=True)) for n in nodes]


def cmd_docs(args: argparse.Namespace) -> int:
    soup = BeautifulSoup(_fetch(args.url, timeout=args.timeout), "html.parser")
    title = _clean(soup.title.get_text(strip=True)) if soup.title else "(no title)"
    print(f"title: {title}")
    print(f"url: {args.url}")

    lines = _extract_text_nodes(soup)
    keywords = [k.lower() for k in args.keywords]

    hits: list[str] = []
    for line in lines:
        low = line.lower()
        if all(k in low for k in keywords):
            hits.append(line)
            continue
        if args.mode == "any" and any(k in low for k in keywords):
            hits.append(line)

    if not keywords:
        hits = lines[: args.limit]

    if not hits:
        print("no matches")
        return 0

    for i, line in enumerate(hits[: args.limit], 1):
        print(f"{i}. {line}")
    return 0


def cmd_quote(args: argparse.Namespace) -> int:
    soup = BeautifulSoup(_fetch(args.url, timeout=args.timeout), "html.parser")
    lines = _extract_text_nodes(soup)
    pattern = re.compile(args.contains, re.IGNORECASE)
    hits = [line for line in lines if pattern.search(line)]

    print(f"url: {args.url}")
    if not hits:
        print("no matches")
        return 0

    for i, line in enumerate(hits[: args.limit], 1):
        print(f"{i}. {line}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Citation-grade web lookup helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Web search via DDG HTML endpoint")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=8)
    s.add_argument("--snippets", action="store_true")
    s.add_argument("--timeout", type=int, default=20)
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("forum", help="Odoo forum-focused search")
    f.add_argument("query")
    f.add_argument("--limit", type=int, default=8)
    f.add_argument("--snippets", action="store_true")
    f.add_argument("--timeout", type=int, default=20)
    f.set_defaults(func=cmd_forum)

    g = sub.add_parser("github", help="Search GitHub issues/PRs via API")
    g.add_argument("query", help="GitHub search query, e.g. repo:odoo/odoo reversed payment_state")
    g.add_argument("--limit", type=int, default=10)
    g.add_argument("--timeout", type=int, default=20)
    g.set_defaults(func=cmd_github)

    d = sub.add_parser("docs", help="Extract quote candidates from a documentation page")
    d.add_argument("url")
    d.add_argument("--keywords", nargs="*", default=[])
    d.add_argument("--mode", choices=["all", "any"], default="any")
    d.add_argument("--limit", type=int, default=20)
    d.add_argument("--timeout", type=int, default=20)
    d.set_defaults(func=cmd_docs)

    q = sub.add_parser("quote", help="Extract lines matching a regex phrase from URL")
    q.add_argument("url")
    q.add_argument("--contains", required=True, help="Regex phrase to match")
    q.add_argument("--limit", type=int, default=20)
    q.add_argument("--timeout", type=int, default=20)
    q.set_defaults(func=cmd_quote)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except requests.HTTPError as e:
        print(f"http error: {e}", file=sys.stderr)
        return 2
    except requests.RequestException as e:
        print(f"request error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
