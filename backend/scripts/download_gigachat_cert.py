#!/usr/bin/env python3
"""
Script to download Russian Ministry of Digital Development (Минцифры) root certificate.

This certificate is required for GigaChat API SSL verification.
"""

import os
import sys
import urllib.request
from pathlib import Path


def download_certificate():
    """Download the Russian Ministry of Digital Development root certificate."""
    
    # URLs for the certificate (multiple sources for redundancy)
    urls = [
        "https://gu-st.ru/content/lending/russian_trusted_root_ca.cer",
        "https://www.ministry.digital.gov.ru/upload/cert/russian_trusted_root_ca.cer",
    ]
    
    # Target directory
    cert_dir = Path(__file__).parent.parent / "certs"
    cert_dir.mkdir(exist_ok=True)
    
    cert_path = cert_dir / "russian_trusted_root_ca.cer"
    
    print("="*60)
    print("Скачивание корневого сертификата НУЦ Минцифры")
    print("="*60)
    print(f"\nЦелевой путь: {cert_path}")
    
    # Try each URL
    for url in urls:
        print(f"\nПопытка скачивания с: {url}")
        try:
            urllib.request.urlretrieve(url, cert_path)
            print(f"✅ Сертификат успешно скачан!")
            print(f"   Размер: {cert_path.stat().st_size} байт")
            print(f"\n" + "="*60)
            print("ИНСТРУКЦИЯ ПО НАСТРОЙКЕ")
            print("="*60)
            print(f"\n1. Добавьте в backend/.env:")
            print(f"   GIGACHAT_CA_CERT_PATH={cert_path}")
            print(f"\n2. Перезапустите backend:")
            print(f"   uvicorn app.main:app --reload")
            print(f"\n3. Проверьте работу:")
            print(f"   python test_gigachat.py")
            print("="*60)
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            continue
    
    print("\n❌ Не удалось скачать сертификат ни с одного источника.")
    print("\nАльтернативные решения:")
    print("1. Скачайте сертификат вручную:")
    print("   https://gu-st.ru/content/lending/russian_trusted_root_ca.cer")
    print(f"   Сохраните в: {cert_path}")
    print("\n2. Или установите сертификат в системное хранилище Windows:")
    print("   - Откройте скачанный файл .cer")
    print("   - Нажмите 'Установить сертификат'")
    print("   - Выберите 'Локальная машина'")
    print("   - Выберите 'Поместить все сертификаты в следующее хранилище'")
    print("   - Выберите 'Доверенные корневые центры сертификации'")
    print("\n3. Или временно отключите проверку SSL (НЕ ДЛЯ ПРОДАКШЕНА):")
    print("   Удалите GIGACHAT_CA_CERT_PATH из backend/.env")
    
    return False


if __name__ == "__main__":
    success = download_certificate()
    sys.exit(0 if success else 1)
