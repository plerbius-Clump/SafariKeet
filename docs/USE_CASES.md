# Intended use cases

## Fast capture

Open the saved private web app, tap Record, see English appear while speaking,
copy a partial without stopping, then use Pause & save to make one durable text
block. Copy + new begins another block only after copying succeeds.

## Thought fragments

Each pause creates exactly one immutable history item. Starting another block
must not discard the prior text. The current result stays visible until copied,
archived, deleted, or replaced by an explicit new block.

## Review and reuse

Active history is chronological. Copy reuses text, Archive removes it from the
default view without destroying it, Restore returns it, and Delete requires an
explicit confirmation.

## Phone-over-SSH setup

A user can ask a local coding agent to run the scrubbed doctor, explain missing
capabilities, perform an approved model prefetch/build, install the local user
service, and verify the app without exposing machine identifiers in the repo or
chat.

## Failure expectations

- Microphone denial gives a direct Safari permission recovery message.
- Model warming is distinct from listening.
- An interrupted live session must never delete already saved history.
- Empty speech does not create a history item.
- A clipboard failure does not start another block.
- A second device must not appear to record successfully while the model is busy.

An optional, clearable recovery draft for interrupted unsaved partial text is a
future enhancement. It should use browser storage only for that draft; SQLite
remains the history source of truth.
