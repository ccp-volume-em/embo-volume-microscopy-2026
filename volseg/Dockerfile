FROM python:3.11-slim

RUN pip install --no-cache-dir torch==2.10.0 --index-url https://download.pytorch.org/whl/cu126

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    mesa-utils \
    libglx-mesa0 \
    libegl1 \
    libdbus-1-3 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libxcb-xfixes0 \
    x11-utils \
    libxcb-cursor0 \
    libopengl0 \
    libfontconfig1 \
    libxrender1 \
    libxi6 \
    libxcb-shape0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /opt
COPY volseg-settings/ volseg-settings/
RUN chmod -R a+rX /opt/volseg-settings

ENV NO_ALBUMENTATIONS_UPDATE=1

CMD ["bash"]
