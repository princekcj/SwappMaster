# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Create a virtual environment and activate it
RUN python -m venv venv
RUN . venv/bin/activate && pip install --no-cache-dir --upgrade pip setuptools
ADD requirements.txt .
# Install project dependencies from requirements.txt
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt

RUN mkdir /app
ADD . /app/
# Set the working directory to /app
WORKDIR /app

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV DEBUG=false

# Run app.py when the container launches
ENTRYPOINT python Horizonpay.py --host 10.1.40.51 --port 5000