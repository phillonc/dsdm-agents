#!/usr/bin/env python3
"""
Update Jira stories with acceptance criteria and Gherkin scenarios.

Usage:
    python update_jira_stories.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from src.tools.integrations.jira_tools import get_jira_client

JIRA_PROJECT = "DD"


# Comprehensive requirements with acceptance criteria and Gherkin scenarios
REQUIREMENTS = [
    # ============================================================================
    # AUTHENTICATION REQUIREMENTS
    # ============================================================================
    {
        "summary": "[MUST] FR-AUTH-001: Google OAuth Login",
        "description": """## Description
Users can authenticate using Google accounts via OAuth 2.0 flow.

## Acceptance Criteria
- [ ] User can click "Sign in with Google" button on landing page
- [ ] User is redirected to Google consent screen
- [ ] After consent, user is redirected back to application
- [ ] User session is created with profile data (id, name, email, picture)
- [ ] User is redirected to shopping list page after successful login
- [ ] Failed authentication redirects to landing page with no error exposed

## Non-Functional Requirements
- NFR-SEC-001: Use OAuth 2.0 industry standard
- NFR-PERF-001: OAuth callback should complete within 2 seconds
- NFR-SEC-003: Never expose OAuth tokens to client-side code

## Gherkin Scenarios

```gherkin
Feature: Google OAuth Login
  As a user
  I want to sign in with my Google account
  So that I can access my personal shopping list

  Scenario: Successful Google OAuth login
    Given I am on the landing page
    And I am not logged in
    When I click the "Sign in with Google" button
    Then I should be redirected to Google consent screen
    When I approve the consent
    Then I should be redirected to the shopping list page
    And I should see my name displayed in the header
    And I should see my profile picture

  Scenario: User cancels Google consent
    Given I am on the landing page
    When I click the "Sign in with Google" button
    And I cancel the Google consent
    Then I should be redirected to the landing page
    And I should see the login button

  Scenario: Already authenticated user visits landing page
    Given I am already logged in
    When I visit the landing page
    Then I should be automatically redirected to the shopping list page

  Scenario: OAuth callback with invalid state
    Given I am on the landing page
    When the OAuth callback is triggered with invalid parameters
    Then I should be redirected to the landing page
    And no session should be created

  Scenario: Network error during OAuth
    Given I am on the landing page
    When I click "Sign in with Google"
    And there is a network error
    Then I should see the landing page
    And I should not be logged in
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "authentication", "dsdm", "oauth"]
    },
    {
        "summary": "[MUST] FR-AUTH-002: Session Persistence",
        "description": """## Description
User sessions persist for 24 hours using secure cookie-based session management.

## Acceptance Criteria
- [ ] Session cookie is set after successful login
- [ ] Session persists across page refreshes
- [ ] Session persists across browser tabs
- [ ] Session expires after 24 hours of inactivity
- [ ] Session data includes user profile information
- [ ] Session is stored server-side (not in cookie payload)

## Non-Functional Requirements
- NFR-SEC-002: HTTP-only cookies to prevent XSS
- NFR-SEC-004: Secure flag enabled in production (HTTPS)
- NFR-REL-001: Session should survive server restarts (future: Redis)
- NFR-PERF-002: Session lookup should be < 10ms

## Gherkin Scenarios

```gherkin
Feature: Session Persistence
  As a logged-in user
  I want my session to persist
  So that I don't have to log in repeatedly

  Scenario: Session persists across page refresh
    Given I am logged in as "test@example.com"
    And I am on the shopping list page
    When I refresh the page
    Then I should still be logged in
    And I should see my shopping list

  Scenario: Session persists across browser tabs
    Given I am logged in as "test@example.com"
    When I open the application in a new tab
    Then I should be logged in in the new tab
    And I should see the same user profile

  Scenario: Session expires after 24 hours
    Given I am logged in as "test@example.com"
    And my session was created 25 hours ago
    When I try to access the shopping list
    Then I should be redirected to the login page
    And I should see the login button

  Scenario: Session cookie is HTTP-only
    Given I am logged in
    When I try to access the session cookie via JavaScript
    Then the cookie should not be accessible
    And document.cookie should not contain the session ID

  Scenario: Concurrent sessions from same user
    Given I am logged in on Device A
    When I log in on Device B
    Then both sessions should be valid
    And changes on Device A should be independent of Device B
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "authentication", "session", "dsdm"]
    },
    {
        "summary": "[MUST] FR-AUTH-003: Logout Functionality",
        "description": """## Description
Users can securely log out, clearing their session and returning to the landing page.

## Acceptance Criteria
- [ ] Logout button is visible when user is logged in
- [ ] Clicking logout clears the server-side session
- [ ] Clicking logout clears the session cookie
- [ ] User is redirected to landing page after logout
- [ ] Shopping list data is not accessible after logout
- [ ] Back button after logout does not restore session

## Non-Functional Requirements
- NFR-SEC-005: Session must be invalidated server-side
- NFR-PERF-001: Logout should complete within 500ms
- NFR-USE-001: Clear visual feedback during logout

## Gherkin Scenarios

```gherkin
Feature: Logout Functionality
  As a logged-in user
  I want to log out of my account
  So that others cannot access my shopping list

  Scenario: Successful logout
    Given I am logged in as "test@example.com"
    And I am on the shopping list page
    When I click the "Logout" button
    Then I should be redirected to the landing page
    And I should see the "Sign in with Google" button
    And I should not see my profile information

  Scenario: Cannot access shopping list after logout
    Given I was logged in as "test@example.com"
    And I have logged out
    When I try to access "/api/shopping-list"
    Then I should receive a 401 Unauthorized response

  Scenario: Back button after logout
    Given I am logged in as "test@example.com"
    And I am on the shopping list page
    When I click "Logout"
    And I click the browser back button
    Then I should not be logged in
    And I should see the login page

  Scenario: Logout with network error
    Given I am logged in
    When I click "Logout"
    And the network request fails
    Then I should see an error message
    And I should remain on the current page

  Scenario: Logout clears all session data
    Given I am logged in with shopping items
    When I log out
    And I log back in as the same user
    Then my shopping list should still contain my items
    But the client-side state should have been cleared
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "authentication", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-AUTH-004: Development Mode Login",
        "description": """## Description
Mock authentication available for local development when Google OAuth credentials are not configured.

## Acceptance Criteria
- [ ] Dev mode activates when GOOGLE_CLIENT_ID is not set
- [ ] Dev mode activates when GOOGLE_CLIENT_SECRET is not set
- [ ] Console displays clear "DEVELOPMENT MODE" message on startup
- [ ] Dev login page allows entering name and email
- [ ] Dev login creates valid session with mock user data
- [ ] Dev mode is clearly indicated in the UI

## Non-Functional Requirements
- NFR-SEC-006: Dev mode must NOT be accidentally enabled in production
- NFR-USE-002: Clear visual indicator that dev mode is active
- NFR-MAIN-001: Dev mode should mirror production auth flow

## Gherkin Scenarios

```gherkin
Feature: Development Mode Login
  As a developer
  I want to test the app without OAuth setup
  So that I can develop and debug locally

  Scenario: Dev mode activates without credentials
    Given GOOGLE_CLIENT_ID is not set
    And GOOGLE_CLIENT_SECRET is not set
    When the server starts
    Then the console should display "RUNNING IN DEVELOPMENT MODE"
    And the console should display instructions for enabling OAuth

  Scenario: Dev login flow
    Given the app is running in development mode
    When I visit the landing page
    And I click "Sign in with Google"
    Then I should be redirected to the dev login page
    And I should see a "DEVELOPMENT MODE" badge

  Scenario: Dev login with custom credentials
    Given I am on the dev login page
    When I enter name "Test Developer"
    And I enter email "dev@test.com"
    And I click "Continue to Shopping List"
    Then I should be logged in as "Test Developer"
    And my email should be "dev@test.com"
    And I should be on the shopping list page

  Scenario: Dev login with default values
    Given I am on the dev login page
    When I click "Continue to Shopping List" without changing defaults
    Then I should be logged in as "Dev User"
    And my email should be "dev@example.com"

  Scenario: Dev mode disabled with valid credentials
    Given GOOGLE_CLIENT_ID is set to a valid value
    And GOOGLE_CLIENT_SECRET is set to a valid value
    When the server starts
    Then the console should NOT display "DEVELOPMENT MODE"
    And clicking "Sign in" should redirect to Google
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "authentication", "developer-experience", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-AUTH-005: Auto-redirect on Auth",
        "description": """## Description
Automatic navigation based on authentication state - authenticated users go to app, others see login.

## Acceptance Criteria
- [ ] Landing page checks auth status on load
- [ ] Authenticated users are redirected to shopping list
- [ ] Unauthenticated users see the login button
- [ ] Direct URL to shopping-list.html checks auth
- [ ] Loading state shown during auth check
- [ ] No flash of wrong content during redirect

## Non-Functional Requirements
- NFR-PERF-003: Auth check should complete within 500ms
- NFR-USE-003: Smooth transition without content flashing
- NFR-REL-002: Graceful handling of auth check failures

## Gherkin Scenarios

```gherkin
Feature: Auto-redirect on Authentication
  As a user
  I want to be automatically directed to the right page
  So that I have a seamless experience

  Scenario: Authenticated user visits landing page
    Given I am logged in as "test@example.com"
    When I visit the landing page "/"
    Then I should be automatically redirected to "/shopping-list.html"
    And the redirect should happen within 500ms

  Scenario: Unauthenticated user visits landing page
    Given I am not logged in
    When I visit the landing page "/"
    Then I should see the landing page content
    And I should see the "Sign in with Google" button

  Scenario: Unauthenticated user tries to access shopping list
    Given I am not logged in
    When I directly visit "/shopping-list.html"
    Then I should see a loading state briefly
    Then I should see the login prompt
    And I should NOT see the shopping list

  Scenario: Auth check during page load
    Given I am logged in
    When I visit any page
    Then I should see a loading indicator
    Until the auth check completes
    Then I should see the appropriate content

  Scenario: Auth check fails due to network error
    Given there is a network error
    When I visit the landing page
    Then I should see the login page
    And I should be able to retry login
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "authentication", "ux", "dsdm"]
    },

    # ============================================================================
    # SHOPPING LIST REQUIREMENTS
    # ============================================================================
    {
        "summary": "[MUST] FR-LIST-001: Add Item",
        "description": """## Description
Users can add new text items to their shopping list.

## Acceptance Criteria
- [ ] Input field accepts text for new item
- [ ] "Add" button adds item to list
- [ ] Enter key in input field adds item
- [ ] Input field clears after adding
- [ ] Input field receives focus after adding
- [ ] New item appears at bottom of list
- [ ] New item is initially unchecked
- [ ] Item is persisted to server immediately
- [ ] Empty input does not add item

## Non-Functional Requirements
- NFR-PERF-001: Add operation should complete within 200ms
- NFR-USE-004: Visual feedback when item is added (animation)
- NFR-REL-003: Optimistic UI update with rollback on failure

## Gherkin Scenarios

```gherkin
Feature: Add Shopping List Item
  As a user
  I want to add items to my shopping list
  So that I can track what I need to buy

  Scenario: Add item using Add button
    Given I am logged in
    And I am on the shopping list page
    When I type "Milk" in the input field
    And I click the "Add" button
    Then "Milk" should appear in my shopping list
    And the input field should be empty
    And the input field should have focus

  Scenario: Add item using Enter key
    Given I am logged in
    And the input field has focus
    When I type "Bread"
    And I press the Enter key
    Then "Bread" should appear in my shopping list
    And the input field should be empty

  Scenario: Cannot add empty item
    Given I am logged in
    And the input field is empty
    When I click the "Add" button
    Then no item should be added
    And the input field should have focus

  Scenario: Cannot add whitespace-only item
    Given I am logged in
    When I type "   " in the input field
    And I click the "Add" button
    Then no item should be added
    And the input field should be empty

  Scenario: Add item with special characters
    Given I am logged in
    When I type "Ben & Jerry's Ice Cream" in the input field
    And I click "Add"
    Then "Ben & Jerry's Ice Cream" should appear in my list

  Scenario: Add item persists to server
    Given I am logged in
    When I add "Eggs" to my list
    And I refresh the page
    Then "Eggs" should still be in my list

  Scenario: Add item with network failure
    Given I am logged in
    And the network is unavailable
    When I try to add "Cheese"
    Then the item should not be saved
    And I should see the item locally (optimistic)
    When the network is restored
    Then the item should sync to the server

  Scenario: Add very long item text
    Given I am logged in
    When I type a 500 character item name
    And I click "Add"
    Then the item should be added
    And the full text should be displayed
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "shopping-list", "dsdm"]
    },
    {
        "summary": "[MUST] FR-LIST-002: View Items",
        "description": """## Description
All shopping list items are displayed in an organized list format.

## Acceptance Criteria
- [ ] All items are displayed in a vertical list
- [ ] Each item shows checkbox, text, and delete button
- [ ] Completed items show strikethrough text
- [ ] Completed items appear visually distinct (opacity)
- [ ] Items maintain order (most recent at bottom)
- [ ] Empty list shows appropriate message
- [ ] List updates in real-time after changes

## Non-Functional Requirements
- NFR-PERF-004: List should render within 100ms for up to 100 items
- NFR-USE-005: Items should have sufficient touch targets (44x44px)
- NFR-ACC-001: List should be keyboard navigable

## Gherkin Scenarios

```gherkin
Feature: View Shopping List Items
  As a user
  I want to see all my shopping items
  So that I know what I need to buy

  Scenario: View list with multiple items
    Given I am logged in
    And I have items "Milk", "Bread", "Eggs" in my list
    When I view the shopping list page
    Then I should see all 3 items displayed
    And each item should have a checkbox
    And each item should have a delete button

  Scenario: View empty list
    Given I am logged in
    And I have no items in my list
    When I view the shopping list page
    Then I should see "Your shopping list is empty"

  Scenario: Completed items appear different
    Given I am logged in
    And "Milk" is marked as completed
    And "Bread" is not completed
    When I view the shopping list
    Then "Milk" should have strikethrough text
    And "Milk" should have reduced opacity
    And "Bread" should appear normal

  Scenario: Items maintain order
    Given I am logged in
    When I add "First" then "Second" then "Third"
    Then the items should appear in order: "First", "Second", "Third"

  Scenario: List loads on page load
    Given I am logged in
    And I have 5 items saved
    When I navigate to the shopping list page
    Then all 5 items should be visible
    And loading should complete within 2 seconds

  Scenario: Large list performance
    Given I am logged in
    And I have 100 items in my list
    When I view the shopping list page
    Then all items should render within 1 second
    And scrolling should be smooth
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "shopping-list", "dsdm"]
    },
    {
        "summary": "[MUST] FR-LIST-003: Toggle Complete",
        "description": """## Description
Users can mark items as completed or uncompleted by toggling their status.

## Acceptance Criteria
- [ ] Clicking checkbox toggles item status
- [ ] Clicking item row toggles item status
- [ ] Visual feedback shows completion state
- [ ] Status change persists to server
- [ ] Statistics update after toggle
- [ ] Toggle works on both completed and uncompleted items

## Non-Functional Requirements
- NFR-PERF-001: Toggle should respond within 100ms
- NFR-USE-006: Clear visual feedback on toggle
- NFR-REL-004: Optimistic update with rollback on failure

## Gherkin Scenarios

```gherkin
Feature: Toggle Item Completion
  As a user
  I want to mark items as complete
  So that I can track my shopping progress

  Scenario: Mark item as complete via checkbox
    Given I am logged in
    And I have an uncompleted item "Milk"
    When I click the checkbox for "Milk"
    Then "Milk" should be marked as completed
    And the checkbox should be checked
    And "Milk" should have strikethrough styling

  Scenario: Mark item as incomplete via checkbox
    Given I am logged in
    And I have a completed item "Bread"
    When I click the checkbox for "Bread"
    Then "Bread" should be marked as incomplete
    And the checkbox should be unchecked
    And "Bread" should have normal styling

  Scenario: Toggle via clicking item row
    Given I am logged in
    And I have an uncompleted item "Eggs"
    When I click on the text "Eggs"
    Then "Eggs" should be marked as completed

  Scenario: Toggle persists to server
    Given I am logged in
    And I have an uncompleted item "Cheese"
    When I mark "Cheese" as completed
    And I refresh the page
    Then "Cheese" should still be marked as completed

  Scenario: Statistics update on toggle
    Given I am logged in
    And I have 3 items with 1 completed
    When I complete another item
    Then completed count should change from 1 to 2
    And remaining count should change from 2 to 1

  Scenario: Toggle with network failure
    Given I am logged in
    And the network is unavailable
    When I toggle "Milk"
    Then the item should show toggled state (optimistic)
    When the network is restored
    Then the state should sync to server

  Scenario: Rapid toggling
    Given I am logged in
    And I have item "Apple"
    When I rapidly toggle "Apple" 5 times
    Then the final state should be consistent
    And only the final state should be saved
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "shopping-list", "dsdm"]
    },
    {
        "summary": "[MUST] FR-LIST-004: Delete Item",
        "description": """## Description
Users can remove individual items from their shopping list.

## Acceptance Criteria
- [ ] Each item has a visible delete button
- [ ] Clicking delete removes item from list
- [ ] Deletion is immediate (no confirmation for single item)
- [ ] Deleted item is removed from server
- [ ] Statistics update after deletion
- [ ] Delete works for both completed and uncompleted items

## Non-Functional Requirements
- NFR-PERF-001: Delete should complete within 200ms
- NFR-USE-007: Animation on delete for visual feedback
- NFR-REL-005: Undo functionality (future enhancement)

## Gherkin Scenarios

```gherkin
Feature: Delete Shopping List Item
  As a user
  I want to delete items from my list
  So that I can remove items I no longer need

  Scenario: Delete uncompleted item
    Given I am logged in
    And I have items "Milk", "Bread", "Eggs"
    When I click delete on "Bread"
    Then "Bread" should be removed from the list
    And I should see only "Milk" and "Eggs"

  Scenario: Delete completed item
    Given I am logged in
    And I have a completed item "Milk"
    When I click delete on "Milk"
    Then "Milk" should be removed from the list

  Scenario: Delete persists to server
    Given I am logged in
    And I have item "Cheese"
    When I delete "Cheese"
    And I refresh the page
    Then "Cheese" should not be in my list

  Scenario: Delete last item
    Given I am logged in
    And I have only one item "Apple"
    When I delete "Apple"
    Then I should see "Your shopping list is empty"

  Scenario: Statistics update on delete
    Given I am logged in
    And I have 3 items with 1 completed
    When I delete the completed item
    Then total count should be 2
    And completed count should be 0

  Scenario: Delete with network failure
    Given I am logged in
    And the network is unavailable
    When I try to delete "Milk"
    Then the item should be removed visually (optimistic)
    But an error indicator should show
    When the network is restored
    Then the deletion should sync

  Scenario: Cannot delete non-existent item
    Given I am logged in
    When I try to delete an item that doesn't exist
    Then no error should occur
    And the list should remain unchanged
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "shopping-list", "dsdm"]
    },
    {
        "summary": "[COULD] FR-LIST-005: Clear All",
        "description": """## Description
Users can clear their entire shopping list with a single action.

## Acceptance Criteria
- [ ] DELETE /api/shopping-list endpoint available
- [ ] Endpoint requires authentication
- [ ] All items removed from user's list
- [ ] Other users' lists not affected
- [ ] Returns success response

## Non-Functional Requirements
- NFR-SEC-007: Must verify user owns the list
- NFR-PERF-005: Should complete within 500ms regardless of list size
- NFR-USE-008: Should require confirmation (future UI)

## Gherkin Scenarios

```gherkin
Feature: Clear All Shopping List Items
  As a user
  I want to clear my entire list
  So that I can start fresh

  Scenario: Clear list via API
    Given I am logged in
    And I have 10 items in my list
    When I call DELETE /api/shopping-list
    Then I should receive a 200 response
    And my list should be empty

  Scenario: Clear empty list
    Given I am logged in
    And I have no items in my list
    When I call DELETE /api/shopping-list
    Then I should receive a 200 response
    And no error should occur

  Scenario: Clear list requires authentication
    Given I am not logged in
    When I call DELETE /api/shopping-list
    Then I should receive a 401 response

  Scenario: Clear list doesn't affect other users
    Given user A has items "A1", "A2"
    And user B has items "B1", "B2"
    When user A clears their list
    Then user A's list should be empty
    And user B should still have "B1", "B2"

  Scenario: Clear list with confirmation (future)
    Given I am logged in
    And I have items in my list
    When I click "Clear All"
    Then I should see a confirmation dialog
    When I confirm
    Then all items should be deleted
```
""",
        "issue_type": "Story",
        "priority": "Medium",
        "labels": ["could-have", "shopping-list", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-LIST-006: Statistics Display",
        "description": """## Description
Display statistics showing total, completed, and remaining item counts.

## Acceptance Criteria
- [ ] Total count shows number of all items
- [ ] Completed count shows checked items
- [ ] Remaining count shows unchecked items
- [ ] Statistics update in real-time
- [ ] Statistics hidden when list is empty
- [ ] Format: "Total: X | Completed: Y | Remaining: Z"

## Non-Functional Requirements
- NFR-PERF-006: Statistics should update within 50ms of change
- NFR-USE-009: Statistics should be clearly readable
- NFR-ACC-002: Statistics should be accessible to screen readers

## Gherkin Scenarios

```gherkin
Feature: Shopping List Statistics
  As a user
  I want to see statistics about my list
  So that I can track my shopping progress

  Scenario: View statistics with mixed items
    Given I am logged in
    And I have 5 items with 2 completed
    When I view the shopping list
    Then I should see "Total: 5"
    And I should see "Completed: 2"
    And I should see "Remaining: 3"

  Scenario: Statistics update on add
    Given I am logged in
    And I have 3 items with 1 completed
    When I add a new item
    Then Total should change to 4
    And Remaining should change to 3

  Scenario: Statistics update on toggle
    Given I am logged in
    And I have 3 items with 1 completed
    When I complete another item
    Then Completed should change to 2
    And Remaining should change to 1

  Scenario: Statistics update on delete
    Given I am logged in
    And I have 3 items with 1 completed
    When I delete an uncompleted item
    Then Total should change to 2
    And Remaining should change to 1

  Scenario: Statistics hidden for empty list
    Given I am logged in
    And I have no items
    When I view the shopping list
    Then statistics should not be displayed

  Scenario: All items completed
    Given I am logged in
    And I have 3 items all completed
    Then I should see "Completed: 3"
    And I should see "Remaining: 0"
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "shopping-list", "ux", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-LIST-007: Empty State",
        "description": """## Description
Display a friendly message when the shopping list is empty.

## Acceptance Criteria
- [ ] Empty message displayed when no items exist
- [ ] Message text: "Your shopping list is empty"
- [ ] Message is centered in list area
- [ ] Message disappears when items are added
- [ ] Statistics not shown when empty

## Non-Functional Requirements
- NFR-USE-010: Message should be friendly and encouraging
- NFR-ACC-003: Empty state should be announced to screen readers

## Gherkin Scenarios

```gherkin
Feature: Empty List State
  As a user
  I want to see a helpful message when my list is empty
  So that I know the page loaded correctly

  Scenario: New user sees empty state
    Given I am logged in for the first time
    And I have no items
    When I view the shopping list
    Then I should see "Your shopping list is empty"

  Scenario: Empty state after deleting all items
    Given I am logged in
    And I have 1 item "Milk"
    When I delete "Milk"
    Then I should see "Your shopping list is empty"

  Scenario: Empty state disappears after adding item
    Given I am logged in
    And my list is empty
    And I see the empty state message
    When I add "Bread"
    Then I should not see "Your shopping list is empty"
    And I should see "Bread" in my list

  Scenario: Empty state styling
    Given I am logged in
    And my list is empty
    Then the empty message should be centered
    And the empty message should be styled in gray
    And the statistics should be hidden
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "shopping-list", "ux", "dsdm"]
    },

    # ============================================================================
    # UI REQUIREMENTS
    # ============================================================================
    {
        "summary": "[MUST] FR-UI-001: Responsive Design",
        "description": """## Description
Application works seamlessly on desktop and mobile browsers.

## Acceptance Criteria
- [ ] Layout adapts to screen sizes from 320px to 1920px+
- [ ] Touch targets are at least 44x44px on mobile
- [ ] Text is readable without zooming on mobile
- [ ] No horizontal scrolling on any device
- [ ] Input field and buttons remain usable on small screens
- [ ] Modal dialogs (if any) fit on mobile screens

## Non-Functional Requirements
- NFR-USE-011: Mobile-first design approach
- NFR-PERF-007: No layout shifts during load
- NFR-ACC-004: Viewport meta tag properly configured

## Gherkin Scenarios

```gherkin
Feature: Responsive Design
  As a user
  I want to use the app on any device
  So that I can manage my list anywhere

  Scenario: Mobile phone layout (320px)
    Given I am viewing on a 320px wide screen
    When I view the shopping list page
    Then all content should be visible
    And there should be no horizontal scroll
    And buttons should be easily tappable

  Scenario: Tablet layout (768px)
    Given I am viewing on a 768px wide screen
    When I view the shopping list page
    Then the layout should be comfortable
    And the container should be centered

  Scenario: Desktop layout (1200px)
    Given I am viewing on a 1200px wide screen
    When I view the shopping list page
    Then the container should have max-width of 500px
    And the container should be centered

  Scenario: Touch targets on mobile
    Given I am using a touch device
    When I view any button or interactive element
    Then it should be at least 44x44 pixels

  Scenario: Orientation change
    Given I am on a mobile device in portrait
    When I rotate to landscape
    Then the layout should adapt smoothly
    And no content should be cut off

  Scenario: Font size readability
    Given I am on a mobile device
    When I view the shopping list
    Then text should be at least 16px
    And I should not need to zoom to read
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["must-have", "ui", "responsive", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-UI-002: User Profile Display",
        "description": """## Description
Show logged-in user's name and profile picture in the header.

## Acceptance Criteria
- [ ] User's display name shown in header
- [ ] User's Google profile picture shown (40x40px)
- [ ] Fallback for missing profile picture
- [ ] Profile info positioned next to logout button
- [ ] Profile picture has circular styling
- [ ] Profile picture has border styling

## Non-Functional Requirements
- NFR-PERF-008: Profile picture should lazy load
- NFR-USE-012: Graceful fallback for missing images
- NFR-ACC-005: Alt text for profile picture

## Gherkin Scenarios

```gherkin
Feature: User Profile Display
  As a logged-in user
  I want to see my profile information
  So that I know which account I'm using

  Scenario: Display user profile with picture
    Given I am logged in with Google
    And my Google account has a profile picture
    When I view the shopping list page
    Then I should see my name in the header
    And I should see my profile picture
    And my profile picture should be circular

  Scenario: Display user profile without picture (dev mode)
    Given I am logged in via dev mode
    And I have no profile picture
    When I view the shopping list page
    Then I should see my name in the header
    And I should see a placeholder or no image

  Scenario: Profile picture loading
    Given I am logged in
    When the page loads
    Then my name should appear immediately
    And the profile picture should load asynchronously
    And there should be no layout shift when it loads

  Scenario: Long username display
    Given I am logged in as "Very Long Username That Could Break Layout"
    When I view the header
    Then the name should be displayed
    And it should not break the layout
    And it may be truncated if necessary
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "ui", "profile", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-UI-003: Visual Feedback",
        "description": """## Description
CSS animations and effects provide visual feedback for user actions.

## Acceptance Criteria
- [ ] New items slide in with animation
- [ ] Buttons have hover effects
- [ ] Buttons have active/pressed states
- [ ] List items have hover highlight
- [ ] Checkboxes have custom styling
- [ ] Transitions are smooth (0.2-0.3s)

## Non-Functional Requirements
- NFR-PERF-009: Animations should be GPU-accelerated
- NFR-USE-013: Respect prefers-reduced-motion setting
- NFR-ACC-006: Focus states clearly visible

## Gherkin Scenarios

```gherkin
Feature: Visual Feedback
  As a user
  I want visual feedback for my actions
  So that I know the app is responding

  Scenario: Add item animation
    Given I am logged in
    When I add an item to my list
    Then the item should slide in from the left
    And the animation should take about 0.3 seconds

  Scenario: Button hover effect
    Given I am viewing the shopping list
    When I hover over the "Add" button
    Then the button should lift slightly (transform)
    And the button should have a shadow effect

  Scenario: Button click effect
    Given I am viewing the shopping list
    When I click the "Add" button
    Then the button should press down visually
    And the effect should be immediate

  Scenario: Item hover highlight
    Given I am logged in with items
    When I hover over a list item
    Then the item background should change color
    And the transition should be smooth

  Scenario: Checkbox styling
    Given I am viewing a list item
    Then the checkbox should have custom purple accent
    And the checkbox should be larger than default (22px)

  Scenario: Reduced motion preference
    Given I have prefers-reduced-motion enabled
    When items are added or removed
    Then animations should be instant or disabled
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "ui", "animation", "dsdm"]
    },
    {
        "summary": "[SHOULD] FR-UI-004: Keyboard Support",
        "description": """## Description
Enter key submits new items for improved usability.

## Acceptance Criteria
- [ ] Enter key adds item when input is focused
- [ ] Tab navigates between interactive elements
- [ ] Focus is visible on all interactive elements
- [ ] Enter on buttons triggers action
- [ ] Escape clears input field (optional)

## Non-Functional Requirements
- NFR-ACC-007: Full keyboard navigation support
- NFR-USE-014: Logical tab order
- NFR-ACC-008: No keyboard traps

## Gherkin Scenarios

```gherkin
Feature: Keyboard Support
  As a user
  I want to use the keyboard to interact
  So that I can work efficiently

  Scenario: Enter key adds item
    Given I am logged in
    And the input field has focus
    When I type "Milk"
    And I press Enter
    Then "Milk" should be added to my list
    And the input should be cleared
    And the input should keep focus

  Scenario: Tab navigation
    Given I am on the shopping list page
    When I press Tab repeatedly
    Then focus should move through:
      | element        |
      | input field    |
      | Add button     |
      | first checkbox |
      | first delete   |
      | Logout button  |

  Scenario: Visible focus indicator
    Given I am using keyboard navigation
    When I tab to any interactive element
    Then that element should have a visible focus ring
    And the focus ring should have sufficient contrast

  Scenario: Enter on delete button
    Given I am logged in with items
    When I tab to a delete button
    And I press Enter
    Then that item should be deleted

  Scenario: Shift+Tab reverse navigation
    Given focus is on the Add button
    When I press Shift+Tab
    Then focus should move to the input field
```
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["should-have", "ui", "accessibility", "dsdm"]
    },

    # ============================================================================
    # NON-FUNCTIONAL REQUIREMENTS
    # ============================================================================
    {
        "summary": "[NFR] PERF-001: API Response Time < 200ms",
        "description": """## Description
All API endpoints should respond within 200ms under normal load.

## Acceptance Criteria
- [ ] GET /api/shopping-list responds in < 200ms
- [ ] POST /api/shopping-list responds in < 200ms
- [ ] DELETE /api/shopping-list responds in < 200ms
- [ ] Authentication endpoints respond in < 500ms
- [ ] Response times measured at 95th percentile

## Test Scenarios

```gherkin
Feature: API Performance
  As a user
  I want fast API responses
  So that the app feels responsive

  Scenario: GET shopping list performance
    Given I am logged in
    And I have 50 items in my list
    When I request GET /api/shopping-list
    Then the response should arrive within 200ms

  Scenario: POST shopping list performance
    Given I am logged in
    When I POST a new shopping list with 50 items
    Then the response should arrive within 200ms

  Scenario: Performance under load
    Given 100 concurrent users
    When all users request their shopping lists
    Then 95% of responses should be under 200ms
```

## Measurement Approach
- Use browser DevTools Network tab
- Implement server-side timing headers
- Monitor with APM tools in production
""",
        "issue_type": "Story",
        "priority": "High",
        "labels": ["non-functional", "performance", "dsdm"]
    },
    {
        "summary": "[NFR] SEC-001: OAuth 2.0 Implementation",
        "description": """## Description
Implement industry-standard OAuth 2.0 authentication with Google provider.

## Acceptance Criteria
- [ ] OAuth 2.0 Authorization Code flow implemented
- [ ] State parameter used for CSRF protection
- [ ] Tokens stored server-side only
- [ ] Refresh tokens handled securely
- [ ] Proper error handling for OAuth failures
- [ ] Secure callback URL validation

## Security Requirements
- Never expose access tokens to client
- Validate OAuth state parameter
- Use HTTPS for all OAuth endpoints
- Implement proper token expiry handling

## Test Scenarios

```gherkin
Feature: OAuth 2.0 Security
  As a security requirement
  OAuth implementation must follow best practices

  Scenario: State parameter validation
    Given I initiate OAuth login
    When the callback receives a different state
    Then authentication should fail
    And no session should be created

  Scenario: Token security
    Given I am logged in via OAuth
    When I inspect the browser storage
    Then I should not find any OAuth tokens
    And tokens should only exist server-side

  Scenario: HTTPS requirement
    Given I am in production environment
    When OAuth callback is triggered
    Then it must be over HTTPS
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["non-functional", "security", "oauth", "dsdm"]
    },
    {
        "summary": "[NFR] SEC-002: Session Security",
        "description": """## Description
Use HTTP-only session cookies with proper security flags.

## Acceptance Criteria
- [ ] Session cookies are HTTP-only
- [ ] Session cookies have Secure flag in production
- [ ] Session cookies have SameSite attribute
- [ ] Session secret is cryptographically random
- [ ] Session data not stored in cookie (server-side only)
- [ ] Session expiry is enforced

## Security Requirements
- Cookie flags: HttpOnly, Secure (prod), SameSite=Lax
- Session secret minimum 32 characters
- Session stored in server memory (or Redis in production)
- 24-hour session expiry

## Test Scenarios

```gherkin
Feature: Session Security
  As a security requirement
  Sessions must be secured properly

  Scenario: HTTP-only cookie
    Given I am logged in
    When I try to access cookies via JavaScript
    Then the session cookie should not be accessible

  Scenario: Secure flag in production
    Given I am in production environment
    When I inspect the session cookie
    Then it should have the Secure flag

  Scenario: Session expiry
    Given I logged in 25 hours ago
    When I try to access the API
    Then I should receive 401 Unauthorized
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["non-functional", "security", "session", "dsdm"]
    },

    # ============================================================================
    # TECHNICAL STORIES
    # ============================================================================
    {
        "summary": "[TECH] Set up Express.js server",
        "description": """## Description
Initialize Node.js project with Express.js framework and configure middleware.

## Acceptance Criteria
- [ ] Express.js server runs on configurable port
- [ ] CORS middleware configured for localhost
- [ ] JSON body parser middleware enabled
- [ ] Static file serving from root directory
- [ ] Error handling middleware in place
- [ ] Graceful shutdown handling

## Technical Requirements
- Node.js v18+ (v22 recommended)
- Express.js v4.18+
- Environment variables via dotenv
- PORT configurable (default 3000)

## Test Scenarios

```gherkin
Feature: Express Server Setup
  As a developer
  I need a properly configured server

  Scenario: Server starts successfully
    Given all dependencies are installed
    When I run "npm start"
    Then the server should start without errors
    And I should see "Server running on http://localhost:3000"

  Scenario: Static file serving
    Given the server is running
    When I request "/"
    Then I should receive index.html

  Scenario: CORS headers
    Given the server is running
    When I make a request from localhost:3000
    Then the request should succeed
    And CORS headers should be present
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["technical", "backend", "setup", "dsdm"]
    },
    {
        "summary": "[TECH] Implement Passport.js authentication",
        "description": """## Description
Configure Passport.js with Google OAuth 2.0 strategy.

## Acceptance Criteria
- [ ] Passport initialized with Express
- [ ] Google OAuth 2.0 strategy configured
- [ ] User serialization/deserialization implemented
- [ ] Session integration working
- [ ] Error handling for OAuth failures
- [ ] Development mode fallback

## Technical Requirements
- passport v0.7+
- passport-google-oauth20 v2+
- express-session v1.17+

## Test Scenarios

```gherkin
Feature: Passport Authentication
  As a developer
  I need OAuth authentication working

  Scenario: Passport initialization
    Given the server starts
    Then Passport should be initialized
    And session handling should be configured

  Scenario: Google strategy configuration
    Given Google OAuth credentials are set
    Then the Google strategy should be active
    And /auth/google should redirect to Google

  Scenario: User session persistence
    Given a user has authenticated
    Then their session should be serialized
    And subsequent requests should include user data
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["technical", "backend", "authentication", "dsdm"]
    },
    {
        "summary": "[TECH] Create REST API endpoints",
        "description": """## Description
Implement RESTful API endpoints for shopping list operations.

## Acceptance Criteria
- [ ] GET /api/shopping-list returns user's items
- [ ] POST /api/shopping-list saves user's items
- [ ] DELETE /api/shopping-list clears user's items
- [ ] All endpoints require authentication
- [ ] Proper HTTP status codes returned
- [ ] JSON request/response format

## API Specification

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /api/shopping-list | Yes | Get items |
| POST | /api/shopping-list | Yes | Save items |
| DELETE | /api/shopping-list | Yes | Clear items |

## Test Scenarios

```gherkin
Feature: REST API Endpoints
  As a frontend developer
  I need working API endpoints

  Scenario: GET returns user's items
    Given I am authenticated
    And I have items saved
    When I GET /api/shopping-list
    Then I should receive my items as JSON

  Scenario: POST saves items
    Given I am authenticated
    When I POST items to /api/shopping-list
    Then the items should be saved
    And I should receive a success response

  Scenario: Unauthenticated request
    Given I am not authenticated
    When I request any API endpoint
    Then I should receive 401 Unauthorized
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["technical", "backend", "api", "dsdm"]
    },
    {
        "summary": "[TECH] Build frontend SPA",
        "description": """## Description
Create shopping-list.html with vanilla JavaScript for item management.

## Acceptance Criteria
- [ ] Single HTML file with embedded CSS and JS
- [ ] Fetch API for server communication
- [ ] DOM manipulation for list rendering
- [ ] Event listeners for user interactions
- [ ] Auth state management
- [ ] Error handling and user feedback

## Technical Requirements
- Vanilla JavaScript (ES6+)
- Fetch API with credentials: 'include'
- CSS Grid/Flexbox for layout
- No external frameworks required

## Test Scenarios

```gherkin
Feature: Frontend SPA
  As a developer
  I need a working frontend application

  Scenario: Page loads and checks auth
    Given I visit shopping-list.html
    Then the page should check /auth/user
    And display appropriate content

  Scenario: Items render correctly
    Given I am authenticated with items
    Then all items should render in the DOM
    And each item should have checkbox and delete

  Scenario: User interactions work
    Given I am on the shopping list page
    When I add, toggle, or delete items
    Then the UI should update immediately
    And changes should persist to server
```
""",
        "issue_type": "Story",
        "priority": "Highest",
        "labels": ["technical", "frontend", "spa", "dsdm"]
    },
    {
        "summary": "[FUTURE] Replace in-memory storage with database",
        "description": """## Description
Replace Map-based storage with persistent database for production use.

## Acceptance Criteria
- [ ] Database connection management
- [ ] User data persists across server restarts
- [ ] Shopping list data properly indexed by user
- [ ] Migration from in-memory to database
- [ ] Connection pooling configured
- [ ] Error handling for database failures

## Technical Options
- MongoDB with Mongoose
- PostgreSQL with Prisma
- SQLite for simple deployment

## Future Scenarios

```gherkin
Feature: Database Storage
  As a production requirement
  Data must persist across restarts

  Scenario: Data survives server restart
    Given I have items in my list
    When the server restarts
    Then my items should still be available

  Scenario: Multi-server deployment
    Given multiple server instances
    When I save items on server A
    Then I should see them on server B

  Scenario: Database failure handling
    Given the database is unavailable
    When I try to access my list
    Then I should see a friendly error message
    And the app should not crash
```
""",
        "issue_type": "Story",
        "priority": "Low",
        "labels": ["future", "backend", "database", "dsdm"]
    },
]


def update_jira_stories():
    """Create new stories with full details."""
    client = get_jira_client()

    if not client.is_configured:
        print("ERROR: Jira not configured. Set environment variables:")
        print("  JIRA_BASE_URL, JIRA_USERNAME, JIRA_API_TOKEN")
        return []

    print(f"\nCreating {len(REQUIREMENTS)} Jira stories in project {JIRA_PROJECT}...")
    print("-" * 70)

    results = []

    for req in REQUIREMENTS:
        summary = req["summary"]

        try:
            # Create new story with full acceptance criteria
            issue = client.create_issue(
                project_key=JIRA_PROJECT,
                summary=summary,
                description=req["description"],
                issue_type=req["issue_type"],
                priority=req.get("priority"),
                labels=req.get("labels")
            )
            print(f"  Created: {issue['key']} - {summary[:50]}...")
            results.append({"key": issue["key"], "action": "created", "summary": summary})

        except Exception as e:
            print(f"  ERROR: {summary[:40]}... - {e}")
            results.append({"key": None, "action": "error", "summary": summary, "error": str(e)})

    print("-" * 70)

    # Summary
    created = sum(1 for r in results if r["action"] == "created")
    errors = sum(1 for r in results if r["action"] == "error")

    print(f"\nSummary: Created: {created}, Errors: {errors}")

    return results


def main():
    """Main entry point."""
    print("=" * 70)
    print("Shopping List - Update Jira Stories with Acceptance Criteria")
    print("=" * 70)

    results = update_jira_stories()

    print("\nDone!")

    # Print URLs for verification
    client = get_jira_client()
    if client.is_configured:
        print(f"\nView in Jira: {client.base_url}/browse/{JIRA_PROJECT}")


if __name__ == "__main__":
    main()
