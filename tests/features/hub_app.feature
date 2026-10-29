# The officers' desktop app (docs/desktop.md): the live hub in its own window, with native menus, a tray and desk
# alerts. The site stays the source of every page and permission; the app adds the native touches around it.
Feature: HUB APP

  @ears_ubiquitous @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-APP-001 The desktop app shall open the live hub in its own window, sign in with Discord inside that window and keep the member signed in between launches
    Given the desktop app
    Then it opens https://toads.gg, or a hub given with --hub or TOADS_HUB_URL that is https or plain http to localhost
    And Discord's authorize and login pages stay in the window and the hub's session lives in one persistent partition
    And a smoke run of the built app signs in against a fake hub and its own requests carry the session cookie
    And the window comes back where it was, shows an offline page in the hub's colours that tries again by itself when the hub cannot be reached, and a second launch focuses the first

  @ears_ubiquitous @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-APP-002 The desktop app's Hub, Me and Officers menus shall be the website's own top bar for the signed-in member, so an officer sees only the raid nights they run and a raider sees what the launch hold shows them
    Given the desktop app
    Then its menus are built from the web app's nav, launch hold and access modules, compiled in rather than copied
    And they follow the member's /api/session after every page load, with keyboard shortcuts for the hub pages and the officer tools

  @ears_unwanted_behavior @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-APP-003 If a page links away from the hub or Discord's sign-in, then the desktop app shall open it in the default browser, never in the app, and the app window shall have no Node access and grant the hub only notifications, clipboard writes and fullscreen
    Given the desktop app
    Then links to other sites, the rest of Discord and new windows open in the default browser, and other schemes are refused
    And the window runs sandboxed with context isolation, no Node integration and no webviews
    And every other permission request is refused, even from the hub

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-APP-004 When new work reaches an officer's raid leader desk, the desktop app shall raise one native notification and count what waits on the dock or taskbar, from the tray as well when the window is closed
    Given the desktop app
    Then it reads the officer's desk every two minutes and on focus, counts it on the badge and lists it in the tray in the hub's words
    And it notifies only about what grew, never on the first look, and an officer can turn that off or keep the app in the tray

  @ears_event_driven @maintainer @phase_2_7
  Scenario: REQ-HUB-APP-005 When a desktop-v tag matching the app's version is pushed, the desktop workflow shall build the Windows, macOS and Linux installers and publish them as a GitHub release
    Given the desktop workflow
    Then it builds on Windows, macOS and Linux, checks the tag against the app's version, and publishes the installers on a tag only
    And CI's desktop job runs the app's types, tests, smoke run, packaging and audit on every PR

  @ears_ubiquitous @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-APP-006 The desktop app shall stay consistent with the website it shows: the live site's top bar lists and launch hold, its account menu and Log out, and the reader's theme
    Given the desktop app
    Then it reads the site's /desktop.json after every page load and draws its menus from it, keeping the bundled lists only until the site answers
    And its Me menu is the site's account menu, with the site's sign-in wording and a Log out that posts to the hub as the site does
    And it takes the reader's theme from the site's theme-color tag for its window, title bar and offline page, and remembers it for the next launch
    And the web app's tests hold every top bar link to a page on the site and the theme-color values to theme.css's page colours

  @ears_event_driven @raid_leader @member @phase_2_7
  Scenario: REQ-HUB-APP-007 When a newer desktop release is published, the installed desktop app shall update itself without a reinstall, downloading it in the background and installing it on restart, and on an unsigned Mac build shall instead link its release page
    Given the desktop app
    Then it checks the latest desktop-v release's update feed shortly after starting, every six hours and from Help, Check for updates
    And on Windows, Linux and a signed Mac it downloads a newer version in the background and asks once to restart into it, or installs it when the app quits
    And an unsigned Mac build, which macOS will not let install an update, says the new version is out and opens its release page
    And each desktop release carries the update feeds, blockmaps and Mac zips beside the installers
