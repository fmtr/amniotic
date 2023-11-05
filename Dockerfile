ARG VERSION
ARG TYPE=development

FROM fmtr/python:v3.12 as base
ENV DEBIAN_FRONTEND=noninteractive

RUN useradd --uid 1000 --create-home amniotic

RUN apt -qq update -y
RUN apt -qq install -y pulseaudio vlc alsa-utils

COPY amniotic.client.conf /amniotic.client.conf

FROM base AS development
WORKDIR /usr/src
COPY . .
RUN pip install .

FROM base AS release
RUN if [ -z "$VERSION" ] ; then pip3 install amniotic ; else pip3 install amniotic==${VERSION} ; fi


FROM ${TYPE} as image

CMD amniotic


