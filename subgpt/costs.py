'''Calculate the costs of the API usage
Pricing: https://platform.openai.com/docs/pricing
Copy and give to chatGPT
prompt: Please turn the following text copied from an html table into a markdown table and sort it by `input` reversed:
```txt
...
```
'''

s = '''
  |    Model     | Input  | Cached |  Output |
  | gpt-5.5-pro  | $30.00 | -      | $180.00 |
  | gpt-5.4-pro  | $30.00 | -      | $180.00 |
  | gpt-5.5      | $5.00  | $0.50  | $30.00  |
  | gpt-5.4      | $2.50  | $0.25  | $15.00  |
  | gpt-5.4-mini | $0.75  | $0.075 | $4.50   |
  | gpt-5.4-nano | $0.20  | $0.02  | $1.25   |
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
    try:
        completion_tokens = int(response['usage']['completion_tokens'])
        prompt_tokens = int(response['usage']['prompt_tokens'])
        cached_tokens = int(response['usage']['prompt_tokens_details']['cached_tokens'])
        model_rates = OPEN_API_PRICING[model]
        input_price = (prompt_tokens - cached_tokens) * model_rates['input'] / 1e6
        cached_price = cached_tokens * model_rates['cached'] / 1e6
        output_price = completion_tokens * model_rates['output'] / 1e6
        return input_price + cached_price + output_price
    except Exception as e:
        print(model, response, e)
        print('failed to get cost')
        return 'N/A'