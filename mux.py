#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import tomllib
import shutil
from ass import Comment
from pathlib import Path

from muxtools import (
    Setup,
    GlobSearch,
    Premux,
    SubFile,
    Chapters,
    ShiftMode,
    ASSHeader,
    mux,
    TmdbConfig,
)
from muxtools.utils.log import debug, error, info, warn, log_escape


def ensure_muxtools_installed():
    try:
        import muxtools  # noqa: F401
    except ImportError:
        print("The 'muxtools' package is not installed.")
        print("Please install it with:")
        print("    pip install muxtools")
        sys.exit(1)


def get_project_path():
    if len(sys.argv) < 2:
        print(
            "Usage: python mux.py <project_path>\nExample: python mux.py franchise/show"
        )
        sys.exit(1)

    project_path = Path(sys.argv[1])
    if not project_path.exists():
        print(f"Project path not found: {project_path}")
        sys.exit(1)

    config_file = project_path / "config.toml"
    if not config_file.exists():
        print(f"No config.toml found in: {project_path}")
        sys.exit(1)

    return project_path.resolve(), config_file


PROJECT_DIR, CONFIG_PATH = get_project_path()


def parse_episodes(value):
    """
    Accepts:
      - episodes = "1...4"  → range inclusive
      - episodes = 1        → single episode
      - episodes = [1, 2, 3] → list
    Returns: list[int]
    """
    if isinstance(value, list):
        return [int(x) for x in value]
    elif isinstance(value, int):
        return [value]
    elif isinstance(value, str) and "..." in value:
        try:
            start, end = value.split("...")
            return list(range(int(start), int(end) + 1))
        except Exception as e:
            raise ValueError(f"Invalid episodes range: {value}") from e
    else:
        raise ValueError(f"Invalid 'episodes' format: {value!r}")


def load_config(cfg_path: Path):
    with open(cfg_path, "rb") as f:
        data = tomllib.load(f)

    width, height = data["resolution"]
    data["video_resolution"] = f"{height}p"

    def resolve_path(key):
        if key in data:
            data[key] = (PROJECT_DIR / Path(data[key])).resolve()

    for path_key in ("episodes_path", "extras_path", "output_path"):
        resolve_path(path_key)

    data["episodes"] = parse_episodes(data["episodes"])

    return data


CONFIG = load_config(CONFIG_PATH)


def validate_paths():
    episodes_path = CONFIG["episodes_path"]
    extras_path = CONFIG.get("extras_path")
    extras_cfg = CONFIG.get("extras", {})

    if not episodes_path.exists():
        error(f"Episodes path not found: {episodes_path}")
        sys.exit(1)

    if extras_cfg and extras_path and not extras_path.exists():
        error(f"Extras path not found: {extras_path}")
        sys.exit(1)


def parse_extras_merge_config():
    """
    Reads [extras.merge."1-14"] style configuration blocks.
    """
    extras_cfg = CONFIG.get("extras", {})
    merge_cfg = extras_cfg.get("merge", {})
    merge_rules = []

    for key, entries in merge_cfg.items():
        try:
            start, end = map(int, key.split("-"))
        except ValueError:
            raise ValueError(f"Invalid merge range '{key}' in extras.merge block")

        files = {fname: (meta["from"], meta["to"]) for fname, meta in entries.items()}
        merge_rules.append((start, end, files))

    return merge_rules


MERGE_RULES = parse_extras_merge_config()


def get_merge_files_for_episode(ep: int):
    for start, end, files in MERGE_RULES:
        if start <= ep <= end:
            base_path = CONFIG["extras_path"]
            return {base_path / f: pair for f, pair in files.items()}
    return {}


def configure_subtitles(sub: SubFile):
    width, height = CONFIG["resolution"]
    sub.clean_garbage().clean_extradata().set_headers(
        (ASSHeader.PlayResX, width),
        (ASSHeader.PlayResY, height),
        (ASSHeader.LayoutResX, width),
        (ASSHeader.LayoutResY, height),
        (ASSHeader.YCbCr_Matrix, CONFIG["ycbcr_matrix"]),
        (ASSHeader.ScaledBorderAndShadow, True),
        (ASSHeader.WrapStyle, 0),
        ("Title", CONFIG["fansub_group"]),
    )


def process_episode(ep: int):
    info("=" * 70)
    info(f"Processing episode {ep:02d}")

    setup = Setup(
        f"{ep:02d}",
        config_file="",
        show_name=CONFIG["show_name"],
        out_name=rf"[{CONFIG['fansub_group']}] $show$ - $ep$ [{CONFIG['video_resolution']}] [{CONFIG['video_source']}] [$crc32$]",
        mkv_title_naming=R"$show$ - $ep$ - $title$",
        out_dir=str(CONFIG["output_path"]),
        clean_work_dirs=True,
        error_on_danger=True,
        work_dir=str(PROJECT_DIR / "_workdir"),
    )

    episode_dir = CONFIG["episodes_path"] / setup.episode
    video_file = GlobSearch("*.mkv", dir=str(episode_dir))
    setup.set_default_sub_timesource(video_file)

    premux = Premux(
        video_file,
        subtitles=None,
        keep_attachments=False,
        mkvmerge_args=[
            "--no-global-tags",
            "--no-chapters",
            "--language",
            f"1:{CONFIG['audio_lang_code']}",
        ],
    )

    subtitle = SubFile(GlobSearch("*.ass", allow_multiple=True, dir=str(episode_dir)))
    chapters = Chapters.from_sub(subtitle, use_actor_field=True)

    merge_files = get_merge_files_for_episode(ep)
    if merge_files:
        for path, (from_marker, to_marker) in merge_files.items():
            debug(f"Merging extra {path.name}: {from_marker} → {to_marker}")
            subtitle.merge(
                str(path),
                from_marker,
                to_marker,
                no_error=True,
                shift_mode=ShiftMode.FRAME,
            )
    else:
        debug(f"No extra merges for episode {ep:02d}")

    # Add credits from config.toml to the subtitle file before further processing
    add_credits(
        subtitle,
        CONFIG.get("fansub_group", ""),
        CONFIG.get("translation", ""),
        CONFIG.get("editing", ""),
        CONFIG.get("translation_checking", ""),
        CONFIG.get("timing", ""),
        CONFIG.get("typesetting", ""),
        CONFIG.get("quality_checking", ""),
    )

    configure_subtitles(subtitle)
    fonts = subtitle.collect_fonts(use_system_fonts=True)
    debug(f"Collected {len(fonts)} fonts")

    subtitle = subtitle.clean_comments().clean_garbage()

    mux(
        premux,
        subtitle.to_track(CONFIG["sub_language"], CONFIG["sub_lang_code"]),
        *fonts,
        chapters,
        tmdb=TmdbConfig(CONFIG["tmdb_id"]),
    )

    info(f"Episode {ep:02d} muxed successfully.\n")


def add_credits(
    sub: SubFile,
    fansub: str,
    translator: str,
    editing: str,
    tc: str,
    timing: str,
    ts: str,
    qc: str,
):
    # Note: Script, Translation, Editing, and Timing will be displayed in Aegisub's properties window.
    credits = [
        ("Script", fansub),
        ("Translation", translator),
        ("Editing", editing),
        ("Translation Checking", tc),
        ("Timing", timing),
        ("Typesetting", ts),
        ("Quality Checking", qc),
    ]

    for credit in reversed(credits):
        sub.manipulate_lines(
            lambda lines: lines.insert(0, Comment(text=f"{credit[0]}: {credit[1]}"))
        )
    for credit in credits:
        sub.set_header(f"Original {credit[0]}", credit[1])


def main():
    validate_paths()

    info("=" * 70)
    info(f"Starting mux for {CONFIG['show_name']}")
    info(
        f"Audio: {CONFIG['audio_language']} | Subtitles: {CONFIG['sub_language']} ({CONFIG['sub_lang_code']})"
    )
    info(
        f"Resolution: {CONFIG['resolution'][0]}x{CONFIG['resolution'][1]} ({CONFIG['video_resolution']}) | YCbCr: {CONFIG['ycbcr_matrix']}"
    )
    info(f"Episodes: {CONFIG['episodes']}")
    info(
        f"Paths - Episodes: {CONFIG['episodes_path']} | Extras: {CONFIG['extras_path']} | Output: {CONFIG['output_path']}"
    )
    info("Beginning batch processing...\n")

    for ep in CONFIG["episodes"]:
        try:
            process_episode(ep)
        except Exception as e:
            error(f"Error processing episode {ep:02d}: {e}")

    work_dir = PROJECT_DIR / "_workdir"
    if work_dir.exists():
        shutil.rmtree(work_dir)
        info("Work directory removed successfully.")

    info("=" * 70)
    info("All episodes processed successfully.")


if __name__ == "__main__":
    main()
