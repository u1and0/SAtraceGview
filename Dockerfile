# Just Upload & Plot. Easy visualize tool via http.
# Usage: docker run -d -p 8880:8880 u1and0/uplot

FROM python:3.8-alpine
RUN apk --update-cache \
    add musl \
    linux-headers \
    gcc \
    g++ \
    make \
    gfortran \
    openblas-dev
COPY requirements.txt requirements.txt
RUN pip install --upgrade --no-cache-dir -r requirements.txt

COPY gview.py /usr/bin/gview
COPY ../SAtraceWatchdog/tracer.py /usr/bin/SAtraceWatchdog/tracer.py
RUN chmod +x /usr/bin/gview /usr/bin/SAtraceWatchdog/tracer.py
ENV PYTHONPATH=/usr/bin
CMD ["/usr/bin/gview"]

LABEL maintainer="u1and0 <e01.ando60@gmail.com>" \
      description="Just Upload & Plot. Easy visualize tool via http." \
      description.ja="UplodしてPlotするだけ。簡単なhttp経由の可視化ツール。" \
      version="uplot:v0.0.0" \
      usage="docker run -d -p 8880:8880 u1and0/uplot"
