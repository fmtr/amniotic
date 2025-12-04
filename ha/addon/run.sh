#!/usr/bin/with-contenv bashio


export HOME_ASSISTANT_URL="http://supervisor"

export AMNIOTIC__MQTT__HOSTNAME="$(bashio::services mqtt 'host')"
export AMNIOTIC__MQTT__PORT="$(bashio::services mqtt 'port')"
export AMNIOTIC__MQTT__USERNAME="$(bashio::config 'username')"
export AMNIOTIC__MQTT__PASSWORD="$(bashio::services mqtt 'password')"




#export AMNIOTIC__MQTT__HOSTNAME="$(bashio::config 'amniotic__mqtt__hostname')"
#export AMNIOTIC__MQTT__PORT="$(bashio::config 'amniotic__mqtt__port')"
#export AMNIOTIC__MQTT__USERNAME="$(bashio::config 'amniotic__mqtt__username')"
#export AMNIOTIC__MQTT__PASSWORD="$(bashio::config 'amniotic__mqtt__password')"



export AMNIOTIC__STREAM_URL="$(bashio::config 'amniotic__stream_url')"
export AMNIOTIC__PATH_AUDIO="$(bashio::config 'amniotic__path_audio')"

/opt/dev/venv/amniotic/bin/amniotic
