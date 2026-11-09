---
name: Bug report
about: Report something that doesn't work as documented
labels: bug
---

## Summary
<!-- One or two sentences. -->

## Task reference
<!-- Which task ID from tasks.md / which module failed? -->

## Steps to reproduce
1.
2.
3.

## Expected behavior

## Actual behavior

## Error output
```text
<paste logs / response JSON>
```

## Environment
- OS:
- Component: backend / agent / integrations / frontend / voice
- Commit / branch:

## Diagnostics checklist
- [ ] Backend reachable (`GET /api/v1/health` returns 200)?
- [ ] Ollama running (`OLLAMA_BASE_URL` reachable)?
- [ ] Spreadsheet ID and credentials valid?
- [ ] Only reproducible with real Google Sheets (needs credentials)?
