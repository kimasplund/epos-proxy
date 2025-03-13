FROM python:3.12-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./

# Create required directories
RUN mkdir -p cert log data

# Expose HTTPS port
EXPOSE 443

# Run the application
CMD ["python", "main.py"]