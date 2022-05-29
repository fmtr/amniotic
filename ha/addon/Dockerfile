ARG BUILD_FROM
FROM $BUILD_FROM

ARG BUILD_VERSION
RUN apk add --no-cache git py3-pip vlc
RUN pip install amniotic==${BUILD_VERSION}

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]