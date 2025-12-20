This section covers installing Amniotic outside of Home Assistant (i.e. on a separate, dedicated machine, a desktop PC,
etc.)

# Hardware

Any vaguely suitable device (i.e. with a network connection and audio outputs) should work, but it was primarily
intended for (and developed on) a dedicated Raspberry Pi 4B. The lowest spec I've tested on is a Pi Zero W 1, which
works fine but struggled playing more than one Theme at a time. And obviously you'll have better results with better
audio equipment (amps, speakers, etc.), especially for lower-frequency themes.

# Platform

Raspbian/Debian are best tested and covered here. But for other platforms etc., see
the [Other Platforms](#other-platforms) section.

# Installing  on Raspberry Pi (Linux)

To install on Raspbian, or any Debian Linux etc., first install dependencies, then the Amniotic package:

```console
sudo apt update -y
sudo apt install -y python3-pip pulseaudio vlc
pip3 install amniotic
```

Once done, you should find `amnitoic` installed in  `~/.local/bin/amniotic`

# Config File

You will need to add a config file at the path `~/.config/amniotic/config.yml`. It's primarily for adding your MQTT
credentials. A commented example file that you can modify is [
`config.example.yml`](https://github.com/fmtr/amniotic/blob/main/config.example.yml).

# Default Audio Directory

This can be set in the Config File, as above, but by default it's the following path: `~/.local/share/amniotic`

# Running

You should now simply be able to run `~/.local/bin/amniotic`, which will connect to MQTT:

```console
2022-05-20 15:14:51 INFO  amniotic.mqtt    : Amniotic 0.0.1 has started.
2022-05-20 15:14:51 INFO  amniotic.mqtt    : Amniotic 0.0.1 starting MQTT...
2022-05-20 15:14:51 INFO  amniotic.mqtt    : Attempting to connect to MQTT "homeassistant.local:1883": Connection successful
```

# Installing as a Service

Since a dedicated Amniotic device (e.g. a Pi) functions like an appliance, you might want to install as a service, so
that restarts, running on boot etc., are handled automatically.

- Ensure the current user has session lingering enabled, to allow long-running services: `loginctl enable-linger $USER`.
- Copy the service unit file [`amniotic.service`](https://github.com/fmtr/amniotic/blob/main/amniotic.service) to
  `~/.config/systemd/user/amniotic.service`
- Enable the service: `systemctl --user enable amniotic.service`. The service should now start automatically on each
  boot.
- If you want to start immediately: `systemctl --user start amniotic.service`
- And to stop: `systemctl --user stop amniotic.service`
- To view service logs: `journalctl --user --unit amniotic.service`

Installing on **macOS** using `brew` will look (roughly) like this:

```console
brew install python3
brew install --cask vlc
pip3 install amniotic
```

# Updating

Amniotic also exposes its updater to Home Assistant, so newer versions can be installed from there. Updating
will restart automatically and the device will reappear running the latest version, so all quite seamless.

<figure><img src="assets/ha-updater.png" width="280"/></figure>

To update manually, enter:

`pip install amniotic --upgrade`