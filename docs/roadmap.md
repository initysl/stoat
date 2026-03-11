# Stoat Roadmap

This roadmap reflects the current repository state rather than the original recovery plan.

## Current Status

### Complete

- Core command loop
- Rule-based parser and intent schema
- App launch and close
- File search
- Move, copy, delete, undo, and history
- Dry-run previews
- Initial system-info commands for disk, memory, and battery status
- Structured JSON output
- Diagnostics and structured logging

### In Progress

- Release hardening
- Documentation cleanup

### Not Started

- Broader post-MVP capabilities
- Optional LLM fallback as a product enhancement

## Next Milestones

## Phase A: Release Candidate

Goal: make `v0.1.0` credible and easy to install.

Exit criteria:
- Docs match the actual CLI behavior.
- Build and smoke-install checks pass consistently.
- Changelog and release workflow are in place.

## Phase B: Safe System Information Expansion

Goal: expand the current read-only system-info slice with broader Linux diagnostics.

Candidate commands:
- `stoat run "show disk usage"`
- `stoat run "what's using my ram"`
- `stoat run "battery status"`

Next additions:
- CPU usage
- network status
- process-list queries
- service-status queries

## Phase C: Search and Parser Growth

Goal: make file search feel more natural without giving up determinism.

Focus areas:
- more temporal phrases
- better path and location inference
- better file-type groupings
- clarification for ambiguous requests

## Phase D: Optional LLM Enhancement

Goal: improve long-tail natural-language understanding without making LLM support mandatory.

Constraints:
- Stoat must remain usable without any LLM
- rule parser stays the primary path
- all LLM output must still pass validation and safety checks
