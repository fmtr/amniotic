Amniotic requires MQTT.

## Add-On

If you don't already have MQTT set up, it's easy to install the official Home Assistant Add-On. Full instructions are [here](https://www.home-assistant.io/integrations/mqtt/).

## Custom MQTT Broker

If you're running a custom MQTT broker, you probably don't need extra instructions. Just ensure you provide your MQTT details in the Add-On configuration, if that's how you're running it - or otherwise via your [Docker Compose](docker.md) file or via CLI arguments etc.