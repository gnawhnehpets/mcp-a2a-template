FROM python:3.12-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
# Assumes requirements.txt is in the project root (build context)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code from the build context
COPY . .

# EXPOSE directives are for documentation; actual port mapping is in docker-compose.yml
EXPOSE 8080
EXPOSE 8181
EXPOSE 8182

# The CMD will be overridden by the 'command' in docker-compose.yml for each service
