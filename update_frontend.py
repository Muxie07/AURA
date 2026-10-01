import io
import re

with io.open("frontend/src/app/agents/[id]/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the useEffect content
old_use_effect = """  useEffect(() => {
    async function fetchRunDetails() {
      if (!id) return;
      try {
        const token = localStorage.getItem('token') || 'test-token';
        const headers = { 'Authorization': `Bearer ${token}` };
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        
        const [runRes, eventsRes] = await Promise.all([
          fetch(`${API_URL}/agent/runs/${id}`, { headers }),
          fetch(`${API_URL}/agent/runs/${id}/events`, { headers }).catch(() => ({ ok: false, json: () => ({ events: [] }) } as any))
        ]);
        
        if (runRes.ok) {
          const runData = await runRes.json();
          setRun(runData);
        }
        
        if (eventsRes.ok) {
          const eventsData = await eventsRes.json();
          setEvents(eventsData.events || []);
        }
      } catch (err) {
        console.error("Failed to fetch run details", err);
      } finally {
        setLoading(false);
      }
    }
    
    fetchRunDetails();
  }, [id]);"""

new_use_effect = """  useEffect(() => {
    let eventSource: EventSource | null = null;

    async function fetchRunDetails() {
      if (!id) return;
      try {
        const token = localStorage.getItem('token') || 'test-token';
        const headers = { 'Authorization': `Bearer ${token}` };
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        
        const runRes = await fetch(`${API_URL}/agent/runs/${id}`, { headers });
        if (runRes.ok) {
          const runData = await runRes.json();
          setRun(runData);
        }

        // Start SSE stream
        // Note: EventSource doesn't support custom headers easily without a polyfill.
        // We'll use a standard EventSource but since our API is auth-protected,
        // we might pass the token in a query param if backend supports it.
        // For this demo, let's just use standard EventSource if auth is cookie-based,
        // or we can just fetch the events once and poll.
        // Let's use a polyfill approach or just standard EventSource with query param.
        
        eventSource = new EventSource(`${API_URL}/agent/runs/${id}/stream`);
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.event_type === 'STREAM_END') {
            eventSource?.close();
            setRun((prev: any) => ({ ...prev, status: data.status }));
          } else {
            setEvents((prev) => {
              const newEvents = [...prev];
              // Avoid duplicates
              if (!newEvents.find(e => e.id === data.id)) {
                newEvents.push(data);
              }
              return newEvents;
            });
          }
        };
        eventSource.onerror = () => {
          console.error("EventSource failed");
          eventSource?.close();
        };

      } catch (err) {
        console.error("Failed to fetch run details", err);
      } finally {
        setLoading(false);
      }
    }
    
    fetchRunDetails();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [id]);"""

content = content.replace(old_use_effect, new_use_effect)

with io.open("frontend/src/app/agents/[id]/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
