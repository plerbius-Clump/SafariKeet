# SafaraKeet agent rules

These rules apply to every change under this directory.

## Non-negotiable privacy gate

Before any commit or push, inspect the complete staged diff and verify that it
contains no personally identifiable information or machine-specific data.
Reject the change if it contains any of the following:

- real names, email addresses, usernames, home-directory paths, or account IDs
- IP addresses, Tailscale node names, hostnames, device names, or network URLs
- API keys, tokens, cookies, passwords, private keys, or credentials
- real audio, transcripts, screenshots, logs, history databases, or recordings
- absolute paths beginning with `/`, `~`, a drive letter, or an environment
  variable that reveals a local machine location

Use only relative paths in documentation, examples, tests, logs, and generated
output. Use placeholders such as `<tailscale-ip>` and `<local-port>` where
connection details are needed.

## Push checklist

The coding agent must run a privacy-oriented staged-diff review before pushing:

1. Review `git diff --cached -- .`.
2. Search the staged content for secrets, emails, IP addresses, absolute paths,
   usernames, and private recordings.
3. Confirm local state files and audio are ignored and absent from the diff.
4. Confirm the README still describes local-only processing and does not imply
   that FluidVoice is controlled or exposed through an API.

If any check fails, stop and report the exact relative file and category. Do
not push until the issue is removed or explicitly resolved by the user.

## Scope for the staged groundwork

Do not scan the host for STT tools, install dependencies, configure Tailscale,
or implement the backend/frontend until the user starts the build session.

## Subagent use

For non-trivial work, use subagents for bounded, independent research or review
when that improves speed or confidence. Keep trivial edits and tightly sequential
work with the primary agent, and keep all subagents under the same privacy gate.
