import unittest
import subprocess
from tests.test_imputation import imputation_test

class TestCommanline(unittest.TestCase):
    p_value_threshold = 0.01
    def test_impute_runner_with_pedigree(self):
        command = ["python",
                   "impute_runner.py",
                   "test_data/sample.segments.gz",
                   "test_data/sample~",
                   "--from_chr", "1",
                   "--to_chr", "3",
                   "--pedigree", "test_data/sample.ped",
                   "--output_address", "outputs/tmp/test_sample_imputed~",
                   ]
        subprocess.check_call(command)
    
    def test_impute_runner_with_pedigree_control(self):
        command = ["python",
                   "impute_runner.py",
                   "-c",
                   "test_data/sample.segments.gz",
                   "test_data/sample~",
                   "--from_chr", "1",
                   "--to_chr", "3",
                   "--pedigree", "test_data/sample.ped",
                   "--output_address", "outputs/tmp/test_sample_imputed~",
                   ]
        subprocess.check_call(command)
        coef, z, p_value = imputation_test([1, 2],
                imputed_prefix = "outputs/tmp/test_sample_imputed",
                expected_prefix = "test_data/sample",
                )
        self.assertGreaterEqual(p_value[0], self.p_value_threshold)
        self.assertGreaterEqual(p_value[1], self.p_value_threshold)

    def test_impute_runner_with_king(self):
        command = ["python",
                   "impute_runner.py",
                   "test_data/sample.segments.gz",
                   "test_data/sample~",
                   "--from_chr", "1",
                   "--to_chr", "3",
                   "--king", "test_data/sample.king",
                   "--agesex", "test_data/sample.agesex",
                   "--output_address", "outputs/tmp/test_sample_imputed~",
                   ]
        subprocess.check_call(command)

    def test_impute_runner_with_king_control(self):
        command = ["python",
                   "impute_runner.py",
                   "-c",
                   "test_data/sample.segments.gz",
                   "test_data/sample~",
                   "--from_chr", "1",
                   "--to_chr", "3",
                   "--king", "test_data/sample.king",
                   "--agesex", "test_data/sample.agesex",
                   "--output_address", "outputs/tmp/test_sample_imputed~",
                   ]
        subprocess.check_call(command)
        coef, z, p_value = imputation_test([1, 2],
                imputed_prefix = "outputs/tmp/test_sample_imputed",
                expected_prefix = "test_data/sample",
                )
        self.assertGreaterEqual(p_value[0], self.p_value_threshold)
        self.assertGreaterEqual(p_value[1], self.p_value_threshold)


    def test_impute_runner_with_pedigree_control_multithread(self):
        command = ["python",
                   "impute_runner.py",
                   "-c",
                   "test_data/sample.segments.gz",
                   "test_data/sample~",
                   "--from_chr", "1",
                   "--to_chr", "3",
                   "--pedigree", "test_data/sample.ped",
                   "--output_address", "outputs/tmp/test_sample_imputed~",
                   "--threads", "2",
                   ]
        subprocess.check_call(command)
        coef, z, p_value = imputation_test([1, 2],
                imputed_prefix = "outputs/tmp/test_sample_imputed",
                expected_prefix = "test_data/sample",
                )
        self.assertGreaterEqual(p_value[0], self.p_value_threshold)
        self.assertGreaterEqual(p_value[1], self.p_value_threshold)

    def test_impute_runner_with_pedigree_control_multiprocess(self):
        command = ["python",
                   "impute_runner.py",
                   "-c",
                   "test_data/sample.segments.gz",
                   "test_data/sample~",
                   "--from_chr", "1",
                   "--to_chr", "3",
                   "--pedigree", "test_data/sample.ped",
                   "--output_address", "outputs/tmp/test_sample_imputed~",
                   "--processes", "2",
                   ]
        subprocess.check_call(command)
        coef, z, p_value = imputation_test([1, 2],
                imputed_prefix = "outputs/tmp/test_sample_imputed",
                expected_prefix = "test_data/sample",
                )
        self.assertGreaterEqual(p_value[0], self.p_value_threshold)
        self.assertGreaterEqual(p_value[1], self.p_value_threshold)

    def test_impute_runner_with_pedigree_control_notilda(self):
        command = ["python",
                   "impute_runner.py",
                   "-c",
                   "test_data/sample.segments.gz",
                   "test_data/sample1",
                   "--pedigree", "test_data/sample.ped",
                   "--output_address", "outputs/tmp/test_sample_imputed1",
                   "--threads", "2",
                   ]
        subprocess.check_call(command)
        coef, z, p_value = imputation_test([1],
                imputed_prefix = "outputs/tmp/test_sample_imputed",
                expected_prefix = "test_data/sample",
                )
        self.assertGreaterEqual(p_value[0], self.p_value_threshold)
        self.assertGreaterEqual(p_value[1], self.p_value_threshold)

