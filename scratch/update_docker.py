with open('../docker-compose.yml', 'r') as f: text = f.read()

mcp_service = '''  # ---------------------------------------------------------------------------
  # AURA MCP Server (Phase 5.1)
  # ---------------------------------------------------------------------------
  mcp-server:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: development
    container_name: aura-mcp
    restart: unless-stopped
    command: uvicorn app.mcp_main:app --host 0.0.0.0 --port 8000
    env_file:
      - .env
    environment:
      POSTGRES_HOST: postgres
      REDIS_HOST: redis
      AURA_ENV: development
    # Not exposed directly to host to enforce internal boundary
    expose:
      - "8000"
    volumes:
      - ./backend:/app
      - /app/.venv
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - aura-network
'''

text = text.replace('  backend:', mcp_service + '\n  backend:')
text = text.replace(
    '      POSTGRES_HOST: postgres\n      REDIS_HOST: redis\n      AURA_ENV: development',
    '      POSTGRES_HOST: postgres\n      REDIS_HOST: redis\n      AURA_ENV: development\n      MCP_SERVER_URL: http://mcp-server:8000/api/v1/mcp/'
)

with open('../docker-compose.yml', 'w') as f: f.write(text)
