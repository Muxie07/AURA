with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = """
  const startStreaming = async (runId: string, convId: string) => {
    const token = localStorage.getItem('token') || '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    
    try {
      const response = await fetch(`${API_URL}/runs/${runId}/stream`, {
"""

text = text.replace("""  const startStreaming = async (runId: string, convId: string) => {
    const token = localStorage.getItem('token') || '';
    
    try {
      const response = await fetch(`/api/v1/runs/${runId}/stream`, {""", replacement)

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
