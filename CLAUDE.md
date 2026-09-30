# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Sound Switcher Indicator — a Linux tray/indicator app (GTK 3 + AppIndicator) that lets the user switch the active
PulseAudio input/output *port* from a menu. It talks to the PulseAudio daemon directly through `libpulse.so.0` via a
generated ctypes binding.

## Running & developing

Run from the source tree without installing (package lives under `lib/`):

```bash
PYTHONPATH=lib python3 -m indicator_sound_switcher -vv
```

`-v` = INFO logging, `-vv` = DEBUG. Debug output prints the PulseAudio card/port names needed for the config file (see
`doc/config.md`). A single running instance is enforced via an flock on a lockfile in the temp dir, so kill an existing
instance before launching another.

Runtime dependencies (system packages, imported via GObject Introspection — there is no `pip install`): `python3-gi`,
`gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1` (or the older `gir1.2-appindicator3-0.1`), `libpulse0`; optionally
`gir1.2-keybinder-3.0` (global shortcuts on X11).

Unit tests live in `tests/` (pytest, configured in `pytest.ini`; currently `Config` only) and run in GitHub Actions
(`.github/workflows/test.yml`):

```bash
python3 -m pytest
```

They import the real package, so they need the same system packages as the app; outside an installed copy, the package
metadata the app reads its version from must exist first (`python3 setup.py egg_info --egg-base lib`). There is **no
linter config**. Per `__init__.py`, several PEP8 rules (E211, E221, E241, E272,
E402) are deliberately ignored — the code uses column-aligned assignments; match that style.

### Verifying changes

Verification is manual: run the app with `-vv` against a real PulseAudio daemon and watch the debug log while
exercising the affected flow. Kill any running instance first (single-instance lock), then:

```bash
PYTHONPATH=lib python3 -m indicator_sound_switcher -vv
```

The DEBUG log traces the full PulseAudio event flow — cards/ports being added, subscribe events, profile/port switches,
and shortcut binding — so it's the primary way to confirm a change behaves. To exercise a change, trigger the matching
real-world action and look for the corresponding log lines:

- **Menu / port switching** — plug or unplug a device, or pick a port from the indicator menu, and confirm the card/port
  add/remove and activation lines appear and the menu updates.
- **Config handling** — edit `~/.config/indicator-sound-switcher.json` while the app is stopped (it rewrites the file on
  exit), start with `-vv`, and confirm it logs the loaded config and applies device/port names, visibility, and
  preferred profiles.
- **Keyboard shortcuts** — confirm the `Bound keyboard shortcut …` lines at startup, then press the combo and verify the
  port switches.
- **Daemon reconnection** — restart PulseAudio (e.g. `pulseaudio -k`) with the app running and confirm it reconnects
  and rebuilds the menu.

## Architecture

`SoundSwitcherIndicator` in `indicator.py` (~1200 lines) is the core. It owns everything:

- **PulseAudio event loop.** Uses libpulse's native async API. All `pacb_*` methods are C callbacks (wrapped in
  `pa_*_cb_t` ctypes prototypes stored on `self._pacb_*` so they aren't garbage-collected). The daemon pushes
  `subscribe` events → the indicator re-queries card/sink/source/stream info → callbacks fire on the main loop → the
  menu is rebuilt. `PULSEAUDIO_MAX_RETRIES` guards reconnection to the daemon.
- **Menu.** Rebuilt from the current object model on every relevant change. Input ports and output ports form two
  sections with headers/separators.
- **Indicator library.** Uses GTK 3 `AyatanaAppIndicator3` (falling back to `AppIndicator3`), which takes a `Gtk.Menu`
  and exports it via `com.canonical.dbusmenu`. That library is deprecated and warns about it when the indicator is
  created. **Don't migrate to the suggested `AyatanaAppIndicatorGlib` (libayatana-appindicator-glib)**: it exports the 
  menu only via `org.gtk.Menus`/`org.gtk.Actions`, which common tray hosts (GNOME Shell's AppIndicator extension, KDE
  Plasma) don't support — the icon would show but its menu wouldn't work. Revisit only once tray hosts support 
  `org.gtk.Menus`.

The PulseAudio object model (each a `GObject.GObject`, mostly plain data + menu wiring):

- **`Card`** (`card.py`) — a physical device: has `profiles` (`CardProfile`) and card `ports`. `find_stream_port()`
  maps a card port to the sink/source port that realizes it; `update_port_activity()` derives each port's active state
  from its stream. Ports are what the user actually switches between.
- **`Stream` → `Sink`/`Source`** (`stream.py`) — an output/input endpoint, keyed to a card by `card_index`, holding its
  own `ports`. "Stream" naming mirrors the GNOME Sound panel.
- **`Port`** (`port.py`) — the switchable unit. `is_active`/`is_available` are GObject properties whose setters directly
  drive the associated Gtk menu item (check/show/hide). A "dummy" port is treated as always available. Setting a
  property mutates the UI — keep that in mind when touching these.

`config.py`:

- **`Config`** — a `dict` subclass used for the whole config tree. Two custom behaviors to know: indexing with a
  `(key, default)` tuple returns the default instead of raising; indexing a missing plain key **auto-creates and
  inserts** an empty `Config` (so read access can mutate). Assigning `None` deletes the key. Nested dicts are
  auto-converted to `Config`. Loaded from / saved to `~/.config/indicator-sound-switcher.json` — **the app overwrites
  this file on exit**, so never hand-edit it while the app is running.
- **`KeyboardManager`** — global hotkeys. Builds a shortcut→[(device, port)] map from the config and binds/unbinds it;
  `suspend()`/`resume()` are used while the preferences dialog captures keystrokes. `KeyboardManager.create()` picks a
  backend: `PortalKeyboardManager` (XDG Desktop Portal `GlobalShortcuts` over D-Bus — preferred on Wayland; the
  configured combo is only a *preferred trigger*, the desktop may prompt the user or remap it) or
  `KeybinderKeyboardManager` (preferred on X11). The base class itself is a no-op fallback when neither is available.

`prefs.py` — the GTK preferences dialog, built from `prefs.glade`. `utils.py` — small Gtk label/box helpers and
`get_key_name()` for rendering shortcuts.

**`lib_pulseaudio.py` is generated** (via `h2xml`/`xml2py` from the libpulse headers — see the header comment) and is a
raw ctypes binding. Don't edit it by hand.

## Localization

Translations are gettext `.po` files in `po/`, compiled to `.mo` at build time by `setup.py::compile_lang_files()` into
`locale/`. Update the `.pot` template with:

```bash
find . -name '*.py' -or -name '*.glade' | xargs xgettext --from-code=UTF-8 --output=po/indicator-sound-switcher.pot
```

User-facing strings use the gettext `_()` function (installed globally in `main()`). See `doc/i18n.md`.

## Releasing

Version lives in **one place**: `APP_VERSION` in `setup.py` (read at runtime via `importlib.metadata`, and scraped by
`build_package`/snapcraft with `sed`). Release steps (`doc/release_checklist.md`): bump `setup.py`, add a
`debian/changelog` entry (`dch -v <VERSION>-1`), run `./build_package` to produce a source tarball + Debian package,
then `dput` to the PPA. Snap: `snapcraft snap` then `snapcraft upload`.

## Conventions

* **Never commit.** Committing is the user's alone — leave finished work in the working tree and say what it consists
  of, no matter how routine the change is or how clearly it is done; also propose a commit message. This holds even when
  asked to "finish" or "wrap up" a task: that never includes `git commit`. The same goes for anything that rewrites
  history or publishes (`git commit --amend`, `rebase`, `reset` over a commit, `push`, `gh pr create`).
