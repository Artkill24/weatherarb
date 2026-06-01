import os, requests, time

OR_KEY = os.getenv('OPENROUTER_API_KEY','')
GROQ_KEY_1 = os.getenv('GROQ_API_KEY','')
GROQ_KEY_2 = os.getenv('GROQ_API_KEY_2','')

OR_MODELS = [
    'moonshotai/kimi-k2.6:free',
    'google/gemma-4-31b-it:free',
    'nvidia/nemotron-3-super-120b-a12b:free',
]

_call_count = 0

def call_groq(key, prompt, max_tokens):
    r = requests.post('https://api.groq.com/openai/v1/chat/completions',
        headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},
        json={'model':'llama-3.3-70b-versatile',
              'messages':[{'role':'user','content':prompt}],
              'max_tokens':max_tokens,'temperature':0.7},timeout=20)
    d = r.json()
    if 'choices' in d:
        return d['choices'][0]['message']['content'].strip()
    raise Exception(d.get('error',{}).get('message','error'))

def generate(prompt, max_tokens=400):
    global _call_count
    _call_count += 1

    # Rotazione: pari=key1, dispari=key2
    groq_keys = []
    if GROQ_KEY_1: groq_keys.append(GROQ_KEY_1)
    if GROQ_KEY_2: groq_keys.append(GROQ_KEY_2)

    # 1. Try Groq con rotazione
    for i, key in enumerate(groq_keys):
        try:
            result = call_groq(key, prompt, max_tokens)
            if result and len(result) > 20:
                return result, f'groq-key{i+1}'
        except Exception as e:
            if 'Rate limit' in str(e):
                time.sleep(2)
            continue

    # 2. Fallback OpenRouter
    if OR_KEY:
        for model in OR_MODELS:
            try:
                r = requests.post('https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {OR_KEY}',
                        'Content-Type': 'application/json',
                        'HTTP-Referer': 'https://weatherarb.com',
                        'X-Title': 'WeatherArb'
                    },
                    json={'model': model,
                          'messages': [{'role':'user','content':prompt}],
                          'max_tokens': max_tokens},
                    timeout=30)
                d = r.json()
                if 'choices' in d:
                    text = d['choices'][0]['message']['content'].strip()
                    if len(text) > 20:
                        return text, model.split('/')[1]
            except: pass
            time.sleep(0.5)

    return None, None

if __name__ == '__main__':
    for i in range(5):
        result, src = generate(f"Write weather tip #{i+1} in 10 words.")
        print(f"[{src}]: {result}")
        time.sleep(0.5)
