FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATE_FILE=/data/state.json

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY *.py tweet_template.txt ./

# state.json lives here: mount a volume so restarts don't miss or double-post sales.
VOLUME /data

CMD ["python", "bot.py"]
