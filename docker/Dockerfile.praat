FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    praat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /praat

# Keep container running
CMD ["tail", "-f", "/dev/null"]
