# Copyright 2025. ThingsBoard
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from unittest.mock import patch, MagicMock
from tb_gateway_mqtt import TBGatewayMqttClient
from tb_device_mqtt import TBDeviceMqttClient
import threading


class TestOnServiceConfiguration(unittest.TestCase):
    def setUp(self):
        self.client = TBGatewayMqttClient("localhost", 1883, "dummy_token")
        if not hasattr(self.client, "_lock"):
            self.client._lock = threading.Lock()
        self.client._devices_connected_through_gateway_messages_rate_limit = MagicMock()
        self.client._devices_connected_through_gateway_telemetry_messages_rate_limit = MagicMock()
        self.client._devices_connected_through_gateway_telemetry_datapoints_rate_limit = MagicMock()
        self.client.rate_limits_received = False

    def test_on_service_configuration_error(self):
        error_response = {"error": "timeout"}
        parent_class = self.client.__class__.__bases__[0]
        with patch.object(parent_class, "on_service_configuration") as mock_parent_on_service_configuration:
            self.client._TBGatewayMqttClient__on_service_configuration("dummy_arg", error_response)
            self.assertTrue(self.client.rate_limits_received)
            mock_parent_on_service_configuration.assert_not_called()

    def test_on_service_configuration_valid(self):
        response = {
            "gatewayRateLimits": {
                "messages": "10:20",
                "telemetryMessages": "30:40",
                "telemetryDataPoints": "50:60",
            },
            "rateLimits": {"limit": "value"},
            "other_config": "other_value"
        }
        response_copy = response.copy()
        parent_class = self.client.__class__.__bases__[0]
        with patch.object(parent_class, "on_service_configuration") as mock_parent_on_service_configuration:
            self.client._TBGatewayMqttClient__on_service_configuration("dummy_arg", response_copy, "extra_arg", key="extra")
            self.client._devices_connected_through_gateway_messages_rate_limit.set_limit.assert_called_with("10:20")
            self.client._devices_connected_through_gateway_telemetry_messages_rate_limit.set_limit.assert_called_with("30:40")
            self.client._devices_connected_through_gateway_telemetry_datapoints_rate_limit.set_limit.assert_called_with("50:60")
            expected_dict = {'rateLimit': {"limit": "value"}, "other_config": "other_value"}
            mock_parent_on_service_configuration.assert_called_with("dummy_arg", expected_dict, "extra_arg", key="extra")

    def test_on_service_configuration_default_telemetry_datapoints(self):
        response = {
            "gatewayRateLimits": {
                "messages": "10:20",
                "telemetryMessages": "30:40",
            },
            "rateLimits": {"limit": "value"},
            "other_config": "other_value"
        }
        response_copy = response.copy()
        parent_class = self.client.__class__.__bases__[0]
        with patch.object(parent_class, "on_service_configuration") as mock_parent_on_service_configuration:
            self.client._TBGatewayMqttClient__on_service_configuration("dummy_arg", response_copy, "extra_arg", key="extra")
            self.client._devices_connected_through_gateway_telemetry_datapoints_rate_limit.set_limit.assert_called_with("0:0,")
            expected_dict = {'rateLimit': {"limit": "value"}, "other_config": "other_value"}
            mock_parent_on_service_configuration.assert_called_with("dummy_arg", expected_dict, "extra_arg", key="extra")


class TestRateLimitInitialization(unittest.TestCase):
    @staticmethod
    def fake_init(instance, host, port, username, password, quality_of_service, client_id, **kwargs):
        instance._init_kwargs = kwargs
        instance._client = MagicMock()

    def test_custom_rate_limits(self):
        custom_rate = "MY_RATE_LIMIT"
        custom_dp = "MY_RATE_LIMIT_DP"

        with patch("tb_gateway_mqtt.RateLimit.__init__", return_value=None), \
                patch("tb_gateway_mqtt.RateLimit.get_rate_limits_by_host", return_value=(custom_rate, custom_dp)), \
                patch("tb_gateway_mqtt.RateLimit.get_rate_limit_by_host", return_value=custom_rate), \
                patch.object(TBDeviceMqttClient, '__init__', new=TestRateLimitInitialization.fake_init):
            client = TBGatewayMqttClient(
                host="localhost",
                port=1883,
                username="dummy_token",
                rate_limit=custom_rate,
                dp_rate_limit=custom_dp
            )
            captured = client._init_kwargs

        self.assertEqual(captured.get("messages_rate_limit"), custom_rate)
        self.assertEqual(captured.get("telemetry_rate_limit"), custom_rate)
        self.assertEqual(captured.get("telemetry_dp_rate_limit"), custom_dp)

    def test_default_rate_limits(self):
        default_rate = "DEFAULT_RATE_LIMIT"
        with patch("tb_gateway_mqtt.RateLimit.__init__", return_value=None), \
                patch("tb_gateway_mqtt.RateLimit.get_rate_limits_by_host",
                      return_value=("DEFAULT_MESSAGES_RATE_LIMIT", "DEFAULT_TELEMETRY_DP_RATE_LIMIT")), \
                patch("tb_gateway_mqtt.RateLimit.get_rate_limit_by_host", return_value="DEFAULT_MESSAGES_RATE_LIMIT"), \
                patch.object(TBDeviceMqttClient, '__init__', new=TestRateLimitInitialization.fake_init):
            client = TBGatewayMqttClient(
                host="localhost",
                port=1883,
                username="dummy_token",
                rate_limit=default_rate,
                dp_rate_limit=default_rate
            )
            captured = client._init_kwargs

        self.assertEqual(captured.get("messages_rate_limit"), "DEFAULT_MESSAGES_RATE_LIMIT")
        self.assertEqual(captured.get("telemetry_rate_limit"), "DEFAULT_TELEMETRY_RATE_LIMIT")
        self.assertEqual(captured.get("telemetry_dp_rate_limit"), "DEFAULT_TELEMETRY_DP_RATE_LIMIT")


if __name__ == '__main__':
    unittest.main()
