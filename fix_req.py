with open('backend/app/api/v1/agent.py', 'r') as f:
    text = f.read()

text = text.replace('content=req.message', 'content=req.request')
text = text.replace('user_request=req.message', 'user_request=req.request')

with open('backend/app/api/v1/agent.py', 'w') as f:
    f.write(text)
