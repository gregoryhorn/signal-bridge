from pathlib import Path

from sb_channels import (
    build_channel_catalog,
    catalog_summary,
    channel_from_filename,
    discover_channel_metadata,
    normalize_channel_name,
)


def test_normalize_and_filename():
    assert normalize_channel_name("  Intel  HQ  ") == "Intel HQ"
    assert channel_from_filename(Path("Local_20260710_120000.txt")) == "Local"


def test_persisted_channel_without_logfile_stays_active(tmp_path: Path):
    chat = tmp_path / "Chatlogs"
    chat.mkdir()
    (chat / "ChannelA_20260710_120000.txt").write_text("x", encoding="utf-8")
    catalog = build_channel_catalog(
        chatlog_dir=chat,
        active_channels={"ChannelA", "ChannelB"},
        hidden_tab_ids=set(),
        tab_order=["__ALL_CHANNELS__", "ChannelA", "ChannelB"],
    )
    assert catalog["ChannelA"]["status"] == "tracking"
    assert catalog["ChannelB"]["status"] == "tracking, waiting for log"
    assert catalog["ChannelB"]["active"] is True
    summary = catalog_summary(catalog)
    assert summary["tracking"] == 2
    assert summary["waiting"] == 1


def test_discovery_only_when_no_persist(tmp_path: Path):
    chat = tmp_path / "Chatlogs"
    chat.mkdir()
    (chat / "Fleet_20260710_120000.txt").write_text("x", encoding="utf-8")
    discovered = discover_channel_metadata(chat)
    assert "Fleet" in discovered
    catalog = build_channel_catalog(
        chatlog_dir=chat,
        active_channels=set(),
        hidden_tab_ids=set(),
        tab_order=["__ALL_CHANNELS__"],
        discovered=discovered,
    )
    assert catalog["Fleet"]["status"] == "discovered"
