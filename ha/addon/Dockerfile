ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION

RUN apk add --no-cache py3-pip make openssh rsync sudo # YS installer uses make
RUN ssh-keygen -A
RUN mkdir -p /opt/dev/repo
#RUN python3 -m venv /opt/dev/venv/amniotic
RUN python -m pip install amniotic==${BUILD_VERSION} --break-system-packages --no-cache-dir
RUN fmtr-tools-install-yamlscript

CMD ha-addon-launch --name=amniotic