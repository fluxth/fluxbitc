# fluxbitc

A burn-in timecode and video conversion utility for film post-production proxy makers

## Features

- Configurable burn-in timecode styling in `config.json`
- Included preset for the "hurry" users
- Extensible, create your own preset and save it for later uses
- Video converter/encoder built in, powered by the ffmpeg library (defaults to ProRes 422)
- Automatic framerate detection, overridable
- You can easily set your own timecode start and frame count start
- Automatically burn-in information from metadata of the file (color space, resolution, framerates) without human input
- Ability to discard or convert embedded audio to other codecs (see examples)
- Scale your media up/down to 1920x1080 or 1280x720 for easier handling in post-production [To be implemented]

## Dependencies

- python3
- ffmpeg
- ffprobe

On macOS, run
```bash
./install.sh
```
in your terminal to automatically install the required dependencies.

## Examples

To burn-in timecode using the default preset, use:
```bash
./fluxbitc.py -i input.mp4 output.mov
```

![Default Preset](https://raw.githubusercontent.com/fluxTH/fluxbitc/main/docs/screenshot_default.png)

To add additional info along with the timecode, use:
```bash
./fluxbitc.py -i input.mp4 output.mov --data timecode_start=00:59:52:00 heading_title="My new film" heading_sub="FOR SOUND ONLY"
```

![Default Preset Customized](https://raw.githubusercontent.com/fluxTH/fluxbitc/main/docs/screenshot_default_custom.png)

fluxbitc also has a `verbose` preset, to activate it, use:
```bash
./fluxbitc.py -p verbose -i input.mp4 output.mov
```

![Verbose Preset](https://raw.githubusercontent.com/fluxTH/fluxbitc/main/docs/screenshot_verbose.png)

All the settings are customizable, too!
```bash
./fluxbitc.py -p verbose -i input.mp4 output.mov \
    --data timecode_start=00:59:52:00 frame_start=740 \
           heading_title="My new film" heading_sub="Final Draft v9" \
           info_1="property of some studio" info_2="note: definitely not color graded"
```

![Verbose Preset Customized](https://raw.githubusercontent.com/fluxTH/fluxbitc/main/docs/screenshot_verbose_custom.png)

To encode the output file to a different video and audio codec, use:
```bash
./fluxbitc.py -i input.mp4 -vc hevc_videotoolbox -vb 5M -ac aac_at -ab 128k output.mov
```

To discard the audio completely, use:
```bash
./fluxbitc.py -i input.mp4 output.mov -ac off
```

To force an output file container format, use:
```bash
./fluxbitc.py -i input.mp4 output.ts --container mpegts
```

Feel free to play around! Consult the Usage section and the `config.json` file for more info :)

## Usage

For usage guide and help messages, use:
```bash
./fluxbitc -h
```

The usage guide should appear:
```
usage: fluxbitc.py [-h] -i FILENAME [-p PRESET] [-vc CODEC] [-vb BITRATE] [-vp PROFILE] [--scale {off,1080p,720p}] [-ac AUDIO_CODEC]
                   [-ab AUDIO_BITRATE] [-d DATA [DATA ...]] [--flags FLAGS [FLAGS ...]] [--container CONTAINER] [--config CONFIG] [-y]
                   output

fluxbitc burn-in timecode and video conversion utility

positional arguments:
  output                output filename

optional arguments:
  -h, --help            show this help message and exit
  -i FILENAME           input filename
  -p PRESET, --preset PRESET
                        processing preset name (default: default)
  -vc CODEC, --codec CODEC
                        output video codec (default: prores_ks)
  -vb BITRATE, --bitrate BITRATE
                        output video bitrate (default: auto)
  -vp PROFILE, --profile PROFILE
                        output video profile
  --scale {off,1080p,720p}
                        scale the video to one of the predefined standard (default: off)
  -ac AUDIO_CODEC, --audio-codec AUDIO_CODEC
                        output audio codec (default: auto)
  -ab AUDIO_BITRATE, --audio-bitrate AUDIO_BITRATE
                        output audio bitrate (default: auto)
  -d DATA [DATA ...], --data DATA [DATA ...]
                        custom user data in KEY=VALUE format
  --flags FLAGS [FLAGS ...]
                        additional ffmpeg flags
  --container CONTAINER
                        output container format (default: auto)
  --config CONFIG       config filename (default: config.json)
  -y                    override existing file check, will replace output file without asking!
```

-----

© 2020 fluxth. Released under the GNU GPL v3.
