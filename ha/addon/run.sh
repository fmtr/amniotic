#!/usr/bin/with-contenv bashio

export AMNIOTIC_IS_ADDON=true
export AMNIOTIC_CONFIG_PATH="/data/options.json"
export AMNIOTIC_MQTT_HOST="$(bashio::services mqtt 'host')"
export AMNIOTIC_MQTT_PASSWORD="$(bashio::services mqtt 'password')"
export AMNIOTIC_MQTT_PORT="$(bashio::services mqtt 'port')"
export AMNIOTIC_MQTT_USERNAME="$(bashio::services mqtt 'username')"
export AMNIOTIC_PATH_AUDIO="/media/$(bashio::config 'audio_subdirectory')"

amniotic