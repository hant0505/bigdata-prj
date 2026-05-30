FROM python:3.11-slim-bullseye

WORKDIR /app

# 1. Cài đặt dependencies hệ thống và JAVA (Bắt buộc cho Spark)
RUN apt-get update \
    && mkdir -p /usr/share/man/man1 \
    && apt-get install -y --no-install-recommends \
       gcc \
       build-essential \
       curl \
       openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Cấu hình biến môi trường JAVA cho Spark
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# 2. Nâng cấp PIP trước và cấu hình Timeout cao hơn (1000 giây)
ENV PIP_DEFAULT_TIMEOUT=1000
RUN pip install --no-cache-dir --upgrade pip

# 3. Copy file requirements độc lập để tận dụng Docker Cache layer
COPY requirements.txt /app/requirements.txt

# 4. Cài đặt các thư viện Python tiêu chuẩn
RUN pip install --no-cache-dir -r /app/requirements.txt


# 5. Copy toàn bộ code nguồn sau cùng
COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "main_benchmark_test.py"]
