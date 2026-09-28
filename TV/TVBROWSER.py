#!/usr/bin/env python3

"""Start een tv-zender in Firefox en wacht tot de browser gesloten is.

TV.py start dit script als kindproces en verbergt ondertussen zijn menu. Dit
script blijft actief zolang Firefox actief is. Wanneer de gebruiker Firefox
sluit, eindigt dit script en kan TV.py het zenderkeuzemenu opnieuw tonen.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from collections.abc import Sequence
import time

PROGRAM_URLS = {
    "vrt": "https://www.vrt.be/vrtmax/livestream/video/vrt1/",
    "canvas": "https://www.vrt.be/vrtmax/livestream/video/canvas/",
    "ketnet": "https://www.vrt.be/vrtmax/livestream/video/ketnet/",
    "ketnetjr": "https://www.vrt.be/vrtmax/livestream/video/ketnet-jr/",
    "sporza":"https://sporza.be/nl/",
    "vtm": "https://www.vtmgo.be/vtmgo/live-kijken/vtm",
    "play": "https://www.play.tv/live-kijken/play",
    "focus": "https://focus-wtv.be/tv-zone",
    "netflix": "https://www.netflix.com/",
    "q-music": "https://www.vtmgo.be/vtmgo/live-kijken/qmusic",
    "joe": "https://www.vtmgo.be/vtmgo/live-kijken/joe",
    "mnm": "https://www.vrt.be/vrtmax/livestream/audio/mnm/",
    "nostalgi": "https://www.play.tv/live-kijken/play-nostalgie",
    "stubru": "https://www.vrt.be/vrtmax/livestream/audio/studio-brussel/",
    "radio1": "https://www.vrt.be/vrtnu/livestream/audio/radio1",
    "radio2": "https://www.vrt.be/vrtnu/livestream/audio/radio2",
    "radio1classic": "https://www.vrt.be/vrtnu/livestream/audio/radio1classics/",
    "unwind": "https://www.vrt.be/vrtnu/livestream/audio/radio2unwind/",
    "klara": "https://www.vrt.be/vrtnu/livestream/audio/klara/",
    "klara-continuo": "https://www.vrt.be/vrtnu/livestream/audio/klaracontinuo/",
    "ketnethits": "https://www.vrt.be/vrtnu/livestream/audio/ketnethits/",
    "mnmhits": "https://www.vrt.be/vrtnu/livestream/audio/mnmhits/",
    "tijdloze": "https://www.vrt.be/vrtnu/livestream/audio/tijdloze/",
    "stubru-vuurland": "https://www.vrt.be/vrtnu/livestream/audio/vuurland/",
    "stubru-untz": "https://www.vrt.be/vrtnu/livestream/audio/untz/",
    "radio2-benebene": "https://www.vrt.be/vrtnu/livestream/audio/radio2benebene/",
    "watchseries": "https://watchseries.bar/home",
    "plex": "https://watch.plex.tv/nl",
    "youtube": "https://www.youtube.com",
    "bingebang": "https://bingebang.tv/",
    "movienerds": "https://movienerds.site/",
    "flickbuff": "https://flickbuff.cc/",
    "zenox": "https://zenox.lol",
    "shiopa":"https://shiopa.com/",
    "zoechip":"https://zoechip.bz/",
    "flystream":"https://flystream.net/",
    "pstream":"https://pstream.cfd/",
    "allflix":"https://allflix.org/",
    "dazn":"https://www.dazn.com/en-BE/home",
    "redbulltv":"https://www.redbull.tv/en_US",
    "uefa":"https://www.uefa.tv/home",
    "eurovisionsport": "https://eurovisionsport.com/en",
    "fifaplus": "https://www.plus.fifa.com/en/",
    "olympics": "https://olympics.com/en/live-events/",
    "rtlplay": "https://www.rtlplay.be/rtlplay/direct",
    "rtbfauvio": "https://auvio.rtbf.be/direct",
    "radioplayer": "https://www.radioplayer.be/",
    "nasa": "https://plus.nasa.gov/",
    "euronews": "https://www.euronews.com/live",
    "france24": "https://www.france24.com/en/live",
    "arte": "https://www.arte.tv/en",
    "worldathleticsr": "https://worldathletics.org/videos",
    "tvmonde": "https://www.tv5mondeplus.com/"
}


def firefox_command(url: str) -> list[str]:
    """Bouw de Firefox-opdracht voor een afzonderlijk kioskvenster."""

    executable = os.environ.get("TV_FIREFOX_EXECUTABLE", "firefox").strip()
    if not executable:
        executable = "firefox"

    return [executable, "--new-instance", url]


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("Gebruik: TVBROWSER.py <zender>", file=sys.stderr)
        return 2

    program = arguments[0].strip().casefold()
    url = PROGRAM_URLS.get(program)
    if url is None:
        print(f"Onbekende zender: {arguments[0]}", file=sys.stderr)
        return 2

    command = firefox_command(url)


    try:
        browser_process = subprocess.Popen(command)
    except FileNotFoundError:
        print(
            f"Firefox werd niet gevonden: {command[0]}",
            file=sys.stderr,
        )
        return 127
    except OSError as error:
        print(f"Firefox kon niet starten: {error}", file=sys.stderr)
        return 1

    shutdown_requested = False
    time.sleep(3)
    subprocess.run(["xdotool","key", "F11"])
    def stop_browser(_signum: int, _frame: object) -> None:
        """Sluit ook Firefox wanneer TV.py dit launcherproces beëindigt."""

        nonlocal shutdown_requested
        shutdown_requested = True
        if browser_process.poll() is None:
            browser_process.terminate()

    signal.signal(signal.SIGTERM, stop_browser)
    signal.signal(signal.SIGINT, stop_browser)

    try:
        exit_code = browser_process.wait()
    except KeyboardInterrupt:
        stop_browser(signal.SIGINT, None)
        exit_code = browser_process.wait()

    # Een bewuste afsluiting vanuit TV.py is geen browserfout.
    return 0 if shutdown_requested else exit_code


if __name__ == "__main__":
    sys.exit(main())
