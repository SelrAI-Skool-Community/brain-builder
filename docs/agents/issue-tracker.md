# Issue Tracker

Issues for this repo are tracked in **Selr's Linear**, not GitHub Issues — GitHub is the public distribution surface only.

- **Team:** Core Builds
- **Project:** Claude Brains Kit
- **Access:** the Linear MCP tools (`mcp__linear__*`); create and update issues with `save_issue`
- **Blocking edges:** use Linear's native blocked-by relations (`blockedBy` on `save_issue`), never prose-only
- **Provenance:** link new build issues `relatedTo` CORE-121 (the closed planning map). Never modify or reopen CORE-121 or other closed planning issues (CORE-122…145)
- **Identifiers:** CORE-nnn; the v1 build tickets are CORE-146 through CORE-151

When a skill says "create an issue" or "publish tickets", it means a Linear issue in the team and project above, using the issue template from the invoking skill.
