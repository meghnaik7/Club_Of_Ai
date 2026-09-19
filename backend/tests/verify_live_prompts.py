import sys
import os
import io
sys.path.insert(0, os.path.abspath("."))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app.ai.llm_service import llm_service
from app.core.config import settings

print('==================================================')
print('           LIVE AI MODEL VERIFICATION             ')
print('==================================================')
print(f'Provider: {settings.PRIMARY_LLM_PROVIDER}')
print(f'Model:    {settings.PRIMARY_LLM_MODEL}')
print(f'Active:   {bool(settings.PRIMARY_LLM_API_KEY)}')
print('==================================================\n')

test_prompts = [
    {
        'category': '1. Event Planning',
        'prompt': 'Plan a 1-day AI Bootcamp with 3 phases: Morning Workshops, Afternoon Hackathon, and Evening Demos. Provide 1 sentence per phase.'
    },
    {
        'category': '2. Operational Guidance',
        'prompt': 'What are 3 critical checks a student club lead should perform 48 hours before a major tech symposium?'
    },
    {
        'category': '3. Social Announcement (WhatsApp style)',
        'prompt': 'Write a short 3-line high-energy announcement inviting students to the annual Robotics Expo.'
    },
    {
        'category': '4. Structured JSON Output',
        'prompt': 'Output only a JSON object with key "tasks", containing a list of 2 tasks. Each task has "title", "phase", and "priority". No prose outside the JSON.'
    }
]

for test in test_prompts:
    print(f'>>> CATEGORY: {test["category"]}')
    print(f'PROMPT: {test["prompt"]}')
    try:
        resp = llm_service.invoke(prompt=test['prompt'])
        print(f'STATUS: [SUCCESS] | Model: {resp.model_used} | Latency: {resp.latency_ms:.0f}ms | Fallback Used: {resp.fallback_used}')
        print('RESPONSE:')
        print(resp.content.strip())
    except Exception as exc:
        print(f'STATUS: [FAILED] -> {exc}')
    print('\n' + '-'*60 + '\n')
