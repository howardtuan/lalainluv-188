FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd -r django && useradd -r -g django django
COPY --chown=django:django . .
RUN mkdir -p /app/media /app/staticfiles && chown -R django:django /app/media /app/staticfiles && chmod +x /app/entrypoint.sh
USER django
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
