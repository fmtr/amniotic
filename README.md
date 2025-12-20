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

![Dashboard Screenshot](https://fmtr.link/amniotic/doc/dashboard/screenshot)

# Documentation

[See Documentation](https://fmtr.link/amniotic/doc)
