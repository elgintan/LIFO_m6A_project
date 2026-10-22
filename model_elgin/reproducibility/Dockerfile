FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install --no-install-recommends -y python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
# The CPU index avoids installing a multi-gigabyte CUDA runtime for CPU inference.
RUN python -m pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt
COPY code/ /work/code/
COPY model.pt example_input.json example_expected.csv verify_container.py /work/
WORKDIR /work
CMD ["python", "-B", "verify_container.py"]
