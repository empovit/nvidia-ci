import copy
import unittest
from utils import calculate_diffs, create_tests_matrix

base_versions = {
    'gpu-main-latest': 'A',
    'gpu-operator': {
        '25.1': '25.1.0',
        '25.2': '25.2.0'
    },
    'ocp': {
        '4.12': '4.12.1',
        '4.14': '4.14.1'
    }
}

class TestCreateTestsMatrix(unittest.TestCase):

    def test_bundle_changed(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        new_versions['gpu-main-latest'] = 'B'
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {'gpu-main-latest': 'B'})

    def test_gpu_version_changed(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        new_versions['gpu-operator']['25.1'] = '25.1.1'
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {'gpu-operator': {'25.1': '25.1.1'}})

    def test_gpu_version_added(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        new_versions['gpu-operator']['25.3'] = '25.3.0'
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {'gpu-operator': {'25.3': '25.3.0'}})

    def test_gpu_version_removed(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        del new_versions['gpu-operator']['25.2']
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {})

    def test_ocp_version_changed(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        new_versions['ocp']['4.12'] = '4.12.2'
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {'ocp': {'4.12': '4.12.2'}})

    def test_ocp_version_added(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        new_versions['ocp']['4.15'] = '4.15.0'
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {'ocp': {'4.15': '4.15.0'}})

    def test_ocp_version_removed(self):
        old_versions = base_versions
        new_versions = copy.deepcopy(old_versions)
        del new_versions['ocp']['4.14']
        diff = calculate_diffs(old_versions, new_versions)
        self.assertEqual(diff, {})

if __name__ == '__main__':
    unittest.main()