"""Offline regression tests for portable planning and evidence contracts."""
from copy import deepcopy
import json
import unittest

from src.tools.planning_tools import generate_development_plan, review_development_plan
from src.tools.dsdm_tools import create_dsdm_tool_registry
from src.orchestrator.execution_evidence import verify_execution_evidence


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.reqs = [dict(id='r1', title='Export report', feature='Reports', epic='Export',
                         priority='must_have', story_points=3,
                         acceptance_criteria=['Given a report, when exported, then a CSV downloads'])]

    def plan(self):
        return generate_development_plan(self.reqs, 'Portable reports')

    def test_deterministic_hierarchy_and_traceability(self):
        before = deepcopy(self.reqs)
        plan = self.plan()
        self.assertEqual([i['type'] for i in plan['items']], ['GOAL', 'FEATURE', 'EPIC', 'STORY', 'TASK'])
        self.assertEqual(plan, self.plan())
        self.assertEqual(self.reqs, before)
        self.assertTrue(plan['review']['passed'])
        self.assertFalse(plan['review']['execution_verified'])
        link = plan['traceability'][3]
        self.assertEqual(link['requirement_id'], 'r1')
        self.assertEqual(link['acceptance_criteria_ids'], ['story-1-ac-1'])
        self.assertEqual(len(link['test_case_ids']), 3)

    def test_grouping(self):
        self.reqs.append(dict(self.reqs[0], id='r2'))
        plan = self.plan()
        self.assertEqual(sum(i['type'] == 'FEATURE' for i in plan['items']), 1)
        self.assertEqual(plan['items'][0]['requirement_ids'], ['r1', 'r2'])
        self.assertTrue(plan['review']['passed'])

    def test_invalid_inputs(self):
        for change in [dict(priority='urgent'), dict(story_points=True), dict(story_points=0),
                       dict(acceptance_criteria='text'), dict(title='')]:
            original = deepcopy(self.reqs)
            with self.subTest(change=change):
                self.reqs[0].update(change)
                with self.assertRaises(ValueError):
                    self.plan()
            self.reqs = original
        self.reqs *= 2
        with self.assertRaises(ValueError):
            self.plan()

    def test_missing_criteria_and_large_story_block(self):
        self.reqs[0].update(acceptance_criteria=[], story_points=13)
        review = self.plan()['review']
        self.assertFalse(review['passed'])
        self.assertTrue({'AC_REQUIRED', 'STORY_SIZE', 'TEST_LEVEL_UNIT'} <= {i['rule'] for i in review['issues']})

    def test_invalid_mapping_parent_and_duplicate_test(self):
        plan = self.plan()
        story = plan['items'][3]
        story['parent_id'] = 'missing'
        story['test_cases'][0]['acceptance_criteria_ids'] = ['invented']
        story['test_cases'][1]['id'] = story['test_cases'][0]['id']
        rules = {i['rule'] for i in review_development_plan(plan)['issues']}
        self.assertTrue({'HIERARCHY', 'TEST_MAPPING', 'DUPLICATE_TEST_ID'} <= rules)

    def test_uncovered_criteria_and_missing_level(self):
        plan = self.plan()
        story = plan['items'][3]
        story['acceptance_criteria'].append(dict(id='extra', text='Another criterion'))
        story['test_cases'] = story['test_cases'][:1]
        rules = {i['rule'] for i in review_development_plan(plan)['issues']}
        self.assertTrue({'AC_COVERAGE', 'TEST_LEVEL_E2E', 'TEST_LEVEL_INTEGRATION'} <= rules)

    def test_no_stories_cannot_pass(self):
        plan = self.plan()
        plan['items'] = plan['items'][:1]
        self.assertFalse(review_development_plan(plan)['passed'])

    def test_registry(self):
        registry = create_dsdm_tool_registry(include_file_tools=False, include_git_pin=False, include_mcp=False)
        plan = json.loads(registry.execute('generate_development_plan', requirements=self.reqs, goal='Reports'))
        self.assertTrue(json.loads(registry.execute('review_development_plan', plan=plan))['passed'])
        self.assertEqual(json.loads(registry.execute('build_traceability', plan=plan)), plan['traceability'])
        self.assertIsNone(registry.get('verify_execution_evidence'))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(execution_id='run1', task_id='task1', agent_id='tester',
                           authorization_decision_id='decision1', started_at='2026-01-01T10:00:00Z',
                           finished_at='2026-01-01T10:01:00Z',
                           artifacts=[dict(uri='artifact:report', sha256='a' * 64)],
                           tests=[dict(suite='unit', status='PASSED', report_uri='report:unit')])

    def verify(self, verifier=lambda e: True):
        return verify_execution_evidence(self.record, 'task1', verifier)

    def test_requires_independent_verifier(self):
        self.assertTrue(self.verify()['verified'])
        for verifier in [None, lambda e: False, lambda e: 'true']:
            self.assertFalse(self.verify(verifier)['verified'])

    def test_model_flags_ignored_and_input_not_mutated(self):
        self.record['verification'] = dict(verified=True)
        self.assertFalse(self.verify(lambda e: False)['verified'])
        self.assertTrue(self.verify(lambda e: 'verification' not in e)['verified'])
        self.assertIn('verification', self.record)

    def test_malformed_records_do_not_reach_verifier(self):
        original = deepcopy(self.record)
        for change in [dict(task_id='other'), dict(artifacts=[]), dict(tests=[]),
                       dict(started_at='bad'), dict(started_at='2026-01-01T10:00:00'),
                       dict(finished_at='2025-01-01T00:00:00Z'),
                       dict(artifacts=[dict(uri='x', sha256='bad')]),
                       dict(tests=[dict(suite='unit', status='FAILED', report_uri='x')])]:
            with self.subTest(change=change):
                self.record = dict(original, **change)
                called = []
                self.assertFalse(self.verify(lambda e: called.append(e))['verified'])
                self.assertFalse(called)

    def test_verifier_errors_fail_closed(self):
        def unavailable(record):
            raise RuntimeError('offline')
        self.assertFalse(self.verify(unavailable)['verified'])
