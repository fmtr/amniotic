FROM python



ENV DEBIAN_FRONTEND=noninteractive
RUN apt -qq update -y
RUN apt -qq install -y tmate

CMD [ "tmate" ]

#ARG BUILD_FROM
#FROM alpine
#
#RUN apk add --no-cache git py3-pip vlc
#
#RUN pip install git+https://github.com/fmtr/amniotic.git@feature/ha_addon
#RUN which amniotic
