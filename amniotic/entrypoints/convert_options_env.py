from fmtr.tools.ha_tools.constants import PATH_ADDON_ENV
from fmtr.tools.ha_tools.utils import convert_options_env


def main():
    text = convert_options_env()
    PATH_ADDON_ENV.write_text(text)



if __name__ == '__main__':
    main()
