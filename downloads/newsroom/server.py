from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import datetime,json
from collector import collect
ROOT=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,data,kind='application/json; charset=utf-8'):
  if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/':return self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
  if self.path=='/latest':
   files=sorted((ROOT/'runs').glob('*/verified-packet.json'),key=lambda x:x.stat().st_mtime,reverse=True)
   return self.send(200,json.loads(files[0].read_text()) if files else {})
  self.send(404,{'error':'not found'})
 def do_POST(self):
  if self.path!='/collect':return self.send(404,{'error':'not found'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>2000:raise ValueError('request too large')
   value=json.loads(self.rfile.read(length));date=value.get('date','');datetime.date.fromisoformat(date)
   packet,out=collect(date);self.send(200,packet)
  except Exception as exc:self.send(400,{'error':str(exc)[:300]})
if __name__=='__main__':
 server=ThreadingHTTPServer(('127.0.0.1',8275),Handler)
 print('Collector UI: http://127.0.0.1:8275',flush=True)
 server.serve_forever()
