with open('test_flow.py', 'r') as f:
    text = f.read()

text = text.replace('/api/v1/agent/runs', '/api/v1/runs')
text = text.replace(\"'message':'What is our refund policy?'\", \"'request':'Investigate our recent API latency.'\")

with open('test_flow.py', 'w') as f:
    f.write(text)
