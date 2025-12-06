# Amniotic

A multi-output ambient sound mixer for Home Assistant.

Amniotic lets you use a single device to create on-the-fly, custom ambient audio mixes - e.g. mixing Waterfall sounds with Birdsong on one media player entity, while playing Fireplace sounds from a second audio device - to suit your tastes and environment.

The library integrates with Home Assistant via MQTT as a new device, allowing you to create and control ambient mixes from the Home Assistant interface.

### Why Would I Want Such a Thing?

I won't explain the general reasons for introducing non-musical sounds into one's environment, but if you find [sound masking](https://en.wikipedia.org/wiki/Sound_masking) helps you concentrate in noisy environments, if you're (as I am) slightly [misophonic](https://www.webmd.com/mental-health/what-is-misophonia), if you use [white noise machines](https://en.wikipedia.org/wiki/White_noise_machine) to induce sleep or relaxation, or if you just think sound is an important factor in setting a pleasant ambience, then you might find Amniotic useful.

### Can't I do This with Spotify, Volumio, HifiBerry etc.?

Since those systems are intended for music, they aren't designed for playing or mixing multiple streams simultaneously with a single device, even if set up in multi-room configurations. Also, the streaming services often won't allow a single account to play multiple streams, even
_if_ multiple devices are used.

Anyway, those limitations motivated this library.

There are two ways to install and run Amniotic:

- On the Home Assistant machine itself, as an add-on.
- Install manually, on a separate machine.

## Home Assistant Addon

To add as an Addon, click here:

[![Open your Home Assistant instance and show the add add-on repository dialog with the repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://fmtr.link/amniotic/addon-install)

## Dashboard

[Lovelace Dashboard](https://fmtr.link/amniotic/doc/dashboard)

![Dashboard Screenshot](https://fmtr.link/amniotic/doc/dashboard/screenshot)

## Getting Started

Better documentation is coming soon. Currently, the easiest workflow is the following:

- Install as an Addon, using the button above.
- If you're using a non-default address for Home Assistant on your network (i.e. not
  `homeassistant.local`), set that in the Addon configuration.
- Add some audio files to the Home Assistant
  `/media/Amniotic` directory. Note: currently, you'll need to restart the Addon for it to see new files.
- Add the Dashboard to Lovelace.
- Select a Default Theme from A or B. Note: Adding your own themes isn't implemented yet, nor will they be saved between restarts.
- Select a Recording from the dropdown.
- Toggle to Enable the Recording.
- Select a Media Player to stream the Theme to. Note: Your media player needs to support streaming from a basic HTTP stream, which most should.
- Click Stream to Media Player.
- Your Theme should start playing on your Media Player.
- You can now Enable additional Recordings in the Theme, modify their volume, etc., to create a custom mix.
- Note: there's also a Current Theme URL, for if you want to manually paste stream to a non-HA player, like a phone or something.

## Do I need a Sonos Speaker? Can't I just use a Raspberry Pi, etc?

- You can use basically any device with audio hardware. You just need to allow Home Assistant to see it as a Media Player entity.
- In Home Assistant, install the https://www.home-assistant.io/integrations/vlc_telnet
- On your Device, install VLC, and start it in telnet mode, e.g.
  `vlc -I telnet --telnet-password password --telnet-host 0.0.0.0:4212`
- Add your VLC server to the integration.
