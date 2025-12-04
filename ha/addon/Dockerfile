ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION

RUN apk add --no-cache py3-pip make # YS installer uses make
RUN mkdir -p /opt/dev/venv
RUN python3 -m venv /opt/dev/venv/amniotic
RUN /opt/dev/venv/amniotic/bin/pip install amniotic==${BUILD_VERSION} --no-cache-dir
RUN /opt/dev/venv/amniotic/bin/fmtr-tools-install-yamlscript

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]