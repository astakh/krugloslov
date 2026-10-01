"""Test script for GigaChat API connection and debugging."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.llm import gigachat_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_config():
    """Test configuration."""
    print("\n" + "="*60)
    print("1. Проверка конфигурации")
    print("="*60)
    
    print(f"  AUTH_KEY: {'*' * 20}{settings.GIGACHAT_AUTH_KEY[-10:]}")
    print(f"  SCOPE: {settings.GIGACHAT_SCOPE}")
    print(f"  MODEL: {settings.GIGACHAT_MODEL}")
    print(f"  CA_CERT_PATH: {settings.GIGACHAT_CA_CERT_PATH or '(not set)'}")
    print(f"  MAX_CONCURRENCY: {settings.GIGACHAT_MAX_CONCURRENCY}")
    print(f"  REQUEST_TIMEOUT: {settings.LLM_REQUEST_TIMEOUT}s")
    print(f"  TOKEN_TIMEOUT: {settings.LLM_TOKEN_TIMEOUT}s")
    print(f"  GEN_TEMPERATURE: {settings.GEN_TEMPERATURE}")
    print(f"  EVAL_TEMPERATURE: {settings.EVAL_TEMPERATURE}")
    
    if not settings.GIGACHAT_AUTH_KEY or settings.GIGACHAT_AUTH_KEY == "your-gigachat-auth-key":
        print("\n❌ ОШИБКА: GIGACHAT_AUTH_KEY не установлен!")
        print("   Добавьте ваш ключ авторизации в backend/.env")
        return False
    
    print("\n✅ Конфигурация проверена")
    return True


async def test_token():
    """Test token retrieval."""
    print("\n" + "="*60)
    print("2. Получение токена")
    print("="*60)
    
    try:
        token = await gigachat_client._get_token()
        print(f"  ✅ Токен получен: {token[:20]}...")
        print(f"  ✅ Длина токена: {len(token)} символов")
        return True
    except Exception as e:
        print(f"  ❌ ОШИБКА получения токена: {e}")
        print("\n  Возможные причины:")
        print("  - Неправильный GIGACHAT_AUTH_KEY")
        print("  - Неправильный GIGACHAT_SCOPE")
        print("  - Проблемы с SSL сертификатом")
        print("  - Нет доступа к интернету")
        return False


async def test_simple_chat():
    """Test simple chat request."""
    print("\n" + "="*60)
    print("3. Простой запрос к модели")
    print("="*60)
    
    try:
        messages = [
            {"role": "user", "content": "Скажи 'тест' одним словом."}
        ]
        
        print("  Отправка запроса...")
        response = await gigachat_client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=50,
            timeout=30.0,
        )
        
        content = response.get('content', '')
        print(f"  ✅ Ответ получен: {content[:100]}...")
        print(f"  ✅ Finish reason: {response.get('finish_reason')}")
        print(f"  ✅ Tokens used: {response.get('usage', {})}")
        return True
    except Exception as e:
        print(f"  ❌ ОШИБКА запроса: {e}")
        print("\n  Возможные причины:")
        print("  - Таймаут запроса")
        print("  - Превышен лимит запросов")
        print("  - Недостаточно токенов на аккаунте")
        return False


async def test_lesson_generation():
    """Test lesson generation scenario."""
    print("\n" + "="*60)
    print("4. Тест генерации предложений для урока")
    print("="*60)
    
    try:
        system_prompt = """You are an English language teacher. Generate 2 English sentences for a student at A1 level.

Requirements:
- Each sentence must contain the target word
- Sentences should be natural and contextually appropriate
- Use vocabulary appropriate for A1 level
- Each sentence should be 5-15 words long
- Provide a Russian translation for each sentence

Return JSON format:
{
  "sentences": [
    {
      "english": "English sentence with target word",
      "russian": "Russian translation"
    }
  ]
}"""
        
        user_prompt = """Generate 2 English sentences, one for each word group.

Groups:
Group 0: run (verb)
Group 1: fast (adverb)

Return JSON with 'sentences' array."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        print("  Отправка запроса на генерацию...")
        print(f"  System prompt: {len(system_prompt)} символов")
        print(f"  User prompt: {len(user_prompt)} символов")
        
        response = await gigachat_client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            timeout=60.0,
        )
        
        content = response.get('content', '')
        print(f"  ✅ Ответ получен ({len(content)} символов)")
        print(f"  ✅ Finish reason: {response.get('finish_reason')}")
        print(f"  ✅ Tokens used: {response.get('usage', {})}")
        
        # Try to parse JSON
        import json
        try:
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            data = json.loads(content.strip())
            print(f"  ✅ JSON распарсен успешно")
            print(f"  ✅ Найдено предложений: {len(data.get('sentences', []))}")
            
            for i, sentence in enumerate(data.get('sentences', []), 1):
                print(f"     {i}. {sentence.get('english', 'N/A')}")
                print(f"        → {sentence.get('russian', 'N/A')}")
            
            return True
        except json.JSONDecodeError as e:
            print(f"  ⚠️  ОШИБКА парсинга JSON: {e}")
            print(f"  Ответ модели:\n{content[:500]}...")
            return False
            
    except Exception as e:
        print(f"  ❌ ОШИБКА запроса: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ GIGACHAT API")
    print("="*60)
    
    results = []
    
    # Test 1: Configuration
    result = await test_config()
    results.append(("Конфигурация", result))
    
    if not result:
        print("\n❌ Тестирование прервано из-за ошибки конфигурации")
        return
    
    # Test 2: Token
    result = await test_token()
    results.append(("Получение токена", result))
    
    if not result:
        print("\n❌ Тестирование прервано из-за ошибки получения токена")
        return
    
    # Test 3: Simple chat
    result = await test_simple_chat()
    results.append(("Простой запрос", result))
    
    # Test 4: Lesson generation
    result = await test_lesson_generation()
    results.append(("Генерация урока", result))
    
    # Summary
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 Все тесты пройдены успешно!")
        print("   GigaChat API работает корректно.")
    else:
        print("\n⚠️  Некоторые тесты не пройдены.")
        print("   Проверьте логи выше для диагностики проблем.")
        print("\n📖 Дополнительная информация:")
        print("   - backend/GIGACHAT_DEBUG_GUIDE.md")
        print("   - https://developers.sber.ru/docs/ru/gigachat/api/main")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
