# Entry point for "python -m otripy", used by Briefcase bundles.
try:
    from .main import main
except ImportError:
    from main import main

main()
