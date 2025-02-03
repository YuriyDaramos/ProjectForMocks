from unittest import TestCase
from unittest.mock import MagicMock, patch, mock_open

from main import main
from pokemon_name_translator import PokemonNameTranslator
from pokemon_service import PokemonService
from pokemon_report import PokemonReport


class TestMain(TestCase):
    def setUp(self):
        self.pokemon_info = {"name": "pikachu",
                             "height": 4,
                             "weight": 60,
                             "abilities": [{"ability": {"name": "static"}},
                                           {"ability": {"name": "lightning rod"}}]}
        self.translated_name = "PikaPika"

    @patch("main.PokemonService")
    @patch("main.PokemonNameTranslator")
    @patch("main.PokemonReport")
    @patch("builtins.print")
    def test_main(self, mock_print, mock_report_generator, mock_translator, mock_service):
        mock_service.return_value.get_pokemon_info.return_value = self.pokemon_info
        mock_translator.return_value.translate.return_value = self.translated_name
        mock_report_generator.return_value.generate_report.return_value = None

        main()

        mock_service.return_value.get_pokemon_info.assert_called_once_with("pikachu")
        mock_translator.return_value.translate.assert_called_once_with("pikachu", target_language="fr")
        mock_report_generator.return_value.generate_report.assert_called_once_with(self.pokemon_info,
                                                                                   self.translated_name,
                                                                                   "pokemon_report.pdf")
        mock_print.assert_called_once_with("PDF report saved as pokemon_report.pdf")


class TestPokemonService(TestCase):
    def setUp(self):
        self.mock_response = MagicMock()
        self.pokemon_name = "pikachu"

    @patch("pokemon_service.requests.get")
    def test_get_pokemon_info_success(self, mock_get):
        expected_json = {"name": self.pokemon_name}

        self.mock_response.status_code = 200
        self.mock_response.json.return_value = expected_json
        mock_get.return_value = self.mock_response

        service = PokemonService()
        result = service.get_pokemon_info(self.pokemon_name)

        self.assertEqual(result, expected_json)
        mock_get.assert_called_once_with(f"https://pokeapi.co/api/v2/pokemon/{self.pokemon_name}")

    @patch("pokemon_service.requests.get")
    def test_get_pokemon_info_failure(self, mock_get):
        self.mock_response.status_code = 404
        self.mock_response.json.return_value = {}
        mock_get.return_value = self.mock_response

        service = PokemonService()
        result = service.get_pokemon_info(self.pokemon_name)

        self.assertIsNone(result)
        mock_get.assert_called_once_with(f"https://pokeapi.co/api/v2/pokemon/{self.pokemon_name}")


class TestNameTranslator(TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_translation = MagicMock()
        self.mock_translation.translated_text = "PikaPika"
        self.mock_client.translate_text.return_value.translations = [self.mock_translation]
        self.mock_client.location_path.return_value = "mocked_location_path"

    @patch("pokemon_name_translator.translate.TranslationServiceClient")
    def test_translator_service(self, MockClient):
        MockClient.return_value = self.mock_client

        translator = PokemonNameTranslator()
        result = translator.translate("Pikachu")

        self.assertEqual(result, "PikaPika")
        self.mock_client.translate_text.assert_called_once_with(parent="mocked_location_path",
                                                                contents=["Pikachu"],
                                                                target_language_code="en")


class TestReport(TestCase):
    def setUp(self):
        self.report = PokemonReport()
        self.pokemon_info = {"name": "pikachu",
                             "height": 4,
                             "weight": 60,
                             "abilities": [{"ability": {"name": "static"}},
                                           {"ability": {"name": "lightning rod"}}]}
        self.translated_name = "PikaPika"
        self.template_name = "report_template.html"

    @patch("pokemon_report.pdfkit.from_file")
    @patch("pokemon_report.PokemonReport.create_html_report")
    def test_generate_report(self, mock_report, mock_convert):
        from pokemon_report import config as pdfkit_config
        config = pdfkit_config
        mock_report.return_value = self.template_name

        output_pdf = "test_report.pdf"

        self.report.generate_report(self.pokemon_info, self.translated_name, output_pdf)

        mock_convert.assert_called_once_with(self.template_name, output_pdf, configuration=config)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_html_report(self, mock_file):
        abilities = "static, lightning rod"
        expected_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pokemon Report</title>
        </head>
        <body>
            <h1>Pokemon Report</h1>
            <p><strong>Name:</strong> {self.translated_name}</p>
            <p><strong>Height:</strong> {self.pokemon_info['height']} decimetres</p>
            <p><strong>Weight:</strong> {self.pokemon_info['weight']} hectograms</p>
            <p><strong>Abilities:</strong> {abilities}</p>
        </body>
        </html>
        """
        expected_content = expected_content.format(translated_name=self.translated_name, pokemon_info=self.pokemon_info,
                                                   abilities=abilities)

        result = self.report.create_html_report(self.pokemon_info, self.translated_name)

        mock_file.assert_called_once_with("report_template.html", "w", encoding="utf-8")
        mock_file.return_value.write.assert_called_once_with(expected_content)
        self.assertEqual(result, self.template_name)
