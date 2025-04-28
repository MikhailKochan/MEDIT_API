FROM python:3.10.12-slim

WORKDIR /app

COPY ./entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

RUN apt-get update && apt-get install -y --no-install-recommends\
 libgl1-mesa-glx\
 libglib2.0-0\
 libopenslide0\
 build-essential\
 libopenslide-dev\
 python3-dev\
 && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app