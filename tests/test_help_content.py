from pathlib import Path

import sb_help

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_ten_topics_with_files_present():
    assert len(sb_help.HELP_TOPICS) == 11
    for title, filename in sb_help.HELP_TOPICS:
        assert title and filename.endswith(".md")
        assert (sb_help.help_dir(REPO_ROOT) / filename).is_file(), f"missing {filename}"


def test_load_topic_reads_file_content():
    text = sb_help.load_topic(REPO_ROOT, sb_help.HELP_TOPICS[0][1])
    assert text.startswith("# ")


def test_load_topic_missing_file_returns_fallback():
    text = sb_help.load_topic(REPO_ROOT, "no-such-topic.md")
    assert text == sb_help.FALLBACK_TEXT
    assert "github.com" in text


def test_docs_contain_no_mojibake():
    for _title, filename in sb_help.HELP_TOPICS:
        text = sb_help.load_topic(REPO_ROOT, filename)
        assert "â" not in text and "Ã" not in text, \
            f"{filename} contains double-encoded UTF-8"
