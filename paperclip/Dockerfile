# Build Paperclip from official source
# See: https://github.com/paperclipai/paperclip
FROM node:lts-trixie-slim AS base

ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     ca-certificates gosu curl git wget ripgrep python3 \
  && mkdir -p -m 755 /etc/apt/keyrings \
  && wget -nv -O/etc/apt/keyrings/githubcli-archive-keyring.gpg \
     https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  && echo "20e0125d6f6e077a9ad46f03371bc26d90b04939fb95170f5a1905099cc6bcc0  /etc/apt/keyrings/githubcli-archive-keyring.gpg" | sha256sum -c - \
  && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && mkdir -p -m 755 /etc/apt/sources.list.d \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends gh \
  && rm -rf /var/lib/apt/lists/* \
  && corepack enable

RUN usermod -u $USER_UID --non-unique node \
  && groupmod -g $USER_GID --non-unique node \
  && usermod -g $USER_GID -d /paperclip node

# Clone and build Paperclip
FROM base AS deps
WORKDIR /app
# Pinned to commit 3e0ab97 (April 2026). To update: check github.com/paperclipai/paperclip/commits/master
RUN git clone https://github.com/paperclipai/paperclip.git . && \
    git checkout 3e0ab97b12fa389354db37ad52aa92b9686e5058
RUN pnpm install --frozen-lockfile

FROM base AS build
WORKDIR /app
COPY --from=deps /app /app
RUN pnpm --filter @paperclipai/ui build
RUN pnpm --filter @paperclipai/plugin-sdk build
RUN pnpm --filter @paperclipai/server build

FROM base AS production
ARG USER_UID=1000
ARG USER_GID=1000
WORKDIR /app
COPY --chown=node:node --from=build /app /app

RUN npm install --global --omit=dev \
      @anthropic-ai/claude-code@latest \
  && mkdir -p /paperclip \
  && chown node:node /paperclip

# Install OpenCode CLI for opencode_local adapter (LM Studio / OpenRouter support)
# Copy binary to /usr/local/bin (not symlink) so non-root users can execute it.
# /root is 700 — a symlink into /root/.opencode/bin is inaccessible to the node user.
RUN curl -fsSL https://opencode.ai/install | bash \
  && cp /root/.opencode/bin/opencode /usr/local/bin/opencode \
  && chmod +x /usr/local/bin/opencode \
  && npm install --global @ai-sdk/openai-compatible

# Bake OpenCode LM Studio config into image at a non-volume path.
# The entrypoint copies this to /paperclip/.config/opencode/ (inside the volume) if absent.
RUN mkdir -p /etc/opencode \
  && printf '{\n  "$schema": "https://opencode.ai/config.json",\n  "provider": {\n    "lmstudio": {\n      "npm": "@ai-sdk/openai-compatible",\n      "name": "LM Studio",\n      "options": {\n        "baseURL": "http://host.docker.internal:1234/v1"\n      },\n      "models": {\n        "qwen3-coder-next": {\n          "name": "Qwen3 Coder Next",\n          "limit": {"context": 32768, "output": 8192}\n        }\n      }\n    }\n  }\n}\n' > /etc/opencode/config.json

ENV NODE_ENV=production \
    HOME=/paperclip \
    HOST=0.0.0.0 \
    PORT=3100 \
    SERVE_UI=true \
    PAPERCLIP_HOME=/paperclip \
    PAPERCLIP_INSTANCE_ID=default \
    PAPERCLIP_DEPLOYMENT_MODE=authenticated \
    PAPERCLIP_DEPLOYMENT_EXPOSURE=private

VOLUME ["/paperclip"]
EXPOSE 3100

# Use patched entrypoint that fixes .claude ownership on every start
# (docker cp creates files as root; node process needs write access)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["node", "--import", "./server/node_modules/tsx/dist/loader.mjs", "server/dist/index.js"]
