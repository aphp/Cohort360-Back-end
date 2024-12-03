from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from admin_cohort.services.maintenance import MaintenanceService, WSMaintenanceInfo


class TestMaintenanceService(TestCase):
    @patch('admin_cohort.services.maintenance.maintenance_phase_to_info')
    @patch('admin_cohort.services.maintenance.MaintenanceService.send_maintenance_notification')
    def test_send_deleted_maintenance_notification_within_time_range(self, mock_send_notification, mock_phase_to_info):
        now = timezone.now()
        maintenance_info = MagicMock()
        maintenance_info.start_datetime = now - timedelta(minutes=5)
        maintenance_info.end_datetime = now + timedelta(minutes=5)
        mock_phase_to_info.return_value = WSMaintenanceInfo(id=1, maintenance_start=str(maintenance_info.start_datetime),
                                                            maintenance_end=str(maintenance_info.end_datetime), active=True, type='test',
                                                            subject='test', message='test')

        MaintenanceService.send_deleted_maintenance_notification(maintenance_info)
        mock_send_notification.assert_called_once()

    @patch('admin_cohort.services.maintenance.maintenance_phase_to_info')
    @patch('admin_cohort.services.maintenance.MaintenanceService.send_maintenance_notification')
    def test_send_deleted_maintenance_notification_outside_time_range(self, mock_send_notification, mock_phase_to_info):
        now = timezone.now()
        maintenance_info = MagicMock()
        maintenance_info.start_datetime = now - timedelta(minutes=10)
        maintenance_info.end_datetime = now - timedelta(minutes=5)

        MaintenanceService.send_deleted_maintenance_notification(maintenance_info)
        mock_send_notification.assert_not_called()

    @patch('admin_cohort.services.maintenance.dateutil.parser.parse')
    @patch('admin_cohort.services.maintenance.MaintenancePhase.objects.filter')
    @patch('admin_cohort.services.maintenance.WebsocketManager.send_to_client')
    def test_send_maintenance_notification_active(self, mock_send_to_client, mock_filter, mock_parse):
        now = timezone.now()
        maintenance_info = WSMaintenanceInfo(id=1, maintenance_start=str(now - timedelta(minutes=5)),
                                             maintenance_end=str(now + timedelta(minutes=5)), active=True, type='test',
                                             subject='test', message='test')
        mock_parse.side_effect = [now - timedelta(minutes=5), now + timedelta(minutes=5)]
        mock_filter.return_value.exclude.return_value = []

        MaintenanceService.send_maintenance_notification(maintenance_info)
        mock_send_to_client.assert_called_once()

    @patch('admin_cohort.services.maintenance.dateutil.parser.parse')
    @patch('admin_cohort.services.maintenance.MaintenancePhase.objects.filter')
    @patch('admin_cohort.services.maintenance.WebsocketManager.send_to_client')
    def test_send_maintenance_notification_inactive_with_current_active(self, mock_send_to_client, mock_filter, mock_parse):
        now = timezone.now()
        maintenance_info = WSMaintenanceInfo(id=1, maintenance_start=str(now - timedelta(minutes=10)),
                                             maintenance_end=str(now - timedelta(minutes=5)), active=False, type='test',
                                             subject='test', message='test')
        mock_parse.side_effect = [now - timedelta(minutes=10), now - timedelta(minutes=5)]
        mock_filter.return_value.order_by.return_value.all.return_value = [MagicMock()]

        MaintenanceService.send_maintenance_notification(maintenance_info)
        mock_send_to_client.assert_not_called()
