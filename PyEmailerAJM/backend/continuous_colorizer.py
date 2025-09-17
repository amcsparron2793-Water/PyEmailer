from typing import Union, Tuple

from ColorizerAJM import Colorizer

from . import AlertTypes


class ContinuousColorizer(Colorizer):
    """
    Class providing functionality to handle and apply color coding for alert messages.
    It extends functionality from the parent `Colorizer` class,
    adding customized color management, HTML-based color translation,
    and support for critical warning, overdue, and other alerts.

    Attributes:
      LIGHT_GRAY: ANSI escape code for light gray colored text.
      DARK_GRAY: ANSI escape code for dark gray colored text.
      ORANGE: ANSI escape code for orange colored text.
      DARK_YELLOW: ANSI escape code for dark yellow colored text.

    Methods:
      __init__(**kwargs):
        Initialize the OverdueColorizer with optional custom colors and specific default color assignments.

      get_alert_color(alert: 'AlertTypes') -> str:
        Return the appropriate color for a given alert type.

      _populate_html(unpopulated_html: str, text_for_population: str) -> str:
        Populate a provided HTML template with the given text before the closing '</span>' tag.

      colorize(text: str, color: str or None = None, bold: bool = False, **kwargs) -> str:
        Apply colorization to the provided text using ANSI escape codes or HTML formatting.

      get_color_code(color: Union[str, dict, int, Tuple[int, int, int]], **kwargs) -> str:
        Retrieve the processed color code either in plain format or as HTML, based on the settings.

      translate_color_to_html(color_code: str) -> str:
        Transform a color code into an HTML-compliant string using a `<span>` element.
    """
    ORANGE = '\x1b[33m'
    DARK_YELLOW = '\x1b[220m'

    def __init__(self, **kwargs):
        custom_colors = kwargs.pop('custom_colors', {})
        custom_colors.update({'ORANGE': self.__class__.ORANGE,
                              # DARKGOLDENROD is the color name HTML will recognize
                              'DARKGOLDENROD': self.__class__.DARK_YELLOW})
        super().__init__(custom_colors=custom_colors, **kwargs)

        self.overdue_color = self.get_color_code(self.__class__.RED, html_mode=True)
        self.critical_warning_color = self.get_color_code(self.__class__.ORANGE, html_mode=True)
        self.warning_color = self.get_color_code(self.__class__.DARK_YELLOW, html_mode=True)
        self.other_color = self.get_color_code(self.__class__.WHITE, html_mode=True)

    def get_alert_color(self, alert: 'AlertTypes'):
        """
        :param alert: The type of alert to determine the corresponding color.
        :type alert: AlertTypes
        :return: The color associated with the specified alert type.
        :rtype: str
        """
        if alert == AlertTypes.WARNING:
            return self.warning_color
        elif alert == AlertTypes.CRITICAL_WARNING:
            return self.critical_warning_color
        elif alert == AlertTypes.OVERDUE:
            return self.overdue_color
        else:
            return self.other_color

    @staticmethod
    def _populate_html(unpopulated_html: str, text_for_population: str):
        """
        :param unpopulated_html: HTML string that contains unpopulated sections marked by the closing '</span>' tag.
        :type unpopulated_html: str
        :param text_for_population: Text value to populate into the unpopulated HTML section before the closing '</span>' tag.
        :type text_for_population: str
        :return: A new HTML string with the text populated into the specified sections.
        :rtype: str
        """
        return unpopulated_html.replace('</span>', f'{text_for_population}</span>')

    def colorize(self, text, color=None, bold=False, **kwargs):
        """
        :param text: The text to be colorized.
        :type text: str
        :param color: The color to apply to the text. Defaults to None.
        :type color: str or None
        :param bold: A flag to indicate whether the text should be bold. Defaults to False.
        :type bold: bool
        :param kwargs: Additional optional parameters to control various aspects of the function. The 'html_mode' key can be used to specify whether HTML formatting is applied.
        :return: The colorized text, optionally in HTML format if 'html_mode' is enabled in kwargs.
        :rtype: str
        """
        html_mode = kwargs.get('html_mode', False)
        if html_mode:
            blank_html = self.translate_color_to_html(color)
            colorized = self._populate_html(blank_html, text)
        else:
            colorized = super().colorize(text, color=color, bold=bold)
        return colorized

    def get_color_code(self, color: Union[str, dict, int, Tuple[int, int, int]], **kwargs) -> str:
        """
        :param color: The color input which can be a string, dictionary, integer, or a tuple representing RGB values.
        :type color: Union[str, dict, int, Tuple[int, int, int]]
        :param kwargs: Additional keyword arguments. Specifically, 'html_mode' can be passed to control whether the color code is translated to HTML.
        :return: The processed color code as a string. If 'html_mode' is enabled, the color code is returned in HTML format, otherwise it's returned as is.
        :rtype: str
        """
        html_mode = kwargs.get('html_mode', False)
        if not color.startswith('\x1b') or not color.startswith('\033'):
            cc = super().get_color_code(color)
        else:
            cc = color
        if html_mode:
            return self.translate_color_to_html(cc)
        return cc

    def translate_color_to_html(self, color_code: str):
        """
        Translate a specified color code to an HTML span element.

        :param color_code: The color code in text representation. If the `color_code` starts with '<span',
                           the method attempts to map it to corresponding custom or default color codes.
                           If no mapping is found, an AttributeError is raised.
        :type color_code: str
        :return: The HTML span element string with the appropriate color style applied.
        :rtype: str
        """
        if color_code.startswith('<span'):
            new_color_code = [x[0] for x in {**self.custom_colors, **self.__class__.DEFAULT_COLOR_CODES}.items()
                              if x[1] == color_code.split('color:')[1].split('">')[0]]
            if new_color_code:
                color_code = new_color_code[0]
            else:
                raise AttributeError(f'Could not translate color code: {color_code}')
        return f'<span style="color:{color_code}"></span>'
