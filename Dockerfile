# Use the official Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# The base image already has a user 1000. We do NOT need to create one.

# Set working directory
WORKDIR /app

# Copy requirements first. We use '1000:1000' to assign ownership to the existing non-root user.
COPY --chown=1000:1000 requirements.txt /app/requirements.txt

# Install dependencies
# (Pip installs run as root here so they are available globally, which is fine)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Chromium
RUN playwright install chromium

# Copy the rest of the application code with correct ownership
COPY --chown=1000:1000 . /app

# Switch to the existing non-root user (UID 1000)
USER 1000

# Expose the HF specific port
EXPOSE 7860

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
