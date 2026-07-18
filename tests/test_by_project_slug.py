"""Tests for _sanitize_project_slug (cross-platform filesystem safety).

Phase 2 ship (post-v1.1.0, 2026-07-18): fix Windows-illegal chars in project
slugs so by-project/<slug>.md works on Windows / macOS / Linux uniformly.

M-SlugSanitize-001: project slugs must be lowercased, no path separators,
no Windows-illegal chars (<>:"/\\|?*), no shell glob chars.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a standalone script.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

from wiki_ingest import _sanitize_project_slug  # noqa: E402

tests = []


def t(name, got, want):
    ok = got == want
    tests.append((name, ok, got, want))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


# Lowercase + trim
t("lowercase", _sanitize_project_slug("FOO"), "foo")
t("trim spaces", _sanitize_project_slug("  bar  "), "bar")

# Path separators → -
t("slash → dash", _sanitize_project_slug("team/a"), "team-a")
t("backslash → dash (Windows safety)",
  _sanitize_project_slug("team\\a"), "team-a")
t("both slashes", _sanitize_project_slug("a/b\\c"), "a-b-c")

# Windows-illegal chars → -
t("angle brackets", _sanitize_project_slug("foo<bar>baz"), "foo-bar-baz")
t("colon", _sanitize_project_slug("foo:bar"), "foo-bar")
t("double quote", _sanitize_project_slug('foo"bar'), "foo-bar")
t("pipe", _sanitize_project_slug("foo|bar"), "foo-bar")
t("question mark", _sanitize_project_slug("foo?bar"), "foo-bar")
t("asterisk", _sanitize_project_slug("foo*bar"), "foo-bar")

# Parens (the original bug: "(uncategorized)" produced
# "by-project/(uncategorized).md" which git ls-files displayed oddly)
t("parens round",
  _sanitize_project_slug("(uncategorized)"), "uncategorized")
t("square brackets",
  _sanitize_project_slug("foo[bar]baz"), "foo-bar-baz")

# Whitespace → -
t("spaces collapse", _sanitize_project_slug("foo bar baz"), "foo-bar-baz")
t("tabs and newlines",
  _sanitize_project_slug("foo\tbar\nbaz"), "foo-bar-baz")

# Multiple dashes collapse
t("collapse dashes", _sanitize_project_slug("foo---bar"), "foo-bar")
t("leading/trailing dash stripped",
  _sanitize_project_slug("---foo---"), "foo")

# Empty fallback
t("empty string → uncategorized", _sanitize_project_slug(""), "uncategorized")
t("only special chars → uncategorized",
  _sanitize_project_slug("()[]"), "uncategorized")
t("only dashes → uncategorized",
  _sanitize_project_slug("---"), "uncategorized")

# Realistic project names
t("kebab-case preserved", _sanitize_project_slug("mini-mp-agent"), "mini-mp-agent")
t("CamelCase lowercased", _sanitize_project_slug("MiniMpAgent"), "minimpagent")
t("mixed case + path", _sanitize_project_slug("Team/Awesome"), "team-awesome")

passed = sum(1 for _, ok, _, _ in tests if ok)
failed = len(tests) - passed
print(f"\n=== {passed}/{len(tests)} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)