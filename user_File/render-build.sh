#!/usr/bin/env bash
# exit on error
set -o errexit

apt-get update && apt-get install -y libsndfile1 portaudio19-dev

pip install -r requirements.txt
