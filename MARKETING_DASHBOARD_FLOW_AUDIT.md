# Marketing Dashboard Flow Audit

## Fixed Flow
1. Add/select business.
2. Generate content or generate all.
3. Content Studio loads saved business-specific library.
4. Dashboard home shows selected business, latest generated items, active media job counts, and next action.
5. Business detail shows quick actions (Generate, Generate Pack, View Library, Schedule), drafts, and learning insight notes.

## Empty State Contract
- Standard empty state now reads:
  - `No generated content yet. Choose a business and generate your first campaign.`

## Regression Guard
- Added `scripts/test_generated_content_visibility.sh` to verify generate -> fetch -> list -> pack -> delete lifecycle.
