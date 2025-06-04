# Use an official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file first and install requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app files
COPY . .

# Run the application
CMD ["python", "main.py"]
