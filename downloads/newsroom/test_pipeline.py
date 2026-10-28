"""Offline SYNTHETIC tests. No HTTP, model requests, persistent keys or real article bodies.
Requires cryptography. Production validator is loaded unchanged, then PUBLIC_N/E are
replaced only in this test namespace with an ephemeral RSA public key.
"""
from pathlib import Path
import copy
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

ROOT=Path(__file__).resolve().parent

def synthetic_evidence():
    texts=[
        'Учебная вымышленная заметка сообщает о макете газового терминала. Участники занятия рассматривают иллюстрацию, обсуждают источники и отмечают границы автоматической проверки. Этот текст написан специально для теста, не опубликован в СМИ и не описывает реальную сделку. Проверка цитаты должна находить только точные фразы этого авторского текста.',
        'Учебная вымышленная заметка описывает предложение условного поставщика JERA для демонстрации сохранения оговорок. Это не реальная публикация и не сообщение о компании. Ключевые слова deferred и vetting нужны исключительно для тестирования правила: предложение отложено до проверки. Материал создан автором учебного примера, а не извлечён с сайта.',
        'Учебная вымышленная заметка посвящена обсуждению макета морской перевозки СПГ. Она создана для проверки русского вывода, сопоставления идентификаторов и блокировки выдуманной цитаты. Никаких действительных инвестиций или производственных планов здесь не заявлено. Использование домена example.org обозначает условный адрес; сетевой запрос к нему не выполняется.',
    ]
    articles=[]
    for index,text in enumerate(texts,1):
        title='Вымышленный учебный материал' if index!=2 else 'Fictional JERA proposal for a synthetic test'
        articles.append({'id':'N'+str(index),'title':title,'source':'СИНТЕТИЧЕСКИЙ ИСТОЧНИК — НЕ СМИ','url':f'https://example.org/synthetic-news/{index}','final_url':f'https://example.org/synthetic-news/{index}','http_status':200,'published_at':'2026-10-25','published_at_raw':'2026-10-25T12:00:00+00:00','index_date':'2026-10-25T12:00:00','text':text,'evidence_quotes':[text.split('. ')[0]+'.'],'verification':'https_200+page_metadata+publisher_archive+text_match','test_only':True})
    return {'schema':'club-news-evidence-v1','period_start':'2026-10-25','period_end':'2026-10-25','checked_at':'2026-10-28T00:00:00+00:00','date_basis':'MOCK ONLY: dates, HTTP status and verification strings are test doubles; nothing downloaded','test_only':True,'articles':articles,'discovery':[{'source':'СИНТЕТИЧЕСКИЙ ИСТОЧНИК — НЕ СМИ','status':'ok'}],'excluded':[]}

def main():
    evidence=synthetic_evidence()
    # A temporary in-memory key; never persisted, printed or added to the package.
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public=key.public_key().public_numbers()
    data=json.dumps(evidence,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    packet={'evidence':evidence,'signature':key.sign(data,padding.PKCS1v15(),hashes.SHA256()).hex()}
    validator={};exec((ROOT/'verify_evidence.py').read_text(encoding='utf-8'),validator)
    validator['PUBLIC_N']=public.n;validator['PUBLIC_E']=public.e
    def validate(p):return validator['transform']({'in1':json.dumps(p,ensure_ascii=False)})['result']
    result=validate(packet);assert result['gate']=='PASS',result
    bad=copy.deepcopy(packet);bad['evidence']['articles'][0]['published_at']='2026-10-26';assert 'SOURCE_PROOF_INVALID' in validate(bad)['text']
    assert validator['transform']({'in1':' '})['result']['gate']=='BLOCK'
    bad=copy.deepcopy(packet);bad['signature']='0'*512;assert validate(bad)['gate']=='BLOCK'
    renderer={};exec((ROOT/'render_checked.py').read_text(encoding='utf-8'),renderer)
    model={'articles':[{'id':a['id'],'title_ru':'Учебный вымышленный заголовок','summary_ru':'Это синтетический материал для проверки алгоритма; реальная новость здесь не заявлена.','analysis':'Учебный пример не даёт оснований для выводов о рынке.','quote':a['evidence_quotes'][0]} for a in evidence['articles']]}
    model['articles'][1]['summary_ru']='Учебное предложение отложено до проверки; событие вымышленное.'
    def render(value):return renderer['transform']({'in1':value,'in2':result['text']})['result']
    assert render(json.dumps(model,ensure_ascii=False)).endswith('Дайджест завершён')
    for value,expected in [(' ','EMPTY_RESPONSE'),('{bad','INVALID_JSON')]:
        try:render(value);raise AssertionError('not blocked')
        except ValueError as error:assert expected in str(error)
    bad=copy.deepcopy(model);bad['articles'][0]['quote']='This fabricated quote is absent from the synthetic source.'
    try:render(json.dumps(bad));raise AssertionError('not blocked')
    except ValueError as error:assert 'QUOTE_NOT_IN_SOURCE' in str(error)
    for field in ('title_ru','summary_ru','analysis'):
        bad=copy.deepcopy(model);bad['articles'][0][field]='This English output must be rejected.'
        try:render(json.dumps(bad));raise AssertionError('English output accepted')
        except ValueError as error:assert 'RUSSIAN_TRANSLATION_MISSING' in str(error)
    checks={'signed_packet':'PASS','tampered_date':'BLOCK','empty_input':'BLOCK','forged_signature':'BLOCK','valid_render':'PASS','empty_model':'BLOCK','invalid_json':'BLOCK','invented_quote':'BLOCK','english_title':'BLOCK','english_summary':'BLOCK','english_analysis':'BLOCK'}
    report={'test_type':'SYNTHETIC OFFLINE; no network or model calls','private_key':'ephemeral in memory only','checks':checks}
    examples=ROOT/'examples';examples.mkdir(exist_ok=True)
    (examples/'synthetic-test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (examples/'synthetic-unsigned-example.json').write_text(json.dumps({'TEST_ONLY':'Synthetic unsigned format example; HTTP/date verification fields are mocks, URLs were NOT fetched. Must be rejected by production without a valid trusted signature.','evidence':evidence},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('11 SYNTHETIC offline acceptance checks passed. Network/date verification and LLM quality were NOT tested.')

if __name__=='__main__':main()
