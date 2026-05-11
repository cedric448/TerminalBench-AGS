FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy cmd_server
COPY src/cmd_server.py /cmd_server.py

# Copy task files (tests + instruction)
COPY src/tests/test_outputs.py /tests/test_outputs.py
COPY src/tests/positive_probe.c /tests/positive_probe.c
COPY src/tests/negative_probe.c /tests/negative_probe.c
COPY src/tests/test.sh /tests/test.sh
COPY instruction.md /instruction.md

EXPOSE 8080

CMD ["python3", "/cmd_server.py"]
