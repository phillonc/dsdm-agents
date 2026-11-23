"""Execution evidence contract. Verification belongs to the hosting application.

Not exposed as an agent tool. The trusted callback must check authorization,
artifact bytes/hashes and passing reports against independent executor stores.
Model-supplied verification flags are never accepted as proof.
"""

from copy import deepcopy
from datetime import datetime
import re


def _timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamps require a timezone')
    return result


def verify_execution_evidence(evidence, expected_task_id, verifier):
    """Fail closed unless an application-bound verifier returns literal True.

    This contract does not implement a trusted executor, run tests or authorize
    deployments. Bind the verifier in application code, never from agent input.
    """
    if not callable(verifier):
        return dict(verified=False, reason='Independent verifier required')
    try:
        record = deepcopy(evidence)
        for key in ['execution_id', 'task_id', 'agent_id', 'authorization_decision_id']:
            if not isinstance(record[key], str) or not record[key].strip():
                raise ValueError('Missing ' + key)
        if not expected_task_id or record['task_id'] != expected_task_id:
            raise ValueError('Task mismatch')
        if _timestamp(record['finished_at']) < _timestamp(record['started_at']):
            raise ValueError('Reversed timestamps')
        for key in ['artifacts', 'tests']:
            if not isinstance(record[key], list) or not record[key]:
                raise ValueError('Missing ' + key)
        for artifact in record['artifacts']:
            if not isinstance(artifact['uri'], str) or not artifact['uri'].strip():
                raise ValueError('Missing artifact URI')
            if not isinstance(artifact['sha256'], str) or not re.fullmatch(r'[a-fA-F0-9]{64}', artifact['sha256']):
                raise ValueError('Invalid SHA-256')
        for test in record['tests']:
            if test['status'] != 'PASSED':
                raise ValueError('Test report did not pass')
            for key in ['suite', 'report_uri']:
                if not isinstance(test[key], str) or not test[key].strip():
                    raise ValueError('Missing test ' + key)
        record.pop('verification', None)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        return dict(verified=False, reason=f'Invalid evidence: {exc}')
    execution_id = record['execution_id']
    try:
        if verifier(record) is not True:
            return dict(verified=False, reason='Independent verification failed')
    except Exception:
        return dict(verified=False, reason='Independent verifier unavailable')
    return dict(verified=True, execution_id=execution_id, task_id=expected_task_id)
