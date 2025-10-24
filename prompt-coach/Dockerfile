FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENV PYTHONUNBUFFERED=1
EXPOSE 8088
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8088"]

# docker build -t prompt-coach .
# docker run -e OPENAI_API_KEY=$OPENAI_API_KEY -p 8088:8088 prompt-coach
