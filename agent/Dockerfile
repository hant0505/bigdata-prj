FROM python:3.11-slim

WORKDIR /app

# 1. Cài đặt dependencies hệ thống
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Nâng cấp PIP trước và cấu hình Timeout cao hơn (1000 giây)
ENV PIP_DEFAULT_TIMEOUT=1000
RUN pip install --no-cache-dir --upgrade pip

# 3. Copy file requirements độc lập để tận dụng Docker Cache layer
COPY requirements.txt /app/requirements.txt

# 4. Cache pip downloads between Docker builds to speed rebuilds
#    Requires Docker BuildKit (DOCKER_BUILDKIT=1) — first build still downloads
#    Subsequent builds will use the cached wheels in /root/.cache/pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    --index-url https://pypi.org/simple \
    --prefer-binary \
    -r /app/requirements.txt

# 5. Copy toàn bộ code nguồn sau cùng
COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
