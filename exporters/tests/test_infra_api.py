from django.test import TestCase

from exporters.infra_api import get_tokens, InfraAPI


class TestInfraAPI(TestCase):
    def setUp(self):
        super().setUp()

    def test_successfully_get_tokens(self):
        bigdata_service = "bigdata"
        hadoop_service = "hadoop"
        token_for_bigdata = "token-for-bigdata"
        token_for_hadoop = "token-for-hadoop"
        tokens = f"{bigdata_service}:{token_for_bigdata},{hadoop_service}:{token_for_hadoop}"
        token_by_service = get_tokens(tokens)
        self.assertEqual(token_by_service[InfraAPI.Services.BIG_DATA], token_for_bigdata)
        self.assertEqual(token_by_service[InfraAPI.Services.HADOOP], token_for_hadoop)

    def test_error_get_tokens(self):
        wrong_service = "wrong"
        hadoop_service = "hadoop"
        token_for_bigdata = "token-for-bigdata"
        token_for_hadoop = "token-for-hadoop"
        tokens = f"{wrong_service}:{token_for_bigdata},{hadoop_service}:{token_for_hadoop}"
        with self.assertRaises(ValueError):
            _ = get_tokens(tokens)


