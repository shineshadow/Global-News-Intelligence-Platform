#!/usr/bin/env bash
set -e

sudo apt update

sudo apt install -y \
    postgresql \
    postgresql-contrib \
    redis-server \
    curl \
    git \
    build-essential \
    libpq-dev \
    bubblewrap \
    libseccomp2 \
    clamav \
    clamav-freshclam
