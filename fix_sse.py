import io

with io.open("frontend/src/app/agents/[id]/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

old_use_effect = content[content.find('  useEffect(() => {'):content.find('  if (loading) return')]

new_use_effect = """  useEffect(() => {
    let abortController = new AbortController();
    let isMounted = true;
    let streamRetryCount = 0;

    async function fetchRunDetails() {
      if (!id) return;
      try {
        const runRes = await fetchApi(`/agent/runs/${id}`);
        if (runRes.ok) {
          const runData = await runRes.json();
          setRun(runData);
        }
      } catch (err) {
        console.error("Failed to fetch run details", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    async function startStream() {
      if (!id || !isMounted) return;
      try {
        const response = await fetchApi(`/agent/runs/${id}/stream`, { signal: abortController.signal });
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) return;
        
        let buffer = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\\n\\n');
            buffer = lines.pop() || "";
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.event_type === 'STREAM_END') {
                            setRun((prev: any) => ({ ...prev, status: data.status }));
                            abortController.abort();
                            return; // end stream gracefully
                        } else {
                            setEvents((prev) => {
                                const newEvents = [...prev];
                                if (!newEvents.find(e => e.id === data.id)) {
                                    newEvents.push(data);
                                }
                                return newEvents;
                            });
                        }
                    } catch(e) {}
                }
            }
        }
        
        // If we broke out of loop without STREAM_END and are still mounted, we should reconnect
        if (isMounted && !abortController.signal.aborted) {
            throw new Error("Stream ended unexpectedly");
        }
      } catch (err: any) {
        if (err.name !== 'AbortError' && isMounted) {
            console.error("Stream failed, reconnecting...", err);
            streamRetryCount++;
            if (streamRetryCount < 10) {
                setTimeout(startStream, Math.min(1000 * Math.pow(2, streamRetryCount), 30000));
            }
        }
      }
    }
    
    fetchRunDetails();
    startStream();

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [id]);

"""

content = content.replace(old_use_effect, new_use_effect)

with io.open("frontend/src/app/agents/[id]/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
