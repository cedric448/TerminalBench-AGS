FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY cmd_server.py /cmd_server.py

EXPOSE 8080

CMD ["python3", "/cmd_server.py"]
