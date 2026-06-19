FROM node:20-bookworm-slim AS frontend

WORKDIR /src

COPY web/package*.json ./web/
RUN cd web && npm ci

COPY web ./web
COPY pdf2zh_next ./pdf2zh_next
RUN cd web && npm run build

FROM python:3.13.3-slim-bookworm

WORKDIR /app

EXPOSE 7860

ENV PYTHONUNBUFFERED=1
ENV PDF2ZH_RUNTIME_DIR=/app
ENV PDF2ZH_DATA_DIR=/app/data
ENV PDF2ZH_CONFIG_DIR=/app/config
ENV PDF2ZH_OUTPUT_DIR=/app/pdf2zh_files
ENV PDF2ZH_CUSTOMER_GLOSSARY_DIR=/app/config
ENV BABELDOC_CACHE_DIR=/app/data/babeldoc-cache
ENV HOME=/app/data/home
ENV USERPROFILE=/app/data/home
ENV XDG_CACHE_HOME=/app/data/xdg-cache
ENV XDG_DATA_HOME=/app/data/xdg-data
ENV XDG_CONFIG_HOME=/app/data/xdg-config
ENV PDF2ZH_REQUIRE_GUI_LOGIN=true
ENV PDF2ZH_USER_USERNAME=user
ENV PDF2ZH_USER_PASSWORD=pdftranslate
ENV PDF2ZH_ADMIN_USERNAME=admin
ENV PDF2ZH_ADMIN_PASSWORD=admin
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
COPY --from=frontend /src/pdf2zh_next/web_frontend ./pdf2zh_next/web_frontend

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
RUN mkdir -p "$PDF2ZH_CONFIG_DIR" "$PDF2ZH_OUTPUT_DIR" "$BABELDOC_CACHE_DIR" "$HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" && \
    babeldoc --warmup
RUN pdf2zh --version
CMD ["pdf2zh", "--gui"]
