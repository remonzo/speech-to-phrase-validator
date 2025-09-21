#!/usr/bin/env python3
"""Script per aggiornare automaticamente la versione in tutti i file."""

import re
from pathlib import Path
from version import VERSION

def update_config_yaml():
    """Aggiorna config.yaml con la versione corrente."""
    config_path = Path("config.yaml")
    if config_path.exists():
        content = config_path.read_text(encoding='utf-8')
        content = re.sub(r'version: "[^"]*"', f'version: "{VERSION}"', content)
        config_path.write_text(content, encoding='utf-8')
        print(f"✅ Updated config.yaml to version {VERSION}")

def update_js_file():
    """Aggiorna i riferimenti versione nel file JavaScript."""
    js_path = Path("src/web/static/js/app.js")
    if js_path.exists():
        content = js_path.read_text(encoding='utf-8')

        # Aggiorna header commento
        content = re.sub(
            r'Speech-to-Phrase Validator Frontend v[\d.]+',
            f'Speech-to-Phrase Validator Frontend v{VERSION}',
            content
        )

        # Aggiorna console.log
        content = re.sub(
            r"console\.log\('🎤 Speech-to-Phrase Validator v[\d.]+ - HA Add-on Optimized'\);",
            f"console.log('🎤 Speech-to-Phrase Validator v{VERSION} - HA Add-on Optimized');",
            content
        )

        # Aggiorna CONFIG.VERSION
        content = re.sub(
            r"VERSION: '[^']*'",
            f"VERSION: '{VERSION}'",
            content
        )

        js_path.write_text(content, encoding='utf-8')
        print(f"✅ Updated app.js to version {VERSION}")

if __name__ == "__main__":
    print(f"🔄 Updating version to {VERSION}")
    update_config_yaml()
    update_js_file()
    print("✅ Version update complete!")