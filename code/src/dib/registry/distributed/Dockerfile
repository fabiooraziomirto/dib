FROM python:3.11-slim
WORKDIR /app
# uvicorn is pinned: dib.registry.distributed.mtls subclasses its HTTP protocol (audit 13).
RUN pip install --no-cache-dir fastapi>=0.111 uvicorn==0.51.0 httpx>=0.27 pydantic>=2
# Build context is code/ (see docker-compose.yml) so this can also bundle the
# minimal slice of the main dib package the /export_mud endpoint reuses
# (dib.core.{io,models}, dib.evaluation.mud_export) rather than reimplementing
# RFC 8520 ACE emission a second time for the distributed prototype.
COPY src/dib/registry/distributed/service.py /app/service.py
COPY src/dib/__init__.py /app/dib/__init__.py
COPY src/dib/core/__init__.py /app/dib/core/__init__.py
COPY src/dib/core/io.py /app/dib/core/io.py
COPY src/dib/core/models.py /app/dib/core/models.py
COPY src/dib/evaluation/__init__.py /app/dib/evaluation/__init__.py
COPY src/dib/evaluation/mud_export.py /app/dib/evaluation/mud_export.py
COPY src/dib/registry/__init__.py /app/dib/registry/__init__.py
COPY src/dib/registry/distributed/mtls.py /app/dib/registry/distributed/mtls.py
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]
