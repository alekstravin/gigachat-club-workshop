import json
import hashlib
import re
from datetime import date

PUBLIC_N = 18666971075369673771641770855539412305280044100151819081046746173720605562193127094786957906194490397533447143095970487027627193116244212630176982566125036387907649196301557491219626631956439376089213840429095741476147982265227457597393158288479229280000560585881355098166973244237026936557662502236821579671868700092056152504374347959874907138436878377532864924600196296317233253626272262428703117977103154878238972891378565176678849108798663078257397490399106271179155145310253684709162985517714083070255282468542606678539363663797404105089694723547159490771977382765764905679980196797156143554306719623416796908901
PUBLIC_E = 65537

def stop(code):
    raise ValueError('Выпуск остановлен: ' + code)

def unpack(v):
    if isinstance(v,dict):
        if 'evidence' in v or 'articles' in v: return v
        if 'text' in v: return unpack(v['text'])
        if isinstance(v.get('data'),dict): return unpack(v['data'])
    if not isinstance(v,str): v=getattr(v,'text',None)
    if not isinstance(v,str) or not v.strip(): stop('EMPTY_RESPONSE')
    if len(v)>150000: stop('INPUT_TOO_LARGE')
    try: obj=json.loads(v)
    except Exception: stop('INVALID_JSON')
    if not isinstance(obj,dict): stop('ROOT_NOT_OBJECT')
    return obj

def signed_evidence(packet):
    evidence=packet.get('evidence')
    sig=packet.get('signature')
    if not isinstance(evidence,dict) or not isinstance(sig,str) or not re.fullmatch('[0-9a-f]{512}',sig):stop('SOURCE_PROOF_MISSING')
    data=json.dumps(evidence,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    digest=hashlib.sha256(data).hexdigest()
    # RSA PKCS#1 v1.5 / SHA256: public verification only, no secret in Studio.
    prefix='3031300d060960864801650304020105000420'
    expected='0001'+'ff'*(256-3-19-32)+'00'+prefix+digest
    if int(sig,16)>=PUBLIC_N or pow(int(sig,16),PUBLIC_E,PUBLIC_N)!=int(expected,16):stop('SOURCE_PROOF_INVALID')
    if evidence.get('schema')!='club-news-evidence-v1':stop('SCHEMA_INVALID')
    start=evidence.get('period_start');end=evidence.get('period_end')
    if not isinstance(start,str) or not isinstance(end,str):stop('PERIOD_MISSING')
    try:
        first=date.fromisoformat(start);last=date.fromisoformat(end)
    except Exception:stop('PERIOD_INVALID')
    if first>last:stop('PERIOD_INVALID')
    articles=evidence.get('articles')
    if not isinstance(articles,list) or not articles:stop('NO_VERIFIED_ARTICLES')
    if len(articles)>12:stop('TOO_MANY_ARTICLES')
    seen=set()
    for a in articles:
        if not isinstance(a,dict):stop('ARTICLE_INVALID')
        if a.get('http_status')!=200 or a.get('verification')!='https_200+page_metadata+publisher_archive+text_match':stop('SOURCE_NOT_VERIFIED')
        if not isinstance(a.get('url'),str) or not a['url'].startswith('https://') or not isinstance(a.get('final_url'),str) or not a['final_url'].startswith('https://'):stop('URL_INVALID')
        if not isinstance(a.get('text'),str) or len(a['text'])<200:stop('SOURCE_TEXT_MISSING')
        try:published=date.fromisoformat(a.get('published_at',''))
        except Exception:stop('DATE_INVALID')
        if not first<=published<=last:stop('DATE_OUT_OF_PERIOD')
        if a.get('index_date','')[:10]!=a['published_at'] or a.get('published_at_raw','')[:10]!=a['published_at']:stop('DATE_CONFLICT')
        if a['url'] in seen:stop('DUPLICATE_URL')
        seen.add(a['url'])
    return evidence

def transform(inputs):
    try:
        evidence=signed_evidence(unpack(inputs.get('in1')))
        return {'result':{'gate':'PASS','text':json.dumps(evidence,ensure_ascii=False)}}
    except Exception as exc:
        message=str(exc)
        if not message.startswith('Выпуск остановлен:'):message='Выпуск остановлен: VALIDATOR_ERROR'
        return {'result':{'gate':'BLOCK','text':message}}
