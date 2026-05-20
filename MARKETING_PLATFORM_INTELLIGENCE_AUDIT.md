# Marketing Platform Intelligence Audit

## Platforms covered

- Instagram
- Facebook
- LinkedIn
- X/Twitter
- TikTok
- YouTube
- Reddit
- Pinterest

## Rules exposed

- Format preference
- Cadence guidance
- Hook style
- Caption/hashtag guidance
- Media requirements
- Compliance and terms guardrails
- Spam/automation risk rules
- Posting time windows
- Engagement/follower/customer tactics
- Prohibited claims/actions
- Human-review triggers

## Endpoints

- `GET /api/v1/platform-intelligence`
- `GET /api/v1/platform-intelligence/{platform}`
- `POST /api/v1/platform-intelligence/review-content`

Review endpoint returns:

- `platform_fit_score`
- `risks`
- `improvements`
- `terms_policy_warnings`
- `algorithm_fit_suggestions`
- `customer_conversion_suggestions`
- `follower_growth_suggestions`

Language is constrained to realistic expectations (optimize/increase likelihood), never guaranteed results.
