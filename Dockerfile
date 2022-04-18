FROM python:3.9
WORKDIR /usr/src/app
EXPOSE 8888
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "--port", "8888", "class_registerer.main:app"]
