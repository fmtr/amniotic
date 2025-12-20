!!! note "What's a Recording?"
Recording just means a atomic, un-mixed piece of ambient audio content represented by a file on disk, like birdsong, white noise, etc. The name has been chosen to differentiate the ambient nature of the content from terms typically used by music-focused services like Spotify.

There are two ways to add Recordings to Amniotic:

- The easier way: Populate them with YouTube links, via the Home Assistant interface.
- The more manual way: Copy audio files (e.g. MP3) to audio folder directly.

!!! note "Why YouTube?"

    Originally I'd planned Spotify integration. But on the _very day_ I started to work on it, the `libspotify` [ API was closed down](https://developer.spotify.com/community/news/2022/04/12/libspotify-sunset/). Anyway, since I wanted some kind of cloud integration (so as not to strictly _require_ local files), and because YouTube contains a lot ambient audio content, I though that it would make for a decent solution, at least for the meantime.

## Adding Recordings Manually

### Addon via Media Browser

If you're running as a Home Assistant addon, you can simply use the Home Assistant Media Browser to add/modify Recordings.

[![Open your Home Assistant instance and browse available media.](https://my.home-assistant.io/badges/media_browser.svg)](https://my.home-assistant.io/redirect/media_browser/)

With the Media Browser open, navigate to "My media" -> "Amniotic".

### Directory Structure

The directory structure must be _flat_ - as Amniotic won't look in subfolders.

#### Example Directory Structure

- `/media/Amniotic`
    - `Birdsong - Wren at Dawn.mp3`
    - `Birdsong - Starling in Trees.mp3`
    - `Rainfall - Rain in forest.m4a`
    - `Rainfall - Downpour on tent.webm`
    - `Fireplace - Roaring wood stove (loopable).mp3`
    - ...

## Non-Addon

If you're not running as an addon, you'll need to manually copy audio files to whatever path on your host machine that you mapped into the container.

## Audio Formats

Since Amniotic uses the [Python FFMPEG bindings](https://pyav.org/docs/develop/overview/installation.html), it should support [any format FFMPEG does](https://ffmpeg.org/ffmpeg-formats.html) - but probably safest to stick to simple audio formats, MP3, M4A etc., which have been tested during development.