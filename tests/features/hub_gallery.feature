# The Highlights page (docs/highlights.md): members post photos with the Toad Bot's /highlight, which show in a 48-hour
# carousel and stay in the archive for good; a global officer picks a photo of the week for seven days; /stream puts a
# member's Twitch channel on the page while they are live; /clip shares a video clip for the clips section.
Feature: HUB GALLERY

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-GALLERY-001 When a raider posts a photo with the Toad Bot's /highlight, the hub shall keep it re-encoded without its EXIF data and show it to members in the Highlights carousel for 48 hours
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    When the Toad Bot posts a phone photo with its location for the raider captioned "Gruul down!"
    Then the member sees the photo in the carousel, captioned "Gruul down!" and posted by "Hopscotch"
    And the stored photo is a WebP image with no EXIF data
    And after 48 hours the photo has left the carousel

  @ears_ubiquitous @member @phase_2_7
  Scenario: REQ-HUB-GALLERY-002 The hub shall keep every photo in the Highlights archive after it leaves the carousel, newest first, a page at a time
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    And the raider has posted 3 photos a day apart
    Then the member sees all 3 photos in the archive, newest first
    And the archive pages through them 2 at a time

  @ears_event_driven @raid_leader @phase_2_7
  Scenario: REQ-HUB-GALLERY-003 When a global officer picks a photo of the week, the hub shall show it at the top of Highlights for seven days, replace any pick still running, and record the pick on the audit log
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    And a global officer
    And the raider has posted 3 photos a day apart
    When the global officer picks the oldest photo as the photo of the week
    And a day later picks the newest photo instead
    Then the member sees the newest photo as the photo of the week, picked by the global officer
    And both picks are listed among the photos of the week
    And the audit log records "gallery.photo_of_the_week" twice
    And after seven days there is no photo of the week

  @ears_unwanted_behavior @raid_leader @phase_2_7
  Scenario: REQ-HUB-GALLERY-004 If anyone but its poster or a global officer takes a photo down, or anyone but a global officer picks the photo of the week, then the hub shall refuse it and change nothing
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    And a global officer
    And the raider has posted 3 photos a day apart
    Then the member cannot take a photo down or pick the photo of the week
    And a Wednesday officer cannot pick the photo of the week
    And the member cannot post a photo, and a visitor cannot see one
    And the archive still holds 3 photos
    When the raider takes one of their photos down
    And the global officer takes another down
    Then the archive holds 1 photo and the audit log records "gallery.remove_photo" for both

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-GALLERY-005 If a raider sends the Toad Bot a file that is not a photo, then the hub shall refuse it with the reason and keep nothing
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    When the Toad Bot posts a PDF for the raider
    Then it is refused as not a photo and the archive is empty

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-GALLERY-006 When a raider runs the Toad Bot's /stream with their Twitch channel's link, the hub shall show that channel's live player on Highlights until they end it or 12 hours pass
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    When the Toad Bot starts a stream for the raider at "https://www.twitch.tv/Hopscotch" titled "Sunday Gruul"
    Then the member sees "hopscotch" live, titled "Sunday Gruul", streamed by "Hopscotch"
    When the Toad Bot ends the raider's stream
    Then no stream is live
    When the Toad Bot starts a stream for the raider at "twitch.tv/hopscotch" with no title
    And 12 hours pass
    Then no stream is live

  @ears_unwanted_behavior @member @phase_2_7
  Scenario: REQ-HUB-GALLERY-007 If a /stream link is not a Twitch channel, then the hub shall refuse it and show nothing
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    When the Toad Bot starts a stream for the raider at "https://evil.example/hopscotch" with no title
    Then it is refused as not a Twitch channel and no stream is live

  @ears_optional @maintainer @phase_2_7
  Scenario: REQ-HUB-GALLERY-008 Where the hub has a Twitch application, Highlights shall show a stream only while Twitch lists its channel as live
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    And the hub asks Twitch who is live, and Twitch lists only "croak"
    When the Toad Bot starts a stream for the raider at "https://twitch.tv/hopscotch" with no title
    And 10 minutes pass
    Then no stream is live

  @ears_event_driven @member @phase_2_7
  Scenario: REQ-HUB-GALLERY-009 When a raider shares a clip with the Toad Bot's /clip, the hub shall hold it for a global officer's review and then list it in the Highlights clips section
    Given a raider who goes by the nickname "Hopscotch"
    And a guild member who signed in
    And a global officer
    When the Toad Bot shares "https://youtu.be/dQw4w9WgXcQ" for the raider titled "Prince one-shot"
    Then the member sees no clips yet and the global officer has one clip to review
    When the global officer publishes the clip to the guild
    Then the member sees the clip "Prince one-shot" from YouTube
