# Just Upload & Plot. Easy visualize tool via http.
# Usage: docker run -d -p 8880:8880 u1and0/satracegview

# ビルドコンテナ
# 処理系入りを敢えて選択
# multi-stage buildで捨てられるため
# 容量は気にしない
FROM python:3.8.1-buster as builder
WORKDIR /opt/app
COPY requirements.lock /opt/app
RUN pip install --upgrade -r requirements.lock

# 実行コンテナ
FROM python:3.8.1-slim-buster as runner
COPY --from=builder /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

# ユーザー追加
RUN useradd -r gviewuser

# APP追加
COPY gview.py /usr/bin/gview
COPY SAtraceWatchdog/tracer.py /usr/bin/SAtraceWatchdog/tracer.py
RUN chmod +x /usr/bin/gview /usr/bin/SAtraceWatchdog/tracer.py

USER gviewuser
ENV PYTHONPATH=/usr/bin
CMD ["/usr/bin/gview"]
EXPOSE 8880

LABEL maintainer="u1and0 <e01.ando60@gmail.com>" \
      description="Just Upload & Plot. Easy visualize tool via http." \
      description.ja="UplodしてPlotするだけ。簡単なhttp経由の可視化ツール。" \
      version="satracegview:v0.0.0" \
      usage="docker run -d -p 8880:8880 u1and0/satracegview"
