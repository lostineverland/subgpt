'''Calculate the costs of the API usage
Pricing: https://platform.openai.com/docs/pricing
Copy and give to chatGPT
prompt: Please turn the following text copied from an html table into a markdown table and sort it by `input` reversed:
```txt
...
```
'''

s = '''
  | Model                        | input   | cached | output  |
  | o1-pro                       | $150.00 | -      | $600.00 |
  | gpt-4.5-preview              | $75.00  | $37.50 | $150.00 |
  | o1                           | $15.00  | $7.50  | $60.00  |
  | gpt-4o-realtime-preview      | $5.00   | $2.50  | $20.00  |
  | computer-use-preview         | $3.00   | -      | $12.00  |
  | gpt-4o-search-preview        | $2.50   | -      | $10.00  |
  | gpt-4o-audio-preview         | $2.50   | -      | $10.00  |
  | gpt-4o                       | $2.50   | $1.25  | $10.00  |
  | gpt-4.1                      | $2.00   | $0.50  | $8.00   |
  | o3-mini                      | $1.10   | $0.55  | $4.40   |
  | o1-mini                      | $1.10   | $0.55  | $4.40   |
  | gpt-4o-mini-realtime-preview | $0.60   | $0.30  | $2.40   |
  | gpt-4.1-mini                 | $0.40   | $0.10  | $1.60   |
  | gpt-4o-mini-search-preview   | $0.15   | -      | $0.60   |
  | gpt-4o-mini-audio-preview    | $0.15   | -      | $0.60   |
  | gpt-4o-mini                  | $0.15   | $0.075 | $0.60   |
  | gpt-4.1-nano                 | $0.10   | $0.025 | $0.40   |
'''
import json
proc_line = lambda s: filter(
    bars,
    s.replace('$', '').replace(' - ', ' 0 ').split())
bars = lambda s: s != '|'
lines = filter(None, s.split('\n'))
proc_line(next(lines))
OPEN_API_PRICING = {model: dict(input=float(input), cached=float(cached), output=float(output))
    for model, input, cached, output in map(proc_line, lines)}

def calc_cost(model, response):
    if isinstance(model, list): model = model[0]
    try:
        completion_tokens = int(response['usage']['completion_tokens'])
        prompt_tokens = int(response['usage']['prompt_tokens'])
        cached_tokens = int(response['usage']['prompt_tokens_details']['cached_tokens'])
        model_rates = OPEN_API_PRICING[model]
        input_price = (prompt_tokens - cached_tokens) * model_rates['input'] / 1e6
        cached_price = cached_tokens * model_rates['cached'] / 1e6
        output_price = completion_tokens * model_rates['output'] / 1e6
        return input_price + cached_price + output_price
    except:
        print(model, response)
        print('failed to get cost')
        return 'N/A'