import json
import re

def load(value):
    if isinstance(value,dict):
        if 'articles' in value:return value
        if 'text' in value:return load(value['text'])
        if isinstance(value.get('data'),dict):return load(value['data'])
    if not isinstance(value,str):value=getattr(value,'text',None)
    if not isinstance(value,str) or not value.strip():raise ValueError('Выпуск остановлен: EMPTY_RESPONSE')
    try:return json.loads(value)
    except Exception:raise ValueError('Выпуск остановлен: INVALID_JSON')

def numbers(text):
    found=set(x.replace(',','.') for x in re.findall(r'(?<![a-zA-Z])\d+(?:[.,]\d+)*',text))
    words={'one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9','ten':'10'}
    for word,value in words.items():
        if re.search(r'\b'+word+r'\b',text.lower()):found.add(value)
    return found

def transform(inputs):
    original=load(inputs.get('in2'));model=load(inputs.get('in1'))
    if not isinstance(model,dict) or not isinstance(model.get('articles'),list):raise ValueError('Выпуск остановлен: MODEL_SCHEMA')
    expected={a['id']:a for a in original['articles']}
    results=model['articles']
    if len(results)!=len(expected) or set(x.get('id') for x in results if isinstance(x,dict))!=set(expected):raise ValueError('Выпуск остановлен: ARTICLES_CHANGED')
    lines=['Газ и СПГ — '+original['period_start'],'Дата публикации сверена по странице и архиву; ссылки загружены сборщиком. Проверка: '+original['checked_at'],'Содержание СМИ не является независимым подтверждением события.','']
    for item in results:
        article=expected[item['id']]
        for key in ('title_ru','summary_ru','analysis','quote'):
            if not isinstance(item.get(key),str) or not item[key].strip():raise ValueError('Выпуск остановлен: EMPTY_'+key.upper())
        for language_key in ('title_ru','summary_ru','analysis'):
            if not re.search('[А-Яа-яЁё]',item[language_key]):raise ValueError('Выпуск остановлен: RUSSIAN_TRANSLATION_MISSING')
        if len(item['title_ru'])>250:raise ValueError('Выпуск остановлен: TITLE_TOO_LONG')
        quote=item['quote'].strip()
        if len(quote)<35 or len(quote)>450 or quote not in article['text']:raise ValueError('Выпуск остановлен: QUOTE_NOT_IN_SOURCE')
        if len(item['summary_ru'])>800 or len(item['analysis'])>500:raise ValueError('Выпуск остановлен: MODEL_TEXT_TOO_LONG')
        if re.search(r'https?://',item['title_ru']+' '+item['summary_ru']+' '+item['analysis']):raise ValueError('Выпуск остановлен: MODEL_ADDED_URL')
        if not numbers(item['title_ru']+' '+item['summary_ru']).issubset(numbers(article['title']+' '+article['text'])):raise ValueError('Выпуск остановлен: MODEL_ADDED_NUMBER')
        body=article['text'].lower();summary=item['summary_ru'].lower()
        if ('deferred' in body or 'vetting' in body) and 'jera' in article['title'].lower() and not re.search('отлож|предлож|проверк|рассмотр|не одобрен',summary):raise ValueError('Выпуск остановлен: PROPOSAL_QUALIFIER_MISSING')
        lines += [article['source']+' · '+article['published_at'],item['title_ru'],article['url'],'Пересказ: '+item['summary_ru'],'Возможное влияние (оценка модели): '+item['analysis'],'']
    lines+=['Охват: '+', '.join(d['source']+' — '+{'ok':'проверен','unavailable':'недоступен'}.get(d['status'],'проверка не завершена') for d in original.get('discovery',[])),'Исключено материалов: '+str(len(original.get('excluded',[]))),'Дайджест завершён']
    return {'result':'\n'.join(lines)}
