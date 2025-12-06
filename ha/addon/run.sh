#!/usr/bin/with-contenv bashio


export HOME_ASSISTANT_URL="http://supervisor/core/api"

export AMNIOTIC__MQTT__HOSTNAME="$(bashio::services mqtt 'host')"
export AMNIOTIC__MQTT__PORT="$(bashio::services mqtt 'port' || echo 1883)"
export AMNIOTIC__MQTT__USERNAME="$(bashio::services mqtt 'username')"
export AMNIOTIC__MQTT__PASSWORD="$(bashio::services mqtt 'password')"




#export AMNIOTIC__MQTT__HOSTNAME="$(bashio::config 'amniotic__mqtt__hostname')"
#export AMNIOTIC__MQTT__PORT="$(bashio::config 'amniotic__mqtt__port')"
#export AMNIOTIC__MQTT__USERNAME="$(bashio::config 'amniotic__mqtt__username')"
#export AMNIOTIC__MQTT__PASSWORD="$(bashio::config 'amniotic__mqtt__password')"



export AMNIOTIC__STREAM_URL="$(bashio::config 'amniotic__stream_url')"
export AMNIOTIC__PATH_AUDIO="$(bashio::config 'amniotic__path_audio')"


IS_SSH="$(bashio::config 'is_ssh')"

if bashio::var.true "${IS_SSH}"; then
    bashio::log.info "Starting SSHD because is_ssh == true"
    export FMTR_DEV=true
    export FMTR_LOG_LEVEL=DEBUG
    printenv > /addon.env
    echo "root:password" | chpasswd
    /usr/sbin/sshd -D -o Port=22 -o PermitRootLogin=yes -o PasswordAuthentication=yes -o AllowTcpForwarding=yes -o LogLevel=VERBOSE
else
    bashio::log.info "Starting Amniotic service"
    amniotic
fi
