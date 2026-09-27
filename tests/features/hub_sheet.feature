# The guild's weekly CBA and RPB Google Sheets, imported read-only and attached to the raid each tab describes.
Feature: HUB SHEET

  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-SHEET-001 When the worker imports a CBA or RPB spreadsheet, the hub shall attach each tab to the raid named by the tab's date and raid day
    Given the Toads raid sheets are configured
    When the worker imports the CBA sheet with a tab named "Wed 23/09/2026"
    Then the Wednesday raid on 2026-09-23 shows the CBA tab "Wed 23/09/2026"
    And the tab links to the CBA spreadsheet on Google Sheets

  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-SHEET-002 When a sheet tab changes between imports, the hub shall keep the earlier version as history and show the newest; an unchanged tab shall add nothing
    Given the Toads raid sheets are configured
    And the worker imported the CBA sheet with a tab named "Wed 23/09/2026"
    When the worker imports the same tab again unchanged
    Then the import reports the tab as unchanged
    When the worker imports the tab with one more row
    Then the raid shows the newer version and both versions are stored

  @ears_unwanted_behavior @raid_leader @phase_2_6
  Scenario: REQ-HUB-SHEET-003 If a tab has no date in its name or first rows, then the hub shall store it without attaching it to any raid and report it as undated
    Given the Toads raid sheets are configured
    When the worker imports the RPB sheet with a tab named "Notes" and no dates
    Then the import reports "Notes" as undated
    And no raid shows it

  @ears_unwanted_behavior @maintainer @phase_2_6
  Scenario: REQ-HUB-SHEET-004 If an import arrives without the service token or names a spreadsheet that is not configured, then the hub shall refuse it
    Given the Toads raid sheets are configured
    Then an import without the service token is refused with 401
    And an import of an unconfigured spreadsheet is refused with 422

  @ears_ubiquitous @member @phase_2_6
  Scenario: REQ-HUB-SHEET-005 The hub shall list the latest raids that have CBA or RPB sheets, newest first, for the home page
    Given the Toads raid sheets are configured
    And the worker imported sheets for the Sunday raid on 2026-09-20 and the Wednesday raid on 2026-09-23
    Then a member sees the 2026-09-23 raid listed before the 2026-09-20 raid

  @ears_ubiquitous @maintainer @phase_2_6
  Scenario: REQ-HUB-SHEET-006 The hub shall never write to the CBA or RPB spreadsheets; the worker shall only download them
    Then the raid sheet importer only reads from Google Sheets

  @ears_unwanted_behavior @maintainer @phase_2_6
  Scenario: REQ-HUB-SHEET-007 If a downloaded sheet holds setup tabs, Discord webhooks or e-mail addresses, then the hub shall not store the setup tabs and shall blank the webhooks and e-mails, keeping only the Warcraft Logs report code
    Given the Toads raid sheets are configured with RPB following CBA
    When the worker imports the CBA sheet for the 2026-09-23 raid with its Instructions tab
    Then the import skips the Instructions tab
    And no stored tab holds the webhook or the e-mail address
    And the 2026-09-23 raid names the Warcraft Logs report the CBA sheet was run for

  @ears_event_driven @raid_leader @phase_2_6
  Scenario: REQ-HUB-SHEET-008 When an RPB sheet with no dates arrives with new content, the hub shall attach it to the latest CBA raid from the week before the download, or once that raid's CBA arrives
    Given the Toads raid sheets are configured with RPB following CBA
    And the worker imported the CBA sheet for the 2026-09-23 raid
    When the worker imports the RPB sheet
    Then the 2026-09-23 raid shows both the CBA and the RPB tabs

  @ears_ubiquitous @member @phase_2_6
  Scenario: REQ-HUB-SHEET-009 The hub shall show each raid's CBA and RPB totals (clear times, consumable uptime, gear issues, drums, potions, interrupts, deaths and avoidable damage) with a line per player, and list recent raids' totals newest first for the home page
    Given the Toads raid sheets are configured with RPB following CBA
    And the worker imported the CBA and RPB sheets for the 2026-09-23 raid
    Then a member sees the 2026-09-23 raid's clear times, consumable uptime, gear issues and deaths
    And a member sees each player's line for the 2026-09-23 raid
    And a member sees the 2026-09-23 raid in the home page trend
