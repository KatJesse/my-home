ARG BUILD_FROM
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-pip tesseract-ocr tesseract-ocr-data-deu tesseract-ocr-data-eng tesseract-ocr-data-osd poppler-utils jpeg-dev zlib-dev freetype-dev build-base python3-dev linux-headers
WORKDIR /opt/haus
COPY requirements.txt .
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
