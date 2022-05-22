FROM edwardbrown/python as base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y
RUN apt install -y vlc
ARG VERSION
RUN if [ -z "$VERSION" ] ; then pip3 install amniotic ; else pip3 install amniotic==${VERSION} ; fi
CMD amniotic
