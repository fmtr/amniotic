#!/usr/bin/with-contenv bashio

export FMTR_DEV="$(bashio::config 'fmtr_dev')"

if bashio::var.true "${FMTR_DEV}"; then
    bashio::log.info "Starting SSH Development Server"
    printenv > /addon.env
    echo "root:password" | chpasswd
    /usr/sbin/sshd -D -o Port=22 -o PermitRootLogin=yes -o PasswordAuthentication=yes -o AllowTcpForwarding=yes -o LogLevel=VERBOSE
else
    amniotic
fi
