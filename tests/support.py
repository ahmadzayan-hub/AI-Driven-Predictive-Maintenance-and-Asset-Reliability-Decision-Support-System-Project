"""Shared test fixtures.

Windows will not delete a file another handle still has open. A test that
builds a SQLite-backed app inside a `TemporaryDirectory` and lets the
directory clean up while the connection is live fails teardown with
`PermissionError [WinError 32]` - and that error is raised *after* the
test body, so it is reported as an ERROR on a test that actually passed.

Hundreds of those bury the handful of real failures underneath them, and
a suite nobody can read is a suite that stops catching things. These
helpers close the connection first, in the order `addCleanup` runs
(last registered, first executed).
"""


def closing(case, app):
    """Register the app's store to close before the test's other cleanups.

    Call it around `create_app(...)` at the point the app is built:

        self.client = TestClient(closing(self, create_app(path, env=env)))

    Returns the app, so it drops into an existing expression without
    restructuring the fixture.
    """
    store = getattr(getattr(app, "state", None), "store", None)
    if store is not None and callable(getattr(store, "close", None)):
        case.addCleanup(store.close)
    return app


def closing_store(case, store):
    """Register a bare store to close before the test's other cleanups.

    `closing` reaches the store through the app that owns it. A test that
    opens a store directly - to build a `RunEngine`, say - has no app to
    reach through, so it registers the store itself.

    Returns the store, so it drops into an existing expression without
    restructuring the fixture.
    """
    if store is not None and callable(getattr(store, "close", None)):
        case.addCleanup(store.close)
    return store


def temp_workspace(case, tempfile_module):
    """A temporary directory that cleans up after the stores inside it."""
    directory = tempfile_module.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    return directory
