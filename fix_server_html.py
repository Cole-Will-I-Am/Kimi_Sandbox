from pathlib import Path
p = Path('server/app.py')
text = p.read_text()

# Add _html helper after _bad
helper = '''
    def _html(self, body):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
'''
if 'def _html(self, body):' not in text:
    text = text.replace(
        '    def _bad(self, message):\n        body = message.encode("utf-8")',
        '    def _bad(self, message):\n        body = message.encode("utf-8")'
    )
    # Actually insert after _bad block
    old_end = '''        self.end_headers()\n        self.wfile.write(body)\n\n    def do_GET'''
    new_end = '''        self.end_headers()\n        self.wfile.write(body)\n\n''' + helper + '''\n    def do_GET'''
    text = text.replace(old_end, new_end, 1)
    print('added _html helper')
else:
    print('_html helper already exists')

# Fix the /council route to use _html and _text if not present
if 'def _text(self, message' not in text:
    text_helper = '''    def _text(self, message, status=200):
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

'''
    # Insert _text before _html
    text = text.replace('    def _html(self, body):', text_helper + '    def _html(self, body):')
    print('added _text helper')
else:
    print('_text helper already exists')

# Make sure /council uses _html (it already does) but _text is defined now.
p.write_text(text)
print('fixed server/app.py')
