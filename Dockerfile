FROM python:3.12

ARG BUILDX_QEMU_ENV

WORKDIR /usr/src/app

COPY ./requirements.txt ./

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

RUN pip install --upgrade pip

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -qq -y --fix-missing --no-install-recommends \
    gcc \
    libffi-dev \
    rustc \
    zlib1g-dev \
    libjpeg-dev \
    libssl-dev \
    libblas-dev \
    liblapack-dev \
    make \
    cmake \    
    automake \
    ninja-build \
    g++ \
    subversion \
    python3-dev \
    wget \
    curl \
    unzip \
    gnupg \
  && if [ "${BUILDX_QEMU_ENV}" = "true" ] && [ "$(getconf LONG_BIT)" = "32" ]; then \
        pip install -U cryptography==3.3.2; \
     fi \
  && pip install -r requirements.txt \
  && pip cache purge

# Install Google Chrome and ChromeDriver for Selenium
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-archive-keyring.gpg \
  && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update \
  && apt-get install -y google-chrome-stable \
  && CHROME_VERSION=$(google-chrome --version | awk '{print $3}') \
  && CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) \
  && wget -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
  && unzip /tmp/chromedriver.zip -d /tmp/ \
  && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
  && chmod +x /usr/local/bin/chromedriver \
  && rm -rf /tmp/chromedriver* \
  && apt-get remove -y gcc rustc wget curl unzip gnupg \
  && apt-get autoremove -y \
  && apt-get autoclean -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /usr/share/doc/*

# Copy application files
ADD ./TwitchChannelPointsMiner ./TwitchChannelPointsMiner
COPY ./run.py ./run.py
COPY ./login.py ./login.py
COPY ./manualactivate.py ./manualactivate.py

# Copy configuration files (these should be mounted as volumes in production)
COPY ./pass.txt ./pass.txt
COPY ./*.txt ./

# Set environment variables for headless operation
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_DRIVER=/usr/local/bin/chromedriver

ENTRYPOINT [ "python", "run.py" ]
