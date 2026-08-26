from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, AsyncMock
from .models import Node, Metrics
from unittest.mock import patch
from .models import Node


class NodeRegistrationTests(APITestCase):

    def test_node_can_register_successfully(self):
        payload = {
            "node_name": "web_01",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "os_version": "12.31",
            "password": "StrongPassword123!"
        }

        response = self.client.post(
            "/api/register/",
            payload,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Node.objects.count(), 1)

        node = Node.objects.first()

        self.assertEqual(node.node_name, "web_01")
        self.assertEqual(node.mac_address, "00:1A:2B:3C:4D:5E")
        self.assertEqual(node.os_version, "12.31")
        self.assertTrue(node.check_password("StrongPassword123!"))

    def test_node_name_is_normalized_to_lowercase(self):
        payload = {
            "node_name": "WEB_02",
            "mac_address": "00:1A:2B:3C:4D:5F",
            "os_version": "12.31",
            "password": "StrongPassword123!"
        }

        response = self.client.post(
            "/api/register/",
            payload,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        node = Node.objects.get(mac_address="00:1A:2B:3C:4D:5F")

        self.assertEqual(node.node_name, "web_02")
    def test_duplicate_mac_address_is_rejected(self):
        payload = {
            "node_name": "web_01",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "os_version": "12.31",
            "password": "StrongPassword123!"
        }

        first_response = self.client.post(
            "/api/register/",
            payload,
            format="json"
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        payload["node_name"] = "web_02"

        second_response = self.client.post(
            "/api/register/",
            payload,
            format="json"
        )

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_fails_with_invalid_password(self):
        Node.objects.create_user(
            node_name="web_01",
            mac_address="00:1A:2B:3C:4D:5E",
            os_version="12.31",
            password="CorrectPassword123!"
        )

        response = self.client.post(
            "/api/login/",
            {
                "node_name": "web_01",
                "password": "WrongPassword123!"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_login_returns_tokens(self):
        Node.objects.create_user(
            node_name="web_01",
            mac_address="00:1A:2B:3C:4D:5E",
            os_version="12.31",
            password="CorrectPassword123!"
        )

        response = self.client.post(
            "/api/login/",
            {
                "node_name": "web_01",
                "password": "CorrectPassword123!"
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user_id", response.data)
        self.assertIn("node_name", response.data)
        self.assertIn("last_sent_seq_id", response.data)

        self.assertEqual(response.data["node_name"], "web_01")
        self.assertEqual(response.data["last_sent_seq_id"], 0)
    def test_unauthenticated_node_cannot_send_metrics(self):
        response = self.client.post(
            "/api/metrics/",
            {
                "node_server": 1,
                "seq_id": 1,
                "metrics": {
                    "cpu": 50,
                    "memory": 60,
                    "disk": 40
                }
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    @patch("clients.views.get_channel_layer")
    def test_authenticated_node_can_submit_metrics(self, mock_channel_layer):
        node = Node.objects.create_user(
            node_name="web_01",
            mac_address="00:1A:2B:3C:4D:5E",
            os_version="12.31",
            password="CorrectPassword123!"
        )

        login_response = self.client.post(
            "/api/login/",
            {
                "node_name": "web_01",
                "password": "CorrectPassword123!"
            },
            format="json"
        )

        access_token = login_response.data["access"]

        mock_layer = mock_channel_layer.return_value
        mock_layer.group_send = AsyncMock()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.post(
            "/api/metrics/",
            {
                "node_server": node.id,
                "seq_id": 1,
                "metrics": {
                    "cpu": 50,
                    "memory": 60,
                    "disk": 40
                }
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(
            Metrics.objects.filter(
                node_server=node,
                seq_id=1
            ).exists()
        )

    def test_cpu_severity_is_calculated_correctly(self):
        node = Node.objects.create_user(
            node_name="web_01",
            mac_address="00:1A:2B:3C:4D:5E",
            os_version="12.31",
            password="StrongPassword123!"
        )

        normal_data = {
            "node_server": node.id,
            "seq_id": 1,
            "metrics": {
                "cpu": 50,
                "memory": 60,
                "disk": 40
            }
        }

        warning_data = {
            "node_server": node.id,
            "seq_id": 2,
            "metrics": {
                "cpu": 80,
                "memory": 60,
                "disk": 40
            }
        }

        critical_data = {
            "node_server": node.id,
            "seq_id": 3,
            "metrics": {
                "cpu": 95,
                "memory": 60,
                "disk": 40
            }
        }

        from .serializers import MetricsSerializer

        normal_serializer = MetricsSerializer(data=normal_data)
        self.assertTrue(normal_serializer.is_valid())
        normal_metric = normal_serializer.save()

        warning_serializer = MetricsSerializer(data=warning_data)
        self.assertTrue(warning_serializer.is_valid())
        warning_metric = warning_serializer.save()

        critical_serializer = MetricsSerializer(data=critical_data)
        self.assertTrue(critical_serializer.is_valid())
        critical_metric = critical_serializer.save()

        self.assertEqual(normal_metric.severity, "NORMAL")
        self.assertEqual(warning_metric.severity, "WARNING")
        self.assertEqual(critical_metric.severity, "CRITICAL")

    @patch("clients.views.get_channel_layer")
    def test_duplicate_metric_returns_conflict(self, mock_channel_layer):
        node = Node.objects.create_user(
            node_name="web_01",
            mac_address="00:1A:2B:3C:4D:5E",
            os_version="12.31",
            password="StrongPassword123!"
        )

        login_response = self.client.post(
            "/api/login/",
            {
                "node_name": "web_01",
                "password": "StrongPassword123!"
            },
            format="json"
        )

        access_token = login_response.data["access"]

        mock_layer = mock_channel_layer.return_value
        mock_layer.group_send = AsyncMock()

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        payload = {
            "node_server": node.id,
            "seq_id": 1,
            "metrics": {
                "cpu": 50,
                "memory": 60,
                "disk": 40
            }
        }

        first_response = self.client.post(
            "/api/metrics/",
            payload,
            format="json"
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED
        )

        second_response = self.client.post(
            "/api/metrics/",
            payload,
            format="json"
        )


        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST
        )