FROM python:3.13.3-slim-bookworm

WORKDIR /app

EXPOSE 7860

ENV PYTHONUNBUFFERED=1
ENV PDF2ZH_CONFIG_DIR=/app/config
ARG BABELDOC_SOURCE=stable
ARG BABELDOC_GIT_REF=
ARG BABELDOC_STABLE_REF=v0.6.3

# # Download all required fonts
# ADD "https://github.com/satbyy/go-noto-universal/releases/download/v7.0/GoNotoKurrent-Regular.ttf" /app/
# ADD "https://github.com/timelic/source-han-serif/releases/download/main/SourceHanSerifCN-Regular.ttf" /app/
# ADD "https://github.com/timelic/source-han-serif/releases/download/main/SourceHanSerifTW-Regular.ttf" /app/
# ADD "https://github.com/timelic/source-han-serif/releases/download/main/SourceHanSerifJP-Regular.ttf" /app/
# ADD "https://github.com/timelic/source-han-serif/releases/download/main/SourceHanSerifKR-Regular.ttf" /app/

RUN apt-get update && \
     apt-get install --no-install-recommends -y git libgl1 libglib2.0-0 libxext6 libsm6 libxrender1 build-essential && \
     rm -rf /var/lib/apt/lists/* && \
     python -m pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache -r pyproject.toml && babeldoc --version

COPY . .

RUN set -eux; \
    case "$BABELDOC_SOURCE" in \
      stable) BABELDOC_INSTALL_TARGET="git+https://github.com/funstory-ai/BabelDOC.git@${BABELDOC_STABLE_REF}" ;; \
      latest) BABELDOC_INSTALL_TARGET="git+https://github.com/funstory-ai/BabelDOC.git" ;; \
      ref) \
        test -n "$BABELDOC_GIT_REF"; \
        BABELDOC_INSTALL_TARGET="git+https://github.com/funstory-ai/BabelDOC.git@${BABELDOC_GIT_REF}" ;; \
      *) \
        echo "Unsupported BABELDOC_SOURCE: $BABELDOC_SOURCE" >&2; \
        exit 1 ;; \
    esac; \
    echo "Installing BabelDOC from $BABELDOC_INSTALL_TARGET"; \
    uv pip install --system --no-cache --compile-bytecode "$BABELDOC_INSTALL_TARGET"; \
    uv pip install --system --no-cache .; \
    babeldoc --version
RUN pdf2zh --version
CMD ["pdf2zh", "--gui"]
