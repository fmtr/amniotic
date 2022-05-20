FROM edwardbrown/python
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y
RUN apt install -y git vlc python3-pip python-is-python3
WORKDIR /usr/src
COPY . .
RUN pip install .
RUN which amniotic
CMD amniotic
