"""Provider-independent DSDM plans, test specifications and traceability."""

import json
from .tool_registry import Tool

PRIORITIES = ['must_have', 'should_have', 'could_have', 'wont_have']
LEVELS = ['UNIT', 'INTEGRATION', 'E2E']


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected a non-empty string')
    return value.strip()


def build_traceability(plan):
    """Map explicit requirement IDs to work items and their test specifications."""
    return [dict(requirement_id=rid, work_item_id=item['id'],
                 acceptance_criteria_ids=[a['id'] for a in item.get('acceptance_criteria', [])],
                 test_case_ids=[t['id'] for t in item.get('test_cases', [])])
            for item in plan['items'] for rid in item.get('requirement_ids', [])]


def review_development_plan(plan, max_story_points=8):
    """Check specification completeness. This does not execute or verify tests."""
    if (not isinstance(max_story_points, int) or isinstance(max_story_points, bool)) or max_story_points < 1:
        raise ValueError('max_story_points must be a positive integer')
    items = plan['items']
    if not isinstance(items, list) or not items:
        raise ValueError('Plan needs a non-empty items array')
    issues, ids, test_ids = [], set(), set()
    parents = dict(FEATURE='GOAL', EPIC='FEATURE', STORY='EPIC', TASK='STORY')
    by_id = {text(i['id']): i for i in items}

    def issue(item, rule):
        issues.append(dict(item_id=item['id'], rule=rule))

    for item in items:
        kind = item.get('type')
        if item['id'] in ids:
            issue(item, 'DUPLICATE_ID')
        ids.add(item['id'])
        if kind not in ['GOAL', *parents]:
            issue(item, 'ITEM_TYPE')
        if kind in parents and by_id.get(item.get('parent_id'), {}).get('type') != parents[kind]:
            issue(item, 'HIERARCHY')
        if kind == 'GOAL' and item.get('parent_id'):
            issue(item, 'HIERARCHY')
        if not isinstance(item.get('title'), str) or not item['title'].strip():
            issue(item, 'TITLE_REQUIRED')
        sources = item.get('requirement_ids')
        if not isinstance(sources, list) or not sources or any(not isinstance(r, str) or not r.strip() for r in sources):
            issue(item, 'SOURCE_REQUIRED')
        if kind != 'STORY':
            continue
        ac = item.get('acceptance_criteria', [])
        ac_ids = {text(a['id']) for a in ac}
        if not ac or len(ac_ids) != len(ac) or any(not isinstance(a.get('text'), str) or not a['text'].strip() for a in ac):
            issue(item, 'AC_REQUIRED')
        points = item.get('story_points')
        if (not isinstance(points, int) or isinstance(points, bool)) or not 1 <= points <= max_story_points:
            issue(item, 'STORY_SIZE')
        if item.get('priority') not in PRIORITIES:
            issue(item, 'MOSCOW_REQUIRED')
        tests = item.get('test_cases', [])
        for level in LEVELS:
            if not any(t.get('level') == level for t in tests):
                issue(item, 'TEST_LEVEL_' + level)
        mapped = set()
        for test in tests:
            tid = text(test['id'])
            if tid in test_ids:
                issue(item, 'DUPLICATE_TEST_ID')
            test_ids.add(tid)
            refs = set(test.get('acceptance_criteria_ids', []))
            if not refs or not refs <= ac_ids:
                issue(item, 'TEST_MAPPING')
            mapped.update(refs)
            if test.get('level') not in LEVELS:
                issue(item, 'TEST_LEVEL_INVALID')
            if not isinstance(test.get('objective'), str) or not test['objective'].strip():
                issue(item, 'TEST_OBJECTIVE')
        if ac_ids - mapped:
            issue(item, 'AC_COVERAGE')
    if not any(i.get('type') == 'STORY' for i in items):
        issue(items[0], 'STORY_REQUIRED')
    return dict(passed=not issues, issues=issues, items_reviewed=len(items),
                coverage_kind='specification', execution_verified=False)


def generate_development_plan(requirements, goal):
    """Expand one structured requirement per story into a deterministic hierarchy.

    Caller supplies feature/epic grouping and acceptance criteria. Generated test
    objectives remain draft specifications, not executable tests or passing runs.
    """
    goal = text(goal)
    if not isinstance(requirements, list) or not requirements:
        raise ValueError('requirements must be a non-empty array')
    items = [dict(id='goal-1', type='GOAL', title=goal, requirement_ids=[])]
    features, epics, seen = {}, {}, set()
    for n, req in enumerate(requirements, 1):
        rid, title = text(req['id']), text(req['title'])
        feature, epic = text(req['feature']), text(req['epic'])
        if rid in seen:
            raise ValueError('Duplicate requirement ID: ' + rid)
        seen.add(rid)
        priority = req.get('priority', 'must_have')
        if priority not in PRIORITIES:
            raise ValueError('Invalid MoSCoW priority')
        criteria = req.get('acceptance_criteria', [])
        if not isinstance(criteria, list):
            raise ValueError('acceptance_criteria must be an array')
        criteria = [text(c) for c in criteria]
        points = req.get('story_points', 3)
        if (not isinstance(points, int) or isinstance(points, bool)) or points < 1:
            raise ValueError('story_points must be a positive integer')
        if feature not in features:
            features[feature] = f'feature-{len(features) + 1}'
            items.append(dict(id=features[feature], type='FEATURE', title=feature,
                              parent_id='goal-1', requirement_ids=[]))
        key = (feature, epic)
        if key not in epics:
            epics[key] = f'epic-{len(epics) + 1}'
            items.append(dict(id=epics[key], type='EPIC', title=epic,
                              parent_id=features[feature], requirement_ids=[]))
        for ancestor in items:
            if ancestor['id'] in ['goal-1', features[feature], epics[key]]:
                ancestor['requirement_ids'].append(rid)
        sid = f'story-{n}'
        ac = [dict(id=f'{sid}-ac-{i}', text=c) for i, c in enumerate(criteria, 1)]
        tests = [dict(id=f'{sid}-{level.lower()}-{i}', level=level,
                      acceptance_criteria_ids=[a['id']], objective=a['text'],
                      specification_status='DRAFT')
                 for i, a in enumerate(ac, 1) for level in LEVELS]
        items.append(dict(id=sid, type='STORY', title=title, parent_id=epics[key],
                          requirement_ids=[rid], priority=priority, story_points=points,
                          acceptance_criteria=ac, test_cases=tests))
        items.append(dict(id=f'task-{n}', type='TASK', title='Implement: ' + title,
                          parent_id=sid, priority=priority, requirement_ids=[rid]))
    plan = dict(items=items)
    plan['traceability'] = build_traceability(plan)
    plan['review'] = review_development_plan(plan)
    return plan


def register_planning_tools(registry):
    """Register pure operations for the Python runtime and pi bridge."""
    requirement_schema = dict(type='object', properties={
        'id': {'type': 'string'}, 'title': {'type': 'string'},
        'feature': {'type': 'string'}, 'epic': {'type': 'string'},
        'priority': {'type': 'string', 'enum': PRIORITIES},
        'story_points': {'type': 'integer', 'minimum': 1},
        'acceptance_criteria': {'type': 'array', 'items': {'type': 'string'}}},
        required=['id', 'title', 'feature', 'epic', 'acceptance_criteria'])
    definitions = [
        ('generate_development_plan', generate_development_plan,
         {'requirements': {'type': 'array', 'items': requirement_schema}, 'goal': {'type': 'string'}},
         ['requirements', 'goal'], 'Build a DSDM hierarchy with draft test specifications. No tests execute.'),
        ('review_development_plan', review_development_plan,
         {'plan': {'type': 'object'}, 'max_story_points': {'type': 'integer', 'minimum': 1}},
         ['plan'], 'Check hierarchy, MoSCoW, story size and acceptance-to-test mappings. Specification review only.'),
        ('build_traceability', build_traceability, {'plan': {'type': 'object'}},
         ['plan'], 'Map requirements to work items, acceptance criteria and test specifications.')]
    for name, handler, properties, required, description in definitions:
        def execute(_handler=handler, **kwargs):
            return json.dumps(_handler(**kwargs))
        registry.register(Tool(name=name, description=description, handler=execute,
                               input_schema=dict(type='object', properties=properties, required=required),
                               category='planning'))
