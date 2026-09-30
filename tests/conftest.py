import gettext

# The app installs _() globally in main(): install an untranslated one, so that tests don't depend on the locale
gettext.NullTranslations().install()
