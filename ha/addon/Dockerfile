ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION
RUN apk add --no-cache py3-pip vlc
RUN pip install amniotic==${BUILD_VERSION} --break-system-packages

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]