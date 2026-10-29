import json
from pathlib import Path
import unittest
from test_backend import BackendTests as Helpers

class LoopCases(unittest.TestCase):
    setUpClass = classmethod(Helpers.setUpClass.__func__)
    tearDownClass = classmethod(Helpers.tearDownClass.__func__)
    setUp = Helpers.setUp
    emit = Helpers.emit
    output = Helpers.output
    compile = Helpers.compile
    launch = Helpers.launch
    finish = Helpers.finish
    def test_control_flow_and_input_cases(self):
        for case in json.loads((Path(__file__).parent/'program_cases.json').read_text()):
            with self.subTest(case=case['name']):
                self.events.clear()
                self.running.clear()
                self.prompt.clear()
                self.backend.reset()
                if 'EOF loop' in case['name']:
                    thread,outcomes=self.launch(self.compile(case['source']),initial_input=case['input'])
                    self.backend.close_input()
                    result=self.finish(thread,outcomes)
                else:
                    result=self.backend.run(self.compile(case['source']),initial_input=case['input'])
                self.assertEqual(result.returncode,0)
                self.assertEqual(self.output(),case['output'])

del Helpers
