"""Pyodide ile JavaScript arasında JSON tabanlı arayüz."""

import json

from .crossref import doi_requests
from .parse import parse
from .report import build, render


def collect_dois(text):
    return json.dumps(doi_requests(parse(text)))


def audit_json(text, responses_json=None):
    responses = json.loads(responses_json) if responses_json is not None else None
    report = build(text, crossref_responses=responses)
    return json.dumps({"report": report, "markdown": render(report, markdown=True)}, ensure_ascii=False)
