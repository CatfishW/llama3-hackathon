from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

completion = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  
  extra_body={},
  #model="deepseek/deepseek-r1-distill-llama-70b:free",
  model="minimax/minimax-m2:free",
  messages=[
              {
                "role": "user",
                "content": "who are you"
              }
            ]
)
print(completion.choices[0].message.content)