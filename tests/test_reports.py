import importlib.util
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models import ReportFormat, ReportGenerationRequest, ReportScope
from app.services.data_service import data_service
from app.services.report_service import report_service
from app.services.trends_service import trends_service


HAS_EXPORT_DEPS = all(
    importlib.util.find_spec(module_name) is not None
    for module_name in ["docx", "reportlab"]
)


class DataServiceSmokeTests(unittest.TestCase):
    def test_years_and_summary_are_available(self):
        years = data_service.get_available_years()
        self.assertIn(2024, years)

        summary = data_service.get_year_statistics(2024)
        self.assertIsNotNone(summary)
        self.assertGreater(summary.total_population, 0)

    def test_growth_decline_has_results(self):
        result = trends_service.get_growth_decline(2012, 2024, limit=5)
        self.assertTrue(result.growth)
        self.assertTrue(result.decline)


class ReportPayloadStructureTests(unittest.IsolatedAsyncioTestCase):
    async def test_russia_payload_contains_required_sections(self):
        payload = await report_service._build_payload(
            ReportGenerationRequest(
                start_year=2020,
                end_year=2024,
                scope=ReportScope.RUSSIA,
                include_ai_summary=False,
            )
        )

        headings = [section.heading for section in payload.sections]
        self.assertEqual(
            headings[:4],
            [
                "Краткое резюме динамики населения",
                "Выявленные демографические тенденции и возможные факторы влияния",
                "Прогнозная оценка на 5-10 лет",
                "Рекомендации по социальной политике и территориальному планированию",
            ],
        )

        forecast_section = next(
            section
            for section in payload.sections
            if section.heading == "Прогнозная оценка на 5-10 лет"
        )
        self.assertEqual(len(forecast_section.tables), 1)
        self.assertEqual(forecast_section.tables[0].rows[0][0], "Через 5 лет")
        self.assertEqual(forecast_section.tables[0].rows[1][0], "Через 10 лет")

        recommendation_section = next(
            section
            for section in payload.sections
            if section.heading == "Рекомендации по социальной политике и территориальному планированию"
        )
        self.assertGreaterEqual(len(recommendation_section.paragraphs), 4)
        self.assertTrue(
            any(metric.label.startswith("Прогноз населения на ") for metric in payload.summary_metrics)
        )

    async def test_region_payload_contains_required_sections(self):
        payload = await report_service._build_payload(
            ReportGenerationRequest(
                start_year=2020,
                end_year=2024,
                scope=ReportScope.REGION,
                region_name="Московская область",
                include_ai_summary=False,
            )
        )

        headings = [section.heading for section in payload.sections]
        self.assertEqual(
            headings[:4],
            [
                "Краткое резюме динамики населения",
                "Выявленные демографические тенденции и возможные факторы влияния",
                "Прогнозная оценка на 5-10 лет",
                "Рекомендации по социальной политике и территориальному планированию",
            ],
        )
        self.assertIn("Статистические таблицы", headings)
        self.assertNotIn("Дополнительное аналитическое заключение", headings)

        recommendation_section = next(
            section
            for section in payload.sections
            if section.heading == "Рекомендации по социальной политике и территориальному планированию"
        )
        self.assertGreaterEqual(len(recommendation_section.paragraphs), 4)


@unittest.skipUnless(HAS_EXPORT_DEPS, "python-docx and reportlab are required for export tests")
class ReportsApiSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_reports_dir = report_service.reports_dir
        report_service.reports_dir = Path(self.temp_dir.name)

    def tearDown(self):
        report_service.reports_dir = self.original_reports_dir
        self.temp_dir.cleanup()

    def test_generate_and_download_report(self):
        response = self.client.post(
            "/api/v1/reports/generate",
            json={
                "start_year": 2020,
                "end_year": 2024,
                "scope": "russia",
                "format": "both",
                "include_ai_summary": False,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["files"]), 2)

        for file_info in payload["files"]:
            file_format = ReportFormat(file_info["format"])
            file_path = report_service.get_report_file_path(payload["report_id"], file_format)
            self.assertTrue(file_path.exists())

            download = self.client.get(file_info["download_url"])
            self.assertEqual(download.status_code, 200, file_info["download_url"])
            self.assertGreater(len(download.content), 0)
