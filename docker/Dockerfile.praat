FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    praat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /praat

RUN mkdir -p /data/audio_input /data/audio_output /data/praat_output

RUN ln -s /usr/bin/praat /usr/local/bin/praat

CMD ["sleep", "infinity"]