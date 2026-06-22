# Use a lightweight python image
FROM python:3.10-slim

# Set working directory
WORKDIR /code

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# Copy the rest of the application code
COPY . .

# Set up a writeable cache folder for FastF1 data
RUN mkdir -p /code/data/fastf1_cache && chmod -R 777 /code/data

# Hugging Face expects the container to run on port 7860
EXPOSE 7860

# Start command
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]