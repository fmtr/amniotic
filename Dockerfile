ARG VERSION
ARG TYPE=development

FROM edwardbrown/python as base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt -qq update -y
RUN apt -qq install -y pulseaudio vlc

FROM base AS development
WORKDIR /usr/src
COPY . .
RUN pip install .

FROM base AS release
RUN if [ -z "$VERSION" ] ; then pip3 install amniotic ; else pip3 install amniotic==${VERSION} ; fi


FROM ${TYPE} as image

CMD amniotic


