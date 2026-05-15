# Sử dụng base image Spark hiện tại dự án đang dùng
FROM bde2020/spark-base:3.3.0-hadoop3.3

# (Tuỳ chọn) Chuyển quyền user sang root nếu cần cài đặt thêm gói phần mềm khác
# USER root

# Copy các thư viện JAR cần thiết (kết nối MinIO/S3) từ máy host vào thư mục /spark/jars/ trong container
COPY ./jars/hadoop-aws-3.3.2.jar /spark/jars/hadoop-aws-3.3.2.jar
COPY ./jars/aws-java-sdk-bundle-1.11.1026.jar /spark/jars/aws-java-sdk-bundle-1.11.1026.jar

# (Tuỳ chọn) Nếu bạn có code pyspark, scala hoặc data muốn đưa luôn vào image thì có thể copy vào:
# COPY ./src /app/src
# COPY ./data /app/data

# Khôi phục lại cấu hình môi trường chuẩn nếu cần thiết
ENV SPARK_HOME=/spark