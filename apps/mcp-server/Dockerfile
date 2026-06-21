FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /workspace

COPY ./apps/mcp-server/pyproject.toml ./apps/mcp-server/README.md ./apps/mcp-server/uv.lock* ./apps/mcp-server/
COPY ./apps/mcp-server/portfolio_mcp ./apps/mcp-server/portfolio_mcp
COPY ./packages/domain ./packages/domain
COPY ./packages/policy ./packages/policy

WORKDIR /workspace/apps/mcp-server

RUN uv sync --frozen

ENV PYTHONPATH=/workspace/apps/mcp-server:/workspace/packages/domain:/workspace/packages/policy
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8081

EXPOSE 8081

CMD ["uv", "run", "python", "-m", "portfolio_mcp.server"]
