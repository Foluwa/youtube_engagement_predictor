FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary files, not the entire context
COPY api/ ./api/
COPY src/ ./src/
COPY streamlit_app.py ./

# Expose port and set entrypoint
EXPOSE 80
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "80"]