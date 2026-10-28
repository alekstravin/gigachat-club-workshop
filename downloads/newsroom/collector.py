"""Public news collector: publisher date search, independent HTTPS/date/text checks.
Uses Python standard library for HTTP and cryptography only to sign evidence.
"""
import argparse, concurrent.futures, datetime as dt, hashlib, html, json, re, ssl
import urllib.request, urllib.parse, urllib.error
from html.parser import HTMLParser
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import serialization,hashes

SOURCES=[('Just Energy News','https://justenergynews24.com'),('Midstream Calendar','https://midstreamcalendar.com'),('EnergyNow','https://energynow.com')]
HOSTS={urllib.parse.urlsplit(url).hostname for _,url in SOURCES}
TOPIC=re.compile(r'\blng\b|natural gas|liquefied natural gas|газ|спг',re.I)
KEY_PATH=Path.home()/'.local/share/club-lng-collector/signing-key.pem'
ROOT=Path(__file__).parent
class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  p=urllib.parse.urlsplit(newurl)
  if p.scheme!='https' or p.hostname not in HOSTS:raise ValueError('REDIRECT_OUTSIDE_SOURCE')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
OPENER=urllib.request.build_opener(SafeRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
def fetch(url,limit=2500000):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password:raise ValueError('URL_NOT_ALLOWED')
 req=urllib.request.Request(url,headers={'User-Agent':'ClubIIII-Newsroom/1.0 (research; public news)','Accept':'application/json,text/html'})
 with OPENER.open(req,timeout=18) as response:
  body=response.read(limit+1)
  if len(body)>limit:raise ValueError('PAGE_TOO_LARGE')
  return response.status,response.url,body.decode(response.headers.get_content_charset() or 'utf-8','replace')
class TextParser(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0;self.metas=[];self.times=[];self.canonical=''
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style','noscript'):self.skip+=1
  if tag=='meta' and (a.get('property','').lower()=='article:published_time' or a.get('itemprop','')=='datePublished'):self.metas.append(a.get('content',''))
  if tag=='time' and a.get('datetime'):self.times.append(a['datetime'])
  if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href','')
  if tag in ('p','div','br','h1','h2','li'):self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript') and self.skip:self.skip-=1
  if tag in ('p','div','li'):self.parts.append('\n')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
 def text(self):return re.sub(r'[ \t]+',' ',html.unescape(''.join(self.parts))).strip()
def text_of(value):
 p=TextParser();p.feed(value);return re.sub(r'\s+',' ',p.text()).strip()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def signing_key():
 if not KEY_PATH.exists():
  KEY_PATH.parent.mkdir(parents=True,exist_ok=True);KEY_PATH.parent.chmod(0o700)
  key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
  KEY_PATH.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));KEY_PATH.chmod(0o600)
 return serialization.load_pem_private_key(KEY_PATH.read_bytes(),password=None)
def discover(source,date):
 name,root=source
 params=urllib.parse.urlencode({'after':date+'T00:00:00','before':date+'T23:59:59','per_page':100,'_fields':'id,link,date,title,content'})
 status,final,body=fetch(root+'/wp-json/wp/v2/posts?'+params)
 posts=json.loads(body)
 if not isinstance(posts,list):raise ValueError('INDEX_NOT_LIST')
 return [{'source':name,'url':p['link'],'index_date':p['date'],'title':text_of(p.get('title',{}).get('rendered','')),'content':p.get('content',{}).get('rendered','')} for p in posts if TOPIC.search(text_of(p.get('title',{}).get('rendered','')))]
def verify(candidate,date):
 status,final,body=fetch(candidate['url']);page=TextParser();page.feed(body)
 dates=page.metas or re.findall(r'"datePublished"\s*:\s*"([^"]+)"',body)
 if not dates:raise ValueError('PUBLICATION_DATE_MISSING')
 parsed=[]
 for value in dates:
  try:parsed.append(dt.datetime.fromisoformat(value.replace('Z','+00:00')))
  except ValueError:pass
 if not parsed:raise ValueError('PUBLICATION_DATE_INVALID')
 # Calendar date at publisher, corroborated by its archive API; do not use URL date.
 pub=parsed[0].date().isoformat()
 if pub!=date or candidate['index_date'][:10]!=date:raise ValueError('DATE_OUT_OF_PERIOD')
 if any(x.date().isoformat()!=pub for x in parsed):raise ValueError('PUBLICATION_DATE_CONFLICT')
 text=text_of(candidate['content'])
 if len(text)<200:raise ValueError('ARTICLE_TEXT_TOO_SHORT')
 visible=re.sub(r'\s+',' ',page.text())
 # Corroborate actual article paragraphs against the separately fetched HTML page.
 fragments=[x.strip() for x in re.split(r'(?<=[.!?])\s+',text) if len(x.strip())>=60]
 matched=[x for x in fragments if x in visible]
 if not matched:raise ValueError('ARTICLE_TEXT_NOT_ON_PAGE')
 if not TOPIC.search(candidate['title']+' '+text):raise ValueError('OFF_TOPIC')
 return {'title':candidate['title'],'source':candidate['source'],'url':candidate['url'],'final_url':final,'http_status':status,'published_at':pub,'published_at_raw':dates[0],'index_date':candidate['index_date'],'text':text[:11000],'evidence_quotes':matched[:3],'html_sha256':hashlib.sha256(body.encode()).hexdigest(),'verification':'https_200+page_metadata+publisher_archive+text_match'}
def collect(date,outdir=None):
 dt.date.fromisoformat(date);key=signing_key();candidates=[];excluded=[];discovery=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  futures={pool.submit(discover,s,date):s for s in SOURCES}
  for future,s in futures.items():
   try:
    found=future.result();candidates+=found;discovery.append({'source':s[0],'count':len(found),'status':'ok'})
   except Exception as exc:discovery.append({'source':s[0],'status':'unavailable','reason':str(exc)[:180]})
 articles=[];seen=set()
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  futures={pool.submit(verify,c,date):c for c in candidates[:20]}
  for future,c in futures.items():
   try:
    article=future.result()
    if article['final_url'] in seen:continue
    seen.add(article['final_url']);articles.append(article)
   except Exception as exc:excluded.append({'url':c['url'],'reason':str(exc)[:180]})
 articles.sort(key=lambda x:(x['source'],x['url']))
 for extra in articles[12:]:excluded.append({'url':extra['url'],'reason':'OUTPUT_LIMIT_12'})
 articles=articles[:12]
 for i,a in enumerate(articles):a['id']='N'+str(i+1)
 evidence={'schema':'club-news-evidence-v1','period_start':date,'period_end':date,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'date_basis':'publisher calendar date; page metadata and archive API agree','articles':articles,'discovery':discovery,'excluded':excluded}
 sig=key.sign(canonical(evidence),padding.PKCS1v15(),hashes.SHA256()).hex()
 packet={'evidence':evidence,'signature':sig}
 n=key.public_key().public_numbers();(ROOT/'public_key.json').write_text(json.dumps({'n':str(n.n),'e':n.e}))
 out=Path(outdir) if outdir else ROOT/'runs'/date;out.mkdir(parents=True,exist_ok=True)
 (out/'verified-packet.json').write_text(json.dumps(packet,ensure_ascii=False,separators=(',',':')))
 (out/'verification.json').write_text(json.dumps({'date':date,'accepted':len(articles),'discovery':discovery,'excluded':excluded,'articles':[{k:v for k,v in a.items() if k not in ('text','evidence_quotes')} for a in articles]},ensure_ascii=False,indent=2))
 lines=['# Газ и СПГ — '+date,'','Дата сверена с метаданными страниц и архивом издателя. Фактические утверждения СМИ независимо не подтверждены.','']
 for a in articles:
  lines+=['## '+a['title'],a['source']+' · '+a['published_at'],'['+a['title']+']('+a['url']+')','',a['evidence_quotes'][0],'']
 lines+=['## Охват источников']+[d['source']+': '+d['status']+(' — '+d.get('reason','') if d.get('reason') else '') for d in discovery]
 (out/'digest.md').write_text('\n'.join(lines))
 return packet,out
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--date',required=True);parser.add_argument('--output');args=parser.parse_args();packet,out=collect(args.date,args.output)
 print(json.dumps({'accepted':len(packet['evidence']['articles']),'output':str(out),'discovery':packet['evidence']['discovery'],'excluded':packet['evidence']['excluded']},ensure_ascii=False))
