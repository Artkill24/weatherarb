FROM python:3.11-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ .
COPY data/province_coords.json .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
