ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-pip \
        make \
        openssh-client \
        rsync \
        sudo && \
    rm -rf /var/lib/apt/lists/*

RUN ssh-keygen -A

RUN mkdir -p /opt/dev/repo

RUN python3 -m pip install --no-cache-dir amniotic==${BUILD_VERSION} --break-system-packages

CMD ha-addon-launch --name=amniotic