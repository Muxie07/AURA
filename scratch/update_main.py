import re
with open('app/main.py', 'r') as f: text = f.read()

new_lifespan = '''    await initialize_database()
    
    from app.tools.mcp.routes import start_mcp_server
    import asyncio
    mcp_task = asyncio.create_task(start_mcp_server())

    logger.info("aura_ready", api_base_url=str(settings.aura_api_base_url))

    yield

    # ---- Shutdown --------------------------------------------------------
    logger.info("aura_shutting_down")
    mcp_task.cancel()
    await dispose_database()'''

text = re.sub(
    r'    await initialize_database\(\).*?await dispose_database\(\)', 
    new_lifespan, 
    text, 
    flags=re.DOTALL
)

with open('app/main.py', 'w') as f: f.write(text)
