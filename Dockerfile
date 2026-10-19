FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 11000 sample \
    && useradd --uid 11000 --gid sample --create-home sample \
    && mkdir /data && chown sample:sample /data
COPY partner ./partner
USER sample
EXPOSE 8080
# No access log: callback URLs carry short-lived OAuth codes and intent handles.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "45", "partner:create_app()"]
