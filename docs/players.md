## Media Player Entities

Amniotic principally streams audio to Media Players Entities controlled by Home Assistant.

!!! info

    Your media player needs to support streaming from a basic HTTP stream, which most should.

### Do I need a fancy Sonos-type Speaker? Can't I just use a Raspberry Pi, etc?

You can use basically any device you can expose to Home Assistant as a Media Player entity. For something like a Raspberry Pi, for example:

- In Home Assistant, install the [VLC Telnet integration](https://www.home-assistant.io/integrations/vlc_telnet).
- On your Device, install VLC, and start it in telnet mode, e.g.
  `vlc -I telnet --telnet-password password --telnet-host 0.0.0.0:4212`
- Add your device to the VLC Telnet integration.
- Restart Amniotic, and you should see your new device in the Amniotic Media Player pull-down.

## Manual Streams

Ultimately, though, Amniotic just exposes your Themes as regular HTTP/MP3 streams, so you can use any player that supports that. For this purpose, Amniotic exposes the "Stream URL" control (see Dashboard). You can paste this URL to into any player whatsoever, including a desktop browser, phone, etc.