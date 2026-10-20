# syntax=docker/dockerfile:1
# Official Ubuntu OCI index; registry bytes verified against this SHA-256.
FROM ubuntu:24.04@sha256:68ee22004a9109b44973313b02ff7b1de250f1de0f5ecb628d73f579aaff33ac AS base

# Freeze the apt universe as well as the base filesystem. Ubuntu retains its
# signed Release/Packages verification; no third-party Python PPA is required.
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://snapshot.ubuntu.com/ubuntu/20261001T000000Z/|g; s|http://security.ubuntu.com/ubuntu/|http://snapshot.ubuntu.com/ubuntu/20261001T000000Z/|g; s|http://ports.ubuntu.com/ubuntu-ports/|http://snapshot.ubuntu.com/ubuntu/20261001T000000Z/|g' /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates python3.12=3.12.3-1ubuntu0.17 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LENA_ENV_FILE_MODE=disabled REWRITE_PROVIDER=template \
    WFS_AUTO_SYNC=false TOILET_AUTO_SYNC=false DRINKING_FOUNTAIN_AUTO_SYNC=false \
    WFS_AUTO_PROMOTE=false TOILET_AUTO_PROMOTE=false DRINKING_FOUNTAIN_AUTO_PROMOTE=false \
    SPEECH_SYNTHESIS_PROVIDER=openai INTERACTION_LOGGING_ENABLED=false \
    LENA_ALLOW_LIVE_SMOKE=false LENA_DATA_DIR=/tmp/lena/data LENA_RUNTIME_DIR=/tmp/lena/runtime

FROM base AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3.12-venv=3.12.3-1ubuntu0.17 nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && python3.12 -m venv /opt/build
ENV PATH=/opt/build/bin:$PATH PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements/ /locks/
RUN python -m pip download --require-hashes --only-binary=:all: \
      -r /locks/runtime-py312.lock -r /locks/build-py312.lock -d /wheelhouse \
    && python -m pip install --no-index --find-links=/wheelhouse --require-hashes \
      -r /locks/runtime-py312.lock -r /locks/build-py312.lock
ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/wheelhouse PIP_CONSTRAINT=/locks/constraints-py312.txt
WORKDIR /src
COPY . .
RUN --network=none python -m build --outdir /dist \
    && python -m pip check \
    && python -m venv /opt/lena \
    && /opt/lena/bin/python -m pip install --no-index --find-links=/wheelhouse \
       --require-hashes -r /locks/runtime-py312.lock \
    && /opt/lena/bin/python -m pip install --no-deps /dist/*.whl \
    && /opt/lena/bin/python -m pip check \
    && rm -rf /opt/lena/lib/python3.12/site-packages/pip* \
       /opt/lena/lib/python3.12/site-packages/setuptools* /opt/lena/bin/pip*

# Run with docker run --rm --network none lena-check. Packaging subprocesses
# resolve exclusively from the hash-verified wheelhouse, even when isolated.
FROM build AS test
CMD ["sh", "-c", "python -m pytest && python -m compileall -q app tests && python -m pip check && node --test tests/frontend.test.cjs && node --check app/static/app.js && node --check app/static/dialogue.js"]

FROM base AS runtime
COPY --from=build /opt/lena /opt/lena
ENV PATH=/opt/lena/bin:$PATH
WORKDIR /opt/lena
# Numeric IDs avoid adding account-management packages to the runtime image.
USER 10001:10001
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/opt/lena/bin/python", "-c", "import json,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8002/api/health',timeout=3); assert r.status == 200 and json.load(r)['kb_loaded']"]
ENTRYPOINT ["/opt/lena/bin/python", "-m", "app"]
CMD ["--host", "0.0.0.0", "--allow-public", "--port", "8002"]
