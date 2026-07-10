from pathlib import Path


def test_build_script_writes_portable_one_line_checksum_files():
    script = (Path(__file__).resolve().parents[1] / "build_portable.ps1").read_text(encoding="utf-8")
    assert "Select-Object -ExpandProperty Hash" in script
    assert "Set-Content -NoNewline" in script
