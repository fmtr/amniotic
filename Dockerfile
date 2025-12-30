FROM fmtr/python as base

ARG VERSION
RUN python -m venv /opt/dev/ve/amniotic
RUN /opt/dev/ve/amniotic/bin/pip install amniotic==${VERSION} --no-cache-dir
#RUN /opt/dev/ve/amniotic/bin/fmtr-tools-install-yamlscript

CMD /opt/dev/ve/amniotic/bin/amniotic


