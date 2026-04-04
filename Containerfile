FROM python:3.14

# Install dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set up a non-privileged user
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# Set up the environment
COPY --chown=appuser:appuser requirements-reddit-public-media-viewer.txt ./requirements.txt
ENV PATH="/home/appuser/.local/bin:$PATH" PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python3 -m pip install --upgrade pip && pip3 install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser app/ ./

# Run the application
EXPOSE 65010
ENTRYPOINT ["python3", "/home/appuser/app/reddit_public_media_viewer.py"]
