FROM python:3.9

COPY eventParser.py requirements.txt blockNumber.txt config.json /app/
COPY abi /app/abi

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "eventParser.py"]

