# Managed sign-in, verified onboarding and account recovery

Date: 2026-10-23. Status: accepted code design; provider activation is separate.

## Decision

Miyaar uses the existing managed identity provider, never a bypass, shared
password, locally assigned owner role, or invented successful registration.
Password sign-in remains. Password-free existing-account recovery and new-account
registration request a one-use email link using S256 PKCE. Google and Apple
buttons appear only when the provider's public settings report them enabled.
No provider settings, credentials or users are changed by shipping this code.

The operator must configure one exact HTTPS `/auth/callback` URL and allowlist
that URL at the provider. The browser additionally requires its own origin,
exact path and no query/fragment/credentials in that configured URL. OAuth state
is owned and verified by Supabase; the app's randomly generated verifier binds
the returned code to a locally initiated, ten-minute request. A new attempt
replaces the old one. The callback rejects absent/stale/mismatched bindings,
provider errors, repeated codes and implicit token fragments; it strips the
callback URL and consumes the binding before the exchange. An uncertain exchange
is never retried automatically. New attempts are explicit. This follows the
[Supabase PKCE flow](https://supabase.com/docs/guides/auth/sessions/pkce-flow).

Only an access token is stored, using the existing client-token storage policy;
no refresh token or password is persisted. The API must verify the token and
return managed identity before the application accepts sign-in. Existing
server-side tenant/owner checks remain the security boundary. Verified read-only
accounts see an access-pending screen and cannot create a session. Operators
assign an explicit subject the minimum role through a separately approved
security action. User metadata never supplies authorization.

## Delivery and activation limits

An email request is not proof of delivery, signup or login. The UI explicitly
says the visitor is not signed in yet, and exposes provider failures/rate limits.
[Supabase default SMTP](https://supabase.com/docs/guides/auth/auth-smtp) is
restricted to project-team addresses with low sending limits; general delivery
requires an existing approved SMTP configuration. No test email is sent by tests.
Google/Apple activation requires the correct OAuth client, secure credential
configuration and exact redirects. These remain separate security approvals.
Email link verification must occur in the initiating browser (a new tab works);
missing storage or another browser requires a fresh attempt.

## Performance tradeoff

Authentication and its bilingual copy remain in the lazy sign-in bundle, with
no new dependency. Obsolete initial-bundle sign-in messages were removed.
The measured initial JS is 99.3 KB gzip, still below the unchanged 100 KB cap.
Total lazy-inclusive JS increased from the 248 KB cap to approximately 250.3 KB.
The total cap is narrowly adjusted to 252 KB for the requested real managed
onboarding. The 30 KB largest chunk, all CSS/font limits, the dynamic-import
boundary and first-load cap remain enforced. This is a code-size allowance,
not a monetary/provider budget increase. Security checks were not reduced to
save bytes.

## Verification and release acceptance

Synthetic tests cover S256 generation, callback/redirect rejection, one-use
consumption, storage denial, expiry, provider errors, disabled signup/social
methods, identity rejection, permission-limited onboarding and sign-out races.
Existing backend tenant isolation tests remain required. Production acceptance
still requires real owner signup/recovery, a verified API identity, explicit
workspace authorization, isolation from another account, authenticated upload,
analysis, review/publish and a persistent worker restart. A rendered login page
or HTTP 200 is not acceptance. No live provider calls are part of the tests.
