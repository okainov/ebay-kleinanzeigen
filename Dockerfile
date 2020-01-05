FROM python:3.8

RUN mkdir /app

COPY requirements.txt /app

WORKDIR /app
RUN pip install -r requirements.txt

ADD . /app

CMD python /app/main.py