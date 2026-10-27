"""Executar da pasta do projeto: python exportar_openapi.py"""
import json
from pathlib import Path
from main import app

if __name__ == '__main__':
    Path(__file__).with_name('openapi.json').write_text(
        json.dumps(app.openapi(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('openapi.json atualizado.')
