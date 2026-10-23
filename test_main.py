import unittest
from unittest.mock import patch

import main


class JarvisCommandTests(unittest.TestCase):
    def setUp(self):
        speech_patch = patch("main.speak")
        self.speech = speech_patch.start()
        self.addCleanup(speech_patch.stop)

    def test_news_phrases_are_recognized(self):
        for phrase in ("tell me the news", "tell me the nows", "news"):
            with self.subTest(phrase=phrase):
                self.assertTrue(main.is_news_command(main.clean_words(phrase)))

    def test_song_library_has_expected_commands(self):
        self.assertIn("baby", main.musiclibrary.music)
        self.assertIn("sorry", main.musiclibrary.music)
        self.assertIn("unstoppable", main.musiclibrary.music)

    def test_word_launches_installed_application(self):
        with (
            patch("main.os.startfile") as startfile,
            patch("main.webbrowser.open_new_tab") as open_web,
            patch("main.Path.is_file", return_value=True),
        ):
            main.handle_command("open word")

        self.assertTrue(startfile.called)
        self.assertTrue(startfile.call_args.args[0].lower().endswith("winword.exe"))
        open_web.assert_not_called()

    def test_excel_alias_launches_installed_application(self):
        with (
            patch("main.os.startfile") as startfile,
            patch("main.webbrowser.open_new_tab") as open_web,
            patch("main.Path.is_file", return_value=True),
        ):
            main.handle_command("open ms excel")

        self.assertTrue(startfile.called)
        self.assertTrue(startfile.call_args.args[0].lower().endswith("excel.exe"))
        open_web.assert_not_called()

    def test_named_site_opens_directly(self):
        with patch("main.webbrowser.open_new_tab") as open_web:
            main.handle_command("open chat gpt")

        open_web.assert_called_once_with("https://chatgpt.com")

    def test_arbitrary_site_name_searches_web(self):
        with patch("main.webbrowser.open_new_tab") as open_web:
            main.handle_command("open reddit")

        self.assertIn("google.com/search?q=reddit", open_web.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
