FROM fmtr/python as base

ARG VERSION
RUN python -m venv /opt/dev/venv/amniotic
RUN /opt/dev/venv/amniotic/bin/pip install amniotic==${VERSION} --no-cache-dir

CMD /opt/dev/venv/amniotic/bin/amniotic


