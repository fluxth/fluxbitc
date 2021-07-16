#!/usr/bin/env python3
import json
import codecs
import os.path
import argparse
import sys
import subprocess
import datetime

from typing import Dict, List, Union, Any, Optional


class Config:
    filepath: str
    data: Dict[str, dict]

    def __init__(self, filepath: str):
        if not os.path.exists(filepath):
            raise BitcException(f"Config file '{filepath}' does not exist")

        self.filepath = filepath
        with codecs.open(filepath, "r", "utf-8") as f:
            self.data = json.load(f)

        self.init_fonts()

        # _userdata is to be replaced when ${} is seen
        self.data["_userdata"] = {}

    def __getitem__(self, key: str):
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        item = self.data
        for k in key.split("."):
            if item is None or type(item) is not dict:
                return default
            item = item.get(k, default)

        return item

    def hydrate_userdata(self, data: Union[None, List[str], Dict[str, str]]):
        if data is None:
            return

        if type(data) is list:
            for item in data:
                parts = item.split("=")
                if len(parts) != 2:
                    raise BitcException(f"Badly formatted data entry '{item}'")

                self.data["_userdata"][parts[0]] = parts[1]

        elif type(data) is dict:
            self.data["_userdata"].update(data)

    def init_fonts(self):
        if "fonts" in self.data and "colors" in self.data:
            for data in self.data["fonts"].values():
                if (
                    "fontcolor" in data
                    and data["fontcolor"] in self.data["colors"].keys()
                ):
                    data["fontcolor"] = self.data["colors"][data["fontcolor"]]


def main() -> int:
    args = init_arg_parser().parse_args()
    config = Config(args.config)

    input_filepath = os.path.abspath(args.i)
    output_filepath = os.path.abspath(args.output)

    if not os.path.exists(input_filepath):
        raise BitcException(f"Input file '{input_filepath}' does not exist")

    metadata = probe_media(config, input_filepath)
    format = metadata["format"]

    video_stream: Optional[dict] = None
    audio_stream: Optional[dict] = None

    # select first stream
    # TODO: Add option to select stream from media file
    for stream in metadata.get("streams"):
        if video_stream is None and stream["codec_type"] == "video":
            video_stream = stream
            continue

        if audio_stream is None and stream["codec_type"] == "audio":
            audio_stream = stream
            continue

    if video_stream is None:
        raise BitcException(
            f"Input file '{input_filepath}' does not have any video streams"
        )

    # hydrate from metadata first
    config.hydrate_userdata(
        build_userdata_from_metadata(
            os.path.basename(output_filepath), video_stream, audio_stream, format
        )
    )

    # then hydrate from user provided data arg
    config.hydrate_userdata(args.data)

    command = build_ffmpeg_command(
        config,
        args,
        input_filepath,
        output_filepath,
        video_stream,
        audio_stream,
        format,
    )

    if command is None:
        raise BitcException("There was an error while generating the encode command")

    print("Encode starting...")
    result = subprocess.run(command, stderr=subprocess.STDOUT)
    if result.returncode == 0:
        print(
            f"Encode succeeded, your new file has been created at '{output_filepath}'"
        )
        return 0
    else:
        print("Encode FAILED!", file=sys.stderr)
        return result.returncode


def init_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="fluxbitc burn-in timecode and video conversion utility"
    )

    parser.add_argument(
        "-i", type=str, metavar="FILENAME", help="input filename", required=True
    )

    parser.add_argument(
        "-p",
        "--preset",
        help="processing preset name (default: default)",
        default="default",
    )
    parser.add_argument(
        "-vc",
        "--codec",
        help="output video codec (default: prores_ks)",
        default="prores_ks",
    )
    parser.add_argument(
        "-vb", "--bitrate", help="output video bitrate (default: auto)", default="auto"
    )
    parser.add_argument("-vp", "--profile", help="output video profile")
    parser.add_argument(
        "--scale",
        choices=("off", "1080p", "720p"),
        default="off",
        help="scale the video to one of the predefined standard (default: off)",
    )

    parser.add_argument(
        "-ac",
        "--audio-codec",
        help="output audio codec (default: auto)",
        default="auto",
    )
    parser.add_argument(
        "-ab",
        "--audio-bitrate",
        help="output audio bitrate (default: auto)",
        default="auto",
    )

    parser.add_argument(
        "-d", "--data", help="custom user data in KEY=VALUE format", nargs="+"
    )
    parser.add_argument("--flags", nargs="+", help="additional ffmpeg flags")

    parser.add_argument(
        "--container", help="output container format (default: auto)", default="auto"
    )

    parser.add_argument(
        "--config",
        help="config filename (default: config.json)",
        default="config.json",
    )

    parser.add_argument(
        "-y",
        action="store_true",
        help="override existing file check, will replace output file without asking!",
    )

    parser.add_argument("output", help="output filename")

    return parser


def probe_media(config: Config, filename: str) -> Dict[str, Any]:
    ffprobe = config.get("path.ffprobe", "ffprobe")
    if ffprobe is None:
        return {}

    # fmt: off
    result = subprocess.run(
        [
            str(ffprobe),
            "-hide_banner",
            "-show_format",
            "-show_streams",
            "-of", "json",
            "-loglevel", "quiet",
            filename,
        ],
        stdout=subprocess.PIPE,
    )
    # fmt: on

    return json.loads(result.stdout)


def build_userdata_from_metadata(
    output_filename: str,
    video_stream: Dict[str, Any],
    audio_stream: Optional[Dict[str, Any]],
    format: Dict[str, Any],
) -> Dict[str, str]:

    fps_rate = video_stream["avg_frame_rate"]
    if fps_rate != video_stream["r_frame_rate"]:
        raise BitcException("Variable framerate video streams are not supported")

    timestamp = datetime.datetime.utcnow().isoformat()

    fps = fps_rate
    if "/" in fps:
        fps_n, fps_d = fps.split("/")
        fps = float(fps_n) / float(fps_d)
        fps = round(fps, 3)
    else:
        fps = int(fps)

    info_1 = f"{video_stream['width']}x{video_stream['height']}, {fps} FPS"

    color_info = video_stream.get("color_range", "")
    if color_info != "":
        color_info += ", "

    info_2 = f"{video_stream['codec_name']}, {color_info}{video_stream['pix_fmt']}"

    return {
        "frame_start": "0",
        "timecode_start": "01:00:00:00",
        "fps_rate": fps_rate,
        "heading_title": output_filename,
        "heading_sub": timestamp.split(".")[0] + "Z",
        "info_1": info_1,
        "info_2": info_2,
    }


def build_ffmpeg_command(
    config: Config,
    args: argparse.Namespace,
    input_filepath: str,
    output_filepath: str,
    video_stream: Dict[str, Any],
    audio_stream: Optional[Dict[str, Any]],
    format_metadata: Dict[str, Any],
) -> Optional[List[str]]:

    ffmpeg = config.get("path.ffmpeg", "ffmpeg")
    if ffmpeg is None:
        return None

    cmd = [ffmpeg, "-hide_banner", "-loglevel", "warning", "-stats"]

    # input file
    cmd += ["-i", input_filepath]

    # video stream processing
    cmd += ["-map", f"0:{video_stream['index']}"]
    cmd += ["-c:v", args.codec]

    if not args.bitrate == "auto":
        cmd += ["-b:v", args.bitrate]

    if args.profile is not None:
        cmd += ["-profile:v", args.profile]

    # TODO: add scaling filters
    if args.scale != "off":
        raise BitcException("Scaling feature is not yet implemented")

    cmd += build_overlay_flags(
        args.preset, config, args.data, video_stream, format_metadata
    )

    # audio stream processing
    if args.audio_codec != "off" and audio_stream is not None:
        cmd += ["-map", f"0:{audio_stream['index']}"]
        if args.audio_codec != "auto":
            cmd += ["-c:a", args.audio_codec]

        if args.audio_bitrate != "auto":
            cmd += ["-b:a", args.audio_bitrate]

    else:
        cmd.append("-an")

    # additional flags
    if args.flags is not None:
        cmd += " ".join(args.flags).split(" ")

    # container format
    if args.container != "auto":
        cmd += ["-f", args.container]

    # override output checl
    if args.y is True:
        cmd.append("-y")

    # output file
    cmd.append(output_filepath)

    return cmd


def build_overlay_flags(
    preset_name: str,
    config: Config,
    data: List[str],
    video_stream: Dict[str, Any],
    format_metadata: Dict[str, Any],
) -> List[str]:

    if preset_name not in config.get("presets", {}).keys():
        raise BitcException(
            f"Definition of preset '{preset_name}' does not exist in the config file"
        )

    preset = config["presets"][preset_name]
    drawtexts = []

    if "items" not in preset.keys():
        raise BitcException(
            f"Definition of preset '{preset_name}' does not have the `items` key"
        )

    userdata = config.get("_userdata", {})
    fonts = config.get("fonts", {})

    for item in preset["items"]:
        filters = []
        for k, v in item.items():
            v = str(v)

            if k == "font":
                if v in fonts.keys():
                    for fk, fv in fonts[v].items():
                        filters.append(f"{fk}={fv}")

            # Replace ${} with userdata
            for uk, uv in userdata.items():
                target = "${" + uk + "}"
                if target in v:
                    v = v.replace(target, uv)

            # escape : and , in vf
            v = v.replace(":", "\\:")
            v = v.replace(",", "\\,")

            if k == "text" or k == "timecode":
                filters.append(f"{k}='{v}'")
            else:
                filters.append(f"{k}={v}")

        drawtexts.append(":".join(filters))

    return ["-vf", ",".join([f"drawtext={c}" for c in drawtexts])]


class BitcException(Exception):
    pass


if __name__ == "__main__":
    try:
        exit(main())
    except BitcException as e:
        print("ERROR: " + str(e), file=sys.stderr)
        exit(1)
