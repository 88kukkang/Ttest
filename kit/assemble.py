"""Assemble a page: template + common.css + common.js + data JSON.

usage: python3 kit/assemble.py <template.html> <data.json> <out.html> [--standalone]

The template holds three placeholders: /*COMMON_CSS*/ inside <style>, /*COMMON_JS*/ inside the
script's IIFE, and `const DATA = /*DATA*/null;`. The output is an Artifact fragment (<title>,
<style>, <main>, <script>, no <html>/<head>). --standalone wraps it in a full HTML document so
it can be opened directly in a browser or hosted on a static site.
"""
import json, os, sys
args = [a for a in sys.argv[1:] if not a.startswith("--")]
tpl, data, out = args[:3]
K = os.path.dirname(os.path.abspath(__file__))
t = open(tpl, encoding="utf-8").read()
t = t.replace("/*COMMON_CSS*/", open(f"{K}/common.css", encoding="utf-8").read())
t = t.replace("/*COMMON_JS*/", open(f"{K}/common.js", encoding="utf-8").read())
t = t.replace("/*DATA*/null", json.dumps(json.load(open(data, encoding="utf-8")), ensure_ascii=False, separators=(",", ":")))
if "--standalone" in sys.argv:
    t = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n'
         + t + '\n</body>\n</html>\n')
open(out, "w", encoding="utf-8").write(t)
print(out, len(t))
