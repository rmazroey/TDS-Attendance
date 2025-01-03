from django.db import connection
import os
import base64
import requests
from pprint import pprint
from django.core.management.base import BaseCommand, CommandError
from django.attend.util.logging import LogManagement
from django.attend.models import AttByModule
from django.sis.models import Module

class Command(BaseCommand):
    help = 'Imports attendance data from TDS API into the database.'
    log = LogManagement('TDS API Attendance import')

    def add_arguments(self, parser):
        parser.add_argument('--reportby', required=True)
        parser.add_argument('--week', required=True, type=int)
        parser.add_argument('--ay', required=True, type=int)
        parser.add_argument('--live_site', required=True)
        parser.add_argument('--del_existing', default='No')

    def handle(self, *args, **options):
        resource_type = options['reportby']
        if resource_type not in ['module']:
            raise CommandError("TDS ReportBy parameter not specified or invalid")

        tds_base_url, tds_access_username, tds_access_pass = self.get_tds_credentials(options['live_site'])

        try:
            week = int(options['week'])
            if week < 1 or week > 52:
                raise ValueError("Week must be between 1 and 52")
        except (ValueError, TypeError):
            raise CommandError("Invalid week value. It must be an integer between 1 and 52")

        if not (2018 <= options['ay'] <= 2030):
            raise CommandError("Academic Year must be between 2018 and 2030")

        if options['del_existing'].lower() in ['yes', 'y']:
            AttByModule.truncate()
            AttByModule.sequence_setval()

        self.log.startup_info(resource_type, tds_base_url, options['del_existing'], options['week'])

        credential = self.generate_basic_auth(tds_access_username, tds_access_pass)
        request_headers = {'Authorization': f'Basic {credential}'}
        
        qs = Module.objects.filter(
            academic_week_modules_monitored__ay=options['ay'],
            academic_week_modules_monitored__week_num=options['week']
        ).distinct()

        if not qs:
            self.log.fail_safe(99, {"CmdErr_ReportBy": "No modules found for monitoring"})
            raise CommandError("No modules added for monitoring")

        total_updated = 0
        for module in qs:
            total_updated += self.extract_and_process_attendance(module, tds_base_url, request_headers, options)
        
        total_objects = AttByModule.objects.filter(week=options['week'], week_ay=options['ay']).count()

        self.log.completion(total_updated, total_objects)

    def get_tds_credentials(self, live_site):
        if live_site.lower() in ['yes', 'y']:
            return os.getenv('TDS_LIVE_BASE_URL'), os.getenv('TDS_LIVE_ACCESS_USERNAME'), os.getenv('TDS_LIVE_ACCESS_PASSWORD')
        return os.getenv('TDS_TEST_BASE_URL'), os.getenv('TDS_TEST_ACCESS_USERNAME'), os.getenv('TDS_TEST_ACCESS_PASSWORD')

    def generate_basic_auth(self, username, password):
        encoded = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('ascii')
        return f"{encoded[:-2]}=="

    def extract_and_process_attendance(self, module, tds_base_url, request_headers, options):
        from_dt = f"{module['academic_week_modules_monitored__from_dt']}T00:00:00"
        to_dt = f"{module['academic_week_modules_monitored__to_dt']}T23:59:59"
        api_url = f"{tds_base_url}fromDate={from_dt}&toDate={to_dt}&reportBy=module&searchBy={module['id']}&historyData=true"
        
        response = requests.get(api_url, headers=request_headers)
        json_data = response.json()
        new_objects = []

        for item in json_data['items']:
            ay_of_module = ACADEMIC_YR_OF_SEMESTERS[module['id'][-6:]][0]
            obj, created = AttByModule.objects.update_or_create(
                att_user_id=item["student_id"],
                mod_offer_name=module['id'],
                week=options['week'],
                week_ay=options['ay'],
                defaults={
                    'attendance': item["attendance"],
                    'attended': item["attended"],
                    'approved_absence': item["approved_absence"],
                    'total_events': item["total_events"],
                    'late_count': item["late_count"],
                    'user_id': f"LON{item['student_id']}",
                    'ay': ay_of_module,
                }
            )
            if created:
                new_objects.append(obj.id)

        add_student_course_code()
        return len(new_objects)

def add_student_course_code():
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE attend_attbymodule
            SET course_code = subquery.course_code
            FROM (
                SELECT user_id, "primary", course_code FROM studentcourse WHERE "primary" = 'Y'
            ) AS subquery
            WHERE attend_attbymodule.user_id = subquery.user_id;
        """)
