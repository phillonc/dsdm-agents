# Dependency Report — Customer Feedback Portal

_Produced by the `pen-tester` agent · `/security-review`_

**Tooling:** `npm audit` (Node.js project — `bandit`/`safety`/`pip-audit`
skipped, no Python sources in scope)

## Summary

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Moderate | 1 |
| Low | 0 |

## Details

| Package | Installed | Fixed in | Path | Severity |
|---|---|---|---|---|
| `lodash` | 4.17.19 | 4.17.21 | `express-validator > lodash` (transitive, dev) | Moderate |

## Recommendation

```bash
npm audit fix
# or, if the transitive resolution doesn't pick it up:
npm install lodash@^4.17.21 --save-dev
```

No direct (non-transitive) dependencies have known vulnerabilities as of
this scan.
