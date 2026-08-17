"""Unit tests for configuration loading and validation."""
import textwrap
from pathlib import Path

import pytest
import yaml

from correlator.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "cfg.yaml"
    path.write_text(textwrap.dedent(body))
    return path


class TestRoundTrip:

    def test_to_yaml_then_from_yaml_preserves_settings(self, tmp_path):
        original = Config(n_ants=8, n_channels=512, window="blackman",
                          duration=2.5, output_format="npy")
        path = tmp_path / "out.yaml"
        original.to_yaml(path)

        assert Config.from_yaml(path) == original


class TestUnknownKeys:
    """Unknown keys must fail loudly.

    They used to be filtered out silently. A stale file, such as the shipped
    configs written against an older schema, then produced a run at default
    settings that looked entirely successful.
    """

    def test_unknown_key_is_rejected(self, tmp_path):
        path = write(tmp_path, """
            n_ants: 4
            window_type: hanning
        """)
        with pytest.raises(ValueError, match="unknown setting"):
            Config.from_yaml(path)

    def test_error_names_every_offending_key(self, tmp_path):
        path = write(tmp_path, """
            n_ants: 4
            enable_rfi_detection: true
            quantize_bits: 8
        """)
        with pytest.raises(ValueError) as exc:
            Config.from_yaml(path)
        assert "enable_rfi_detection" in str(exc.value)
        assert "quantize_bits" in str(exc.value)

    def test_valid_keys_are_accepted(self, tmp_path):
        path = write(tmp_path, """
            n_ants: 6
            n_channels: 128
            window: hamming
        """)
        cfg = Config.from_yaml(path)
        assert (cfg.n_ants, cfg.n_channels, cfg.window) == (6, 128, "hamming")

    def test_empty_file_gives_defaults(self, tmp_path):
        assert Config.from_yaml(write(tmp_path, "")) == Config()

    def test_non_mapping_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="expected a mapping"):
            Config.from_yaml(write(tmp_path, "- 1\n- 2\n"))


class TestLoadValidates:
    """A file that parses but describes an impossible run must not load."""

    @pytest.mark.parametrize("body,match", [
        ("n_ants: 1", "n_ants"),
        ("n_channels: 100", "power of 2"),
        ("window: gaussian", "window must be"),
        ("mode: network", "mode must be"),
        ("mode: file", "input_file"),
        ("output_format: csv", "output_format"),
    ])
    def test_invalid_settings_are_rejected(self, tmp_path, body, match):
        with pytest.raises(ValueError, match=match):
            Config.from_yaml(write(tmp_path, body))


class TestShippedConfigs:
    """The configs in workspace/configs must actually load.

    They did not for a long time: every F-engine, delay and runtime key in
    them was silently discarded. This test is the reason that cannot recur.
    """

    @pytest.mark.parametrize("name", ["dev", "prod"])
    def test_shipped_config_loads(self, name):
        path = REPO_ROOT / "workspace" / "configs" / name / "default.yaml"
        if not path.exists():
            pytest.skip(f"{path} not present")

        cfg = Config.from_yaml(path)
        cfg.validate()

        # Every key in the file must be a real setting, not just the ones
        # that happen to survive.
        keys = set(yaml.safe_load(path.read_text()) or {})
        assert keys <= set(Config.__dataclass_fields__)
        assert keys, "config file has no settings at all"
