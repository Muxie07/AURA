with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

replacement = """
      await loadMessages(convId);
      setStreamContent('');
    } catch(e) {
"""

text = text.replace("""
      await loadMessages(convId);
    } catch(e) {""", replacement)

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
