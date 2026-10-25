import json
import os
import unittest
from unittest import mock

from abs_kids_player import i18n


class GermanOffTest(unittest.TestCase):
    def test_english_is_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CHAPTER_LANGUAGE", None)
            self.assertEqual(i18n.display("No books"), "No books")
            self.assertEqual(i18n.web_text("Settings"), "Settings")
            self.assertEqual(i18n.html_page("<p>Settings</p>"), "<p>Settings</p>")


@mock.patch.dict(os.environ, {"CHAPTER_LANGUAGE": "de"})
class GermanDisplayTest(unittest.TestCase):
    def test_exact_strings(self):
        self.assertEqual(i18n.display("No books"), "Keine Bücher")
        self.assertEqual(i18n.display("Play"), "Start")

    def test_patterns(self):
        self.assertEqual(
            i18n.display("Are you sure you want to listen to the next chapter?"),
            "Möchtest du wirklich das nächste Kapitel hören?",
        )
        self.assertEqual(i18n.display("listen to the previous chapter?"), "das vorherige Kapitel hören?")
        self.assertEqual(i18n.display("Are you still listening? 12"), "Hörst du noch zu? 12")
        self.assertEqual(i18n.display("By Ulf Blanck"), "von Ulf Blanck")

    def test_book_titles_stay(self):
        self.assertEqual(i18n.display("Die drei ??? Kids"), "Die drei ??? Kids")

    def test_oled_safe_text_translates(self):
        from abs_kids_player.appliance_io import oled_safe_text

        self.assertEqual(oled_safe_text("Check connection"), "Verbindung prüfen")


@mock.patch.dict(os.environ, {"CHAPTER_LANGUAGE": "de"})
class GermanSpokenTest(unittest.TestCase):
    def test_spoken(self):
        self.assertEqual(i18n.spoken("Volume 40 percent"), "Lautstärke 40 Prozent")
        self.assertEqual(i18n.spoken("Play"), "Abspielen")
        self.assertEqual(i18n.spoken("Next chapter"), "Nächstes Kapitel")
        self.assertEqual(i18n.spoken("Start over"), "Von vorn")
        self.assertEqual(i18n.espeak_voice("en-us"), "de")


@mock.patch.dict(os.environ, {"CHAPTER_LANGUAGE": "de"})
class GermanWebTest(unittest.TestCase):
    def test_text_nodes_and_attributes(self):
        page = '<html lang="en"><h2>Settings</h2><input aria-label="Volume"><p> Save </p></html>'
        self.assertEqual(
            i18n.html_page(page),
            '<html lang="de"><h2>Einstellungen</h2><input aria-label="Lautstärke"><p> Speichern </p></html>',
        )

    def test_script_keeps_compared_values(self):
        page = (
            '<script>if (event.key === "Home") {} '
            'button.textContent = playing ? "Pause" : "Play"; '
            'if (status.phase === "installing") { text.textContent = "Up to date"; }</script>'
        )
        result = i18n.html_page(page)
        self.assertIn('event.key === "Home"', result)
        self.assertIn('status.phase === "installing"', result)
        self.assertIn('? "Pause" : "Abspielen"', result)
        self.assertIn('textContent = "Aktuell"', result)

    def test_styles_untouched(self):
        page = "<style>.a>b{color:red}</style><p>Status</p>"
        self.assertEqual(i18n.html_page(page), "<style>.a>b{color:red}</style><p>Status</p>")

    def test_json_translates_state_not_title(self):
        data = {"title": "Play", "state": "Paused", "message": "Installing the software update."}
        result = i18n.json_value(data)
        self.assertEqual(result["title"], "Play")
        self.assertEqual(result["state"], "Pausiert")
        self.assertEqual(result["message"], "Das Software-Update wird installiert.")
        json.dumps(result)

    def test_messages_with_values(self):
        self.assertEqual(
            i18n.web_text("Logged in to https://hoerbuecher.example.com as chapter"),
            "Angemeldet bei https://hoerbuecher.example.com als chapter",
        )
        self.assertEqual(i18n.web_text("Paused · 1:02 / 3:04"), "Pausiert · 1:02 / 3:04")


if __name__ == "__main__":
    unittest.main()
